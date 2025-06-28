#!/usr/bin/env python3
"""
로컬 DynamoDB 테이블 설정 스크립트
로컬 환경에서 DynamoDB 테이블을 생성하고 샘플 데이터를 삽입합니다.
"""

import boto3
import json
from datetime import datetime
from botocore.exceptions import ClientError

def create_local_table():
    """로컬 DynamoDB 테이블 생성"""
    
    # DynamoDB 클라이언트 생성 (로컬 또는 AWS)
    try:
        # 먼저 DynamoDB Local 시도 (Docker 등으로 실행 중인 경우)
        dynamodb = boto3.resource('dynamodb', 
                                endpoint_url='http://localhost:8000',
                                region_name='ap-northeast-2',
                                aws_access_key_id='dummy',
                                aws_secret_access_key='dummy')
        print("🔗 Connecting to DynamoDB Local (localhost:8000)...")
        
        # 연결 테스트
        list(dynamodb.tables.all())
        use_local = True
        
    except Exception:
        # DynamoDB Local 실패시 AWS DynamoDB 사용
        try:
            dynamodb = boto3.resource('dynamodb')
            print("🔗 Connecting to AWS DynamoDB...")
            use_local = False
        except Exception as e:
            print(f"❌ Failed to connect to DynamoDB: {str(e)}")
            print("💡 Make sure you have:")
            print("   - DynamoDB Local running on localhost:8000, OR")
            print("   - AWS credentials configured for DynamoDB access")
            return False
    
    table_name = 'blog-table-local'
    
    try:
        # 기존 테이블 확인
        table = dynamodb.Table(table_name)
        table.load()
        print(f"✅ Table '{table_name}' already exists")
        return setup_sample_data(table)
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            # 테이블이 없으면 생성
            print(f"📝 Creating table '{table_name}'...")
            
            table = dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {
                        'AttributeName': 'id',
                        'KeyType': 'HASH'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'id',
                        'AttributeType': 'S'
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            # 테이블 생성 대기
            print("⏳ Waiting for table to be created...")
            table.wait_until_exists()
            
            print(f"✅ Created table '{table_name}'")
            
            # 샘플 데이터 삽입
            return setup_sample_data(table)
            
        else:
            print(f"❌ Error checking/creating table: {str(e)}")
            return False

def setup_sample_data(table):
    """샘플 데이터 삽입"""
    
    sample_posts = [
        {
            'id': '1',
            'title': '블로그 시스템 소개',
            'content': 'AWS SAM을 사용한 서버리스 블로그 관리 시스템입니다.\n\n이 시스템은 다음과 같은 기능을 제공합니다:\n- 게시글 CRUD\n- 관리자 인증\n- 이미지 업로드',
            'author': 'admin',
            'created_at': '2024-06-24T10:00:00Z',
            'updated_at': '2024-06-24T10:00:00Z',
            'status': 'published',
            'view_count': 15,
            'tags': ['aws', 'serverless', 'blog']
        },
        {
            'id': '2',
            'title': 'Lambda와 API Gateway 활용',
            'content': 'Lambda 함수와 API Gateway를 연동하여 RESTful API를 구축하는 방법을 알아봅니다.\n\n주요 장점:\n- 서버 관리 불필요\n- 자동 스케일링\n- 사용한 만큼만 비용 지불',
            'author': 'admin',
            'created_at': '2024-06-24T15:30:00Z',
            'updated_at': '2024-06-24T15:30:00Z',
            'status': 'published',
            'view_count': 8,
            'tags': ['lambda', 'api-gateway', 'rest']
        },
        {
            'id': '3',
            'title': 'DynamoDB 데이터 모델링',
            'content': 'NoSQL 데이터베이스인 DynamoDB의 효율적인 데이터 모델링 전략을 소개합니다.\n\n아직 작성 중인 글입니다.',
            'author': 'admin',
            'created_at': '2024-06-24T09:15:00Z',
            'updated_at': '2024-06-24T09:15:00Z',
            'status': 'draft',
            'view_count': 0,
            'tags': ['dynamodb', 'nosql', 'modeling']
        }
    ]
    
    print("📝 Inserting sample data...")
    
    try:
        for post in sample_posts:
            table.put_item(Item=post)
            print(f"   ✅ Added post: {post['title']}")
        
        print(f"✅ Successfully inserted {len(sample_posts)} sample posts")
        return True
        
    except Exception as e:
        print(f"❌ Error inserting sample data: {str(e)}")
        return False

def test_table_access(table_name='blog-table-local'):
    """테이블 접근 테스트"""
    
    try:
        # DynamoDB Local 먼저 시도
        try:
            dynamodb = boto3.resource('dynamodb', 
                                    endpoint_url='http://localhost:8000',
                                    region_name='us-east-1',
                                    aws_access_key_id='dummy',
                                    aws_secret_access_key='dummy')
            print("🔗 Testing DynamoDB Local connection...")
        except:
            # AWS DynamoDB 사용
            dynamodb = boto3.resource('dynamodb')
            print("🔗 Testing AWS DynamoDB connection...")
        
        table = dynamodb.Table(table_name)
        response = table.scan(Limit=3)
        
        print(f"📊 Found {response['Count']} items in table:")
        for item in response['Items']:
            print(f"   - {item.get('id', 'unknown')}: {item.get('title', 'No title')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing table access: {str(e)}")
        return False

def main():
    """메인 함수"""
    
    print("🗃️  Setting up local DynamoDB table for testing...")
    print()
    print("ℹ️  This script will:")
    print("   1. Create 'blog-table-local' table")
    print("   2. Insert sample blog posts")
    print("   3. Test table access")
    print()
    print("💡 Options:")
    print("   - DynamoDB Local: Run 'docker run -p 8000:8000 amazon/dynamodb-local'")
    print("   - AWS DynamoDB: Configure AWS credentials")
    print()
    
    # 사용자 확인
    response = input("Continue? (y/N): ").lower().strip()
    if response != 'y' and response != 'yes':
        print("❌ Cancelled by user")
        return
    
    print()
    
    # 테이블 생성 및 데이터 삽입
    if create_local_table():
        print()
        print("🧪 Testing table access...")
        test_table_access()
        
        print()
        print("✅ Local DynamoDB setup completed!")
        print()
        print("📋 Next steps:")
        print("   1. Run 'sam local start-api' to start the API")
        print("   2. Test with: curl http://localhost:3000/board")
        print()
        print("🔌 Connection options:")
        print("   - DynamoDB Local: http://localhost:8000")
        print("   - AWS DynamoDB: Use your configured credentials")
    else:
        print("❌ Failed to setup local DynamoDB table")

if __name__ == "__main__":
    main()
