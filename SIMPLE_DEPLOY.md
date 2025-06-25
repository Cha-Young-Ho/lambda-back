# 단순화된 배포 가이드

태그 푸시만으로 Lambda 함수를 자동 업데이트하는 단순한 CI/CD 시스템입니다.

## 🚀 빠른 배포 방법

### 1. AWS 리소스 준비 (콘솔에서)

#### Secrets Manager 생성
1. AWS Console → Secrets Manager → Store a new secret
2. Secret type: Other type of secret
3. Key/value pairs:
```json
{
  "admin": {
    "username": "admin",
    "password": "admin123!"
  },
  "jwt_secret": "your-super-secret-jwt-key-32-chars"
}
```
4. Secret name: `blog/config`

#### DynamoDB 테이블 생성
1. AWS Console → DynamoDB → Create table
2. Table name: `blog-table`
3. Partition key: `id` (String)
4. Billing mode: On-demand
5. 기본 설정으로 생성

### 2. GitHub Secrets 설정

GitHub Repository → Settings → Secrets and variables → Actions

필요한 Secrets:
- `AWS_ACCESS_KEY_ID`: AWS 액세스 키
- `AWS_SECRET_ACCESS_KEY`: AWS 시크릿 키

### 3. 배포 실행

```bash
# 아무 버전 태그나 푸시하면 Lambda 업데이트
git tag v1.0.0
git push origin v1.0.0

# 또는
git tag v1.1.0
git push origin v1.1.0
```

## 📋 CI/CD가 자동으로 하는 일

1. ✅ SAM 빌드 및 배포
2. ✅ Lambda 함수 코드 업데이트  
3. ✅ 새 Lambda 버전 생성
4. ✅ 버전 정보 출력

## 🔧 설정된 리소스

### AWS Resources:
- **CloudFormation Stack**: `blog-system`
- **Lambda Functions**: `BlogAuth`, `BlogBoard`
- **API Gateway**: 단일 API (Prod stage)
- **Secrets Manager**: `blog/config`
- **DynamoDB**: `blog-table`

### API Endpoints:
- `POST /auth/login` - 관리자 로그인
- `GET /board` - 게시글 목록
- `GET /board/{id}` - 게시글 상세
- `POST /board` - 게시글 생성 (관리자)
- `PUT /board/{id}` - 게시글 수정 (관리자)
- `DELETE /board/{id}` - 게시글 삭제 (관리자)

## 🎯 Lambda 버전 관리

### 자동 관리 (기본):
- Git 태그 푸시 → 새 Lambda 버전 자동 생성
- API Gateway는 `$LATEST` 사용 (자동 업데이트)

### 수동 관리 (필요시):
- AWS Console에서 API Gateway 설정 변경
- 특정 Lambda 버전을 API Gateway에 연결
- `manage_versions.sh` 스크립트 사용 가능

## 🧪 로컬 테스트

```bash
# DynamoDB Local 시작
docker run -p 8000:8000 amazon/dynamodb-local

# 로컬 테이블 생성
python setup_local_table.py

# SAM Local 실행
sam local start-api --env-vars env.json
```

## 📖 사용 예시

### 1. 관리자 로그인
```bash
curl -X POST https://your-api.amazonaws.com/Prod/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123!"}'
```

### 2. 게시글 목록 조회
```bash
curl https://your-api.amazonaws.com/Prod/board
```

### 3. 게시글 생성 (토큰 필요)
```bash
curl -X POST https://your-api.amazonaws.com/Prod/board \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"title": "New Post", "content": "Post content"}'
```

## 🔄 배포 워크플로우

```
Git Tag Push → GitHub Actions → SAM Deploy → Lambda Update → Version Created
```

## 📝 중요 사항

- **API Gateway 설정**: 기존 설정 유지됨
- **Lambda 버전**: 태그별로 자동 생성
- **수동 제어**: AWS Console에서 언제든 변경 가능
- **백업**: Lambda 버전으로 롤백 가능

## 🛠️ 트러블슈팅

### 권한 오류
- IAM 사용자 권한 확인
- `DEPLOY_GUIDE.md` 참고

### 배포 실패
- CloudFormation 스택 상태 확인
- AWS 리소스 생성 여부 확인

### Lambda 함수 404
- API Gateway 배포 상태 확인
- Lambda 통합 설정 확인
