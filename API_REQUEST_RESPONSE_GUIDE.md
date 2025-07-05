# 📡 전체 API 요청/응답 가이드

## 🏠 로컬 환경 (http://localhost:3000)

## 🌐 프로덕션 환경 (https://your-api-id.execute-api.ap-northeast-2.amazonaws.com/Prod)

---

# 🔓 공개 API (인증 불필요)

## 1. 게시판 API

### 1-1. 게시글 목록 조회

#### 요청
```bash
# 로컬
curl http://localhost:3000/board

# 프로덕션
curl https://your-api-gateway-url.com/Prod/board

# 카테고리 필터링
curl "http://localhost:3000/board?categories=센터소식,프로그램소식"
```

#### 응답 (200 OK)
```json
{
  "posts": [
    {
      "id": "1",
      "title": "2025년 가족센터 신규 프로그램 오픈",
      "content": "가족의 건강한 소통과 화합을 위한 다양한 프로그램을 새롭게 선보입니다...",
      "category": "센터소식",
      "created_at": "2025-06-29T10:00:00Z",
      "status": "published",
      "image_url": "https://example.com/images/family-program.jpg",
      "short_description": "가족의 건강한 소통과 화합을 위한 다양한 프로그램을 새롭게 선보입니다."
    },
    {
      "id": "2",
      "title": "다문화가족 자녀 한국어 교육 프로그램 성과 발표",
      "content": "지난 3개월간 진행된 한국어 교육 프로그램의 우수한 성과를 공유합니다...",
      "category": "프로그램소식",
      "created_at": "2025-06-28T15:00:00Z",
      "status": "published",
      "image_url": "https://example.com/images/korean-education.jpg",
      "short_description": "지난 3개월간 진행된 한국어 교육 프로그램의 우수한 성과를 공유합니다."
    }
  ],
  "total": 6,
  "category_filter": ["센터소식", "프로그램소식"]
}
```

### 1-2. 최근 게시글 5개 조회

#### 요청
```bash
# 로컬
curl http://localhost:3000/board/recent

# 카테고리 필터링
curl "http://localhost:3000/board/recent?categories=센터소식"
```

#### 응답 (200 OK)
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
  "total": 5,
  "category_filter": ["센터소식"],
  "is_recent": true
}
```

### 1-3. 게시글 상세 조회

#### 요청
```bash
# 로컬
curl http://localhost:3000/board/1

# 프로덕션
curl https://your-api-gateway-url.com/Prod/board/1
```

#### 응답 (200 OK)
```json
{
  "id": "1",
  "title": "2025년 가족센터 신규 프로그램 오픈",
  "content": "# 2025년 가족센터 신규 프로그램 오픈\n\n가족의 건강한 소통과 화합을 위한 다양한 프로그램을 새롭게 선보입니다.\n\n## 주요 프로그램\n\n### 1. 가족 소통 워크숍\n- 대상: 모든 가족\n- 일시: 매주 토요일 오후 2시\n- 장소: 가족센터 3층 프로그램실\n\n### 2. 부모-자녀 관계 개선 프로그램\n- 대상: 초중고 자녀를 둔 부모\n- 일시: 매주 화요일 오후 7시\n- 장소: 가족센터 2층 상담실\n\n### 3. 다문화 가족 지원 프로그램\n- 대상: 다문화 가족\n- 일시: 매주 목요일 오후 3시\n- 장소: 가족센터 1층 다문화실\n\n## 신청 방법\n\n전화 또는 방문 접수\n- 전화: 02-123-4567\n- 방문: 서울시 종로구 가족센터길 123\n\n많은 관심과 참여 부탁드립니다.",
  "category": "센터소식",
  "created_at": "2025-06-29T10:00:00Z",
  "status": "published",
  "image_url": "https://example.com/images/family-program.jpg",
  "short_description": "가족의 건강한 소통과 화합을 위한 다양한 프로그램을 새롭게 선보입니다."
}
```

#### 에러 응답 (404 Not Found)
```json
{
  "error": "Board not found"
}
```

---

## 2. 뉴스 API

### 2-1. 뉴스 목록 조회 (페이지네이션)

#### 요청
```bash
# 기본 요청 (1페이지, 10개)
curl http://localhost:3000/news

# 페이지네이션
curl "http://localhost:3000/news?page=2&limit=5"

# 카테고리 필터링
curl "http://localhost:3000/news?categories=주요소식,정책소식"

