#!/bin/bash

# 🛑 블로그 시스템 로컬 서버 종료 스크립트

echo "=== 🛑 로컬 블로그 시스템 종료 ==="

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# API 서버 종료
if [ -f api_server.pid ]; then
    PID=$(cat api_server.pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        print_success "API 서버 종료됨 (PID: $PID)"
        rm api_server.pid
    else
        print_warning "PID 파일은 있지만 프로세스가 실행 중이지 않습니다"
        rm api_server.pid
    fi
else
    print_warning "api_server.pid 파일을 찾을 수 없습니다"
fi

# 포트 3002에서 실행 중인 모든 프로세스 종료
if lsof -ti:3002 > /dev/null 2>&1; then
    lsof -ti:3002 | xargs kill -9
    print_success "포트 3002의 모든 프로세스 종료됨"
else
    print_success "포트 3002에 실행 중인 프로세스가 없습니다"
fi

# DynamoDB Local은 유지 (다른 프로젝트에서 사용할 수 있음)
if docker ps | grep -q dynamodb-local; then
    print_warning "DynamoDB Local은 계속 실행됩니다 (필요시 'docker stop dynamodb-local'로 종료)"
else
    print_success "DynamoDB Local이 실행 중이지 않습니다"
fi

print_success "🏁 로컬 블로그 시스템이 종료되었습니다"
