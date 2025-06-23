# 블로그 시스템 Secrets Manager 설정

AWS Secrets Manager에 블로그 시스템 설정을 저장하세요.

## Dev 환경 설정
Secret Name: `blog/dev/config`
```json
{
  "dynamodb": {
    "table_name": "blog-dev-table",
    "endpoint_url": null
  },
  "s3": {
    "bucket_name": "blog-images-dev-123456789012"
  },
  "admin": {
    "username": "admin",
    "password": "your_secure_password_here",
    "jwt_secret": "your_jwt_secret_key_minimum_32_characters_long"
  }
}
```

## Prod 환경 설정
Secret Name: `blog/prod/config`
```json
{
  "dynamodb": {
    "table_name": "blog-prod-table",
    "endpoint_url": null
  },
  "s3": {
    "bucket_name": "blog-images-prod-123456789012"
  },
  "admin": {
    "username": "admin",
    "password": "your_very_secure_password_here",
    "jwt_secret": "your_production_jwt_secret_key_minimum_32_characters_long"
  }
}
```

## Local 환경 설정 (선택사항)
Secret Name: `blog/local/config`
```json
{
  "dynamodb": {
    "table_name": "blog-dev-table",
    "endpoint_url": "http://localhost:8000"
  },
  "s3": {
    "bucket_name": "blog-images-dev-123456789012"
  },
  "admin": {
    "username": "admin",
    "password": "admin123",
    "jwt_secret": "local_jwt_secret_key_for_testing_minimum_32_chars"
  }
}
```

## 블로그 DynamoDB 테이블 스키마

### 게시글 아이템 구조:
```json
{
  "pk": "BOARD#{board_id}",
  "sk": "BOARD#{board_id}",
  "gsi1pk": "BOARD",
  "gsi1sk": "{created_at}",
  "title": "게시글 제목",
  "content": "게시글 내용",
  "created_at": "2024-06-24T12:00:00.000Z",
  "updated_at": "2024-06-24T12:00:00.000Z",
  "view_count": 0,
  "images": ["https://s3.amazonaws.com/bucket/image1.jpg"]
}
```

### GSI1 (생성일시 순 정렬용)
- gsi1pk: "BOARD" (모든 게시글)
- gsi1sk: created_at (최신순 정렬)

## 필요한 IAM 권한

Lambda 실행 역할에 다음 권한이 필요합니다:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:REGION:ACCOUNT:secret:blog/dev/config-*",
        "arn:aws:secretsmanager:REGION:ACCOUNT:secret:blog/prod/config-*"
      ]
    },
    {
      "Effect": "Allow", 
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:REGION:ACCOUNT:table/blog-dev-table",
        "arn:aws:dynamodb:REGION:ACCOUNT:table/blog-dev-table/index/*",
        "arn:aws:dynamodb:REGION:ACCOUNT:table/blog-prod-table",
        "arn:aws:dynamodb:REGION:ACCOUNT:table/blog-prod-table/index/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:PutObjectAcl"
      ],
      "Resource": [
        "arn:aws:s3:::blog-images-dev-*/*",
        "arn:aws:s3:::blog-images-prod-*/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::blog-images-dev-*",
        "arn:aws:s3:::blog-images-prod-*"
      ]
    }
  ]
}
```

## 관리자 자격증명 보안

1. **강력한 비밀번호 사용**: 최소 12자 이상, 특수문자 포함
2. **JWT Secret**: 최소 32자 이상의 랜덤 문자열 사용
3. **주기적 비밀번호 변경**: 3-6개월마다 변경 권장
4. **Secrets Manager 접근 제한**: 필요한 Lambda 함수에만 권한 부여

## API 엔드포인트

### 인증 API
- `POST /auth/login` - 관리자 로그인

### 게시판 API (공개)
- `GET /board` - 게시글 목록 조회
- `GET /board/{boardId}` - 게시글 상세 조회

### 게시판 API (관리자 전용)
- `POST /board` - 게시글 생성
- `PUT /board/{boardId}` - 게시글 수정
- `DELETE /board/{boardId}` - 게시글 삭제
- `POST /board/upload` - 이미지 업로드
