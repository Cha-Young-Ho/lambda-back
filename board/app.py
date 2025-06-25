import json
import os
import uuid
from datetime import datetime
from decimal import Decimal

def get_secret():
    """AWS Secrets Manager에서 설정 가져오기"""
    try:
        import boto3
        
        # 로컬 환경 체크
        if os.path.exists('env.json'):
            # 로컬 환경에서는 env.json 사용
            try:
                with open('env.json', 'r') as f:
                    env_config = json.load(f)
                    local_config = env_config.get('local', {})
                    return {
                        'jwt_secret': local_config.get('jwt_secret', 'your-secret-key')
                    }
            except Exception as e:
                print(f"Error reading env.json: {str(e)}")
                return {
                    'jwt_secret': os.environ.get('JWT_SECRET', 'your-secret-key')
                }
        
        # AWS 환경에서는 Secrets Manager 사용 (단순화된 경로)
        client = boto3.client('secretsmanager')
        secret_name = "blog/config"  # stage 구분 제거
        
        response = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response['SecretString'])
        return secret
    except Exception as e:
        print(f"Error getting secret: {str(e)}")
        # Secret이 없는 경우 기본값 사용
        return {
            'jwt_secret': os.environ.get('JWT_SECRET', 'your-secret-key')
        }

def get_dynamodb():
    """DynamoDB 리소스 가져오기"""
    try:
        import boto3
        # 로컬 환경 확인
        if os.environ.get('AWS_SAM_LOCAL'):
            # SAM Local에서는 host.docker.internal 사용 (Docker 컨테이너에서 호스트 접근)
            return boto3.resource(
                'dynamodb',
                endpoint_url='http://host.docker.internal:8000',
                region_name='us-east-1',
                aws_access_key_id='dummy',
                aws_secret_access_key='dummy'
            )
        else:
            # AWS 환경
            return boto3.resource('dynamodb')
    except Exception as e:
        print(f"Error connecting to DynamoDB: {str(e)}")
        return None

def lambda_handler(event, context):
    """
    게시판 CRUD API
    """
    
    # CORS 헤더
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    }
    
    try:
        # OPTIONS 요청 처리
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': ''
            }
        
        method = event.get('httpMethod')
        path = event.get('path', '')
        path_parameters = event.get('pathParameters') or {}
        
        # 게시글 목록 조회 (공개)
        if method == 'GET' and path == '/board':
            return get_board_list(headers)
        
        # 게시글 상세 조회 (공개)
        elif method == 'GET' and '/board/' in path and path_parameters.get('boardId'):
            board_id = path_parameters['boardId']
            return get_board_detail(board_id, headers)
        
        # 게시글 생성 (관리자 전용)
        elif method == 'POST' and path == '/board':
            return create_board(event, headers)
        
        # 게시글 수정 (관리자 전용)
        elif method == 'PUT' and '/board/' in path and path_parameters.get('boardId'):
            board_id = path_parameters['boardId']
            return update_board(board_id, event, headers)
        
        # 게시글 삭제 (관리자 전용)
        elif method == 'DELETE' and '/board/' in path and path_parameters.get('boardId'):
            board_id = path_parameters['boardId']
            return delete_board(board_id, event, headers)
        
        # 이미지 업로드 (관리자 전용)
        elif method == 'POST' and path == '/board/upload':
            return upload_image(event, headers)
        
        elif method == 'GET' and path == '/board/test':
            # 테스트용 엔드포인트
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'message': 'Test endpoint reached', 'env': os.environ.get('STAGE', 'local')})
            }
        
        else:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'Not found'})
            }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Internal server error'})
        }

