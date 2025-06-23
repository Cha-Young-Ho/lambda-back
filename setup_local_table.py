#!/usr/bin/env python3
"""
DynamoDB Local 테이블 생성 스크립트
"""
import boto3
from botocore.exceptions import ClientError
import time

def create_table():
    print("Connecting to DynamoDB Local...")
    
    # DynamoDB Local 연결 (가짜 자격 증명과 지역 사용)
    dynamodb = boto3.resource(
        'dynamodb', 
        endpoint_url='http://localhost:8000',
        region_name='us-east-1',
        aws_access_key_id='fake',
        aws_secret_access_key='fake'
    )
    
    table_name = 'BlogTable'
    
    try:
        # 기존 테이블 확인
        print("Checking existing tables...")
        existing_tables = list(dynamodb.tables.all())
        existing_table_names = [table.name for table in existing_tables]
        print(f"Existing tables: {existing_table_names}")
        
        if table_name in existing_table_names:
            print(f"Table {table_name} already exists")
            return
        
        print(f"Creating table {table_name}...")
        # 테이블 생성 (GSI 포함)
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'pk',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'sk',
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'pk',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'sk',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'GSI1PK',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'GSI1SK',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'GSI1',
                    'KeySchema': [
                        {
                            'AttributeName': 'GSI1PK',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'GSI1SK',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    }
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        print("Waiting for table to be ready...")
        # 테이블 생성 완료 대기
        table.wait_until_exists()
        print(f"Table {table_name} created successfully!")
        
        print("Adding sample blog data...")
        # 샘플 블로그 데이터 추가
        import datetime
        
        # 블로그 게시글 1
        table.put_item(
            Item={
                'pk': 'BOARD#1',
                'sk': 'POST',
                'GSI1PK': 'BOARD',
                'GSI1SK': '2024-06-24T10:30:00Z',
                'boardId': '1',
                'title': '블로그 시스템 오픈!',
                'content': '안녕하세요! 새로운 블로그 시스템이 오픈되었습니다.\n\n많은 관심과 사랑 부탁드립니다.',
                'author': 'admin',
                'createdAt': '2024-06-24T10:30:00Z',
                'updatedAt': '2024-06-24T10:30:00Z',
                'viewCount': 15,
                'status': 'published'
            }
        )
        
        # 블로그 게시글 2
        table.put_item(
            Item={
                'pk': 'BOARD#2',
                'sk': 'POST',
                'GSI1PK': 'BOARD',
                'GSI1SK': '2024-06-24T14:20:00Z',
                'boardId': '2',
                'title': 'DynamoDB Local 연동 완료',
                'content': 'DynamoDB Local과의 연동이 성공적으로 완료되었습니다!\n\n이제 실제 데이터베이스에 게시글을 저장하고 조회할 수 있습니다.',
                'author': 'admin',
                'createdAt': '2024-06-24T14:20:00Z',
                'updatedAt': '2024-06-24T14:20:00Z',
                'viewCount': 8,
                'status': 'published'
            }
        )
        
        # 블로그 게시글 3 (임시저장)
        table.put_item(
            Item={
                'pk': 'BOARD#3',
                'sk': 'POST',
                'GSI1PK': 'BOARD',
                'GSI1SK': '2024-06-24T16:15:00Z',
                'boardId': '3',
                'title': '다음 업데이트 예정',
                'content': '이미지 업로드 기능과 조회수 증가 기능을 추가할 예정입니다.',
                'author': 'admin',
                'createdAt': '2024-06-24T16:15:00Z',
                'updatedAt': '2024-06-24T16:15:00Z',
                'viewCount': 0,
                'status': 'draft'
            }
        )
        
        print("Sample data added successfully!")
        
        # 테이블 스캔으로 확인
        print("Verifying table contents...")
        response = table.scan(Limit=5)
        items = response.get('Items', [])
        print(f"Items in table: {len(items)}")
        for item in items:
            print(f"  - {item}")
        
    except ClientError as e:
        print(f"Error creating table: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise

if __name__ == "__main__":
    create_table()
