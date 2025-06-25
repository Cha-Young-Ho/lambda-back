# Blog Management System

## 🚀 빠른 시작 가이드

### 1. 로컬 테스트
```bash
# 로컬 환경 설정 (env.json 생성)
python3 setup_secrets.py

# 로컬 DynamoDB 테이블 설정 (선택사항)
python3 setup_local_table.py

# SAM 빌드 및 실행
sam build
sam local start-api

# 테스트
curl http://localhost:3000/board
```

> **💡 로컬 DynamoDB 옵션:**
> - **DynamoDB Local**: `docker run -p 8000:8000 amazon/dynamodb-local`
> - **AWS DynamoDB**: AWS 계정의 테스트 테이블 사용
> - **샘플 데이터**: DynamoDB 연결 실패시 자동으로 사용됨

### 2. AWS 배포 (사전 설정 필요)
AWS 배포 전에 **반드시** 다음을 수동으로 설정하세요:

#### AWS Secrets Manager 설정
```bash
# 제공된 스크립트 사용
./setup_secrets.sh

# 또는 수동 생성
aws secretsmanager create-secret \
  --name "blog/dev/config" \
  --secret-string '{"admin":{"username":"admin","password":"your_password"},"jwt_secret":"your_32_char_secret"}'
```

#### DynamoDB 테이블 생성
```bash
aws dynamodb create-table \
  --table-name blog-table-dev \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

#### 배포 실행
```bash
sam deploy --parameter-overrides Stage=dev
```

## 아키텍처 개요

이 프로젝트는 AWS SAM(Serverless Application Model)을 사용한 블로그 관리 시스템입니다.

### 주요 구조
- **단일 API Gateway**: 하나의 API Gateway에서 dev/prod stage 관리
- **Lambda Alias**: 각 Lambda 함수는 stage별로 alias를 가짐 (dev, prod)
- **외부 리소스**: DynamoDB, S3는 별도로 생성하여 연결
- **단순화된 구조**: 최소한의 리소스로 Lambda 함수와 API Gateway만 관리

### 배포 구조
- **dev 브랜치 → dev stage**: 개발 환경 Lambda alias로 연결
- **main 브랜치 → prod stage**: 프로덕션 환경 Lambda alias로 연결
- **코드 업데이트**: 브랜치에 푸시하면 해당 stage의 alias가 새 버전을 가리킴

## Lambda 함수

### AuthFunction
- **기능**: 관리자 로그인 및 JWT 토큰 발급
- **엔드포인트**: `POST /auth/login`
- **요청**:
  ```json
  {
    "username": "admin",
    "password": "admin123"
  }
  ```
- **응답**:
  ```json
  {
    "message": "Login successful",
    "token": "jwt_token_here",
    "expiresIn": 86400
  }
  ```

### BoardFunction
- **기능**: 게시판 CRUD 작업
- **엔드포인트**:
  - `GET /board` - 게시글 목록 (공개)
  - `GET /board/{boardId}` - 게시글 상세 (공개)
  - `POST /board` - 게시글 생성 (관리자)
  - `PUT /board/{boardId}` - 게시글 수정 (관리자)
  - `DELETE /board/{boardId}` - 게시글 삭제 (관리자)
  - `POST /board/upload` - 이미지 업로드 (관리자)

## API 엔드포인트

### 공개 API (인증 불필요)
```bash
# 게시글 목록 조회
GET https://{api-gateway-id}.execute-api.{region}.amazonaws.com/{stage}/board

# 게시글 상세 조회
GET https://{api-gateway-id}.execute-api.{region}.amazonaws.com/{stage}/board/{boardId}

# 관리자 로그인
POST https://{api-gateway-id}.execute-api.{region}.amazonaws.com/{stage}/auth/login
```

### 관리자 API (JWT 토큰 필요)
```bash
# Authorization: Bearer {jwt_token}

# 게시글 생성
POST https://{api-gateway-id}.execute-api.{region}.amazonaws.com/{stage}/board

# 게시글 수정
PUT https://{api-gateway-id}.execute-api.{region}.amazonaws.com/{stage}/board/{boardId}

