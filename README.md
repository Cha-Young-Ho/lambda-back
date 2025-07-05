# 🎉 Blog Management System

**상태**: ✅ 완료 | **버전**: v2.0 | **최종 업데이트**: 2025-07-06

AWS SAM을 사용한 서버리스 블로그 관리 시스템입니다. 완전히 리팩토링되어 현대적이고 유지보수가 용이한 구조로 재구성되었습니다.

## 📋 주요 기능

- ✅ **News API**: 뉴스 관리 (CRUD + 최근 항목 조회)
- ✅ **Gallery API**: 갤러리 관리 (CRUD + 최근 항목 조회)  
- ✅ **Auth API**: JWT 기반 인증 (로그인 + 토큰 검증)
- ✅ **표준화된 API 응답**: 일관성 있는 JSON 응답 형식
- ✅ **에러 처리**: 중앙집중식 에러 핸들링
- ✅ **성능 모니터링**: 구조화된 로깅 시스템
- ✅ **테스트 커버리지**: pytest + moto를 활용한 단위/통합 테스트

## 🚀 빠른 시작

### 1. 로컬 개발 환경 설정

```bash
# 1. 프로젝트 클론 및 의존성 설치
git clone <repository-url>
cd backend
pip install -r requirements.txt
pip install -r requirements-test.txt

# 2. 환경 설정 파일 생성
cp env.json.template env.json
# env.json 파일에서 필요한 값들 수정

# 3. DynamoDB Local 시작
cd local-setup
docker compose up -d

# 4. 샘플 데이터 삽입
python setup_local_table.py

# 5. SAM Local API 서버 시작
cd ..
sam local start-api --env-vars env.json --host 0.0.0.0 --port 3001
```

### 2. API 테스트

```bash
# 뉴스 목록 조회
curl http://localhost:3001/news

# 로그인
curl -X POST http://localhost:3001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# 종합 API 테스트 실행
./comprehensive_api_test.sh
```

### 3. 단위 테스트 실행

```bash
# 전체 테스트 실행
pytest tests/unit/ -v

# 커버리지 포함 테스트
pytest tests/unit/ --cov=layers/common-layer/python/common --cov-report=html
```

## 🏗️ 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Gateway   │    │   Lambda        │
│   (React/Vue)   │◄──►│  (SAM Local)    │◄──►│   Functions     │
│                 │    │   Port: 3001    │    │   (Auth/News/   │
└─────────────────┘    └─────────────────┘    │    Gallery)     │
                                               └─────────────────┘
                                                        │
                                               ┌─────────────────┐
                                               │   DynamoDB      │
                                               │   Local/AWS     │
                                               │                 │
                                               └─────────────────┘
```

## 📁 프로젝트 구조

```
backend/
├── 📄 README.md              # 프로젝트 가이드
├── 📄 template.yaml           # SAM 템플릿
├── 📄 env.json.template       # 환경 설정 템플릿
├── 🔧 pytest.ini            # 테스트 설정
├── 📦 requirements*.txt      # 의존성 목록
├── 🧪 comprehensive_api_test.sh  # API 테스트 스크립트
├── 🔐 auth/                  # 인증 서비스
├── 📰 news/                  # 뉴스 서비스
├── 🖼️ gallery/               # 갤러리 서비스
├── 📚 layers/common-layer/   # 공통 라이브러리
├── 🧪 tests/                 # 테스트 코드
├── 🐳 local-setup/           # 로컬 환경 설정
└── 📜 scripts/               # 유틸리티 스크립트
```

## 🎯 AWS 리소스 준비 (프로덕션)

### 1. DynamoDB 테이블
- 테이블 이름: `blog-table`
- Primary key: `id` (String)
- Billing mode: On-demand

### 2. Secrets Manager
- Secret 이름: `blog/config`
- Secret 값:
```json
{
  "admin": {
    "username": "admin",
    "password": "CHANGE_THIS_STRONG_PASSWORD"
  },
  "jwt_secret": "CHANGE_THIS_32_CHAR_SECRET_KEY"
}
```

### 3. GitHub Secrets 설정
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

### 4. 배포
```bash
git tag v1.0.0
git push origin v1.0.0
```

## 📋 API 엔드포인트

### 공개 API
- `GET /board` - 게시글 목록
- `GET /board/{id}` - 게시글 상세
- `POST /auth/login` - 관리자 로그인

### 관리자 API (JWT 토큰 필요)
- `POST /board` - 게시글 생성
- `PUT /board/{id}` - 게시글 수정
- `DELETE /board/{id}` - 게시글 삭제

## 🧪 로컬 개발 환경

### 🚀 빠른 시작 (최초 설정)
```bash
# 1. 로컬 환경 설정 파일 생성
cp env.json.sample env.json

# 2. 전체 환경 자동 설정 및 실행
cd local-setup
make dev

# 또는 단계별 실행
./setup_local.sh    # 환경 설정
make build          # SAM 빌드  
make run            # API 실행
```

### ⚠️ 중요사항
- **env.json**: 로컬 개발용으로만 사용 (Git에 포함되지 않음)
- **AWS 배포**: Secrets Manager에서 설정을 가져옴
- **환경 감지**: `AWS_LAMBDA_FUNCTION_NAME` 환경변수로 AWS/로컬 구분

### 📋 자주 사용하는 명령어
```bash
cd local-setup      # 로컬 설정 디렉토리로 이동

make help           # 모든 명령어 보기
make start          # DynamoDB Local 시작
make stop           # DynamoDB Local 중지
make test           # API 테스트
make logs           # 로그 확인
make clean          # 데이터 초기화
```

### 🔗 로컬 서비스 URL
- **DynamoDB Local**: http://localhost:8000
- **DynamoDB Admin UI**: http://localhost:8001  
- **SAM Local API**: http://localhost:3000

### 🛠️ 수동 설정 (고급 사용자)
```bash
# 1. DynamoDB Local 시작
cd local-setup && docker compose up -d

# 2. 테이블 생성
python local-setup/setup_local_table.py

# 3. SAM Local 실행
sam build
sam local start-api --env-vars env.json
```

## 🔄 배포 워크플로우

```
Git Tag Push → GitHub Actions → SAM Deploy → Lambda Update → Version Created
```

태그 푸시하면 자동으로:
1. Lambda 함수 업데이트
2. 새 버전 생성
3. 버전 정보 출력

API Gateway 설정은 그대로 유지됩니다.