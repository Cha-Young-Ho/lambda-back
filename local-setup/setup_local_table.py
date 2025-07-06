#!/usr/bin/env python3
"""
로컬 DynamoDB 테이블 설정 스크립트
로컬 환경에서 DynamoDB 테이블을 생성하고 샘플 데이터를 삽입합니다.
"""

import boto3
import json
from datetime import datetime, timezone
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
    
    table_name = 'blog-table'
    
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
        # News 데이터
        {
            'id': 'news_1',
            'content_type': 'news',
            'title': '가족센터 2025년 상반기 사업계획 발표',
            'content': '올해 상반기 가족센터의 주요 사업계획을 발표합니다.',
            'category': '주요소식',
            'created_at': '2025-07-03T10:00:00Z',
            'status': 'published',
            'image_url': 'https://example.com/images/business-plan.jpg',
            'short_description': '올해 상반기 가족센터의 주요 사업계획을 발표합니다.'
        },
        {
            'id': 'news_2',
            'content_type': 'news',
            'title': '다문화가족 지원 정책 개선안 공지',
            'content': '다문화가족을 위한 새로운 지원 정책이 개선되었습니다.',
            'category': '정책소식',
            'created_at': '2025-07-02T14:30:00Z',
            'status': 'published',
            'image_url': 'https://example.com/images/policy-update.jpg',
            'short_description': '다문화가족을 위한 새로운 지원 정책이 개선되었습니다.'
        },
        # Gallery 데이터
        {
            'id': 'gallery_1',
            'content_type': 'gallery',
            'title': '다문화가족 지원 서비스 안내서',
            'content': '다문화가족을 위한 종합 지원 서비스 안내서입니다.',
            'category': '자료실',
            'created_at': '2025-07-03T09:00:00Z',
            'status': 'published',
            'image_url': 'https://example.com/images/guide-cover.jpg',
            'short_description': '다문화가족을 위한 종합 지원 서비스 안내서입니다.',
            'file_url': 'https://example.com/files/multicultural-guide.pdf',
            'file_name': '다문화가족_지원서비스_안내서.pdf',
            'file_size': 2048576
        },
        {
            'id': 'gallery_2',
            'content_type': 'gallery',
            'title': '가족상담 신청서 양식',
            'content': '가족상담을 신청하실 때 사용하는 양식입니다.',
            'category': '양식다운로드',
            'created_at': '2025-07-02T14:00:00Z',
            'status': 'published',
            'image_url': 'https://example.com/images/form-preview.jpg',
            'short_description': '가족상담을 신청하실 때 사용하는 양식입니다.',
            'file_url': 'https://example.com/files/counseling-application.pdf',
            'file_name': '가족상담_신청서.pdf',
            'file_size': 512000
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

def test_table_access(table_name='blog-table'):
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
    print("   1. Create 'blog-table' table")
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
        print("   2. Test with: curl http://localhost:3000/news")
        print()
        print("🔌 Connection options:")
        print("   - DynamoDB Local: http://localhost:8000")
        print("   - AWS DynamoDB: Use your configured credentials")
    else:
        print("❌ Failed to setup local DynamoDB table")

if __name__ == "__main__":
    main()
