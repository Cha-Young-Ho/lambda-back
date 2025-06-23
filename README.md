# 🚀 SAM 기반 블로그 시스템

완전한 서버리스 블로그 관리 시스템입니다. DynamoDB Local과 연동하여 로컬 환경에서도 완벽하게 테스트할 수 있습니다.

## ✨ 주요 기능

- **관리자 인증**: JWT 기반 로그인 시스템
- **게시판 관리**: CRUD 기능 (생성/조회/수정/삭제)
- **실시간 데이터**: DynamoDB Local 연동
- **조회수 추적**: 자동 조회수 증가
- **최신순 정렬**: GSI를 활용한 효율적인 정렬

## 🏗️ 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Gateway   │────│ Lambda Functions │────│   DynamoDB      │
│                 │    │                 │    │                 │
│ - CORS 설정     │    │ - AuthFunction  │    │ - BlogTable     │
│ - 라우팅        │    │ - BoardFunction │    │ - GSI1 (최신순) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                │
                       ┌─────────────────┐
                       │      S3         │
                       │                 │
                       │ - 이미지 저장   │
                       └─────────────────┘
```

## 🚀 빠른 시작

### 1. 전체 시스템 시작
```bash
# 블로그 시스템 전체 시작 (DynamoDB + API 서버)
./scripts/start_local_blog.sh
```

### 2. API 테스트
```bash
# 자동 API 테스트 실행
./scripts/test_local_blog.sh
```

### 3. 시스템 종료
```bash
# 블로그 시스템 종료
./scripts/stop_local_blog.sh
```

## 📋 API 엔드포인트

### 공개 API
| 메소드 | 엔드포인트 | 설명 | 예시 |
|--------|-----------|------|------|
| GET | `/board` | 게시글 목록 조회 | `curl http://localhost:3002/board` |
| GET | `/board/{id}` | 게시글 상세 조회 | `curl http://localhost:3002/board/1` |

### 관리자 API (인증 필요)
| 메소드 | 엔드포인트 | 설명 | 인증 |
|--------|-----------|------|------|
| POST | `/auth/login` | 관리자 로그인 | ❌ |
| POST | `/board` | 게시글 생성 | ✅ Bearer Token |
| PUT | `/board/{id}` | 게시글 수정 | ✅ Bearer Token |
| DELETE | `/board/{id}` | 게시글 삭제 | ✅ Bearer Token |

## 🧪 API 사용 예제

### 1. 게시글 목록 조회
```bash
curl -s http://localhost:3002/board | jq .
```

### 2. 관리자 로그인
```bash
curl -s -X POST http://localhost:3002/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | jq .
```

### 3. 새 게시글 작성
```bash
TOKEN="YOUR_JWT_TOKEN_HERE"

curl -s -X POST http://localhost:3002/board \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"title": "새로운 게시글", "content": "게시글 내용입니다"}' | jq .
```

## 🗄️ 데이터베이스 구조

### BlogTable (DynamoDB)
```
PK: BOARD#{boardId}    SK: POST
GSI1PK: BOARD         GSI1SK: {createdAt}

속성:
- boardId: 게시글 ID
- title: 제목
- content: 내용
- author: 작성자
- createdAt: 생성일시
- updatedAt: 수정일시
- viewCount: 조회수
- status: 상태 (published/draft)
```

## 🛠️ 개발 환경 설정

### 필수 요구사항
- Docker (DynamoDB Local용)
- AWS SAM CLI
- Python 3.11+
- curl, jq (테스트용)

### 환경 변수 (env.json)
```json
{
  "AuthFunction": {
    "JWT_SECRET": "your-secret-key"
  },
  "BoardFunction": {
    "JWT_SECRET": "your-secret-key",
    "TABLE_NAME": "BlogTable"
  }
}
```

## 📊 현재 상태

✅ **완료된 기능:**
- DynamoDB Local 연동
- 게시글 CRUD 기능
- JWT 기반 인증
- 조회수 추적
- 최신순 정렬

🚧 **개발 예정:**
- 이미지 업로드 (S3 연동)
- 게시글 수정/삭제 API
- 페이징 처리
- 검색 기능

## 🐛 문제 해결

### 서버가 시작되지 않는 경우
```bash
# 포트 충돌 해결
lsof -ti:3002 | xargs kill -9
lsof -ti:8000 | xargs kill -9

# DynamoDB Local 재시작
docker restart dynamodb-local
```

### 데이터베이스 초기화
```bash
# 테이블 재생성
python setup_local_table.py
```

### 로그 확인
```bash
# API 서버 로그
tail -f api_server.log

# DynamoDB Local 로그
docker logs dynamodb-local
```

## 📝 라이센스

MIT License

---

**🎉 즐거운 개발 되세요!** 

문의사항이 있으시면 이슈를 생성해 주세요.