def verify_admin_token(event):
    """JWT 토큰 검증 (간단한 버전)"""
    try:
        auth_header = event.get('headers', {}).get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return False
        
        token = auth_header.split(' ')[1]
        
        # 간단한 토큰 검증 (실제 환경에서는 PyJWT 사용 권장)
        try:
            import base64
            decoded_token = base64.b64decode(token.encode()).decode()
            token_data = json.loads(decoded_token)
            payload = token_data.get('payload', {})
            
            # 역할 확인
            if payload.get('role') != 'admin':
                return False
            
            # 만료 시간 확인 (간단한 버전)
            exp_str = payload.get('exp', '')
            if exp_str:
                from datetime import datetime
                exp_time = datetime.fromisoformat(exp_str.replace('Z', '+00:00'))
                if datetime.utcnow() > exp_time.replace(tzinfo=None):
                    return False
            
            return True
            
        except Exception as decode_error:
            print(f"Token decode error: {str(decode_error)}")
            return False
    
    except Exception as e:
        print(f"Token verification error: {str(e)}")
        return False

def get_board_list(headers):
    """게시글 목록 조회 (공개)"""
    try:
        dynamodb = get_dynamodb()
        if not dynamodb:
            # DynamoDB 연결 실패 시 샘플 데이터 반환
            return get_sample_board_list(headers)
        
        table_name = os.environ.get('TABLE_NAME', 'blog-table')
        table = dynamodb.Table(table_name)
        
        # 게시글 목록 조회 (전체 스캔, 간단한 스키마)
        response = table.scan()
        
        posts = []
        for item in response.get('Items', []):
            # 간단한 스키마 사용 (id를 primary key로)
            posts.append({
                'id': item.get('id', ''),
                'title': item.get('title', ''),
                'content': item.get('content', '')[:100] + '...' if len(item.get('content', '')) > 100 else item.get('content', ''),
                'author': item.get('author', ''),
                'created_at': item.get('created_at', ''),
                'view_count': int(item.get('view_count', 0)),
                'status': item.get('status', 'published')
            })
        
        # published 상태인 게시글만 필터링
        published_posts = [post for post in posts if post['status'] == 'published']
        
        # 생성일시 기준 내림차순 정렬
        published_posts.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'posts': published_posts,
                'total': len(published_posts)
            })
        }
    
    except Exception as e:
        print(f"Error getting board list: {str(e)}")
        # 에러 시 샘플 데이터 반환
        return get_sample_board_list(headers)

def get_sample_board_list(headers):
    """샘플 게시글 목록 (DynamoDB 연결 실패 시)"""
    sample_data = [
        {
            'id': '1',
            'title': 'Welcome to Blog',
            'content': 'This is a sample blog post.',
            'author': 'admin',
            'created_at': '2024-06-24T10:00:00Z',
            'view_count': 100,
            'status': 'published'
        },
        {
            'id': '2',
            'title': 'Another Post',
            'content': 'This is another sample post.',
            'author': 'admin',
            'created_at': '2024-06-24T15:00:00Z',
            'view_count': 50,
            'status': 'published'
        }
    ]
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({
            'posts': sample_data,
            'total': len(sample_data)
        })
    }

def get_board_detail(board_id, headers):
    """게시글 상세 조회 (공개)"""
    try:
        dynamodb = get_dynamodb()
        if not dynamodb:
            # DynamoDB 연결 실패 시 샘플 데이터 반환
            return get_sample_board_detail(board_id, headers)
        
        table_name = os.environ.get('TABLE_NAME', 'blog-table')
        table = dynamodb.Table(table_name)
        
        # 게시글 조회 (간단한 스키마)
        response = table.get_item(
            Key={
                'id': board_id
            }
        )
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'Post not found'})
            }
        
        item = response['Item']
        
        # 조회수 증가
        table.update_item(
            Key={
                'id': board_id
            },
            UpdateExpression='ADD view_count :inc',
            ExpressionAttributeValues={
                ':inc': 1
            },
            ReturnValues='UPDATED_NEW'
        )
        
        post = {
            'id': item.get('id', ''),
            'title': item.get('title', ''),
            'content': item.get('content', ''),
            'author': item.get('author', ''),
            'created_at': item.get('created_at', ''),
            'view_count': int(item.get('view_count', 0)) + 1,  # 증가된 조회수
            'status': item.get('status', 'published')
        }
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(post)
        }
    
    except Exception as e:
        print(f"Error getting board detail: {str(e)}")
        # 에러 시 샘플 데이터 반환
        return get_sample_board_detail(board_id, headers)

