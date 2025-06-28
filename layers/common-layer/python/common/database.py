"""
DynamoDB 연결 유틸리티
지역, 테이블명, 엔드포인트 URL을 매개변수로 받아 DynamoDB 리소스를 반환합니다.
"""
import os


def get_dynamodb(region, table_name, endpoint_url=None):
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


def safe_decimal_convert(obj):
    """DynamoDB Decimal 타입을 안전하게 변환"""
    if hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
        if isinstance(obj, dict):
            return {k: safe_decimal_convert(v) for k, v in obj.items()}
        else:
            return [safe_decimal_convert(item) for item in obj]
    else:
        # Decimal 타입인 경우 int 또는 float로 변환
        from decimal import Decimal
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            else:
                return float(obj)
        return obj
