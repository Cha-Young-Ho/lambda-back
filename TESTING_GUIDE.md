# 📋 Gallery + News API 테스트 가이드

## 🚀 개요
이 가이드는 Gallery, News API의 모든 기능을 체계적으로 테스트하기 위한 종합 가이드입니다.
(Board API는 Gallery로 통합되어 제거되었습니다)

## ⚙️ 사전 준비

### 1. 서버 상태 확인
```bash
# SAM 서버 실행 확인 (포트 3001)
curl http://localhost:3001/health

# DynamoDB Local 실행 확인
docker ps | grep dynamodb
```

### 2. 테스트 도구 준비
- **curl** 또는 **Postman** 사용
- **jq** (JSON 파싱용): `brew install jq`

## 📝 테스트 시나리오

### 🖼️ 1. Gallery API 테스트

#### 1.1 Gallery 카테고리 테스트
```bash
# 유효한 Gallery 카테고리들로 항목 생성
curl -X POST http://localhost:3001/gallery \
  -H "Content-Type: application/json" \
  -d '{
    "title": "세미나 테스트",
    "content": "세미나 카테고리 테스트 내용",
    "category": "세미나"
  }' | jq

curl -X POST http://localhost:3001/gallery \
  -H "Content-Type: application/json" \
  -d '{
    "title": "일정 테스트",
    "content": "일정 카테고리 테스트 내용",
    "category": "일정"
  }' | jq

curl -X POST http://localhost:3001/gallery \
  -H "Content-Type: application/json" \
  -d '{
    "title": "공지사항 테스트",
    "content": "공지사항 카테고리 테스트 내용",
    "category": "공지사항"
  }' | jq
```

#### 1.2 잘못된 Gallery 카테고리 검증
```bash
# Gallery에서 허용되지 않는 카테고리 (400 에러 기대)
curl -X POST http://localhost:3001/gallery \
  -H "Content-Type: application/json" \
  -d '{
    "title": "잘못된 카테고리 테스트",
    "content": "센터소식은 Gallery에서 허용되지 않음",
    "category": "센터소식"
  }' | jq
```

#### 1.3 Gallery Recent API 타입 확인
```bash
# Recent API 호출하여 type 필드 확인
curl http://localhost:3001/gallery/recent | jq

# 응답 형태:
# {
#   "success": true,
#   "type": "gallery",
#   "data": [...],
#   "total": x,
#   "is_recent": true
# }
```

#### 1.4 Gallery 전체 조회
```bash
# 전체 Gallery 조회 (마이그레이션된 데이터 포함)
curl http://localhost:3001/gallery | jq

# 카테고리별 조회
curl "http://localhost:3001/gallery?category=공지사항" | jq
curl "http://localhost:3001/gallery?category=질문" | jq
curl "http://localhost:3001/gallery?category=건의" | jq
curl "http://localhost:3001/gallery?category=참고자료" | jq
curl "http://localhost:3001/gallery?category=기타" | jq
curl "http://localhost:3001/gallery?category=세미나" | jq
curl "http://localhost:3001/gallery?category=일정" | jq
```

### 📰 2. News API 테스트

#### 2.1 유효한 News 카테고리로 뉴스 생성 테스트
```bash
# 유효한 News 카테고리들로 뉴스 생성
curl -X POST http://localhost:3001/news \
  -H "Content-Type: application/json" \
  -d '{
    "title": "센터소식 뉴스",
    "content": "센터소식 카테고리 뉴스 내용",
    "category": "센터소식"
  }' | jq

curl -X POST http://localhost:3001/news \
  -H "Content-Type: application/json" \
  -d '{
    "title": "프로그램소식 뉴스",
    "content": "프로그램소식 카테고리 뉴스 내용",
    "category": "프로그램소식"
  }' | jq

curl -X POST http://localhost:3001/news \
  -H "Content-Type: application/json" \
  -d '{
    "title": "행사소식 뉴스",
    "content": "행사소식 카테고리 뉴스 내용",
    "category": "행사소식"
  }' | jq

curl -X POST http://localhost:3001/news \
  -H "Content-Type: application/json" \
  -d '{
    "title": "생활정보 뉴스",
    "content": "생활정보 카테고리 뉴스 내용",
    "category": "생활정보"
  }' | jq
```

