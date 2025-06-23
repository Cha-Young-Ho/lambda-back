# 블로그 관리 시스템 (SAM + Python + DynamoDB + S3)

## 프로젝트 개요

이 프로젝트는 AWS SAM을 사용한 서버리스 블로그 관리 시스템입니다. 관리자 인증을 통해 게시글을 CRUD할 수 있으며, 이미지 업로드를 지원합니다.

### 주요 특징
- **관리자 인증 시스템**: JWT 기반 토큰 인증
- **게시판 CRUD**: 생성, 조회, 수정, 삭제 기능
- **이미지 업로드**: S3를 통한 이미지 저장
- **이전글/다음글**: 게시글 간 네비게이션
- **공개/비공개**: 조회는 공개, CRUD는 관리자 전용
- **Secrets Manager**: 관리자 자격증명 안전 관리
- **CORS 지원**: 웹 애플리케이션에서 API 호출 가능

## 아키텍처

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │───▶│   API Gateway    │───▶│   Lambda        │
│   (React 등)    │    │                  │    │   Functions     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
                       ┌─────────────────┐             │
                       │   S3 Bucket     │◀────────────┤
                       │   (Images)      │             │
                       └─────────────────┘             │
                                                        │
                       ┌─────────────────┐             │
                       │   DynamoDB      │◀────────────┤
                       │   (Posts)       │             │
                       └─────────────────┘             │
                                                        │
                       ┌─────────────────┐             │
                       │ Secrets Manager │◀────────────┘
                       │   (Config)      │
                       └─────────────────┘
```

## 환경 설정

### 1. Secrets Manager 설정

각 환경별로 AWS Secrets Manager에 설정을 저장하세요. 자세한 내용은 `SECRETS_SETUP.md`를 참조하세요.

### 2. DynamoDB 테이블 생성

SAM 템플릿이 자동으로 테이블을 생성하지만, 수동으로 생성하려면:

```bash
# Dev 환경 테이블
aws dynamodb create-table \
  --table-name blog-dev-table \
  --attribute-definitions \
    AttributeName=pk,AttributeType=S \
    AttributeName=sk,AttributeType=S \
    AttributeName=gsi1pk,AttributeType=S \
    AttributeName=gsi1sk,AttributeType=S \
  --key-schema \
    AttributeName=pk,KeyType=HASH \
    AttributeName=sk,KeyType=RANGE \
  --global-secondary-indexes \
    IndexName=GSI1,KeySchema=[{AttributeName=gsi1pk,KeyType=HASH},{AttributeName=gsi1sk,KeyType=RANGE}],Projection={ProjectionType=ALL} \
  --billing-mode PAY_PER_REQUEST

# Prod 환경 테이블  
aws dynamodb create-table \
  --table-name blog-prod-table \
  --attribute-definitions \
    AttributeName=pk,AttributeType=S \
    AttributeName=sk,AttributeType=S \
    AttributeName=gsi1pk,AttributeType=S \
    AttributeName=gsi1sk,AttributeType=S \
  --key-schema \
    AttributeName=pk,KeyType=HASH \
    AttributeName=sk,KeyType=RANGE \
  --global-secondary-indexes \
    IndexName=GSI1,KeySchema=[{AttributeName=gsi1pk,KeyType=HASH},{AttributeName=gsi1sk,KeyType=RANGE}],Projection={ProjectionType=ALL} \
  --billing-mode PAY_PER_REQUEST
```

### 3. S3 버킷 생성

이미지 저장용 S3 버킷도 SAM 템플릿이 자동으로 생성하지만, 수동으로 생성하려면:

```bash
# Dev 환경 버킷
aws s3 mb s3://blog-images-dev-123456789012

# Prod 환경 버킷
aws s3 mb s3://blog-images-prod-123456789012
```

### 4. IAM 권한 설정

Lambda 실행 역할에 다음 권한을 추가하세요:
- DynamoDB 테이블 및 GSI 접근 권한
- S3 버킷 읽기/쓰기 권한
- Secrets Manager 읽기 권한

자세한 내용은 `SECRETS_SETUP.md`의 IAM 권한 섹션을 참조하세요.

## 로컬 개발

### 1. DynamoDB Local 실행 (선택사항)

```bash
# Docker로 DynamoDB Local 실행
docker run -p 8000:8000 amazon/dynamodb-local

# 또는 별도 터미널에서 백그라운드 실행
docker run -d -p 8000:8000 amazon/dynamodb-local
```

### 2. 로컬 테이블 및 샘플 데이터 설정 (선택사항)

```bash
python setup_local_table.py
```

### 3. SAM Local 실행

```bash
sam build
sam local start-api --env-vars env.json --port 3002
```

### 4. API 테스트

로컬 서버가 실행되면 다음 API들을 테스트할 수 있습니다:

```bash
# 게시글 목록 조회 (공개)
curl http://localhost:3002/board

# 게시글 상세 조회 (공개)
curl http://localhost:3002/board/1

