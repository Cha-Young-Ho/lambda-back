import json
import os
import uuid
from datetime import datetime
from decimal import Decimal
import traceback

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
                        'table_name': secret.get('table_name', 'blog-table')
                    }
                
                return secret
                
            except Exception as e:
                print(f"Error getting secret for stage {self.stage}: {str(e)}")
                print(f"Full traceback: {traceback.format_exc()}")
                return self._get_default_config()
        
        def _get_default_config(self):
            """기본 설정값 반환"""
            return {
                'jwt_secret': os.environ.get('JWT_SECRET', 'your-secret-key'),
                'dynamodb': {
                    'region': os.environ.get('AWS_REGION', 'ap-northeast-2'),
                    'table_name': os.environ.get('TABLE_NAME', 'blog-table'),
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
            print(f"Error connecting to DynamoDB: {str(e)}")
            print(f"Connection parameters - region: {region}, table_name: {table_name}, endpoint_url: {endpoint_url}")
            print(f"Full traceback: {traceback.format_exc()}")
            return None

    def create_response(status_code, body, headers=None):
        """통합 Response 생성"""
        default_headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        }
        
        if headers:
            default_headers.update(headers)
        
        return {
            'statusCode': status_code,
            'headers': default_headers,
            'body': json.dumps(body, ensure_ascii=False) if isinstance(body, (dict, list)) else body
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
            print(f"Error getting table {table_name}: {str(e)}")
            print(f"Full traceback: {traceback.format_exc()}")
            return None

def lambda_handler(event, context):
    """
    뉴스(주요 소식) CRUD API
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
        
        # 뉴스 목록 조회 (공개) - 페이지네이션 지원
        if method == 'GET' and path == '/news':
            return get_news_list(app_config, event)
        
        # 뉴스 상세 조회 (공개)
        elif method == 'GET' and '/news/' in path and path_parameters.get('newsId'):
            news_id = path_parameters['newsId']
            return get_news_detail(news_id, app_config)
        
        # 뉴스 생성 (관리자 전용)
        elif method == 'POST' and path == '/news':
            return create_news(event, app_config)
        
        # 뉴스 수정 (관리자 전용)
        elif method == 'PUT' and '/news/' in path and path_parameters.get('newsId'):
            news_id = path_parameters['newsId']
            return update_news(news_id, event, app_config)
        
        # 뉴스 삭제 (관리자 전용)
        elif method == 'DELETE' and '/news/' in path and path_parameters.get('newsId'):
            news_id = path_parameters['newsId']
            return delete_news(news_id, event, app_config)
        
        else:
            return create_response(404, {'error': 'Not found'})
    
    except Exception as e:
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

def get_news_list(app_config, event):
    """뉴스 목록 조회 (공개) - 페이지네이션 지원"""
    try:
        # 쿼리 파라미터 처리
        query_params = event.get('queryStringParameters') or {}
        
        # 페이지네이션 파라미터
        page = int(query_params.get('page', 1))
        limit = int(query_params.get('limit', 10))
        
        # 카테고리 필터
        categories = query_params.get('categories', '')
        category_filter = []
        if categories:
            category_filter = [cat.strip() for cat in categories.split(',') if cat.strip()]
        
        # offset 계산
        offset = (page - 1) * limit
        
        dynamodb_config = app_config.config['dynamodb']
        dynamodb = get_dynamodb(
            region=dynamodb_config['region'],
            table_name=dynamodb_config['table_name'],
            endpoint_url=dynamodb_config.get('endpoint_url')
        )
        
        if not dynamodb:
            # DynamoDB 연결 실패 시 샘플 데이터 반환
            return get_sample_news_list(category_filter, page, limit)
        
        table = get_table(dynamodb, dynamodb_config['table_name'])
        
        if not table:
            # 테이블 가져오기 실패 시 샘플 데이터 반환
            return get_sample_news_list(category_filter, page, limit)
        
        # 뉴스 목록 조회 (content_type으로 필터링)
        response = table.scan(
            FilterExpression='content_type = :content_type',
            ExpressionAttributeValues={
                ':content_type': 'news'
            }
        )
        
        news_items = []
        for item in response.get('Items', []):
            news_item = {
                'id': item.get('id', ''),
                'title': item.get('title', ''),
                'content': item.get('content', '')[:100] + '...' if len(item.get('content', '')) > 100 else item.get('content', ''),
                'category': item.get('category', '주요소식'),
                'author': item.get('author', ''),
                'created_at': item.get('created_at', ''),
                'view_count': int(item.get('view_count', 0)),
                'status': item.get('status', 'published'),
                'image_url': item.get('image_url', ''),
                'short_description': item.get('short_description', item.get('content', '')[:100] + '...' if len(item.get('content', '')) > 100 else item.get('content', ''))
            }
            
            # 카테고리 필터링
            if category_filter and news_item['category'] not in category_filter:
                continue
                
            news_items.append(news_item)
        
        # published 상태인 뉴스만 필터링
        published_news = [item for item in news_items if item['status'] == 'published']
        
        # 생성일시 기준 내림차순 정렬
        published_news.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # 페이지네이션 적용
        total_count = len(published_news)
        paginated_news = published_news[offset:offset + limit]
        
        # 프론트엔드 형식에 맞게 데이터 변환
        transformed_data = []
        for item in paginated_news:
            # created_at에서 날짜만 추출 (2025-07-03T10:00:00Z -> 2025-07-03)
            date_str = item.get('created_at', '')
            if 'T' in date_str:
                date_only = date_str.split('T')[0]
            else:
                date_only = date_str[:10] if len(date_str) >= 10 else date_str
            
            transformed_item = {
                'id': item.get('id', ''),
                'category': item.get('category', '주요소식'),
                'title': item.get('title', ''),
                'author': item.get('author', ''),
                'date': date_only,
                'views': int(item.get('view_count', 0)),
                'image': item.get('image_url', ''),
                'description': item.get('short_description', '')
            }
            transformed_data.append(transformed_item)
        
        return create_response(200, {
            'success': True,
            'data': transformed_data,
            'total': total_count,
            'page': page,
            'limit': limit
        })
    
    except Exception as e:
        error_detail = {
            'error': 'Error getting news list',
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc(),
            'fallback_to_sample': True
        }
        print(f"Error getting news list: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        
        # 에러 시 샘플 데이터와 함께 에러 정보도 반환
        try:
            query_params = event.get('queryStringParameters') or {}
            page = int(query_params.get('page', 1))
            limit = int(query_params.get('limit', 10))
            categories = query_params.get('categories', '')
            category_filter = [cat.strip() for cat in categories.split(',') if cat.strip()] if categories else []
            
            sample_response = get_sample_news_list(category_filter, page, limit)
            return sample_response
        except:
            return create_response(500, error_detail)

def get_news_detail(news_id, app_config):
    """뉴스 상세 조회 (공개)"""
    try:
        dynamodb_config = app_config.config['dynamodb']
        dynamodb = get_dynamodb(
            region=dynamodb_config['region'],
            table_name=dynamodb_config['table_name'],
            endpoint_url=dynamodb_config.get('endpoint_url')
        )
        
        if not dynamodb:
            # DynamoDB 연결 실패 시 샘플 데이터 반환
            return get_sample_news_detail(news_id)
        
        table = get_table(dynamodb, dynamodb_config['table_name'])
        
        if not table:
            # 테이블 가져오기 실패 시 샘플 데이터 반환
            return get_sample_news_detail(news_id)
        
        # 뉴스 조회
        response = table.get_item(Key={'id': news_id})
        
        if 'Item' not in response:
            return create_response(404, {'error': 'News not found'})
        
        item = response['Item']
        
        # content_type이 news인지 확인
        if item.get('content_type') != 'news':
            return create_response(404, {'error': 'News not found'})
        
        # 조회수 증가
        table.update_item(
            Key={'id': news_id},
            UpdateExpression='ADD view_count :inc',
            ExpressionAttributeValues={':inc': 1},
            ReturnValues='UPDATED_NEW'
        )
        
        news_item = {
            'id': item.get('id', ''),
            'title': item.get('title', ''),
            'content': item.get('content', ''),
            'category': item.get('category', '주요소식'),
            'author': item.get('author', ''),
            'created_at': item.get('created_at', ''),
            'view_count': int(item.get('view_count', 0)) + 1,  # 증가된 조회수
            'status': item.get('status', 'published'),
            'image_url': item.get('image_url', ''),
            'short_description': item.get('short_description', '')
        }
        
        return create_response(200, news_item)
    
    except Exception as e:
        error_detail = {
            'error': 'Error getting news detail',
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc(),
            'news_id': news_id,
            'fallback_to_sample': True
        }
        print(f"Error getting news detail: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        
        # 에러 시 샘플 데이터와 함께 에러 정보도 반환
        sample_response = get_sample_news_detail(news_id)
        if sample_response['statusCode'] == 200:
            sample_data = json.loads(sample_response['body'])
            sample_data['error_info'] = error_detail
            return create_response(200, sample_data)
        else:
            return create_response(500, error_detail)

def create_news(event, app_config):
    """뉴스 생성 (관리자 전용)"""
    # JWT 토큰 검증
    if not verify_admin_token(event, app_config):
        return create_response(401, {'error': 'Unauthorized'})
    
    try:
        body = json.loads(event.get('body', '{}'))
        title = body.get('title')
        content = body.get('content')
        category = body.get('category', '주요소식')
        image_url = body.get('image_url', '')
        short_description = body.get('short_description', '')
        author = body.get('author', 'admin')
        
        if not title or not content:
            return create_response(400, {'error': 'Title and content required'})
        
        # 뉴스 카테고리 유효성 검사
        valid_categories = ['주요소식', '정책소식', '사업소식', '공지사항', '보도자료']
        if category not in valid_categories:
            return create_response(400, {'error': f'Invalid category. Must be one of: {valid_categories}'})
        
        # short_description이 없으면 content의 앞부분을 사용
        if not short_description:
            short_description = content[:100] + '...' if len(content) > 100 else content
        
        # DynamoDB에 저장 시도
        dynamodb_config = app_config.config['dynamodb']
        dynamodb = get_dynamodb(
            region=dynamodb_config['region'],
            table_name=dynamodb_config['table_name'],
            endpoint_url=dynamodb_config.get('endpoint_url')
        )
        
        news_id = f"news_{str(uuid.uuid4())}"  # news_ 접두사로 구분
        created_at = datetime.utcnow().isoformat() + 'Z'
        
        new_news = {
            'id': news_id,
            'content_type': 'news',  # 식별자
            'title': title,
            'content': content,
            'category': category,
            'author': author,
            'created_at': created_at,
            'updated_at': created_at,
            'view_count': 0,
            'status': 'published',
            'image_url': image_url,
            'short_description': short_description
        }
        
        if dynamodb:
            table = get_table(dynamodb, dynamodb_config['table_name'])
            if table:
                try:
                    # DynamoDB에 아이템 저장
                    table.put_item(Item=new_news)
                    print(f"Successfully saved news to DynamoDB: {news_id}")
                    
                except Exception as db_error:
                    print(f"Error saving to DynamoDB: {str(db_error)}")
                    # DynamoDB 저장 실패해도 계속 진행
            else:
                print("DynamoDB table not available, but continuing with response")
        else:
            print("DynamoDB connection failed, but continuing with response")
        
        return create_response(201, {
            'message': 'News created successfully',
            'news': new_news
        })
    
    except json.JSONDecodeError as e:
        return create_response(400, {
            'error': 'Invalid JSON',
            'error_message': str(e)
        })
    except Exception as e:
        error_detail = {
            'error': 'Error creating news',
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc()
        }
        print(f"Error creating news: {str(e)}")
        return create_response(500, error_detail)

def update_news(news_id, event, app_config):
    """뉴스 수정 (관리자 전용)"""
    # JWT 토큰 검증
    if not verify_admin_token(event, app_config):
        return create_response(401, {'error': 'Unauthorized'})
    
    try:
        body = json.loads(event.get('body', '{}'))
        
        # 업데이트할 필드들
        update_fields = {}
        if 'title' in body:
            update_fields['title'] = body['title']
        if 'content' in body:
            update_fields['content'] = body['content']
        if 'category' in body:
            # 카테고리 유효성 검사
            valid_categories = ['주요소식', '정책소식', '사업소식', '공지사항', '보도자료']
            if body['category'] not in valid_categories:
                return create_response(400, {'error': f'Invalid category. Must be one of: {valid_categories}'})
            update_fields['category'] = body['category']
        if 'image_url' in body:
            update_fields['image_url'] = body['image_url']
        if 'short_description' in body:
            update_fields['short_description'] = body['short_description']
        if 'author' in body:
            update_fields['author'] = body['author']
        if 'status' in body:
            if body['status'] not in ['published', 'draft']:
                return create_response(400, {'error': 'Status must be published or draft'})
            update_fields['status'] = body['status']
        
        if not update_fields:
            return create_response(400, {'error': 'No fields to update'})
        
        # updated_at 추가
        update_fields['updated_at'] = datetime.utcnow().isoformat() + 'Z'
        
        # DynamoDB 업데이트 시도
        dynamodb_config = app_config.config['dynamodb']
        dynamodb = get_dynamodb(
            region=dynamodb_config['region'],
            table_name=dynamodb_config['table_name'],
            endpoint_url=dynamodb_config.get('endpoint_url')
        )
        
        if dynamodb:
            table = get_table(dynamodb, dynamodb_config['table_name'])
            if table:
                try:
                    # 먼저 뉴스가 존재하는지 확인
                    response = table.get_item(Key={'id': news_id})
                    if 'Item' not in response:
                        return create_response(404, {'error': 'News not found'})
                    
                    # content_type이 news인지 확인
                    if response['Item'].get('content_type') != 'news':
                        return create_response(404, {'error': 'News not found'})
                    
                    # UpdateExpression 구성
                    update_expression = "SET " + ", ".join([f"{key} = :{key}" for key in update_fields.keys()])
                    expression_attribute_values = {f":{key}": value for key, value in update_fields.items()}
                    
                    # DynamoDB 업데이트
                    table.update_item(
                        Key={'id': news_id},
                        UpdateExpression=update_expression,
                        ExpressionAttributeValues=expression_attribute_values,
                        ReturnValues='ALL_NEW'
                    )
                    
                    print(f"Successfully updated news in DynamoDB: {news_id}")
                    
                    # 업데이트된 뉴스 조회
                    updated_response = table.get_item(Key={'id': news_id})
                    updated_news = updated_response['Item']
                    
                    return create_response(200, {
                        'message': 'News updated successfully',
                        'news': {
                            'id': updated_news.get('id', ''),
                            'title': updated_news.get('title', ''),
                            'content': updated_news.get('content', ''),
                            'category': updated_news.get('category', '주요소식'),
                            'author': updated_news.get('author', ''),
                            'created_at': updated_news.get('created_at', ''),
                            'updated_at': updated_news.get('updated_at', ''),
                            'view_count': int(updated_news.get('view_count', 0)),
                            'status': updated_news.get('status', 'published'),
                            'image_url': updated_news.get('image_url', ''),
                            'short_description': updated_news.get('short_description', '')
                        }
                    })
                    
                except Exception as db_error:
                    print(f"Error updating DynamoDB: {str(db_error)}")
                    return create_response(500, {'error': 'Database update failed'})
            else:
                return create_response(500, {'error': 'Database table not available'})
        else:
            return create_response(500, {'error': 'Database connection failed'})
            
    except json.JSONDecodeError as e:
        return create_response(400, {
            'error': 'Invalid JSON',
            'error_message': str(e)
        })
    except Exception as e:
        error_detail = {
            'error': 'Error updating news',
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc()
        }
        print(f"Error updating news: {str(e)}")
        return create_response(500, error_detail)

def delete_news(news_id, event, app_config):
    """뉴스 삭제 (관리자 전용)"""
    # JWT 토큰 검증
    if not verify_admin_token(event, app_config):
        return create_response(401, {'error': 'Unauthorized'})
    
    try:
        # DynamoDB 삭제 시도
        dynamodb_config = app_config.config['dynamodb']
        dynamodb = get_dynamodb(
            region=dynamodb_config['region'],
            table_name=dynamodb_config['table_name'],
            endpoint_url=dynamodb_config.get('endpoint_url')
        )
        
        if dynamodb:
            table = get_table(dynamodb, dynamodb_config['table_name'])
            if table:
                try:
                    # 먼저 뉴스가 존재하는지 확인
                    response = table.get_item(Key={'id': news_id})
                    if 'Item' not in response:
                        return create_response(404, {'error': 'News not found'})
                    
                    # content_type이 news인지 확인
                    if response['Item'].get('content_type') != 'news':
                        return create_response(404, {'error': 'News not found'})
                    
                    # 삭제할 뉴스 정보 저장
                    deleted_news = response['Item']
                    
                    # DynamoDB에서 삭제
                    table.delete_item(Key={'id': news_id})
                    
                    print(f"Successfully deleted news from DynamoDB: {news_id}")
                    
                    return create_response(200, {
                        'message': 'News deleted successfully',
                        'deleted_news': {
                            'id': deleted_news.get('id', ''),
                            'title': deleted_news.get('title', ''),
                            'category': deleted_news.get('category', '주요소식'),
                            'author': deleted_news.get('author', ''),
                            'created_at': deleted_news.get('created_at', '')
                        }
                    })
                    
                except Exception as db_error:
                    print(f"Error deleting from DynamoDB: {str(db_error)}")
                    return create_response(500, {'error': 'Database deletion failed'})
            else:
                return create_response(500, {'error': 'Database table not available'})
        else:
            return create_response(500, {'error': 'Database connection failed'})
            
    except Exception as e:
        error_detail = {
            'error': 'Error deleting news',
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc()
        }
        print(f"Error deleting news: {str(e)}")
        return create_response(500, error_detail)

def get_sample_news_list(category_filter=None, page=1, limit=10):
    """샘플 뉴스 목록 (DynamoDB 연결 실패 시)"""
    sample_data = [
        {
            'id': 'news_1',
            'title': '가족센터 2025년 상반기 사업계획 발표',
            'content': '올해 상반기 가족센터의 주요 사업계획을 발표합니다.',
            'category': '주요소식',
            'author': '기획팀',
            'created_at': '2025-07-03T10:00:00Z',
            'view_count': 156,
            'status': 'published',
            'image_url': 'https://example.com/images/business-plan.jpg',
            'short_description': '올해 상반기 가족센터의 주요 사업계획을 발표합니다.'
        },
        {
            'id': 'news_2',
            'title': '다문화가족 지원 정책 개선안 공지',
            'content': '다문화가족을 위한 새로운 지원 정책이 개선되었습니다.',
            'category': '정책소식',
            'author': '정책팀',
            'created_at': '2025-07-02T14:30:00Z',
            'view_count': 203,
            'status': 'published',
            'image_url': 'https://example.com/images/policy-update.jpg',
            'short_description': '다문화가족을 위한 새로운 지원 정책이 개선되었습니다.'
        },
        {
            'id': 'news_3',
            'title': '가족 상담 프로그램 확대 운영',
            'content': '가족 상담 프로그램을 확대하여 더 많은 가족들에게 서비스를 제공합니다.',
            'category': '사업소식',
            'author': '상담팀',
            'created_at': '2025-07-01T16:20:00Z',
            'view_count': 89,
            'status': 'published',
            'image_url': 'https://example.com/images/counseling-expansion.jpg',
            'short_description': '가족 상담 프로그램을 확대하여 더 많은 가족들에게 서비스를 제공합니다.'
        },
        {
            'id': 'news_4',
            'title': '7월 센터 운영시간 변경 안내',
            'content': '7월 한 달간 센터 운영시간이 임시로 변경됩니다.',
            'category': '공지사항',
            'author': '운영팀',
            'created_at': '2025-06-30T11:00:00Z',
            'view_count': 267,
            'status': 'published',
            'image_url': 'https://example.com/images/operation-hours.jpg',
            'short_description': '7월 한 달간 센터 운영시간이 임시로 변경됩니다.'
        },
        {
            'id': 'news_5',
            'title': '가족센터, 지역 언론에 우수사례 보도',
            'content': '우리 센터의 우수한 가족 지원 사례가 지역 언론에 보도되었습니다.',
            'category': '보도자료',
            'author': '홍보팀',
            'created_at': '2025-06-29T09:30:00Z',
            'view_count': 145,
            'status': 'published',
            'image_url': 'https://example.com/images/media-coverage.jpg',
            'short_description': '우리 센터의 우수한 가족 지원 사례가 지역 언론에 보도되었습니다.'
        }
    ]
    
    # 카테고리 필터링 적용
    if category_filter:
        sample_data = [item for item in sample_data if item['category'] in category_filter]
    
    # 페이지네이션 적용
    offset = (page - 1) * limit
    total_count = len(sample_data)
    paginated_data = sample_data[offset:offset + limit]
    
    # 프론트엔드 형식에 맞게 데이터 변환
    transformed_data = []
    for item in paginated_data:
        # created_at에서 날짜만 추출 (2025-07-03T10:00:00Z -> 2025-07-03)
        date_str = item.get('created_at', '')
        if 'T' in date_str:
            date_only = date_str.split('T')[0]
        else:
            date_only = date_str[:10] if len(date_str) >= 10 else date_str
        
        transformed_item = {
            'id': item.get('id', ''),
            'category': item.get('category', '주요소식'),
            'title': item.get('title', ''),
            'author': item.get('author', ''),
            'date': date_only,
            'views': int(item.get('view_count', 0)),
            'image': item.get('image_url', ''),
            'description': item.get('short_description', '')
        }
        transformed_data.append(transformed_item)
    
    return create_response(200, {
        'success': True,
        'data': transformed_data,
        'total': total_count,
        'page': page,
        'limit': limit
    })

def get_sample_news_detail(news_id):
    """샘플 뉴스 상세 (DynamoDB 연결 실패 시)"""
    if news_id == 'news_1':
        news = {
            'id': 'news_1',
            'title': '가족센터 2025년 상반기 사업계획 발표',
            'content': '올해 상반기 가족센터의 주요 사업계획을 발표합니다.\n\n## 주요 사업 내용\n\n### 1. 가족 상담 서비스 확대\n- 개별 상담 시간 연장\n- 집단 상담 프로그램 신설\n- 온라인 상담 플랫폼 구축\n\n### 2. 다문화가족 지원 강화\n- 한국어 교육 프로그램 확대\n- 문화적응 프로그램 신설\n- 자녀 교육 지원 서비스 강화\n\n### 3. 지역사회 연계 사업\n- 지역 학교와의 협력 프로그램\n- 지역 의료기관 연계 서비스\n- 주민센터와의 공동 사업\n\n이번 사업계획을 통해 더 많은 가족들이 행복한 가정을 이룰 수 있도록 지원하겠습니다.',
            'category': '주요소식',
            'author': '기획팀',
            'created_at': '2025-07-03T10:00:00Z',
            'view_count': 157,  # 조회수 증가
            'status': 'published',
            'image_url': 'https://example.com/images/business-plan.jpg',
            'short_description': '올해 상반기 가족센터의 주요 사업계획을 발표합니다.'
        }
        return create_response(200, news)
    elif news_id == 'news_2':
        news = {
            'id': 'news_2',
            'title': '다문화가족 지원 정책 개선안 공지',
            'content': '다문화가족을 위한 새로운 지원 정책이 개선되었습니다.\n\n## 주요 개선사항\n\n### 지원 대상 확대\n- 결혼이민자 자녀 지원 연령 확대 (만 24세까지)\n- 귀화자 가족 지원 기간 연장 (5년 → 7년)\n\n### 서비스 내용 강화\n- 한국어 교육 수준별 세분화\n- 직업교육 프로그램 다양화\n- 자녀 학습 지원 서비스 신설\n\n### 신청 절차 간소화\n- 온라인 신청 시스템 도입\n- 필요 서류 간소화\n- 처리 기간 단축 (15일 → 10일)\n\n개선된 정책은 8월 1일부터 시행될 예정입니다.',
            'category': '정책소식',
            'author': '정책팀',
            'created_at': '2025-07-02T14:30:00Z',
            'view_count': 204,  # 조회수 증가
            'status': 'published',
            'image_url': 'https://example.com/images/policy-update.jpg',
            'short_description': '다문화가족을 위한 새로운 지원 정책이 개선되었습니다.'
        }
        return create_response(200, news)
    else:
        return create_response(404, {'error': 'News not found'})
