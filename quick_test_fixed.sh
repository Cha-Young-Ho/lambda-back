#!/bin/bash

# 🚀 Gallery + News API 빠른 테스트 스크립트
# 사용법: bash quick_test.sh

BASE_URL="http://localhost:3001"
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📋 Gallery + News API 테스트 시작${NC}"
echo "======================================"

# 서버 상태 확인
echo -e "\n${BLUE}🔍 서버 상태 확인${NC}"
if curl -s $BASE_URL/gallery/recent > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 서버가 정상적으로 실행 중입니다${NC}"
else
    echo -e "${RED}❌ 서버에 연결할 수 없습니다. SAM 서버가 실행 중인지 확인해주세요${NC}"
    exit 1
fi

# 1. Gallery API 테스트
echo -e "\n${BLUE}🖼️ Gallery API 테스트${NC}"
echo "========================"

echo "1.1 유효한 Gallery 카테고리로 항목 생성 테스트..."
for category in "세미나" "일정" "공지사항"; do
    response=$(curl -s -X POST $BASE_URL/gallery \
        -H "Content-Type: application/json" \
        -d "{
            \"title\": \"${category} 테스트\",
            \"content\": \"${category} 카테고리 테스트 내용\",
            \"category\": \"${category}\"
        }")
    
    if echo $response | jq -e '.success' > /dev/null 2>&1; then
        echo -e "  ${GREEN}✅ ${category} 갤러리 항목 생성 성공${NC}"
    else
        echo -e "  ${RED}❌ ${category} 갤러리 항목 생성 실패${NC}"
        echo "     응답: $response"
    fi
done

echo "1.2 Gallery에서 허용되지 않는 카테고리 검증 테스트..."
response=$(curl -s -X POST $BASE_URL/gallery \
    -H "Content-Type: application/json" \
    -d '{
        "title": "잘못된 카테고리 테스트",
        "content": "센터소식은 Gallery에서 허용되지 않음",
        "category": "센터소식"
    }')

if echo $response | jq -e '.error' > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅ Gallery 잘못된 카테고리 거부 성공${NC}"
else
    echo -e "  ${RED}❌ Gallery 잘못된 카테고리 거부 실패${NC}"
    echo "     응답: $response"
fi

echo "1.3 Gallery Recent API 타입 확인..."
response=$(curl -s $BASE_URL/gallery/recent)
type=$(echo $response | jq -r '.type')
if [ "$type" = "gallery" ]; then
    echo -e "  ${GREEN}✅ Gallery Recent API 타입 확인 성공 (type: gallery)${NC}"
else
    echo -e "  ${RED}❌ Gallery Recent API 타입 확인 실패 (type: $type)${NC}"
fi

# 2. News API 테스트
echo -e "\n${BLUE}📰 News API 테스트${NC}"
echo "==================="

echo "2.1 유효한 News 카테고리로 뉴스 생성 테스트..."
for category in "센터소식" "프로그램소식" "행사소식" "생활정보"; do
    response=$(curl -s -X POST $BASE_URL/news \
        -H "Content-Type: application/json" \
        -d "{
            \"title\": \"${category} 뉴스\",
            \"content\": \"${category} 카테고리 뉴스 내용\",
            \"category\": \"${category}\"
        }")
    
    if echo $response | jq -e '.success' > /dev/null 2>&1; then
        echo -e "  ${GREEN}✅ ${category} 뉴스 생성 성공${NC}"
    else
        echo -e "  ${RED}❌ ${category} 뉴스 생성 실패${NC}"
        echo "     응답: $response"
    fi
done

echo "2.2 News에서 허용되지 않는 카테고리 검증 테스트..."
response=$(curl -s -X POST $BASE_URL/news \
    -H "Content-Type: application/json" \
    -d '{
        "title": "잘못된 카테고리 테스트",
        "content": "공지사항은 News에서 허용되지 않음",
        "category": "공지사항"
    }')

if echo $response | jq -e '.error' > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅ News 잘못된 카테고리 거부 성공${NC}"
else
    echo -e "  ${RED}❌ News 잘못된 카테고리 거부 실패${NC}"
    echo "     응답: $response"
fi

echo "2.3 News Recent API 타입 확인..."
response=$(curl -s $BASE_URL/news/recent)
type=$(echo $response | jq -r '.type')
if [ "$type" = "news" ]; then
    echo -e "  ${GREEN}✅ News Recent API 타입 확인 성공 (type: news)${NC}"
else
    echo -e "  ${RED}❌ News Recent API 타입 확인 실패 (type: $type)${NC}"
fi

# 3. 통합 테스트
echo -e "\n${BLUE}🔄 통합 Recent API 타입 구분 테스트${NC}"
echo "=================================="

echo "모든 Recent API의 타입 구분 확인..."
gallery_type=$(curl -s $BASE_URL/gallery/recent | jq -r '.type')
news_type=$(curl -s $BASE_URL/news/recent | jq -r '.type')

echo -e "  Gallery Recent Type: ${GREEN}$gallery_type${NC}"
echo -e "  News Recent Type: ${GREEN}$news_type${NC}"

if [ "$gallery_type" = "gallery" ] && [ "$news_type" = "news" ]; then
    echo -e "  ${GREEN}✅ 모든 Recent API 타입 구분 성공${NC}"
else
    echo -e "  ${RED}❌ Recent API 타입 구분 실패${NC}"
fi

# 4. 데이터 개수 확인
echo -e "\n${BLUE}📊 데이터 개수 확인${NC}"
echo "=================="

gallery_total=$(curl -s $BASE_URL/gallery/recent | jq -r '.total')
news_total=$(curl -s $BASE_URL/news/recent | jq -r '.total')

echo -e "  Gallery 총 개수: ${GREEN}$gallery_total${NC} (마이그레이션된 데이터 포함)"
echo -e "  News 총 개수: ${GREEN}$news_total${NC}"

echo -e "\n${BLUE}🎉 테스트 완료!${NC}"
echo "================================================"
echo "자세한 테스트 결과는 위의 출력을 확인해주세요."
echo "추가 테스트가 필요하면 TESTING_GUIDE.md를 참고하세요."
