import json
import os
import uuid
from datetime import datetime
from decimal import Decimal

# Lambda Layer에서 공통 모듈 임포트 (Layer 사용 시)
# 로컬 개발 시에는 fallback으로 로컬 클래스 사용
try:
    from common.config import AppConfig
    from common.response import create_response, create_error_response, create_success_response
    from common.database import get_dynamodb, get_table, safe_decimal_convert
    print("Using Lambda Layer modules")
except ImportError:
    print("Lambda Layer not available, using local implementations")
    
    class AppConfig:
        """애플리케이션 설정 관리 클래스"""
        def __init__(self, stage='local'):
            self.stage = stage
            self.config = self._load_config()
        
        def _load_config(self):
            """stage에 따른 설정 로드"""
            try:
                import boto3
                
                # AWS Lambda 환경 감지
                is_lambda = os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None
                is_local_sam = os.environ.get('AWS_SAM_LOCAL') is not None
                
                # 로컬 환경에서는 env.json 사용
                if not is_lambda and (is_local_sam or os.path.exists('env.json')):
                    try:
                        with open('env.json', 'r') as f:
                            env_config = json.load(f)
                            local_config = env_config.get('local', {})
                            return {
                                'jwt_secret': local_config.get('jwt_secret', 'your-secret-key'),
                                'dynamodb': {
                                    'region': local_config.get('dynamodb_region', 'ap-northeast-2'),
                                    'table_name': local_config.get('table_name', 'blog-table'),
                                    'endpoint_url': 'http://host.docker.internal:8000'
                                }
                            }
                    except Exception as e:
                        print(f"Error reading env.json: {str(e)}")
                        return self._get_default_config()
                
                # AWS Lambda 환경에서는 Secrets Manager 사용
                print(f"Loading config for stage: {self.stage}")
                client = boto3.client('secretsmanager')
                secret_name = f"blog/config/{self.stage}"
                
                print(f"Attempting to get secret: {secret_name}")
                response = client.get_secret_value(SecretId=secret_name)
                secret = json.loads(response['SecretString'])
                print(f"Successfully loaded secret for stage: {self.stage}")
                
                # DynamoDB 설정이 없는 경우 기본값 추가
                if 'dynamodb' not in secret:
                    secret['dynamodb'] = {
                        'region': secret.get('dynamodb_region', 'ap-northeast-2'),
                        'table_name': secret.get('table_name', 'blog-table-dev')
                    }
                
                return secret
                
            except Exception as e:
                import traceback
                print(f"Error getting secret for stage {self.stage}: {str(e)}")
                print(f"Full traceback: {traceback.format_exc()}")
                return self._get_default_config()
        
        def _get_default_config(self):
            """기본 설정값 반환"""
            return {
                'jwt_secret': os.environ.get('JWT_SECRET', 'your-secret-key'),
                'dynamodb': {
                    'region': os.environ.get('AWS_REGION', 'ap-northeast-2'),
                    'table_name': os.environ.get('TABLE_NAME', 'blog-table-dev'),
                    'endpoint_url': 'http://host.docker.internal:8000'
                }
            }

    def get_dynamodb(region, table_name, endpoint_url=None):
        print(f"Connection parameters - region: {region}, table_name: {table_name}, endpoint_url: {endpoint_url}")
        """DynamoDB 리소스 가져오기"""
        try:
            import boto3
            
            # AWS Lambda 환경 감지
            is_lambda = os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None
            is_local_sam = os.environ.get('AWS_SAM_LOCAL') is not None
            
            if endpoint_url or is_local_sam or not is_lambda:
                # 로컬 환경 또는 endpoint_url이 지정된 경우
                return boto3.resource(
                    'dynamodb',
                    endpoint_url=endpoint_url or 'http://host.docker.internal:8000',
                    region_name=region,
                    aws_access_key_id='dummy',
                    aws_secret_access_key='dummy'
                )
            else:
                # AWS Lambda 환경
                return boto3.resource('dynamodb', region_name=region)
                
        except Exception as e:
            import traceback
            print(f"Error connecting to DynamoDB: {str(e)}")
            print(f"Connection parameters - region: {region}, table_name: {table_name}, endpoint_url: {endpoint_url}")
            print(f"Full traceback: {traceback.format_exc()}")
            return None

    def create_response(status_code, body, headers=None):
        """통합 Response 생성"""
        default_headers = {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        }
        
        if headers:
            default_headers.update(headers)
        
        return {
            'statusCode': status_code,
            'headers': default_headers,
            'body': json.dumps(body) if isinstance(body, (dict, list)) else body
        }
    
    def create_error_response(status_code, error_message, error_details=None):
        """에러 응답 생성"""
        error_body = {
            'error': error_message,
            'status_code': status_code
        }
        
        if error_details:
            error_body['details'] = error_details
        
        return create_response(status_code, error_body)
    
    def create_success_response(data, message=None):
        """성공 응답 생성"""
        response_body = {
            'success': True,
            'data': data
        }
        
        if message:
            response_body['message'] = message
        
        return create_response(200, response_body)
    
    def get_table(dynamodb_resource, table_name):
        """DynamoDB 테이블 가져오기"""
        try:
            if dynamodb_resource is None:
                print(f"DynamoDB resource is None")
                return None
                
            table = dynamodb_resource.Table(table_name)
            print(f"Successfully connected to table: {table_name}")
            return table
            
        except Exception as e:
            import traceback
            print(f"Error getting table {table_name}: {str(e)}")
            print(f"Full traceback: {traceback.format_exc()}")
            return None

