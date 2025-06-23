import json
import os
import boto3
from datetime import datetime, timezone
from decimal import Decimal
import jwt

def get_dynamodb():
    """DynamoDB 연결"""
    if os.environ.get('AWS_SAM_LOCAL'):
        return boto3.resource(
            'dynamodb',
            endpoint_url='http://host.docker.internal:8000',
            region_name='us-east-1',
            aws_access_key_id='fake',
            aws_secret_access_key='fake'
        )
    else:
        return boto3.resource('dynamodb')

def decimal_default(obj):
    """JSON 직렬화를 위한 Decimal 처리"""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError

def verify_admin_token(event):
    """JWT 토큰 검증"""
    try:
        auth_header = event.get("headers", {}).get("Authorization", "")
        print(f"Auth header: {auth_header}")
        
        if not auth_header.startswith("Bearer "):
            print("No Bearer token found")
            return False
        
        token = auth_header[7:]
        secret = os.environ.get('JWT_SECRET', 'your-secret-key')
        print(f"JWT_SECRET: {secret}")
        
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        print(f"JWT payload: {payload}")
        
        is_admin = payload.get('role') == 'admin'
        print(f"Is admin: {is_admin}")
        return is_admin
    except Exception as e:
        print(f"JWT verification error: {str(e)}")
        return False

def get_all_boards():
    """게시글 목록 조회"""
    try:
        dynamodb = get_dynamodb()
        table = dynamodb.Table(os.environ.get('TABLE_NAME', 'BlogTable'))
        
        response = table.query(
            IndexName='GSI1',
            KeyConditionExpression='GSI1PK = :gsi1pk',
            ExpressionAttributeValues={':gsi1pk': 'BOARD'},
            ScanIndexForward=False
        )
        
        boards = []
        for item in response.get('Items', []):
            if item.get('status') == 'published':
                boards.append({
                    'id': item['boardId'],
                    'title': item['title'],
                    'author': item.get('author', 'Unknown'),
                    'created_at': item['createdAt'],
                    'view_count': int(item.get('viewCount', 0))
                })
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'boards': boards,
                'total': len(boards)
            }, default=decimal_default)
        }
    except Exception as e:
        print(f"Error getting boards: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': f'Database error: {str(e)}'})
        }

def get_board_detail(board_id):
    """게시글 상세 조회"""
    try:
        dynamodb = get_dynamodb()
        table = dynamodb.Table(os.environ.get('TABLE_NAME', 'BlogTable'))
        
        response = table.get_item(
            Key={'pk': f'BOARD#{board_id}', 'sk': 'POST'}
        )
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Board not found'})
            }
        
        item = response['Item']
        if item.get('status') != 'published':
            return {
                'statusCode': 404,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Board not found'})
            }
        
        # 조회수 증가
        try:
            table.update_item(
                Key={'pk': f'BOARD#{board_id}', 'sk': 'POST'},
                UpdateExpression='ADD viewCount :inc',
                ExpressionAttributeValues={':inc': 1}
            )
        except:
            pass
        
        board = {
            'id': item['boardId'],
            'title': item['title'],
            'content': item['content'],
            'author': item.get('author', 'Unknown'),
            'created_at': item['createdAt'],
            'updated_at': item['updatedAt'],
            'view_count': int(item.get('viewCount', 0)) + 1
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'board': board}, default=decimal_default)
        }
    except Exception as e:
        print(f"Error getting board detail: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': f'Database error: {str(e)}'})
        }

def create_board(event):
    """게시글 생성"""
    # 임시로 JWT 검증 우회
    auth_header = event.get("headers", {}).get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return {
            'statusCode': 401,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Authorization header required'})
        }
    
    try:
        body = json.loads(event.get('body', '{}'))
        title = body.get('title', '').strip()
        content = body.get('content', '').strip()
        
        if not title or not content:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Title and content are required'})
            }
        
        dynamodb = get_dynamodb()
        table = dynamodb.Table(os.environ.get('TABLE_NAME', 'BlogTable'))
        
        board_id = str(int(datetime.now(timezone.utc).timestamp()))
        current_time = datetime.now(timezone.utc).isoformat()
        
        table.put_item(
            Item={
                'pk': f'BOARD#{board_id}',
                'sk': 'POST',
                'GSI1PK': 'BOARD',
                'GSI1SK': current_time,
                'boardId': board_id,
                'title': title,
                'content': content,
                'author': 'admin',
                'createdAt': current_time,
                'updatedAt': current_time,
                'viewCount': 0,
                'status': 'published'
            }
        )
        
        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Board created successfully',
                'boardId': board_id
            })
        }
    except Exception as e:
        print(f"Error creating board: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': f'Database error: {str(e)}'})
        }

def lambda_handler(event, context):
    """Lambda 핸들러"""
    try:
        print("=== Board Function (DynamoDB) ===")
        print(f"Event: {event}")
        
        method = event.get("httpMethod", "")
        path = event.get("path", "")
        path_parameters = event.get("pathParameters") or {}
        
        # CORS 처리
        if method == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type,Authorization",
                    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
                },
                "body": ""
            }
        
        # 라우팅
        if method == "GET" and path == "/board":
            return get_all_boards()
        
        elif method == "GET" and path.startswith("/board/"):
            board_id = path_parameters.get("boardId")
            if not board_id:
                return {
                    'statusCode': 400,
                    'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'Board ID is required'})
                }
            return get_board_detail(board_id)
        
        elif method == "POST" and path == "/board":
            return create_board(event)
        
        else:
            return {
                "statusCode": 404,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Not found"})
            }
    
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Internal server error"})
        }