# 관리자 로그인
curl -X POST http://localhost:3002/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# 토큰을 받은 후 게시글 생성 (관리자 전용)
curl -X POST http://localhost:3002/board \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {받은_토큰}" \
  -d '{"title": "새 게시글", "content": "게시글 내용"}'

# 게시글 수정 (관리자 전용)
curl -X PUT http://localhost:3002/board/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {받은_토큰}" \
  -d '{"title": "수정된 제목", "content": "수정된 내용"}'

# 게시글 삭제 (관리자 전용)
curl -X DELETE http://localhost:3002/board/1 \
  -H "Authorization: Bearer {받은_토큰}"

# 이미지 업로드 (관리자 전용)
curl -X POST http://localhost:3002/board/upload \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {받은_토큰}" \
  -d '{"image_data": "base64_encoded_image", "filename": "image.jpg"}'
```

## 배포 방법

### GitHub Actions 자동 배포

This project is configured with GitHub Actions for automatic deployment.
When you push to the `main` branch, the workflow will:
1. Build the SAM application
2. Deploy it to AWS using the configured credentials

#### 필요한 GitHub Secrets:
- `AWS_ACCESS_KEY_ID`: AWS 액세스 키
- `AWS_SECRET_ACCESS_KEY`: AWS 시크릿 키  
- `AWS_REGION`: 배포할 AWS 리전
- `AWS_ROLE_TO_ASSUME`: 배포에 사용할 AWS IAM 역할 ARN

### 수동 배포

```bash
# Dev 환경 배포
sam build
sam deploy --parameter-overrides Stage=dev

# Prod 환경 배포  
sam deploy --parameter-overrides Stage=prod
```

## API 엔드포인트

### 인증 API
- `POST /auth/login`: 관리자 로그인 (username, password → JWT 토큰)

### 게시판 API (공개)
- `GET /board`: 게시글 목록 조회 (페이징 지원)
- `GET /board/{boardId}`: 게시글 상세 조회 (조회수 자동 증가)

### 게시판 API (관리자 전용)
- `POST /board`: 게시글 생성 (제목, 내용, 이미지)
- `PUT /board/{boardId}`: 게시글 수정
- `DELETE /board/{boardId}`: 게시글 삭제 (연관 이미지도 삭제)
- `POST /board/upload`: 이미지 업로드 (S3)

### 기능
- **이전글/다음글**: 게시글 상세 조회 시 자동 포함
- **조회수**: 게시글 조회 시 자동 증가
- **JWT 인증**: 관리자 작업에 토큰 필수
- **CORS 지원**: 모든 엔드포인트에서 지원

## 문제 해결

### 1. Secrets Manager 접근 오류
- Lambda 실행 역할에 secretsmanager:GetSecretValue 권한이 있는지 확인
- Secret 이름이 올바른지 확인 (`blog/{stage}/config`)

### 2. DynamoDB 접근 오류
- Lambda 실행 역할에 DynamoDB 권한이 있는지 확인
- 테이블이 존재하는지 확인 (`blog-{stage}-table`)
- GSI 접근 권한도 확인

### 3. S3 업로드 오류
- Lambda 실행 역할에 S3 권한이 있는지 확인
- 버킷이 존재하는지 확인 (`blog-images-{stage}-{account}`)

### 4. 인증 오류
- JWT 토큰이 올바른지 확인
- Authorization 헤더 형식: `Bearer {token}`
- 토큰 만료 시간 확인 (기본 24시간)

### 5. CORS 오류
- API Gateway에서 CORS가 올바르게 설정되었는지 확인
- OPTIONS 메서드가 구현되어 있는지 확인

## 프로젝트 구조

```
├── README.md
├── template.yaml              # SAM 템플릿
├── requirements.txt           # Python 의존성
├── SECRETS_SETUP.md          # Secrets Manager 설정 가이드
├── env.json                  # 로컬 환경 변수
├── common/                   # 공통 모듈
│   ├── __init__.py
│   ├── config.py            # 설정 관리
│   └── dynamodb_client.py   # DynamoDB 클라이언트
├── hello/                   # Hello Lambda 함수
│   └── app.py
├── users/                   # Users Lambda 함수  
│   └── app.py
└── scripts/
    └── setup_local_dynamodb.sh  # 로컬 DynamoDB 설정 스크립트
