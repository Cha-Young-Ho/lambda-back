# Local Development Setup

이 디렉토리는 로컬 개발 환경 설정을 위한 스크립트들을 포함합니다.

## 🚀 빠른 시작

```bash
# 전체 환경 자동 설정 및 실행
make dev

# 또는 단계별 실행
./setup_local.sh    # 환경 설정
make build          # SAM 빌드  
make run            # API 실행
```

## 📋 포함된 파일들

- **`docker-compose.yml`** - DynamoDB Local + Admin UI
- **`setup_local.sh`** - 전체 환경 자동 설정 스크립트
- **`setup_local_table.py`** - DynamoDB 테이블 생성 및 샘플 데이터
- **`Makefile`** - 개발 작업 단축 명령어들

## 🔗 로컬 서비스

- **DynamoDB Local**: http://localhost:8000
- **DynamoDB Admin UI**: http://localhost:8001
- **SAM Local API**: http://localhost:3000

## 📋 자주 사용하는 명령어

```bash
make help           # 모든 명령어 보기
make start          # DynamoDB Local 시작
make stop           # DynamoDB Local 중지
make test           # API 테스트
make logs           # 로그 확인
make clean          # 데이터 초기화
```

## 🛠️ 수동 설정 (고급)

```bash
# 1. DynamoDB Local 시작
docker-compose up -d

# 2. Python 가상환경 설정
cd .. && python3 -m venv venv && source venv/bin/activate

# 3. 의존성 설치
pip install boto3

# 4. 테이블 생성
python3 local-setup/setup_local_table.py

# 5. SAM 실행
sam build
sam local start-api --env-vars env.json
```
