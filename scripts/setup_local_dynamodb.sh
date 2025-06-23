#!/bin/bash

# 로컬 DynamoDB 테스트용 스크립트
# 사용법: ./scripts/test_local.sh

echo "=== 로컬 환경 테스트 스크립트 ==="

# DynamoDB Local 실행 여부 확인
check_dynamodb_local() {
    if curl -s http://localhost:8000 > /dev/null 2>&1; then
        echo "✅ DynamoDB Local이 실행 중입니다."
        return 0
    else
        echo "❌ DynamoDB Local이 실행되지 않았습니다."
        echo "다음 명령어로 실행하세요:"
        echo "docker run -p 8000:8000 amazon/dynamodb-local"
        return 1
    fi
}

# 테이블 생성
create_test_table() {
    echo "🔧 테스트 테이블 생성 중..."
    
    aws dynamodb create-table \
        --table-name myapp-local-table \
        --attribute-definitions \
            AttributeName=id,AttributeType=S \
            AttributeName=type,AttributeType=S \
        --key-schema \
            AttributeName=id,KeyType=HASH \
            AttributeName=type,KeyType=RANGE \
        --billing-mode PAY_PER_REQUEST \
        --endpoint-url http://localhost:8000 \
        --region us-east-1 2>/dev/null
        
    if [ $? -eq 0 ]; then
        echo "✅ 테이블 'myapp-local-table' 생성 완료"
    else
        echo "ℹ️  테이블이 이미 존재하거나 생성할 수 없습니다."
    fi
}

# 샘플 데이터 삽입
insert_sample_data() {
    echo "📝 샘플 데이터 삽입 중..."
    
    # 샘플 사용자 1
    aws dynamodb put-item \
        --table-name myapp-local-table \
        --item '{
            "id": {"S": "user_test_001"},
            "type": {"S": "user"},
            "name": {"S": "테스트 사용자 1"},
            "email": {"S": "test1@example.com"},
            "created_at": {"S": "2024-01-01T00:00:00Z"},
            "updated_at": {"S": "2024-01-01T00:00:00Z"}
        }' \
        --endpoint-url http://localhost:8000 \
        --region us-east-1 2>/dev/null
        
    # 샘플 사용자 2
    aws dynamodb put-item \
        --table-name myapp-local-table \
        --item '{
            "id": {"S": "user_test_002"},
            "type": {"S": "user"},
            "name": {"S": "테스트 사용자 2"},
            "email": {"S": "test2@example.com"},
            "created_at": {"S": "2024-01-02T00:00:00Z"},
            "updated_at": {"S": "2024-01-02T00:00:00Z"}
        }' \
        --endpoint-url http://localhost:8000 \
        --region us-east-1 2>/dev/null
        
    echo "✅ 샘플 데이터 삽입 완료"
}

# 테이블 조회
list_items() {
    echo "📋 테이블 데이터 조회:"
    aws dynamodb scan \
        --table-name myapp-local-table \
        --endpoint-url http://localhost:8000 \
        --region us-east-1 \
        --output table 2>/dev/null
}

# 메인 실행
main() {
    if check_dynamodb_local; then
        create_test_table
        insert_sample_data
        list_items
        
        echo ""
        echo "🚀 로컬 테스트 환경 준비 완료!"
        echo "이제 SAM Local을 시작할 수 있습니다:"
        echo "sam local start-api --env-vars env.json"
    fi
}

main