```

## ✅ PROJECT STATUS UPDATE

### 🎉 COMPLETED FEATURES

#### 1. **DynamoDB Integration - WORKING** ✅
- **Hello API**: Successfully logging visits to DynamoDB Local
- **Users API**: Complete CRUD operations working with DynamoDB
- **Table Structure**: Using pk/sk pattern for single-table design
- **Local Development**: DynamoDB Local running in Docker container

#### 2. **Environment Configuration - WORKING** ✅
- **Local Environment**: Uses default config with DynamoDB Local endpoint
- **Secrets Manager Integration**: Ready for dev/prod environments
- **Environment Variables**: Proper AWS credentials for local testing
- **Stage Detection**: Automatic stage detection (local/dev/prod)

#### 3. **API Endpoints - FULLY FUNCTIONAL** ✅

**Hello API** (`/hello`):
- ✅ GET with optional `?name=` parameter
- ✅ Logs visits to DynamoDB with timestamp and user info
- ✅ Response time: ~1.5-3.5 seconds (acceptable for local dev)

**Users API** (`/users`):
- ✅ GET `/users` - List all users with pagination
- ✅ POST `/users` - Create new user with validation
- ✅ GET `/users/{userId}` - Get specific user details
- ✅ PUT `/users/{userId}` - Update user information
- ✅ DELETE `/users/{userId}` - Delete user
- ✅ OPTIONS - CORS preflight support

#### 4. **Local Development Environment - FULLY SETUP** ✅
- **DynamoDB Local**: Running on Docker with sample data
- **SAM Local**: API Gateway simulation working perfectly
- **Table Creation**: Automated script for local table setup
- **Sample Data**: Pre-populated users for testing

### 📊 CURRENT TEST RESULTS

```bash
# Hello API Test
curl "http://127.0.0.1:3000/hello?name=Test"
→ Status: 200, log_saved: true ✅

# Users API Tests
curl "http://127.0.0.1:3000/users"
→ Status: 200, returns user list ✅

curl -X POST "http://127.0.0.1:3000/users" -d '{"name":"Test","email":"test@example.com"}'
→ Status: 201, user created ✅

curl "http://127.0.0.1:3000/users/{userId}"
→ Status: 200, user details ✅

curl -X PUT "http://127.0.0.1:3000/users/{userId}" -d '{"name":"Updated"}'
→ Status: 200, user updated ✅

curl -X DELETE "http://127.0.0.1:3000/users/{userId}"
→ Status: 200, user deleted ✅
```

### 🔧 DEVELOPMENT WORKFLOW

#### Quick Start Commands:
```bash
# 1. Start DynamoDB Local
docker run -d --name dynamodb-local -p 8000:8000 amazon/dynamodb-local -jar DynamoDBLocal.jar -inMemory -sharedDb

# 2. Create tables and sample data
source venv/bin/activate && python setup_local_table.py

# 3. Build and start SAM
sam build && sam local start-api --env-vars env.json

# 4. Test endpoints
curl "http://127.0.0.1:3000/hello?name=YourName"
curl "http://127.0.0.1:3000/users"
```

### 🎯 NEXT STEPS

#### 1. **Production Deployment** 🚀
- [ ] Set up Secrets Manager in AWS dev/prod accounts
- [ ] Deploy using `sam deploy --guided`
- [ ] Configure real DynamoDB tables in AWS
- [ ] Test end-to-end in AWS environment

#### 2. **Enhanced Features** 🛠️
- [ ] Add input validation and sanitization
- [ ] Implement JWT authentication
- [ ] Add comprehensive error logging
- [ ] Set up monitoring and alerting
- [ ] Add API rate limiting

#### 3. **Code Quality** 📝
- [ ] Add unit tests for Lambda functions
- [ ] Add integration tests
- [ ] Set up CI/CD pipeline
- [ ] Add code coverage reports
- [ ] Implement automated security scanning

#### 4. **Performance Optimization** ⚡
- [ ] Optimize DynamoDB queries with indexes
- [ ] Implement Lambda function optimization
- [ ] Add caching layer (ElastiCache)
- [ ] Set up Lambda connection pooling

### 🔒 SECURITY CONSIDERATIONS

- ✅ Environment variables properly configured
- ✅ No sensitive data in Git repository
- ✅ Secrets Manager integration ready
- ⚠️ **TODO**: Add input validation and sanitization
- ⚠️ **TODO**: Implement authentication/authorization
- ⚠️ **TODO**: Add request rate limiting

---

## 🎉 블로그 시스템 변환 완료!

### 변환된 기능들:
- ✅ **인증 시스템**: 관리자 로그인 (`POST /auth/login`)
- ✅ **게시판 조회**: 공개 게시글 목록/상세 (`GET /board`, `GET /board/{id}`)
- ✅ **게시판 관리**: 관리자 전용 CRUD (`POST/PUT/DELETE /board`)
- ✅ **이미지 업로드**: S3 연동 이미지 업로드 (`POST /board/upload`)
- ✅ **권한 관리**: JWT 토큰 기반 인증 및 권한 검증
- ✅ **CORS 지원**: 모든 엔드포인트에서 웹 애플리케이션 호출 가능

### 테스트 완료:
```bash
# 로컬 서버: http://127.0.0.1:3002
✅ GET  /board                    # 게시글 목록
✅ GET  /board/1                  # 게시글 상세 
✅ POST /auth/login               # 관리자 로그인
✅ POST /board (with auth)        # 게시글 생성
✅ POST /board (without auth)     # 권한 오류 (정상)
```

기존 Hello/Users API가 완전히 블로그 관리 시스템으로 변환되었습니다!

