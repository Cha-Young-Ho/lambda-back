# Blog Management System

AWS SAM을 사용한 서버리스 블로그 관리 시스템입니다.

## 🚀 빠른 시작

### 1. AWS 리소스 준비 (콘솔에서)

#### Secrets Manager
- Secret 이름: `blog/config`
- Secret 값:
```json
{
  "admin": {
    "username": "admin",
    "password": "admin123!"
  },
  "jwt_secret": "your-super-secret-jwt-key-32-chars"
}
```

#### DynamoDB
- 테이블 이름: `blog-table`
- Primary key: `id` (String)
- Billing mode: On-demand

### 2. GitHub Secrets 설정
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

### 3. 배포
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
cd local-setup && docker-compose up -d

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