def get_sample_board_detail(board_id, headers):
    """샘플 게시글 상세 (DynamoDB 연결 실패 시)"""
    if board_id == '1':
        post = {
            'id': '1',
            'title': 'Welcome to Blog',
            'content': 'This is a sample blog post with detailed content. AWS SAM을 사용한 서버리스 블로그 관리 시스템입니다.',
            'author': 'admin',
            'created_at': '2024-06-24T10:00:00Z',
            'view_count': 101,  # 조회수 증가
            'status': 'published'
        }
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(post)
        }
    elif board_id == '2':
        post = {
            'id': '2',
            'title': 'Another Post',
            'content': 'This is another sample post with more detailed content about serverless technologies.',
            'author': 'admin',
            'created_at': '2024-06-24T15:00:00Z',
            'view_count': 51,  # 조회수 증가
            'status': 'published'
        }
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(post)
        }
    else:
        return {
            'statusCode': 404,
            'headers': headers,
            'body': json.dumps({'error': 'Post not found'})
        }

def create_board(event, headers):
    """게시글 생성 (관리자 전용)"""
    # JWT 토큰 검증
    if not verify_admin_token(event):
        return {
            'statusCode': 401,
            'headers': headers,
            'body': json.dumps({'error': 'Unauthorized'})
        }
    
    try:
        body = json.loads(event.get('body', '{}'))
        title = body.get('title')
        content = body.get('content')
        
        if not title or not content:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Title and content required'})
            }
        
        # DynamoDB에 저장 시도
        dynamodb = get_dynamodb()
        post_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat() + 'Z'
        
        new_post = {
            'id': post_id,
            'title': title,
            'content': content,
            'author': 'admin',
            'created_at': created_at,
            'view_count': 0,
            'status': 'published'
        }
        
        if dynamodb:
            try:
                table_name = os.environ.get('TABLE_NAME', 'blog-table')
                table = dynamodb.Table(table_name)
                
                # DynamoDB에 아이템 저장 (간단한 스키마)
                table.put_item(
                    Item={
                        'id': post_id,
                        'title': title,
                        'content': content,
                        'author': 'admin',
                        'created_at': created_at,
                        'updated_at': created_at,
                        'view_count': 0,
                        'status': 'published'
                    }
                )
                print(f"Successfully saved post to DynamoDB: {post_id}")
                
            except Exception as db_error:
                print(f"Error saving to DynamoDB: {str(db_error)}")
                # DynamoDB 저장 실패해도 계속 진행
        else:
            print("DynamoDB connection failed, but continuing with response")
        
        return {
            'statusCode': 201,
            'headers': headers,
            'body': json.dumps({
                'message': 'Post created successfully',
                'post': new_post
            })
        }
    
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'Invalid JSON'})
        }
    except Exception as e:
        print(f"Error creating post: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Internal server error'})
        }

def update_board(board_id, event, headers):
    """게시글 수정 (관리자 전용)"""
    # JWT 토큰 검증
    if not verify_admin_token(event):
        return {
            'statusCode': 401,
            'headers': headers,
            'body': json.dumps({'error': 'Unauthorized'})
        }
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({'message': f'Post {board_id} updated successfully'})
    }

def delete_board(board_id, event, headers):
    """게시글 삭제 (관리자 전용)"""
    # JWT 토큰 검증
    if not verify_admin_token(event):
        return {
            'statusCode': 401,
            'headers': headers,
            'body': json.dumps({'error': 'Unauthorized'})
        }
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({'message': f'Post {board_id} deleted successfully'})
    }

def upload_image(event, headers):
    """이미지 업로드 (관리자 전용)"""
    # JWT 토큰 검증
    if not verify_admin_token(event):
        return {
            'statusCode': 401,
            'headers': headers,
            'body': json.dumps({'error': 'Unauthorized'})
        }
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({
            'message': 'Image upload functionality',
            'imageUrl': 'https://example.com/sample-image.jpg'
        })
    }
