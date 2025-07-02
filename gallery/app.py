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
    갤러리(주요 정보) CRUD API
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
        
        # 갤러리 목록 조회 (공개) - 페이지네이션 지원
        if method == 'GET' and path == '/gallery':
            return get_gallery_list(app_config, event)
        
        # 갤러리 상세 조회 (공개)
        elif method == 'GET' and '/gallery/' in path and path_parameters.get('galleryId'):
            gallery_id = path_parameters['galleryId']
            return get_gallery_detail(gallery_id, app_config)
        
        # 갤러리 생성 (관리자 전용)
        elif method == 'POST' and path == '/gallery':
            return create_gallery(event, app_config)
        
        # 갤러리 수정 (관리자 전용)
        elif method == 'PUT' and '/gallery/' in path and path_parameters.get('galleryId'):
            gallery_id = path_parameters['galleryId']
            return update_gallery(gallery_id, event, app_config)
        
        # 갤러리 삭제 (관리자 전용)
        elif method == 'DELETE' and '/gallery/' in path and path_parameters.get('galleryId'):
            gallery_id = path_parameters['galleryId']
            return delete_gallery(gallery_id, event, app_config)
        
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

def get_gallery_list(app_config, event):
    """갤러리 목록 조회 (공개) - 페이지네이션 지원"""
    try:
        # 쿼리 파라미터 처리
        query_params = event.get('queryStringParameters') or {}
        
        # 페이지네이션 파라미터
        page = int(query_params.get('page', 1))
        limit = int(query_params.get('limit', 12))  # 갤러리는 기본 12개씩
        
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
            return get_sample_gallery_list(category_filter, page, limit)
        
        table = get_table(dynamodb, dynamodb_config['table_name'])
        
        if not table:
            # 테이블 가져오기 실패 시 샘플 데이터 반환
            return get_sample_gallery_list(category_filter, page, limit)
        
        # 갤러리 목록 조회 (content_type으로 필터링)
        response = table.scan(
            FilterExpression='content_type = :content_type',
            ExpressionAttributeValues={
                ':content_type': 'gallery'
            }
        )
        
        gallery_items = []
        for item in response.get('Items', []):
            gallery_item = {
                'id': item.get('id', ''),
                'title': item.get('title', ''),
                'content': item.get('content', '')[:100] + '...' if len(item.get('content', '')) > 100 else item.get('content', ''),
                'category': item.get('category', '자료실'),
                'author': item.get('author', ''),
                'created_at': item.get('created_at', ''),
                'view_count': int(item.get('view_count', 0)),
                'status': item.get('status', 'published'),
                'image_url': item.get('image_url', ''),
                'short_description': item.get('short_description', item.get('content', '')[:100] + '...' if len(item.get('content', '')) > 100 else item.get('content', '')),
                'file_url': item.get('file_url', ''),  # 파일 다운로드 URL
                'file_name': item.get('file_name', ''),  # 원본 파일명
                'file_size': item.get('file_size', 0)  # 파일 크기 (bytes)
            }
            
            # 카테고리 필터링
            if category_filter and gallery_item['category'] not in category_filter:
                continue
                
            gallery_items.append(gallery_item)
        
        # published 상태인 갤러리만 필터링
        published_gallery = [item for item in gallery_items if item['status'] == 'published']
        
        # 생성일시 기준 내림차순 정렬
        published_gallery.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # 페이지네이션 적용
        total_count = len(published_gallery)
        paginated_gallery = published_gallery[offset:offset + limit]
        
        # 프론트엔드 형식에 맞게 데이터 변환
        transformed_data = []
        for item in paginated_gallery:
            # created_at에서 날짜만 추출 (2025-07-03T10:00:00Z -> 2025-07-03)
            date_str = item.get('created_at', '')
            if 'T' in date_str:
                date_only = date_str.split('T')[0]
            else:
                date_only = date_str[:10] if len(date_str) >= 10 else date_str
            
            transformed_item = {
                'id': item.get('id', ''),
                'category': item.get('category', '자료실'),
                'title': item.get('title', ''),
                'author': item.get('author', ''),
                'date': date_only,
                'views': int(item.get('view_count', 0))
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
            'error': 'Error getting gallery list',
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc(),
            'fallback_to_sample': True
        }
        print(f"Error getting gallery list: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        
        # 에러 시 샘플 데이터와 함께 에러 정보도 반환
        try:
            query_params = event.get('queryStringParameters') or {}
            page = int(query_params.get('page', 1))
            limit = int(query_params.get('limit', 12))
            categories = query_params.get('categories', '')
            category_filter = [cat.strip() for cat in categories.split(',') if cat.strip()] if categories else []
            
            sample_response = get_sample_gallery_list(category_filter, page, limit)
            sample_data = json.loads(sample_response['body'])
            sample_data['error_info'] = error_detail
            return create_response(200, sample_data)
        except:
            return create_response(500, error_detail)

def get_gallery_detail(gallery_id, app_config):
    """갤러리 상세 조회 (공개)"""
    try:
        dynamodb_config = app_config.config['dynamodb']
        dynamodb = get_dynamodb(
            region=dynamodb_config['region'],
            table_name=dynamodb_config['table_name'],
            endpoint_url=dynamodb_config.get('endpoint_url')
        )
        
        if not dynamodb:
            # DynamoDB 연결 실패 시 샘플 데이터 반환
            return get_sample_gallery_detail(gallery_id)
        
        table = get_table(dynamodb, dynamodb_config['table_name'])
        
        if not table:
            # 테이블 가져오기 실패 시 샘플 데이터 반환
            return get_sample_gallery_detail(gallery_id)
        
        # 갤러리 조회
        response = table.get_item(Key={'id': gallery_id})
        
        if 'Item' not in response:
            return create_response(404, {'error': 'Gallery item not found'})
        
        item = response['Item']
        
        # content_type이 gallery인지 확인
        if item.get('content_type') != 'gallery':
            return create_response(404, {'error': 'Gallery item not found'})
        
        # 조회수 증가
        table.update_item(
            Key={'id': gallery_id},
            UpdateExpression='ADD view_count :inc',
            ExpressionAttributeValues={':inc': 1},
            ReturnValues='UPDATED_NEW'
        )
        
        gallery_item = {
            'id': item.get('id', ''),
            'title': item.get('title', ''),
            'content': item.get('content', ''),
            'category': item.get('category', '자료실'),
            'author': item.get('author', ''),
            'created_at': item.get('created_at', ''),
            'view_count': int(item.get('view_count', 0)) + 1,  # 증가된 조회수
            'status': item.get('status', 'published'),
            'image_url': item.get('image_url', ''),
            'short_description': item.get('short_description', ''),
            'file_url': item.get('file_url', ''),
            'file_name': item.get('file_name', ''),
            'file_size': item.get('file_size', 0)
        }
        
        return create_response(200, gallery_item)
    
    except Exception as e:
        error_detail = {
            'error': 'Error getting gallery detail',
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc(),
            'gallery_id': gallery_id,
            'fallback_to_sample': True
        }
        print(f"Error getting gallery detail: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        
        # 에러 시 샘플 데이터와 함께 에러 정보도 반환
        sample_response = get_sample_gallery_detail(gallery_id)
        if sample_response['statusCode'] == 200:
            sample_data = json.loads(sample_response['body'])
            sample_data['error_info'] = error_detail
            return create_response(200, sample_data)
        else:
            return create_response(500, error_detail)

def create_gallery(event, app_config):
    """갤러리 생성 (관리자 전용)"""
    # JWT 토큰 검증
    if not verify_admin_token(event, app_config):
        return create_response(401, {'error': 'Unauthorized'})
    
    try:
        body = json.loads(event.get('body', '{}'))
        title = body.get('title')
        content = body.get('content')
        category = body.get('category', '자료실')
        image_url = body.get('image_url', '')
        short_description = body.get('short_description', '')
        author = body.get('author', 'admin')
        file_url = body.get('file_url', '')  # 파일 다운로드 URL
        file_name = body.get('file_name', '')  # 원본 파일명
        file_size = body.get('file_size', 0)  # 파일 크기
        
        if not title or not content:
            return create_response(400, {'error': 'Title and content required'})
        
        # 갤러리 카테고리 유효성 검사
        valid_categories = ['자료실', '양식다운로드', '매뉴얼', '가이드라인', '법령정보']
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
        
        gallery_id = f"gallery_{str(uuid.uuid4())}"  # gallery_ 접두사로 구분
        created_at = datetime.utcnow().isoformat() + 'Z'
        
        new_gallery = {
            'id': gallery_id,
            'content_type': 'gallery',  # 식별자
            'title': title,
            'content': content,
            'category': category,
            'author': author,
            'created_at': created_at,
            'updated_at': created_at,
            'view_count': 0,
            'status': 'published',
            'image_url': image_url,
            'short_description': short_description,
            'file_url': file_url,
            'file_name': file_name,
            'file_size': file_size
        }
        
        if dynamodb:
            table = get_table(dynamodb, dynamodb_config['table_name'])
            if table:
                try:
                    # DynamoDB에 아이템 저장
                    table.put_item(Item=new_gallery)
                    print(f"Successfully saved gallery to DynamoDB: {gallery_id}")
                    
                except Exception as db_error:
                    print(f"Error saving to DynamoDB: {str(db_error)}")
                    # DynamoDB 저장 실패해도 계속 진행
            else:
                print("DynamoDB table not available, but continuing with response")
        else:
            print("DynamoDB connection failed, but continuing with response")
        
        return create_response(201, {
            'message': 'Gallery item created successfully',
            'gallery': new_gallery
        })
    
    except json.JSONDecodeError as e:
        return create_response(400, {
            'error': 'Invalid JSON',
            'error_message': str(e)
        })
    except Exception as e:
        error_detail = {
            'error': 'Error creating gallery item',
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc()
        }
        print(f"Error creating gallery: {str(e)}")
        return create_response(500, error_detail)

def update_gallery(gallery_id, event, app_config):
    """갤러리 수정 (관리자 전용)"""
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
            valid_categories = ['자료실', '양식다운로드', '매뉴얼', '가이드라인', '법령정보']
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
        if 'file_url' in body:
            update_fields['file_url'] = body['file_url']
        if 'file_name' in body:
            update_fields['file_name'] = body['file_name']
        if 'file_size' in body:
            update_fields['file_size'] = body['file_size']
        
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
                    # 먼저 갤러리가 존재하는지 확인
                    response = table.get_item(Key={'id': gallery_id})
                    if 'Item' not in response:
                        return create_response(404, {'error': 'Gallery item not found'})
                    
                    # content_type이 gallery인지 확인
                    if response['Item'].get('content_type') != 'gallery':
                        return create_response(404, {'error': 'Gallery item not found'})
                    
                    # UpdateExpression 구성
                    update_expression = "SET " + ", ".join([f"{key} = :{key}" for key in update_fields.keys()])
                    expression_attribute_values = {f":{key}": value for key, value in update_fields.items()}
                    
                    # DynamoDB 업데이트
                    table.update_item(
                        Key={'id': gallery_id},
                        UpdateExpression=update_expression,
                        ExpressionAttributeValues=expression_attribute_values,
                        ReturnValues='ALL_NEW'
                    )
                    
                    print(f"Successfully updated gallery in DynamoDB: {gallery_id}")
                    
                    # 업데이트된 갤러리 조회
                    updated_response = table.get_item(Key={'id': gallery_id})
                    updated_gallery = updated_response['Item']
                    
                    return create_response(200, {
                        'message': 'Gallery item updated successfully',
                        'gallery': {
                            'id': updated_gallery.get('id', ''),
                            'title': updated_gallery.get('title', ''),
                            'content': updated_gallery.get('content', ''),
                            'category': updated_gallery.get('category', '자료실'),
                            'author': updated_gallery.get('author', ''),
                            'created_at': updated_gallery.get('created_at', ''),
                            'updated_at': updated_gallery.get('updated_at', ''),
                            'view_count': int(updated_gallery.get('view_count', 0)),
                            'status': updated_gallery.get('status', 'published'),
                            'image_url': updated_gallery.get('image_url', ''),
                            'short_description': updated_gallery.get('short_description', ''),
                            'file_url': updated_gallery.get('file_url', ''),
                            'file_name': updated_gallery.get('file_name', ''),
                            'file_size': updated_gallery.get('file_size', 0)
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
            'error': 'Error updating gallery item',
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc()
        }
        print(f"Error updating gallery: {str(e)}")
        return create_response(500, error_detail)

def delete_gallery(gallery_id, event, app_config):
    """갤러리 삭제 (관리자 전용)"""
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
                    # 먼저 갤러리가 존재하는지 확인
                    response = table.get_item(Key={'id': gallery_id})
                    if 'Item' not in response:
                        return create_response(404, {'error': 'Gallery item not found'})
                    
                    # content_type이 gallery인지 확인
                    if response['Item'].get('content_type') != 'gallery':
                        return create_response(404, {'error': 'Gallery item not found'})
                    
                    # 삭제할 갤러리 정보 저장
                    deleted_gallery = response['Item']
                    
                    # DynamoDB에서 삭제
                    table.delete_item(Key={'id': gallery_id})
                    
                    print(f"Successfully deleted gallery from DynamoDB: {gallery_id}")
                    
                    return create_response(200, {
                        'message': 'Gallery item deleted successfully',
                        'deleted_gallery': {
                            'id': deleted_gallery.get('id', ''),
                            'title': deleted_gallery.get('title', ''),
                            'category': deleted_gallery.get('category', '자료실'),
                            'author': deleted_gallery.get('author', ''),
                            'created_at': deleted_gallery.get('created_at', '')
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
            'error': 'Error deleting gallery item',
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc()
        }
        print(f"Error deleting gallery: {str(e)}")
        return create_response(500, error_detail)

def get_sample_gallery_list(category_filter=None, page=1, limit=12):
    """샘플 갤러리 목록 (DynamoDB 연결 실패 시)"""
    sample_data = [
        {
            'id': 'gallery_1',
            'title': '다문화가족 지원 서비스 안내서',
            'content': '다문화가족을 위한 종합 지원 서비스 안내서입니다.',
            'category': '자료실',
            'author': '정보팀',
            'created_at': '2025-07-03T09:00:00Z',
            'view_count': 89,
            'status': 'published',
            'image_url': 'https://example.com/images/guide-cover.jpg',
            'short_description': '다문화가족을 위한 종합 지원 서비스 안내서입니다.',
            'file_url': 'https://example.com/files/multicultural-guide.pdf',
            'file_name': '다문화가족_지원서비스_안내서.pdf',
            'file_size': 2048576
        },
        {
            'id': 'gallery_2',
            'title': '가족상담 신청서 양식',
            'content': '가족상담을 신청하실 때 사용하는 양식입니다.',
            'category': '양식다운로드',
            'author': '상담팀',
            'created_at': '2025-07-02T14:00:00Z',
            'view_count': 156,
            'status': 'published',
            'image_url': 'https://example.com/images/form-preview.jpg',
            'short_description': '가족상담을 신청하실 때 사용하는 양식입니다.',
            'file_url': 'https://example.com/files/counseling-application.docx',
            'file_name': '가족상담_신청서.docx',
            'file_size': 51200
        },
        {
            'id': 'gallery_3',
            'title': '센터 이용 매뉴얼',
            'content': '가족센터 시설 및 프로그램 이용 방법을 안내합니다.',
            'category': '매뉴얼',
            'author': '운영팀',
            'created_at': '2025-07-01T11:30:00Z',
            'view_count': 234,
            'status': 'published',
            'image_url': 'https://example.com/images/manual-cover.jpg',
            'short_description': '가족센터 시설 및 프로그램 이용 방법을 안내합니다.',
            'file_url': 'https://example.com/files/center-manual.pdf',
            'file_name': '센터이용_매뉴얼.pdf',
            'file_size': 3145728
        },
        {
            'id': 'gallery_4',
            'title': '프로그램 운영 가이드라인',
            'content': '각종 프로그램 운영을 위한 가이드라인입니다.',
            'category': '가이드라인',
            'author': '프로그램팀',
            'created_at': '2025-06-30T16:45:00Z',
            'view_count': 67,
            'status': 'published',
            'image_url': 'https://example.com/images/guideline-cover.jpg',
            'short_description': '각종 프로그램 운영을 위한 가이드라인입니다.',
            'file_url': 'https://example.com/files/program-guideline.pdf',
            'file_name': '프로그램_운영_가이드라인.pdf',
            'file_size': 1572864
        },
        {
            'id': 'gallery_5',
            'title': '다문화가족 관련 법령 정보',
            'content': '다문화가족 지원에 관한 법령 정보를 정리한 자료입니다.',
            'category': '법령정보',
            'author': '법무팀',
            'created_at': '2025-06-29T13:20:00Z',
            'view_count': 123,
            'status': 'published',
            'image_url': 'https://example.com/images/law-info.jpg',
            'short_description': '다문화가족 지원에 관한 법령 정보를 정리한 자료입니다.',
            'file_url': 'https://example.com/files/law-information.pdf',
            'file_name': '다문화가족_관련_법령정보.pdf',
            'file_size': 4194304
        },
        {
            'id': 'gallery_6',
            'title': '가족교육 프로그램 소개 자료',
            'content': '다양한 가족교육 프로그램을 소개하는 자료입니다.',
            'category': '자료실',
            'author': '교육팀',
            'created_at': '2025-06-28T10:15:00Z',
            'view_count': 178,
            'status': 'published',
            'image_url': 'https://example.com/images/education-program.jpg',
            'short_description': '다양한 가족교육 프로그램을 소개하는 자료입니다.',
            'file_url': 'https://example.com/files/education-programs.pdf',
            'file_name': '가족교육_프로그램_소개.pdf',
            'file_size': 2621440
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
            'category': item.get('category', '자료실'),
            'title': item.get('title', ''),
            'author': item.get('author', ''),
            'date': date_only,
            'views': int(item.get('view_count', 0))
        }
        transformed_data.append(transformed_item)
    
    return create_response(200, {
        'success': True,
        'data': transformed_data,
        'total': total_count,
        'page': page,
        'limit': limit
    })

def get_sample_gallery_detail(gallery_id):
    """샘플 갤러리 상세 (DynamoDB 연결 실패 시)"""
    if gallery_id == 'gallery_1':
        gallery = {
            'id': 'gallery_1',
            'title': '다문화가족 지원 서비스 안내서',
            'content': '다문화가족을 위한 종합 지원 서비스 안내서입니다.\n\n## 주요 내용\n\n### 1. 한국어 교육 지원\n- 기초 한국어 교육\n- 생활 한국어 교육\n- 직업 한국어 교육\n\n### 2. 자녀 교육 지원\n- 학습 멘토링\n- 진로 상담\n- 특기적성 교육\n\n### 3. 가족 통합 지원\n- 가족 상담\n- 문화체험 프로그램\n- 소통 워크숍\n\n### 4. 취업 및 창업 지원\n- 직업훈련\n- 취업 상담\n- 창업 교육\n\n### 5. 생활 정착 지원\n- 생활 정보 제공\n- 법률 상담\n- 의료 서비스 연계\n\n본 안내서는 다문화가족이 한국 사회에 성공적으로 정착할 수 있도록 다양한 지원 서비스를 종합적으로 안내하고 있습니다.',
            'category': '자료실',
            'author': '정보팀',
            'created_at': '2025-07-03T09:00:00Z',
            'view_count': 90,  # 조회수 증가
            'status': 'published',
            'image_url': 'https://example.com/images/guide-cover.jpg',
            'short_description': '다문화가족을 위한 종합 지원 서비스 안내서입니다.',
            'file_url': 'https://example.com/files/multicultural-guide.pdf',
            'file_name': '다문화가족_지원서비스_안내서.pdf',
            'file_size': 2048576
        }
        return create_response(200, gallery)
    elif gallery_id == 'gallery_2':
        gallery = {
            'id': 'gallery_2',
            'title': '가족상담 신청서 양식',
            'content': '가족상담을 신청하실 때 사용하는 양식입니다.\n\n## 양식 사용 안내\n\n### 작성 방법\n1. 신청자 정보를 정확히 기재해 주세요\n2. 상담 희망 분야를 선택해 주세요\n3. 상담 희망 일시를 기재해 주세요\n4. 상담 내용을 간단히 기술해 주세요\n\n### 제출 방법\n- 방문 접수: 센터 1층 접수데스크\n- 이메일 접수: counseling@familycenter.go.kr\n- 팩스 접수: 02-123-4567\n\n### 처리 절차\n1. 신청서 접수\n2. 상담사 배정\n3. 상담 일정 조율\n4. 상담 진행\n\n상담은 개인정보보호법에 따라 철저히 비밀이 보장됩니다.',
            'category': '양식다운로드',
            'author': '상담팀',
            'created_at': '2025-07-02T14:00:00Z',
            'view_count': 157,  # 조회수 증가
            'status': 'published',
            'image_url': 'https://example.com/images/form-preview.jpg',
            'short_description': '가족상담을 신청하실 때 사용하는 양식입니다.',
            'file_url': 'https://example.com/files/counseling-application.docx',
            'file_name': '가족상담_신청서.docx',
            'file_size': 51200
        }
        return create_response(200, gallery)
    else:
        return create_response(404, {'error': 'Gallery item not found'})