# 복합 필터링
curl "http://localhost:3000/news?page=1&limit=3&categories=주요소식"
```

#### 응답 (200 OK)
```json
{
  "news": [
    {
      "id": "news_1",
      "title": "가족센터 2025년 상반기 사업계획 발표",
      "content": "올해 상반기 가족센터의 주요 사업계획을 발표합니다...",
      "category": "주요소식",
      "created_at": "2025-07-03T10:00:00Z",
      "status": "published",
      "image_url": "https://example.com/images/business-plan.jpg",
      "short_description": "올해 상반기 가족센터의 주요 사업계획을 발표합니다."
    },
    {
      "id": "news_2",
      "title": "다문화가족 지원 정책 개선안 공지",
      "content": "다문화가족을 위한 새로운 지원 정책이 개선되었습니다...",
      "category": "정책소식",
      "created_at": "2025-07-02T14:30:00Z",
      "status": "published",
      "image_url": "https://example.com/images/policy-update.jpg",
      "short_description": "다문화가족을 위한 새로운 지원 정책이 개선되었습니다."
    }
  ],
  "pagination": {
    "current_page": 1,
    "total_pages": 3,
    "total_count": 25,
    "limit": 10,
    "has_next": true,
    "has_prev": false
  },
  "category_filter": ["주요소식", "정책소식"]
}
```

### 2-2. 뉴스 상세 조회

#### 요청
```bash
curl http://localhost:3000/news/news_1
```

#### 응답 (200 OK)
```json
{
  "id": "news_1",
  "title": "가족센터 2025년 상반기 사업계획 발표",
  "content": "# 가족센터 2025년 상반기 사업계획 발표\n\n올해 상반기 가족센터의 주요 사업계획을 발표합니다.\n\n## 주요 사업 계획\n\n### 1. 가족 상담 서비스 확대\n- 전문 상담사 2명 추가 채용\n- 야간 상담 서비스 신설\n- 온라인 상담 플랫폼 구축\n\n### 2. 교육 프로그램 다양화\n- 연령별 맞춤 교육 프로그램\n- 주말 가족 활동 프로그램\n- 다문화 가족 특화 프로그램\n\n### 3. 지역사회 연계 강화\n- 지역 학교와의 협력 확대\n- 복지관과의 연계 프로그램\n- 기업 사회공헌 활동 연계\n\n## 예산 계획\n\n총 예산: 15억원\n- 인건비: 8억원 (53%)\n- 프로그램 운영비: 5억원 (33%)\n- 시설 개선비: 2억원 (14%)\n\n많은 관심과 지원 부탁드립니다.",
  "category": "주요소식",
  "created_at": "2025-07-03T10:00:00Z",
  "status": "published",
  "image_url": "https://example.com/images/business-plan.jpg",
  "short_description": "올해 상반기 가족센터의 주요 사업계획을 발표합니다."
}
```

---

## 3. 갤러리 API

### 3-1. 갤러리 목록 조회 (페이지네이션)

#### 요청
```bash
# 기본 요청 (1페이지, 12개)
curl http://localhost:3000/gallery

# 페이지네이션
curl "http://localhost:3000/gallery?page=1&limit=8"

