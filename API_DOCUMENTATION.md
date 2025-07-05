# 가족센터 통합 API 문서

가족센터 웹사이트를 위한 게시판, 뉴스, 갤러리 통합 CRUD API입니다.

## 📋 API 개요

### 시스템 구성
- **게시판 API** (`/board`): 센터 소식, 프로그램 소식 등의 카드뷰 게시판
- **뉴스 API** (`/news`): 주요 소식, 정책 소식 등의 뉴스
- **갤러리 API** (`/gallery`): 자료실, 양식 다운로드 등의 파일 공유

### 공통 특징
- **DynamoDB 공유 테이블**: 모든 API가 동일한 테이블을 사용하되 `content_type`으로 구분
- **공개 읽기**: 모든 사용자가 목록/상세 조회 가능
- **관리자 전용 CUD**: 생성/수정/삭제는 JWT 토큰이 필요한 관리자만 가능
- **페이지네이션**: 모든 목록 API에서 지원
- **카테고리 필터링**: 각 API별 고유 카테고리로 필터링 가능

---

## 🔓 공개 API (인증 불필요)

## 게시판 API (`/board`)

### 카테고리
- 센터소식, 프로그램소식, 행사소식, 생활정보, 교육

### 1. 게시글 목록 조회
```
GET /board
GET /board?categories=센터소식,프로그램소식
```

**응답 예시:**
```json
{
  "posts": [
    {
      "id": "1",
      "title": "2025년 가족센터 신규 프로그램 오픈",
      "content": "가족의 건강한 소통과 화합을 위한...",
      "category": "센터소식",
      "created_at": "2025-06-29T10:00:00Z",
      "status": "published",
      "image_url": "https://example.com/images/family-program.jpg",
      "short_description": "가족의 건강한 소통과 화합을 위한 다양한 프로그램을 새롭게 선보입니다."
    }
  ],
  "total": 6,
  "category_filter": ["센터소식", "프로그램소식"]
}
```

#### 2. 최근 게시글 5개 조회
```
GET /board/recent
GET /board/recent?categories=센터소식
```

#### 3. 게시글 상세 조회
```
GET /board/{id}
```

**응답 예시:**
```json
{
  "id": "1",
  "title": "2025년 가족센터 신규 프로그램 오픈",
  "content": "상세 내용 (마크다운 지원)...",
  "category": "센터소식",
  "created_at": "2025-06-29T10:00:00Z",
  "status": "published",
  "image_url": "https://example.com/images/family-program.jpg",
  "short_description": "짧은 설명"
}
```

### 🔒 관리자 API (JWT 토큰 필요)

#### 4. 게시글 생성
```
POST /board
Authorization: Bearer {token}
Content-Type: application/json
```

**요청 본문:**
```json
{
  "title": "새로운 프로그램 안내",
  "content": "프로그램 상세 내용",
  "category": "프로그램소식",
  "image_url": "https://your-s3-bucket.com/images/new-program.jpg",
  "short_description": "카드뷰에 표시될 짧은 설명"
}
```

#### 5. 게시글 수정
```
PUT /board/{id}
Authorization: Bearer {token}
Content-Type: application/json
```

**요청 본문:**
```json
{
  "title": "수정된 제목",
  "content": "수정된 내용",
  "category": "센터소식",
  "image_url": "https://new-image-url.jpg",
  "short_description": "수정된 설명"
}
```

#### 6. 게시글 삭제
```
DELETE /board/{id}
Authorization: Bearer {token}
```

#### 7. 이미지 업로드 정보
```
POST /board/upload
Authorization: Bearer {token}
```

## 📝 카테고리 목록

사진에 표시된 카테고리들:
- `센터소식` (파란색 태그)
- `프로그램소식` (빨간색 태그)
- `행사소식` (초록색 태그)
- `생활정보` (주황색 태그)
- `교육` (파란색 태그)

## 🖼️ 이미지 처리 방식

1. **프론트엔드에서 S3 업로드**
   - 이미지를 S3에 직접 업로드
   - 업로드된 이미지 URL을 받음

2. **게시글 생성/수정 시 URL 포함**
   - `image_url` 필드에 S3 URL 포함
   - `short_description`도 함께 전달

## 🔑 인증 방법

1. **관리자 로그인**
   ```
   POST /auth/login
   ```
   ```json
   {
     "username": "admin",
     "password": "password"
   }
   ```

2. **토큰 사용**
   ```
   Authorization: Bearer {received_token}
   ```

## 📊 데이터 구조

### 게시글 필드
- `id`: 고유 식별자
- `title`: 제목
- `content`: 내용 (마크다운 지원)
- `category`: 카테고리
- `created_at`: 생성일시
- `updated_at`: 수정일시
- `status`: 상태 (published/draft)
- `image_url`: 카드뷰 이미지 URL
- `short_description`: 카드뷰용 짧은 설명

## 🎯 사용 시나리오

### 1. 카드뷰 게시판 표시
```javascript
// 게시글 목록 조회
fetch('/board')
  .then(response => response.json())
  .then(data => {
    data.posts.forEach(post => {
      // 카드뷰 렌더링
      // post.image_url: 카드 이미지
      // post.title: 카드 제목
      // post.short_description: 카드 설명
      // post.category: 카테고리 태그
    });
  });
```

### 2. 카테고리 필터링
```javascript
// 특정 카테고리만 조회
fetch('/board?categories=센터소식,프로그램소식')
```

### 3. 관리자 게시글 작성
```javascript
// 1. 이미지 S3 업로드 (별도 구현)
const imageUrl = await uploadToS3(imageFile);

// 2. 게시글 생성
fetch('/board', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    title: '새로운 프로그램',
    content: '프로그램 상세 내용',
    category: '프로그램소식',
    image_url: imageUrl,
    short_description: '프로그램 요약'
  })
});
```

## 🚀 배포 및 테스트

### 로컬 테스트
```bash
# DynamoDB Local 시작
cd local-setup && docker compose up -d

# 테이블 생성
python setup_local_table.py

# SAM Local 실행
sam build && sam local start-api --env-vars env.json
```

### AWS 배포
```bash
git tag v1.0.0
git push origin v1.0.0
```

API가 배포되면 사진과 같은 카드뷰 게시판을 구현할 수 있습니다!
