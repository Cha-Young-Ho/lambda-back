# Blog Management System - Local Development

.PHONY: help setup start stop clean build test logs

# 기본 타겟
help: ## 도움말 표시
	@echo "📋 사용 가능한 명령어:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "   \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## 로컬 개발 환경 전체 설정 (최초 실행)
	@echo "🚀 로컬 개발 환경 설정 중..."
	./setup_local.sh

start: ## DynamoDB Local 서비스 시작
	@echo "▶️  DynamoDB Local 시작 중..."
	docker-compose up -d
	@echo "✅ 서비스 시작 완료"
	@echo "   🗄️  DynamoDB Local: http://localhost:8000"
	@echo "   🖥️  DynamoDB Admin: http://localhost:8001"

stop: ## DynamoDB Local 서비스 중지
	@echo "⏹️  DynamoDB Local 중지 중..."
	docker-compose down
	@echo "✅ 서비스 중지 완료"

clean: ## 모든 컨테이너 및 볼륨 삭제 (데이터 초기화)
	@echo "🧹 데이터 정리 중..."
	docker-compose down -v --remove-orphans
	@echo "✅ 정리 완료"

build: ## SAM 애플리케이션 빌드
	@echo "🔨 SAM 빌드 중..."
	cd .. && sam build
	@echo "✅ 빌드 완료"

run: build ## SAM Local API 실행
	@echo "🚀 SAM Local API 시작 중..."
	@echo "   API 엔드포인트: http://localhost:3000"
	cd .. && sam local start-api --env-vars env.json

test: ## API 테스트 실행
	@echo "🧪 API 테스트 중..."
	@echo "📋 게시글 목록 조회:"
	@curl -s http://localhost:3000/board | jq . || echo "❌ API가 실행되고 있지 않습니다. 'make run'으로 API를 시작하세요."

logs: ## 컨테이너 로그 확인
	@echo "📋 컨테이너 로그:"
	docker-compose logs -f

status: ## 서비스 상태 확인
	@echo "📊 서비스 상태:"
	@docker-compose ps
	@echo ""
	@echo "🔗 서비스 URL:"
	@echo "   DynamoDB Local: http://localhost:8000"
	@echo "   DynamoDB Admin: http://localhost:8001"
	@echo "   SAM Local API: http://localhost:3000 (실행 중인 경우)"

install-deps: ## 개발 의존성 설치
	@echo "📦 의존성 설치 중..."
	@if [ ! -d "../venv" ]; then cd .. && python3 -m venv venv; fi
	@cd .. && source venv/bin/activate && pip install boto3
	@echo "✅ 의존성 설치 완료"

create-table: install-deps ## DynamoDB 테이블 재생성
	@echo "📊 DynamoDB 테이블 생성 중..."
	@cd .. && source venv/bin/activate && python3 local-setup/setup_local_table.py
	@echo "✅ 테이블 생성 완료"

# 개발 워크플로우 단축키
dev: setup build run ## 전체 개발 환경 설정 및 실행

quick-start: start build run ## 빠른 시작 (설정 완료된 경우)