# 카테고리 필터링
curl "http://localhost:3000/gallery?categories=자료실,양식다운로드"
```

#### 응답 (200 OK)
```json
{
  "gallery": [
    {
      "id": "gallery_1",
      "title": "다문화가족 지원 서비스 안내서",
      "content": "다문화가족을 위한 종합 지원 서비스 안내서입니다...",
      "category": "자료실",
      "created_at": "2025-07-03T09:00:00Z",
      "status": "published",
      "image_url": "https://example.com/images/guide-cover.jpg",
      "short_description": "다문화가족을 위한 종합 지원 서비스 안내서입니다.",
      "file_url": "https://example.com/files/multicultural-guide.pdf",
      "file_name": "다문화가족_지원서비스_안내서.pdf",
      "file_size": 2048576
    },
    {
      "id": "gallery_2",
      "title": "가족상담 신청서 양식",
      "content": "가족상담을 신청하실 때 사용하는 양식입니다...",
      "category": "양식다운로드",
      "created_at": "2025-07-02T14:00:00Z",
      "status": "published",
      "image_url": "https://example.com/images/form-preview.jpg",
      "short_description": "가족상담을 신청하실 때 사용하는 양식입니다.",
      "file_url": "https://example.com/files/counseling-application.docx",
      "file_name": "가족상담_신청서.docx",
      "file_size": 51200
    }
  ],
  "pagination": {
    "current_page": 1,
    "total_pages": 2,
    "total_count": 18,
    "limit": 12,
    "has_next": true,
    "has_prev": false
  },
  "category_filter": ["자료실", "양식다운로드"]
}
```

### 3-2. 갤러리 상세 조회

#### 요청
```bash
curl http://localhost:3000/gallery/gallery_1
```

#### 응답 (200 OK)
```json
{
  "id": "gallery_1",
  "title": "다문화가족 지원 서비스 안내서",
  "content": "# 다문화가족 지원 서비스 안내서\n\n다문화가족을 위한 종합 지원 서비스 안내서입니다.\n\n## 주요 내용\n\n### 1. 한국어 교육 지원\n- 기초 한국어 교육\n- 생활 한국어 교육\n- 직업 한국어 교육\n\n### 2. 자녀 교육 지원\n- 학습 멘토링\n- 진로 상담\n- 특기적성 교육\n\n### 3. 가족 통합 지원\n- 가족 상담\n- 문화체험 프로그램\n- 소통 워크숍\n\n### 4. 취업 지원\n- 직업 상담\n- 취업 교육\n- 일자리 연계\n\n### 5. 정착 지원\n- 생활 정보 제공\n- 행정 업무 지원\n- 지역사회 연계\n\n## 이용 방법\n\n### 신청 자격\n- 결혼이민자 및 그 가족\n- 귀화자 및 그 가족\n- 다문화가족 자녀\n\n### 신청 방법\n1. 방문 신청: 가족센터 1층 접수데스크\n2. 전화 신청: 02-123-4567\n3. 온라인 신청: www.familycenter.go.kr\n\n### 구비 서류\n- 신분증\n- 가족관계증명서\n- 거주지 확인서류\n\n자세한 내용은 첨부된 파일을 다운로드하여 확인하시기 바랍니다.",
  "category": "자료실",
  "created_at": "2025-07-03T09:00:00Z",
  "status": "published",
  "image_url": "https://example.com/images/guide-cover.jpg",
  "short_description": "다문화가족을 위한 종합 지원 서비스 안내서입니다.",
  "file_url": "https://example.com/files/multicultural-guide.pdf",
  "file_name": "다문화가족_지원서비스_안내서.pdf",
  "file_size": 2048576
}
```

---

# 🔐 관리자 API (JWT 토큰 필요)

## 1. 로그인 및 토큰 획득

### 1-1. 관리자 로그인

#### 요청
```bash
curl -X POST http://localhost:3000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your_password"
  }'
```

#### 응답 (200 OK)
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "message": "Login successful"
}
```

#### 에러 응답 (401 Unauthorized)
```json
{
  "error": "Invalid credentials"
}
```

## 2. 게시판 관리자 API

### 2-1. 게시글 생성

#### 요청
```bash
curl -X POST http://localhost:3000/board \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "title": "새로운 프로그램 안내",
    "content": "# 새로운 프로그램 안내\n\n새로운 가족 프로그램을 소개합니다.\n\n## 프로그램 내용\n- 가족 소통 개선\n- 갈등 해결 방법\n- 화합 증진 활동",
    "category": "프로그램소식",
    "image_url": "https://example.com/images/new-program.jpg",
    "short_description": "새로운 가족 프로그램을 소개합니다."
  }'
```

#### 응답 (201 Created)
```json
{
  "message": "Board created successfully",
  "board": {
    "id": "generated_uuid_here",
    "title": "새로운 프로그램 안내",
    "content": "# 새로운 프로그램 안내\n\n새로운 가족 프로그램을 소개합니다.\n\n## 프로그램 내용\n- 가족 소통 개선\n- 갈등 해결 방법\n- 화합 증진 활동",
    "category": "프로그램소식",
    "created_at": "2025-07-03T15:30:00Z",
    "updated_at": "2025-07-03T15:30:00Z",
    "status": "published",
    "image_url": "https://example.com/images/new-program.jpg",
    "short_description": "새로운 가족 프로그램을 소개합니다."
  }
}
```

### 2-2. 게시글 수정

#### 요청
```bash
curl -X PUT http://localhost:3000/board/generated_uuid_here \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "title": "수정된 프로그램 안내",
    "content": "수정된 내용입니다.",
    "image_url": "https://example.com/images/updated-program.jpg"
  }'
```

#### 응답 (200 OK)
```json
{
  "message": "Board updated successfully",
  "board": {
    "id": "generated_uuid_here",
    "title": "수정된 프로그램 안내",
    "content": "수정된 내용입니다.",
    "category": "프로그램소식",
    "created_at": "2025-07-03T15:30:00Z",
    "updated_at": "2025-07-03T15:45:00Z",
    "status": "published",
    "image_url": "https://example.com/images/updated-program.jpg",
    "short_description": "새로운 가족 프로그램을 소개합니다."
  }
}
```

