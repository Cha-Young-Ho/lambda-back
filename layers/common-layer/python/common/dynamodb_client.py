"""
DynamoDB 클라이언트 모듈
설정 기반으로 DynamoDB 연결 및 기본 CRUD 작업 제공
"""
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from typing import Dict, Any, List, Optional
from .config import config_manager

class DynamoDBClient:
    def __init__(self):
        self.config = config_manager.get_dynamodb_config()
        self.table_name = config_manager.get_table_name()
        
        # DynamoDB 리소스 생성 (로컬/AWS 환경 대응)
        dynamodb_kwargs = {}
        if self.config.get("endpoint_url"):
            dynamodb_kwargs["endpoint_url"] = self.config["endpoint_url"]
        
        self.dynamodb = boto3.resource('dynamodb', **dynamodb_kwargs)
        self.table = self.dynamodb.Table(self.table_name)
    
    def get_item(self, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """아이템 조회"""
        try:
            response = self.table.get_item(Key=key)
            return response.get('Item')
        except ClientError as e:
            print(f"Error getting item: {e}")
            return None
    
    def put_item(self, item: Dict[str, Any]) -> bool:
        """아이템 생성/업데이트"""
        try:
            self.table.put_item(Item=item)
            return True
        except ClientError as e:
            print(f"Error putting item: {e}")
            return False
    
    def delete_item(self, key: Dict[str, Any]) -> bool:
        """아이템 삭제"""
        try:
            self.table.delete_item(Key=key)
            return True
        except ClientError as e:
            print(f"Error deleting item: {e}")
            return False
    
    def query_by_pk(self, pk_name: str, pk_value: Any, 
                   sk_name: str = None, sk_value: Any = None) -> List[Dict[str, Any]]:
        """Primary Key로 쿼리"""
        try:
            key_condition = Key(pk_name).eq(pk_value)
            if sk_name and sk_value:
                key_condition = key_condition & Key(sk_name).eq(sk_value)
            
            response = self.table.query(KeyConditionExpression=key_condition)
            return response.get('Items', [])
        except ClientError as e:
            print(f"Error querying items: {e}")
            return []
    
    def scan_with_filter(self, filter_expression=None) -> List[Dict[str, Any]]:
        """스캔으로 전체 조회 (필터 선택적 적용)"""
        try:
            scan_kwargs = {}
            if filter_expression:
                scan_kwargs['FilterExpression'] = filter_expression
            
            response = self.table.scan(**scan_kwargs)
            return response.get('Items', [])
        except ClientError as e:
            print(f"Error scanning items: {e}")
            return []
    
    def update_item(self, key: Dict[str, Any], 
                   update_expression: str, 
                   expression_attribute_values: Dict[str, Any] = None,
                   expression_attribute_names: Dict[str, str] = None) -> bool:
        """아이템 업데이트"""
        try:
            update_kwargs = {
                'Key': key,
                'UpdateExpression': update_expression,
                'ReturnValues': 'UPDATED_NEW'
            }
            
            if expression_attribute_values:
                update_kwargs['ExpressionAttributeValues'] = expression_attribute_values
            if expression_attribute_names:
                update_kwargs['ExpressionAttributeNames'] = expression_attribute_names
            
            self.table.update_item(**update_kwargs)
            return True
        except ClientError as e:
            print(f"Error updating item: {e}")
            return False

# 싱글톤 인스턴스
dynamodb_client = DynamoDBClient()
