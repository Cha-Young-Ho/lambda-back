#!/bin/bash

# 🚀 블로그 시스템 로컬 테스트 가이드
# 작성일: 2025-06-24

echo "=== 🎯 블로그 시스템 로컬 테스트 가이드 ==="
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 단계별 실행 함수
step_number=1

print_step() {
    echo -e "${BLUE}=== 단계 $step_number: $1 ===${NC}"
    step_number=$((step_number + 1))
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 1. 환경 확인
print_step "환경 확인"
echo "필수 도구들이 설치되어 있는지 확인합니다..."

if command -v docker &> /dev/null; then
    print_success "Docker 설치됨"
else
    print_error "Docker가 설치되지 않았습니다"
    exit 1
fi

if command -v sam &> /dev/null; then
    print_success "AWS SAM CLI 설치됨"
else
    print_error "AWS SAM CLI가 설치되지 않았습니다"
    exit 1
fi

if command -v curl &> /dev/null; then
    print_success "curl 설치됨"
else
    print_error "curl이 설치되지 않았습니다"
    exit 1
fi

if command -v jq &> /dev/null; then
    print_success "jq 설치됨"
else
    print_warning "jq가 설치되지 않았습니다 (JSON 파싱용, 선택사항)"
fi

echo ""

# 2. DynamoDB Local 시작
print_step "DynamoDB Local 시작"
if docker ps | grep -q dynamodb-local; then
    print_success "DynamoDB Local이 이미 실행 중입니다"
else
    echo "DynamoDB Local 컨테이너를 시작합니다..."
    if docker start dynamodb-local 2>/dev/null || docker run -d -p 8000:8000 --name dynamodb-local amazon/dynamodb-local; then
        print_success "DynamoDB Local 시작됨"
        sleep 3  # 시작 대기
    else
        print_error "DynamoDB Local 시작 실패"
        exit 1
    fi
fi

# DynamoDB Local 연결 확인
if curl -s http://localhost:8000 > /dev/null; then
    print_success "DynamoDB Local 연결 확인됨 (포트 8000)"
else
    print_error "DynamoDB Local에 연결할 수 없습니다"
    exit 1
fi

echo ""

# 3. 테이블 생성 및 샘플 데이터 추가
print_step "블로그 테이블 생성"
echo "BlogTable 테이블을 생성하고 샘플 데이터를 추가합니다..."

cd /Users/younghocha/my-project/base/backend
if python setup_local_table.py; then
    print_success "블로그 테이블 및 샘플 데이터 생성 완료"
else
    print_warning "테이블 생성 중 오류 발생 (이미 존재할 수 있음)"
fi

echo ""

# 4. SAM 빌드
print_step "SAM 애플리케이션 빌드"
echo "Lambda 함수들을 빌드합니다..."

if sam build; then
    print_success "SAM 빌드 완료"
else
    print_error "SAM 빌드 실패"
    exit 1
fi

echo ""

# 5. API 서버 시작 안내
print_step "API 서버 시작"
echo "로컬 API 서버를 시작합니다..."
echo -e "${YELLOW}주의: 이 명령은 서버를 백그라운드에서 실행합니다${NC}"
echo ""

# 기존 서버 종료
if lsof -ti:3002 > /dev/null 2>&1; then
    print_warning "포트 3002에서 실행 중인 프로세스를 종료합니다"
    lsof -ti:3002 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# 서버 시작
echo "API 서버를 시작합니다 (포트 3002)..."
nohup sam local start-api --port 3002 --env-vars env.json > api_server.log 2>&1 &
API_PID=$!
echo $API_PID > api_server.pid

# 서버 시작 대기
echo "서버 시작을 기다리는 중..."
sleep 10

# 서버 상태 확인
if curl -s http://localhost:3002/board > /dev/null; then
    print_success "API 서버가 성공적으로 시작되었습니다 (PID: $API_PID)"
    print_success "서버 로그: api_server.log"
else
    print_error "API 서버 시작 실패"
    print_warning "로그를 확인하세요: tail -f api_server.log"
    exit 1
fi

echo ""

# 6. 테스트 예제
print_step "API 테스트 예제"
echo "이제 다음 명령들로 블로그 시스템을 테스트할 수 있습니다:"
echo ""

echo -e "${BLUE}📋 게시글 목록 조회:${NC}"
echo "curl -s http://localhost:3002/board | jq ."
echo ""

echo -e "${BLUE}📖 게시글 상세 조회 (ID: 1):${NC}"
echo "curl -s http://localhost:3002/board/1 | jq ."
echo ""

echo -e "${BLUE}🔐 관리자 로그인:${NC}"
echo 'curl -s -X POST http://localhost:3002/auth/login \'
echo '  -H "Content-Type: application/json" \'
echo '  -d '\''{"username": "admin", "password": "admin123"}'\'' | jq .'
echo ""

echo -e "${BLUE}✍️  새 게시글 작성:${NC}"
echo 'curl -s -X POST http://localhost:3002/board \'
echo '  -H "Content-Type: application/json" \'
echo '  -H "Authorization: Bearer YOUR_TOKEN_HERE" \'
echo '  -d '\''{"title": "새로운 게시글", "content": "게시글 내용입니다"}'\'' | jq .'
echo ""

# 7. 서버 종료 안내
echo -e "${BLUE}🛑 서버 종료 방법:${NC}"
echo "1. 직접 종료: kill $API_PID"
echo "2. 스크립트 종료: ./scripts/stop_local_server.sh"
echo "3. 포트별 종료: lsof -ti:3002 | xargs kill -9"
echo ""

print_success "🎉 로컬 블로그 시스템이 준비되었습니다!"
print_success "🌐 API 서버: http://localhost:3002"
print_success "🗄️  DynamoDB Local: http://localhost:8000"

echo ""
echo -e "${YELLOW}💡 팁:${NC}"
echo "- API 서버 로그 확인: tail -f api_server.log"
echo "- DynamoDB Local 웹 쉘: http://localhost:8000/shell"
echo "- 게시글 목록 실시간 확인: watch 'curl -s http://localhost:3002/board | jq .'"
