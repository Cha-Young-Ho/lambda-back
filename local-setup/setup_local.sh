#!/bin/bash

# 로컬 개발 환경 자동 설정 스크립트
# 사용법: ./setup_local.sh

set -e

echo "🚀 로컬 개발 환경 설정 시작..."

# 색깔 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 함수: 색깔있는 출력
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
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

# 1. Docker 설치 확인
print_info "Docker 설치 확인 중..."
if ! command -v docker &> /dev/null; then
    print_error "Docker가 설치되어 있지 않습니다."
    print_info "Docker Desktop을 설치해주세요: https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose가 설치되어 있지 않습니다."
    print_info "Docker Desktop에 포함되어 있는지 확인해주세요."
    exit 1
fi

print_success "Docker 및 docker-compose 확인 완료"

# 2. Docker 서비스 실행 확인
print_info "Docker 서비스 실행 확인 중..."
if ! docker info &> /dev/null; then
    print_error "Docker 서비스가 실행되고 있지 않습니다."
    print_info "Docker Desktop을 실행해주세요."
    exit 1
fi

print_success "Docker 서비스 실행 확인 완료"

# 3. 기존 컨테이너 정리 (있다면)
print_info "기존 컨테이너 정리 중..."
docker-compose down --remove-orphans 2>/dev/null || true
print_success "기존 컨테이너 정리 완료"

# 4. DynamoDB Local 및 Admin 실행
print_info "DynamoDB Local 및 Admin UI 시작 중..."
docker-compose up -d

# 5. 컨테이너 시작 대기
print_info "컨테이너 시작 대기 중..."
sleep 10

# 6. DynamoDB 연결 확인
print_info "DynamoDB Local 연결 확인 중..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -s http://localhost:8000 > /dev/null 2>&1; then
        print_success "DynamoDB Local 연결 성공"
        break
    fi
    
    if [ $attempt -eq $max_attempts ]; then
        print_error "DynamoDB Local 연결 실패"
        print_info "docker-compose logs를 확인해주세요."
        exit 1
    fi
    
    print_info "연결 확인 중... ($attempt/$max_attempts)"
    sleep 2
    ((attempt++))
done

# 7. Python 가상환경 확인
print_info "Python 환경 확인 중..."
if ! command -v python3 &> /dev/null; then
    print_error "Python3가 설치되어 있지 않습니다."
    exit 1
fi

# 8. 가상환경 생성 (없다면)
if [ ! -d "../venv" ]; then
    print_info "Python 가상환경 생성 중..."
    cd .. && python3 -m venv venv && cd local-setup
    print_success "가상환경 생성 완료"
fi

# 9. 가상환경 활성화 및 패키지 설치
print_info "가상환경 활성화 및 의존성 설치 중..."
cd .. && source venv/bin/activate && cd local-setup

# boto3 설치 (DynamoDB 테이블 생성용)
cd .. && source venv/bin/activate && pip install boto3 > /dev/null 2>&1 && cd local-setup
print_success "의존성 설치 완료"

# 10. DynamoDB 테이블 생성
print_info "DynamoDB 테이블 생성 중..."
cd .. && source venv/bin/activate && python3 local-setup/setup_local_table.py && cd local-setup
print_success "DynamoDB 테이블 생성 완료"

# 11. SAM 설치 확인
print_info "SAM CLI 설치 확인 중..."
if ! command -v sam &> /dev/null; then
    print_warning "SAM CLI가 설치되어 있지 않습니다."
    print_info "설치 방법:"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        print_info "  brew install aws-sam-cli"
    else
        print_info "  https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html"
    fi
else
    print_success "SAM CLI 확인 완료"
fi

# 12. 환경 확인 및 정보 출력
echo ""
echo "🎉 로컬 개발 환경 설정 완료!"
echo ""
echo "📋 설정된 서비스:"
echo "   🗄️  DynamoDB Local: http://localhost:8000"
echo "   🖥️  DynamoDB Admin UI: http://localhost:8001"
echo "   📊 테이블: blog-table (샘플 데이터 포함)"
echo ""
echo "🚀 다음 단계:"
echo "   1. SAM 애플리케이션 빌드 및 실행:"
echo "      cd .."
echo "      sam build"
echo "      sam local start-api --env-vars env.json"
echo ""
echo "   2. API 테스트:"
echo "      curl http://localhost:3000/board"
echo ""
echo "🛠️  유용한 명령어:"
echo "   # 컨테이너 상태 확인"
echo "   docker-compose ps"
echo ""
echo "   # 컨테이너 로그 확인"
echo "   docker-compose logs"
echo ""
echo "   # 컨테이너 중지"
echo "   docker-compose down"
echo ""
echo "   # 볼륨까지 삭제 (데이터 초기화)"
echo "   docker-compose down -v"

# 가상환경 비활성화 안내
echo ""
print_info "가상환경이 활성화되어 있습니다. 비활성화하려면 'deactivate' 명령어를 사용하세요."