### 2-3. 게시글 삭제

#### 요청
```bash
curl -X DELETE http://localhost:3000/board/generated_uuid_here \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### 응답 (200 OK)
```json
{
  "message": "Board deleted successfully"
}
```

## 3. 뉴스 관리자 API

### 3-1. 뉴스 생성

#### 요청
```bash
curl -X POST http://localhost:3000/news \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "title": "새로운 정책 발표",
    "content": "# 새로운 정책 발표\n\n가족 지원 정책이 새롭게 발표되었습니다.",
    "category": "정책소식",
    "image_url": "https://example.com/images/policy.jpg",
    "short_description": "가족 지원 정책이 새롭게 발표되었습니다."
  }'
```

#### 응답 (201 Created)
```json
{
  "message": "News created successfully",
  "news": {
    "id": "news_generated_uuid_here",
    "title": "새로운 정책 발표",
    "content": "# 새로운 정책 발표\n\n가족 지원 정책이 새롭게 발표되었습니다.",
    "category": "정책소식",
    "created_at": "2025-07-03T15:30:00Z",
    "updated_at": "2025-07-03T15:30:00Z",
    "status": "published",
    "image_url": "https://example.com/images/policy.jpg",
    "short_description": "가족 지원 정책이 새롭게 발표되었습니다."
  }
}
```

## 4. 갤러리 관리자 API

### 4-1. 갤러리 아이템 생성

#### 요청
```bash
curl -X POST http://localhost:3000/gallery \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "title": "새로운 양식 파일",
    "content": "# 새로운 양식 파일\n\n가족 상담 신청을 위한 새로운 양식입니다.",
    "category": "양식다운로드",
    "image_url": "https://example.com/images/form.jpg",
    "short_description": "가족 상담 신청을 위한 새로운 양식입니다.",
    "file_url": "https://example.com/files/new-form.docx",
    "file_name": "가족상담_신청서_v2.docx",
    "file_size": 65536
  }'
```

#### 응답 (201 Created)
```json
{
  "message": "Gallery item created successfully",
  "gallery": {
    "id": "gallery_generated_uuid_here",
    "title": "새로운 양식 파일",
    "content": "# 새로운 양식 파일\n\n가족 상담 신청을 위한 새로운 양식입니다.",
    "category": "양식다운로드",
    "created_at": "2025-07-03T15:30:00Z",
    "updated_at": "2025-07-03T15:30:00Z",
    "status": "published",
    "image_url": "https://example.com/images/form.jpg",
    "short_description": "가족 상담 신청을 위한 새로운 양식입니다.",
    "file_url": "https://example.com/files/new-form.docx",
    "file_name": "가족상담_신청서_v2.docx",
    "file_size": 65536
  }
}
```

---

# 🚨 공통 에러 응답

## 인증 에러 (401 Unauthorized)
```json
{
  "error": "Unauthorized"
}
```

## 리소스 없음 (404 Not Found)
```json
{
  "error": "Board/News/Gallery item not found"
}
```

## 잘못된 요청 (400 Bad Request)
```json
{
  "error": "Title and content required"
}
```

## 잘못된 카테고리 (400 Bad Request)
```json
{
  "error": "Invalid category. Must be one of: [센터소식, 프로그램소식, 행사소식, 생활정보, 교육]"
}
```

## 서버 에러 (500 Internal Server Error)
```json
{
  "error": "Internal server error",
  "error_type": "DatabaseError",
  "error_message": "Connection failed",
  "traceback": "Traceback (most recent call last)...",
  "stage": "local",
  "config_loaded": true
}
```

---

# 📊 응답 특징

## 1. 페이지네이션 메타데이터
```json
{
  "pagination": {
    "current_page": 2,      // 현재 페이지
    "total_pages": 5,       // 전체 페이지 수
    "total_count": 47,      // 전체 아이템 수
    "limit": 10,            // 페이지당 아이템 수
    "has_next": true,       // 다음 페이지 존재 여부
    "has_prev": true        // 이전 페이지 존재 여부
  }
}
```

## 2. 파일 정보 (갤러리)
```json
{
  "file_url": "https://example.com/files/document.pdf",
  "file_name": "문서.pdf",
  "file_size": 2048576    // bytes
}
```

## 3. 카드뷰 정보 (게시판)
```json
{
  "image_url": "https://example.com/images/card-image.jpg",
  "short_description": "카드뷰에 표시될 짧은 설명"
}
```

## 4. 조회수 자동 증가
- 목록 조회 시에는 증가하지 않음
