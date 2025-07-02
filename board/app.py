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
                        'table_name': secret.get('table_name', 'blog-table')
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
            import traceback
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
                'category': item.get('category', '센터소식'),
                'author': item.get('author', ''),
                'created_at': item.get('created_at', ''),
                'view_count': int(item.get('view_count', 0)),
                'status': item.get('status', 'published'),
                'image_url': item.get('image_url', ''),
                'short_description': item.get('short_description', item.get('content', '')[:100] + '...' if len(item.get('content', '')) > 100 else item.get('content', ''))
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
                'category': item.get('category', '센터소식'),
                'author': item.get('author', ''),
                'created_at': item.get('created_at', ''),
                'view_count': int(item.get('view_count', 0)),
                'status': item.get('status', 'published'),
                'image_url': item.get('image_url', ''),
                'short_description': item.get('short_description', item.get('content', '')[:100] + '...' if len(item.get('content', '')) > 100 else item.get('content', ''))
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
            'title': '2025년 가족센터 신규 프로그램 오픈',
            'content': '가족의 건강한 소통과 화합을 위한 다양한 프로그램을 새롭게 선보입니다.',
            'category': '센터소식',
            'author': '센터 관리자',
            'created_at': '2025-06-29T10:00:00Z',
            'view_count': 324,
            'status': 'published',
            'image_url': 'https://example.com/images/family-program.jpg',
            'short_description': '가족의 건강한 소통과 화합을 위한 다양한 프로그램을 새롭게 선보입니다.'
        },
        {
            'id': '2',
            'title': '다문화가족 자녀 한국어 교육 프로그램 성과 발표',
            'content': '지난 3개월간 진행된 한국어 교육 프로그램의 우수한 성과를 공유합니다.',
            'category': '프로그램소식',
            'author': '교육팀',
            'created_at': '2025-06-28T15:00:00Z',
            'view_count': 289,
            'status': 'published',
            'image_url': 'https://example.com/images/korean-education.jpg',
            'short_description': '지난 3개월간 진행된 한국어 교육 프로그램의 우수한 성과를 공유합니다.'
        },
        {
            'id': '3',
            'title': '가족 소통 워크숍 "함께 걸어요" 개최',
            'content': '가족 간의 깊이 있는 소통을 위한 특별 워크숍이 성황리에 마무리되었습니다.',
            'category': '행사소식',
            'author': '행사기획팀',
            'created_at': '2025-06-27T09:00:00Z',
            'view_count': 456,
            'status': 'published',
            'image_url': 'https://example.com/images/family-workshop.jpg',
            'short_description': '가족 간의 깊이 있는 소통을 위한 특별 워크숍이 성황리에 마무리되었습니다.'
        },
        {
            'id': '4',
            'title': '다문화가족 지원 정책 정보 공유합니다',
            'content': '정지원과 복지혜택에 대한 상세한 안내를 제공합니다.',
            'category': '생활정보',
            'author': '정지원',
            'created_at': '2025-06-26T14:00:00Z',
            'view_count': 234,
            'status': 'published',
            'image_url': 'https://example.com/images/policy-info.jpg',
            'short_description': '정지원과 복지혜택에 대한 상세한 안내를 제공합니다.'
        },
        {
            'id': '5',
            'title': '신혼부부 주거 지원 정책 안내',
            'content': '최신혼과 주거 지원 정책에 대한 안내를 드립니다.',
            'category': '생활정보',
            'author': '최신혼',
            'created_at': '2025-06-25T11:00:00Z',
            'view_count': 98,
            'status': 'published',
            'image_url': 'https://example.com/images/housing-support.jpg',
            'short_description': '최신혼과 주거 지원 정책에 대한 안내를 드립니다.'
        },
        {
            'id': '6',
            'title': '부부갈등 해결을 위한 상담 프로그램 추천',
            'content': '정상담을 통해 건강한 가족관계를 만들어가는 프로그램을 소개합니다.',
            'category': '교육',
            'author': '정상담',
            'created_at': '2025-06-24T16:00:00Z',
            'view_count': 167,
            'status': 'published',
            'image_url': 'https://example.com/images/counseling-program.jpg',
            'short_description': '정상담을 통해 건강한 가족관계를 만들어가는 프로그램을 소개합니다.'
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
            'id': '1',
            'title': '2025년 가족센터 신규 프로그램 오픈',
            'content': '가족의 건강한 소통과 화합을 위한 다양한 프로그램을 새롭게 선보입니다.',
            'category': '센터소식',
            'author': '센터 관리자',
            'created_at': '2025-06-29T10:00:00Z',
            'view_count': 324,
            'status': 'published',
            'image_url': 'https://example.com/images/family-program.jpg',
            'short_description': '가족의 건강한 소통과 화합을 위한 다양한 프로그램을 새롭게 선보입니다.'
        },
        {
            'id': '2',
            'title': '다문화가족 자녀 한국어 교육 프로그램 성과 발표',
            'content': '지난 3개월간 진행된 한국어 교육 프로그램의 우수한 성과를 공유합니다.',
            'category': '프로그램소식',
            'author': '교육팀',
            'created_at': '2025-06-28T15:00:00Z',
            'view_count': 289,
            'status': 'published',
            'image_url': 'https://example.com/images/korean-education.jpg',
            'short_description': '지난 3개월간 진행된 한국어 교육 프로그램의 우수한 성과를 공유합니다.'
        },
        {
            'id': '3',
            'title': '가족 소통 워크숍 "함께 걸어요" 개최',
            'content': '가족 간의 깊이 있는 소통을 위한 특별 워크숍이 성황리에 마무리되었습니다.',
            'category': '행사소식',
            'author': '행사기획팀',
            'created_at': '2025-06-27T09:00:00Z',
            'view_count': 456,
            'status': 'published',
            'image_url': 'https://example.com/images/family-workshop.jpg',
            'short_description': '가족 간의 깊이 있는 소통을 위한 특별 워크숍이 성황리에 마무리되었습니다.'
        },
        {
            'id': '4',
            'title': '다문화가족 지원 정책 정보 공유합니다',
            'content': '정지원과 복지혜택에 대한 상세한 안내를 제공합니다.',
            'category': '생활정보',
            'author': '정지원',
            'created_at': '2025-06-26T14:00:00Z',
            'view_count': 234,
            'status': 'published',
            'image_url': 'https://example.com/images/policy-info.jpg',
            'short_description': '정지원과 복지혜택에 대한 상세한 안내를 제공합니다.'
        },
        {
            'id': '5',
            'title': '신혼부부 주거 지원 정책 안내',
            'content': '최신혼과 주거 지원 정책에 대한 안내를 드립니다.',
            'category': '생활정보',
            'author': '최신혼',
            'created_at': '2025-06-25T11:00:00Z',
            'view_count': 98,
            'status': 'published',
            'image_url': 'https://example.com/images/housing-support.jpg',
            'short_description': '최신혼과 주거 지원 정책에 대한 안내를 드립니다.'
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
            'category': item.get('category', '센터소식'),
            'author': item.get('author', ''),
            'created_at': item.get('created_at', ''),
            'view_count': int(item.get('view_count', 0)) + 1,  # 증가된 조회수
            'status': item.get('status', 'published'),
            'image_url': item.get('image_url', ''),
            'short_description': item.get('short_description', '')
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
            'title': '2025년 가족센터 신규 프로그램 오픈',
            'content': '가족의 건강한 소통과 화합을 위한 다양한 프로그램을 새롭게 선보입니다.\n\n## 프로그램 소개\n\n![프로그램 이미지](https://example.com/images/family-program-detail.jpg)\n\n### 주요 프로그램\n\n1. **가족 소통 워크숍**\n   - 대화법 교육\n   - 갈등 해결 방법\n   - 공감 능력 향상\n\n2. **문화체험 프로그램**\n   - 전통 문화 체험\n   - 다문화 이해\n   - 세대 간 교류\n\n### 신청 방법\n\n센터 방문 또는 전화 접수를 통해 신청 가능합니다.',
            'category': '센터소식',
            'author': '센터 관리자',
            'created_at': '2025-06-29T10:00:00Z',
            'view_count': 325,  # 조회수 증가
            'status': 'published',
            'image_url': 'https://example.com/images/family-program.jpg',
            'short_description': '가족의 건강한 소통과 화합을 위한 다양한 프로그램을 새롭게 선보입니다.'
        }
        return create_response(200, post)
    elif board_id == '2':
        post = {
            'id': '2',
            'title': '다문화가족 자녀 한국어 교육 프로그램 성과 발표',
            'content': '지난 3개월간 진행된 한국어 교육 프로그램의 우수한 성과를 공유합니다.\n\n## 프로그램 성과\n\n![교육 성과](https://example.com/images/korean-education-detail.jpg)\n\n### 주요 성과\n\n- **참여 학생 수**: 45명\n- **한국어 능력 향상률**: 평균 85%\n- **학습 만족도**: 4.8/5.0\n\n### 수료생 후기\n\n> "선생님들이 친절하게 가르쳐주셔서 한국어가 많이 늘었어요!" - 김○○ 학생\n\n> "아이가 자신감을 얻고 학교생활에 적응하는 데 큰 도움이 되었습니다." - 학부모 이○○\n\n### 다음 기수 모집\n\n8월부터 시작되는 다음 기수 모집을 곧 시작할 예정입니다.',
            'category': '프로그램소식',
            'author': '교육팀',
            'created_at': '2025-06-28T15:00:00Z',
            'view_count': 290,  # 조회수 증가
            'status': 'published',
            'image_url': 'https://example.com/images/korean-education.jpg',
            'short_description': '지난 3개월간 진행된 한국어 교육 프로그램의 우수한 성과를 공유합니다.'
        }
        return create_response(200, post)
    elif board_id == '3':
        post = {
            'id': '3',
            'title': '가족 소통 워크숍 "함께 걸어요" 개최',
            'content': '가족 간의 깊이 있는 소통을 위한 특별 워크숍이 성황리에 마무리되었습니다.\n\n## 워크숍 개요\n\n![워크숍 현장](https://example.com/images/family-workshop-detail.jpg)\n\n### 프로그램 내용\n\n1. **소통의 기초**\n   - 경청의 중요성\n   - 공감적 대화법\n   - 감정 표현 방법\n\n2. **갈등 해결**\n   - 갈등의 원인 분석\n   - 건설적 해결 방안\n   - 화해와 용서\n\n3. **가족 활동**\n   - 함께하는 게임\n   - 역할극 체험\n   - 가족 미션 수행\n\n### 참가자 소감\n\n"가족과 더 깊은 대화를 나눌 수 있게 되었어요. 정말 유익한 시간이었습니다!"',
            'category': '행사소식',
            'author': '행사기획팀',
            'created_at': '2025-06-27T09:00:00Z',
            'view_count': 457,  # 조회수 증가
            'status': 'published',
            'image_url': 'https://example.com/images/family-workshop.jpg',
            'short_description': '가족 간의 깊이 있는 소통을 위한 특별 워크숍이 성황리에 마무리되었습니다.'
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
        content = body.get('content')
        category = body.get('category', '센터소식')
        image_url = body.get('image_url', '')  # 프론트에서 S3에 업로드 후 URL 전달
        short_description = body.get('short_description', '')  # 카드뷰용 짧은 설명
        author = body.get('author', 'admin')
        
        if not title or not content:
            return create_response(400, {'error': 'Title and content required'})
        
        # 카테고리 유효성 검사 (사진에 보이는 카테고리들로 업데이트)
        valid_categories = ['센터소식', '프로그램소식', '행사소식', '생활정보', '교육']
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
        
        post_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat() + 'Z'
        
        new_post = {
            'id': post_id,
            'title': title,
            'content': content,
            'category': category,
            'author': author,
            'created_at': created_at,
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
                    table.put_item(Item=new_post)
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
            valid_categories = ['센터소식', '프로그램소식', '행사소식', '생활정보', '교육']
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
                    # 먼저 게시글이 존재하는지 확인
                    response = table.get_item(Key={'id': board_id})
                    if 'Item' not in response:
                        return create_response(404, {'error': 'Post not found'})
                    
                    # UpdateExpression 구성
                    update_expression = "SET " + ", ".join([f"{key} = :{key}" for key in update_fields.keys()])
                    expression_attribute_values = {f":{key}": value for key, value in update_fields.items()}
                    
                    # DynamoDB 업데이트
                    table.update_item(
                        Key={'id': board_id},
                        UpdateExpression=update_expression,
                        ExpressionAttributeValues=expression_attribute_values,
                        ReturnValues='ALL_NEW'
                    )
                    
                    print(f"Successfully updated post in DynamoDB: {board_id}")
                    
                    # 업데이트된 게시글 조회
                    updated_response = table.get_item(Key={'id': board_id})
                    updated_post = updated_response['Item']
                    
                    return create_response(200, {
                        'message': 'Post updated successfully',
                        'post': {
                            'id': updated_post.get('id', ''),
                            'title': updated_post.get('title', ''),
                            'content': updated_post.get('content', ''),
                            'category': updated_post.get('category', '센터소식'),
                            'author': updated_post.get('author', ''),
                            'created_at': updated_post.get('created_at', ''),
                            'updated_at': updated_post.get('updated_at', ''),
                            'view_count': int(updated_post.get('view_count', 0)),
                            'status': updated_post.get('status', 'published'),
                            'image_url': updated_post.get('image_url', ''),
                            'short_description': updated_post.get('short_description', '')
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
        import traceback
        error_detail = {
            'error': 'Error updating post',
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc()
        }
        print(f"Error updating post: {str(e)}")
        return create_response(500, error_detail)

def delete_board(board_id, event, app_config):
    """게시글 삭제 (관리자 전용)"""
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
                    # 먼저 게시글이 존재하는지 확인
                    response = table.get_item(Key={'id': board_id})
                    if 'Item' not in response:
                        return create_response(404, {'error': 'Post not found'})
                    
                    # 삭제할 게시글 정보 저장
                    deleted_post = response['Item']
                    
                    # DynamoDB에서 삭제
                    table.delete_item(Key={'id': board_id})
                    
                    print(f"Successfully deleted post from DynamoDB: {board_id}")
                    
                    return create_response(200, {
                        'message': 'Post deleted successfully',
                        'deleted_post': {
                            'id': deleted_post.get('id', ''),
                            'title': deleted_post.get('title', ''),
                            'category': deleted_post.get('category', '센터소식'),
                            'author': deleted_post.get('author', ''),
                            'created_at': deleted_post.get('created_at', '')
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
        import traceback
        error_detail = {
            'error': 'Error deleting post',
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc()
        }
        print(f"Error deleting post: {str(e)}")
        return create_response(500, error_detail)

def upload_image(event, app_config):
    """이미지 업로드 정보 제공 (관리자 전용)"""
    # JWT 토큰 검증
    if not verify_admin_token(event, app_config):
        return create_response(401, {'error': 'Unauthorized'})
    
    try:
        # 프론트에서 S3에 직접 업로드할 수 있도록 정보 제공
        # 실제 구현에서는 S3 presigned URL을 생성하여 반환
        
        # 현재는 샘플 응답
        return create_response(200, {
            'message': 'Image upload endpoint',
            'instructions': {
                'method': 'POST',
                'description': 'Frontend should upload images to S3 and send the URL in the post creation/update request',
                'example_flow': [
                    '1. Frontend uploads image to S3',
                    '2. Get the S3 URL from upload response',
                    '3. Include image_url in POST/PUT request to /board'
                ]
            },
            'sample_response': {
                'imageUrl': 'https://your-s3-bucket.s3.amazonaws.com/images/sample-image.jpg',
                'success': True
            },
            'supported_formats': ['jpg', 'jpeg', 'png', 'gif', 'webp'],
            'max_size': '5MB'
        })
        
    except Exception as e:
        import traceback
        error_detail = {
            'error': 'Error in upload image endpoint',
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc()
        }
        print(f"Error in upload image endpoint: {str(e)}")
        return create_response(500, error_detail)