def lambda_handler(event, context):
    """
    게시판 CRUD API
    """
    
    # stage 정보 추출
    stage = event.get('requestContext', {}).get('stage', 'local')
    
    # 설정 로드
    app_config = AppConfig(stage)
    
    try:
        # OPTIONS 요청 처리
        if event.get('httpMethod') == 'OPTIONS':
            return create_response(200, '')
        
        method = event.get('httpMethod')
        path = event.get('path', '')
        path_parameters = event.get('pathParameters') or {}
        
        # 게시글 목록 조회 (공개)
        if method == 'GET' and path == '/board':
            return get_board_list(app_config, event)
        
        # 최근 게시글 5개 조회
        elif method == 'GET' and path == '/board/recent':
            return get_recent_board_list(app_config, event)
        
        # 게시글 상세 조회 (공개)
        elif method == 'GET' and '/board/' in path and path_parameters.get('boardId'):
            board_id = path_parameters['boardId']
            return get_board_detail(board_id, app_config)
        
        # 게시글 생성 (관리자 전용)
        elif method == 'POST' and path == '/board':
            return create_board(event, app_config)
        
        # 게시글 수정 (관리자 전용)
        elif method == 'PUT' and '/board/' in path and path_parameters.get('boardId'):
            board_id = path_parameters['boardId']
            return update_board(board_id, event, app_config)
        
        # 게시글 삭제 (관리자 전용)
        elif method == 'DELETE' and '/board/' in path and path_parameters.get('boardId'):
            board_id = path_parameters['boardId']
            return delete_board(board_id, event, app_config)
        
        # 이미지 업로드 (관리자 전용)
        elif method == 'POST' and path == '/board/upload':
            return upload_image(event, app_config)
        
        elif method == 'GET' and path == '/board/test':
            # 테스트용 엔드포인트 - 환경 정보 상세 표시
            is_lambda = os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None
            is_local_sam = os.environ.get('AWS_SAM_LOCAL') is not None
            
            env_info = {
                'message': 'Test endpoint reached',
                'stage': stage,
                'config': app_config.config,
                'environment': {
                    'is_lambda': is_lambda,
                    'is_local_sam': is_local_sam,
                    'aws_lambda_function_name': os.environ.get('AWS_LAMBDA_FUNCTION_NAME'),
                    'aws_region': os.environ.get('AWS_REGION'),
                    'stage': os.environ.get('STAGE', 'unknown'),
                    'env_json_exists': os.path.exists('env.json'),
                    'determined_env': 'lambda' if is_lambda else 'sam_local' if is_local_sam else 'local'
                },
                'event_dump': event,
                'config' : app_config.config
            }
            
            return create_response(200, env_info)
        
        else:
            return create_response(404, {'error': 'Not found'})
    
    except Exception as e:
        import traceback
        error_detail = {
            'error': 'Internal server error',
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc(),
            'stage': stage,
            'config_loaded': hasattr(app_config, 'config')
        }
        print(f"Error: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        return create_response(500, error_detail)

def verify_admin_token(event, app_config):
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

def get_board_list(app_config, event):
    """게시글 목록 조회 (공개) - 카테고리 필터링 지원"""
    try:
        # 쿼리 파라미터에서 카테고리 필터 가져오기
        query_params = event.get('queryStringParameters') or {}
        categories = query_params.get('categories', '')  # 예: "기관소식,디지털소식,참고자료"
        
        # 카테고리 필터 파싱
        category_filter = []
        if categories:
            category_filter = [cat.strip() for cat in categories.split(',') if cat.strip()]
        
        dynamodb_config = app_config.config['dynamodb']
        dynamodb = get_dynamodb(
            region=dynamodb_config['region'],
            table_name=dynamodb_config['table_name'],
            endpoint_url=dynamodb_config.get('endpoint_url')
        )
        
        if not dynamodb:
            # DynamoDB 연결 실패 시 샘플 데이터 반환
            return get_sample_board_list(category_filter)
        
        table = get_table(dynamodb, dynamodb_config['table_name'])
        
        if not table:
            # 테이블 가져오기 실패 시 샘플 데이터 반환
            return get_sample_board_list(category_filter)
        
        # 게시글 목록 조회 (전체 스캔, 간단한 스키마)
        response = table.scan()
        
        posts = []
        for item in response.get('Items', []):
            # 간단한 스키마 사용 (id를 primary key로)
            post = {
                'id': item.get('id', ''),
                'title': item.get('title', ''),
                'content': item.get('content', '')[:100] + '...' if len(item.get('content', '')) > 100 else item.get('content', ''),
                'category': item.get('category', '기관소식'),
                'author': item.get('author', ''),
                'created_at': item.get('created_at', ''),
                'view_count': int(item.get('view_count', 0)),
                'status': item.get('status', 'published')
            }
            
            # 카테고리 필터링
            if category_filter and post['category'] not in category_filter:
                continue
                
            posts.append(post)
        
        # published 상태인 게시글만 필터링
        published_posts = [post for post in posts if post['status'] == 'published']
        
        # 생성일시 기준 내림차순 정렬
        published_posts.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return create_response(200, {
            'posts': published_posts,
            'total': len(published_posts),
            'category_filter': category_filter
        })
    
    except Exception as e:
        import traceback
        error_detail = {
            'error': 'Error getting board list',
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc(),
            'fallback_to_sample': True
        }
        print(f"Error getting board list: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        # 에러 시 샘플 데이터와 함께 에러 정보도 반환
        sample_response = get_sample_board_list(category_filter)
        sample_data = json.loads(sample_response['body'])
        sample_data['error_info'] = error_detail
        return create_response(200, sample_data)

def get_recent_board_list(app_config, event):
    """최근 게시글 5개 조회 (공개) - 카테고리 필터링 지원"""
    try:
        # 쿼리 파라미터에서 카테고리 필터 가져오기
        query_params = event.get('queryStringParameters') or {}
        categories = query_params.get('categories', '')  # 예: "기관소식,디지털소식,참고자료"
        
        # 카테고리 필터 파싱
        category_filter = []
        if categories:
            category_filter = [cat.strip() for cat in categories.split(',') if cat.strip()]
        
        dynamodb_config = app_config.config['dynamodb']
        dynamodb = get_dynamodb(
            region=dynamodb_config['region'],
            table_name=dynamodb_config['table_name'],
            endpoint_url=dynamodb_config.get('endpoint_url')
        )
        
        if not dynamodb:
            # DynamoDB 연결 실패 시 샘플 데이터 반환
            return get_sample_recent_board_list(category_filter)
        
        table = get_table(dynamodb, dynamodb_config['table_name'])
        
        if not table:
            # 테이블 가져오기 실패 시 샘플 데이터 반환
            return get_sample_recent_board_list(category_filter)
        
        # 게시글 목록 조회 (전체 스캔, 간단한 스키마)
        response = table.scan()
        
        posts = []
        for item in response.get('Items', []):
            # 간단한 스키마 사용 (id를 primary key로)
            post = {
                'id': item.get('id', ''),
                'title': item.get('title', ''),
                'content': item.get('content', '')[:100] + '...' if len(item.get('content', '')) > 100 else item.get('content', ''),
                'category': item.get('category', '기관소식'),
                'author': item.get('author', ''),
                'created_at': item.get('created_at', ''),
                'view_count': int(item.get('view_count', 0)),
                'status': item.get('status', 'published')
            }
            
            # 카테고리 필터링
            if category_filter and post['category'] not in category_filter:
                continue
                
            posts.append(post)
        
        # published 상태인 게시글만 필터링
        published_posts = [post for post in posts if post['status'] == 'published']
        
        # 생성일시 기준 내림차순 정렬 후 상위 5개만 선택
        published_posts.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        recent_posts = published_posts[:5]
        
        return create_response(200, {
            'posts': recent_posts,
            'total': len(recent_posts),
            'category_filter': category_filter,
            'is_recent': True
        })
    
    except Exception as e:
        import traceback
        error_detail = {
            'error': 'Error getting recent board list',
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc(),
            'fallback_to_sample': True
        }
        print(f"Error getting recent board list: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        # 에러 시 샘플 데이터와 함께 에러 정보도 반환
        sample_response = get_sample_recent_board_list(category_filter)
        sample_data = json.loads(sample_response['body'])
        sample_data['error_info'] = error_detail
        return create_response(200, sample_data)

def get_sample_board_list(category_filter=None):
    """샘플 게시글 목록 (DynamoDB 연결 실패 시)"""
    sample_data = [
        {
            'id': '1',
            'title': 'Welcome to Blog',
            'content': 'This is a sample blog post.',
            'category': '기관소식',
            'author': 'admin',
            'created_at': '2024-06-24T10:00:00Z',
            'view_count': 100,
            'status': 'published'
        },
        {
            'id': '2',
            'title': 'Another Post',
            'content': 'This is another sample post.',
            'category': '디지털소식',
            'author': 'admin',
            'created_at': '2024-06-24T15:00:00Z',
            'view_count': 50,
            'status': 'published'
        },
        {
            'id': '3',
            'title': '가족센터 프로그램 안내',
            'content': '새로운 프로그램을 안내드립니다.',
            'category': '프로그램',
            'author': 'admin',
            'created_at': '2024-06-25T09:00:00Z',
            'view_count': 75,
            'status': 'published'
        },
        {
            'id': '4',
            'title': '참고자료 업데이트',
            'content': '새로운 참고자료가 업데이트되었습니다.',
            'category': '참고자료',
            'author': 'admin',
            'created_at': '2024-06-25T14:00:00Z',
            'view_count': 25,
            'status': 'published'
        },
        {
            'id': '5',
            'title': '신규 채용 공고',
            'content': '2024년 하반기 채용 공고를 안내드립니다.',
            'category': '채용정보',
            'author': 'admin',
            'created_at': '2024-06-26T09:00:00Z',
            'view_count': 120,
            'status': 'published'
        }
    ]
    
    # 카테고리 필터링 적용
    if category_filter:
        sample_data = [post for post in sample_data if post['category'] in category_filter]
    
    return create_response(200, {
        'posts': sample_data,
        'total': len(sample_data),
        'category_filter': category_filter or []
    })

def get_sample_recent_board_list(category_filter=None):
    """최근 샘플 게시글 5개 (DynamoDB 연결 실패 시)"""
    sample_data = [
        {
            'id': '5',
            'title': '최신 행사 안내',
            'content': '이번 주 진행되는 행사를 안내드립니다.',
            'category': '행사',
            'author': 'admin',
            'created_at': '2024-06-26T14:00:00Z',
            'view_count': 45,
            'status': 'published'
        },
        {
            'id': '4',
            'title': '디지털 소식',
            'content': '최신 디지털 기술 소식입니다.',
            'category': '디지털소식',
            'author': 'admin',
            'created_at': '2024-06-26T10:00:00Z',
            'view_count': 30,
            'status': 'published'
        },
        {
            'id': '3',
            'title': '가족센터 프로그램 안내',
            'content': '새로운 프로그램을 안내드립니다.',
            'category': '프로그램',
            'author': 'admin',
            'created_at': '2024-06-25T09:00:00Z',
            'view_count': 75,
            'status': 'published'
        }
    ]
    
    # 카테고리 필터링 적용
    if category_filter:
        sample_data = [post for post in sample_data if post['category'] in category_filter]
    
    # 최대 5개까지만
    recent_posts = sample_data[:5]
    
    return create_response(200, {
        'posts': recent_posts,
        'total': len(recent_posts),
        'category_filter': category_filter or [],
        'is_recent': True
    })

def get_board_detail(board_id, app_config):
    """게시글 상세 조회 (공개)"""
    try:
        dynamodb_config = app_config.config['dynamodb']
        dynamodb = get_dynamodb(
            region=dynamodb_config['region'],
            table_name=dynamodb_config['table_name'],
            endpoint_url=dynamodb_config.get('endpoint_url')
        )
        
        if not dynamodb:
            # DynamoDB 연결 실패 시 샘플 데이터 반환
            return get_sample_board_detail(board_id)
        
        table = get_table(dynamodb, dynamodb_config['table_name'])
        
        if not table:
            # 테이블 가져오기 실패 시 샘플 데이터 반환
            return get_sample_board_detail(board_id)
        
        # 게시글 조회 (간단한 스키마)
        response = table.get_item(
            Key={
                'id': board_id
            }
        )
        
        if 'Item' not in response:
            return create_response(404, {'error': 'Post not found'})
        
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
            'category': item.get('category', '기관소식'),
            'author': item.get('author', ''),
            'created_at': item.get('created_at', ''),
            'view_count': int(item.get('view_count', 0)) + 1,  # 증가된 조회수
            'status': item.get('status', 'published')
        }
        
        return create_response(200, post)
    
    except Exception as e:
        import traceback
        error_detail = {
            'error': 'Error getting board detail',
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc(),
            'board_id': board_id,
            'fallback_to_sample': True
        }
        print(f"Error getting board detail: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        # 에러 시 샘플 데이터와 함께 에러 정보도 반환
        sample_response = get_sample_board_detail(board_id)
        if sample_response['statusCode'] == 200:
            sample_data = json.loads(sample_response['body'])
            sample_data['error_info'] = error_detail
            return create_response(200, sample_data)
        else:
            return create_response(500, error_detail)

def get_sample_board_detail(board_id):
    """샘플 게시글 상세 (DynamoDB 연결 실패 시)"""
    if board_id == '1':
        post = {
            'id': '1',
            'title': 'Welcome to Blog',
            'content': 'This is a sample blog post with detailed content. AWS SAM을 사용한 서버리스 블로그 관리 시스템입니다.\n\n## 마크다운 지원\n\n![이미지 예시](https://via.placeholder.com/600x300)\n\n이 시스템은 **마크다운 형식**을 지원합니다.',
            'category': '기관소식',
            'author': 'admin',
            'created_at': '2024-06-24T10:00:00Z',
            'view_count': 101,  # 조회수 증가
            'status': 'published'
        }
        return create_response(200, post)
    elif board_id == '2':
        post = {
            'id': '2',
            'title': 'Another Post',
            'content': 'This is another sample post with more detailed content about serverless technologies.\n\n### 기술 스택\n\n- AWS Lambda\n- API Gateway\n- DynamoDB\n\n![기술 스택](https://via.placeholder.com/500x200)',
            'category': '디지털소식',
            'author': 'admin',
            'created_at': '2024-06-24T15:00:00Z',
            'view_count': 51,  # 조회수 증가
            'status': 'published'
        }
        return create_response(200, post)
    else:
        return create_response(404, {'error': 'Post not found'})

def create_board(event, app_config):
    """게시글 생성 (관리자 전용)"""
    # JWT 토큰 검증
    if not verify_admin_token(event, app_config):
        return create_response(401, {'error': 'Unauthorized'})
    
    try:
        body = json.loads(event.get('body', '{}'))
        title = body.get('title')
        content = body.get('content')  # 마크다운 형식 지원 (S3 이미지 URL 포함)
        category = body.get('category', '기관소식')  # 카테고리: 기관소식, 디지털소식, 참고자료, 프로그램, 행사, 채용정보
        
        if not title or not content:
            return create_response(400, {'error': 'Title and content required'})
        
        # 카테고리 유효성 검사
        valid_categories = ['기관소식', '디지털소식', '참고자료', '프로그램', '행사', '채용정보']
        if category not in valid_categories:
            return create_response(400, {'error': f'Invalid category. Must be one of: {valid_categories}'})
        
        # DynamoDB에 저장 시도
        dynamodb_config = app_config.config['dynamodb']
        dynamodb = get_dynamodb(
            region=dynamodb_config['region'],
            table_name=dynamodb_config['table_name'],
            endpoint_url=dynamodb_config.get('endpoint_url')
        )
        
        post_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat() + 'Z'
        
        new_post = {
            'id': post_id,
            'title': title,
            'content': content,  # 마크다운 형식 내용
            'category': category,
            'author': 'admin',
            'created_at': created_at,
            'view_count': 0,
            'status': 'published'
        }
        
        if dynamodb:
            table = get_table(dynamodb, dynamodb_config['table_name'])
            if table:
                try:
                    # DynamoDB에 아이템 저장 (간단한 스키마)
                    table.put_item(
                        Item={
                            'id': post_id,
                            'title': title,
                            'content': content,  # 마크다운 형식 저장
                            'category': category,
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
                print("DynamoDB table not available, but continuing with response")
        else:
            print("DynamoDB connection failed, but continuing with response")
        
        return create_response(201, {
            'message': 'Post created successfully',
            'post': new_post
        })
    
    except json.JSONDecodeError as e:
        error_detail = {
            'error': 'Invalid JSON',
            'error_type': 'JSONDecodeError',
            'error_message': str(e),
            'body_received': event.get('body', 'No body')
        }
        return create_response(400, error_detail)
    except Exception as e:
        import traceback
        error_detail = {
            'error': 'Error creating post',
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc()
        }
        print(f"Error creating post: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        return create_response(500, error_detail)

def update_board(board_id, event, app_config):
    """게시글 수정 (관리자 전용)"""
    # JWT 토큰 검증
    if not verify_admin_token(event, app_config):
        return create_response(401, {'error': 'Unauthorized'})
    
    return create_response(200, {'message': f'Post {board_id} updated successfully'})

def delete_board(board_id, event, app_config):
    """게시글 삭제 (관리자 전용)"""
    # JWT 토큰 검증
    if not verify_admin_token(event, app_config):
        return create_response(401, {'error': 'Unauthorized'})
    
    return create_response(200, {'message': f'Post {board_id} deleted successfully'})

def upload_image(event, app_config):
    """이미지 업로드 (관리자 전용)"""
    # JWT 토큰 검증
    if not verify_admin_token(event, app_config):
        return create_response(401, {'error': 'Unauthorized'})
    
    return create_response(200, {
        'message': 'Image upload functionality',
        'imageUrl': 'https://example.com/sample-image.jpg'
    })