# 게시글 삭제
DELETE https://{api-gateway-id}.execute-api.{region}.amazonaws.com/{stage}/board/{boardId}

# 이미지 업로드
POST https://{api-gateway-id}.execute-api.{region}.amazonaws.com/{stage}/board/upload
```

## 로컬 개발

```bash
# SAM 빌드
sam build

# 로컬 API 서버 시작
sam local start-api --port 3000

# 테스트
curl http://localhost:3000/board
```

## 배포

### Stage별 배포

```bash
# Dev stage 배포
sam deploy --parameter-overrides Stage=dev

# Prod stage 배포
sam deploy --parameter-overrides Stage=prod
```

### Lambda Alias 관리

각 배포 시 새로운 Lambda 버전이 생성되고, stage에 해당하는 alias가 자동으로 업데이트됩니다:

- `BlogAuth:dev` → 개발 버전
- `BlogAuth:prod` → 프로덕션 버전
- `BlogBoard:dev` → 개발 버전
- `BlogBoard:prod` → 프로덕션 버전

## 환경별 설정

### Stage별 구조
- **local**: 로컬 개발 환경 (env.json 사용)
- **dev**: 개발 환경 (AWS Secrets Manager: `blog/dev/config`)
- **prod**: 프로덕션 환경 (AWS Secrets Manager: `blog/prod/config`)

### AWS Secrets Manager 설정

각 환경별로 Secret을 생성해야 합니다:

#### Dev 환경: `blog/dev/config`
```json
{
  "admin": {
    "username": "admin",
    "password": "dev_password"
  },
  "jwt_secret": "dev_jwt_secret_key_32_characters_long"
}
```

#### Prod 환경: `blog/prod/config`
```json
{
  "admin": {
    "username": "admin", 
    "password": "prod_secure_password"
  },
  "jwt_secret": "prod_jwt_secret_key_32_characters_long"
}
```

### DynamoDB 테이블 (수동 생성 필요)

**⚠️ 중요: DynamoDB 테이블은 자동 생성되지 않습니다. 각 환경별로 수동으로 생성해야 합니다.**

각 환경별로 다음 테이블을 생성하세요:
- **Dev**: `blog-table-dev`
- **Prod**: `blog-table-prod`

테이블 생성 명령어:
```bash
# Dev 환경
aws dynamodb create-table \
  --table-name blog-table-dev \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# Prod 환경  
aws dynamodb create-table \
  --table-name blog-table-prod \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

로컬 환경에서는 DynamoDB 연결 실패 시 샘플 데이터를 사용합니다.

### 환경 변수

### Lambda 함수 환경 변수
- `STAGE`: 현재 배포 stage (local/dev/prod)
- `JWT_SECRET`: JWT 토큰 서명용 비밀키 (로컬 환경에서만 사용)
- `TABLE_NAME`: DynamoDB 테이블 이름 (자동 설정)

## 보안 고려사항

- JWT 토큰 만료시간: 24시간
- 관리자 계정: username=admin, password=admin123 (실제 환경에서는 변경 필요)
- CORS: 모든 오리진 허용 (실제 환경에서는 제한 필요)

## 확장 가능한 기능

- DynamoDB 연결로 실제 데이터 저장
- S3 연결로 이미지 업로드
- 사용자 관리 시스템
- 게시글 카테고리 및 태그
- 검색 및 페이징
- 댓글 시스템

## 로컬 DynamoDB 테이블 설정

로컬 환경에서 실제 DynamoDB를 사용하려면 다음 스크립트를 실행하세요:

```bash
# 필요한 패키지 설치 (가상환경 사용 권장)
python3 -m venv venv
source venv/bin/activate
pip install boto3

# 로컬 DynamoDB 테이블 생성 및 샘플 데이터 삽입
python3 setup_local_table.py
```

### DynamoDB 연결 옵션

1. **DynamoDB Local (Docker)**:
   ```bash
   docker run -p 8000:8000 amazon/dynamodb-local
   ```

2. **AWS DynamoDB**: AWS 자격 증명 설정 후 실제 AWS 테이블 사용

3. **샘플 데이터**: DynamoDB 연결 실패시 Lambda 함수에서 자동으로 사용