#### 2.2 잘못된 News 카테고리 검증
```bash
# News에서 허용되지 않는 카테고리 (400 에러 기대)
curl -X POST http://localhost:3001/news \
  -H "Content-Type: application/json" \
  -d '{
    "title": "잘못된 카테고리 테스트",
    "content": "공지사항은 News에서 허용되지 않음",
    "category": "공지사항"
  }' | jq
```

#### 2.3 News Recent API 타입 확인
```bash
# Recent API 호출하여 type 필드 확인
curl http://localhost:3001/news/recent | jq

# 응답 형태:
# {
#   "success": true,
#   "type": "news",
#   "data": [...],
#   "total": x,
#   "is_recent": true
# }
```

#### 2.4 News 전체 조회
```bash
# 모든 뉴스 조회
curl http://localhost:3001/news | jq

# 카테고리별 조회
curl "http://localhost:3001/news?category=센터소식" | jq
curl "http://localhost:3001/news?category=프로그램소식" | jq
curl "http://localhost:3001/news?category=행사소식" | jq
curl "http://localhost:3001/news?category=생활정보" | jq
curl "http://localhost:3001/news?category=기타" | jq
```

### 🔄 3. 통합 Recent API 테스트

#### 3.1 모든 Recent API의 타입 구분 확인
```bash
# Gallery와 News Recent API 타입 구분 확인
echo "=== Gallery Recent ==="
curl http://localhost:3001/gallery/recent | jq '.type'

echo "=== News Recent ==="
curl http://localhost:3001/news/recent | jq '.type'
```

#### 3.2 Recent API 응답 구조 검증
```bash
# Gallery Recent 구조 확인
curl http://localhost:3001/gallery/recent | jq 'has("success") and has("type") and has("data") and has("total") and has("is_recent")'

# News Recent 구조 확인
curl http://localhost:3001/news/recent | jq 'has("success") and has("type") and has("data") and has("total") and has("is_recent")'
```

## 📊 테스트 결과 검증

### ✅ 성공 기준

1. **Gallery API**
   - 허용된 7개 카테고리로만 생성 가능
   - News 카테고리(센터소식 등)로 생성 시 400 에러
   - Recent API에 `"type": "gallery"` 포함
   - 마이그레이션된 데이터 확인 가능

2. **News API**
   - 허용된 5개 카테고리로만 생성 가능
   - Gallery 카테고리(공지사항 등)로 생성 시 400 에러
   - Recent API에 `"type": "news"` 포함

3. **통합 검증**
   - 모든 Recent API가 고유한 타입 구분자 반환
   - 카테고리 제한이 각 API별로 올바르게 적용

### ❌ 실패 시 확인사항

1. **서버 상태**: SAM 로컬 서버와 DynamoDB 실행 상태
2. **포트 충돌**: 3001 포트 사용 가능성
3. **코드 변경**: 최신 변경사항이 배포되었는지 확인

## 🔧 편의 스크립트

### 빠른 테스트 실행
```bash
# 모든 테스트를 한 번에 실행하는 스크립트
bash quick_test.sh
```

### 데이터 초기화
```bash
# 테스트 데이터 정리 (필요시)
curl -X DELETE http://localhost:3001/gallery/all
curl -X DELETE http://localhost:3001/news/all
```

## 📝 테스트 결과 기록

각 테스트 후 결과를 기록해주세요:

- [ ] Gallery 카테고리 제한 테스트
- [ ] Gallery 잘못된 카테고리 검증
- [ ] Gallery Recent API 타입 확인
- [ ] Gallery 마이그레이션 데이터 확인
- [ ] News 카테고리 제한 테스트
- [ ] News 잘못된 카테고리 검증
- [ ] News Recent API 타입 확인
- [ ] 통합 Recent API 타입 구분 확인

---
*테스트 완료 후 모든 API가 예상대로 작동하는지 확인하고, 문제가 있으면 로그를 확인해주세요.*
