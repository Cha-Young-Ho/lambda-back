#!/bin/bash

# 🎯 Blog System API 종합 테스트 스크립트
# 2025년 7월 6일 - 최종 완성 버전

echo "🚀 Blog System API 종합 테스트 시작"
echo "===================================="
echo ""

BASE_URL="http://localhost:3001"

# 색상 코드
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 테스트 결과 저장
PASS_COUNT=0
FAIL_COUNT=0

# 테스트 함수
test_api() {
    local name="$1"
    local url="$2"
    local expected_field="$3"
    
    echo -n "Testing $name... "
    
    response=$(curl -s "$url")
    
    if echo "$response" | jq -e ".success == true and .$expected_field != null" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}"
        ((PASS_COUNT++))
        echo "   Data: $(echo "$response" | jq -r ".$expected_field // \"N/A\"")"
    else
        echo -e "${RED}❌ FAIL${NC}"
        ((FAIL_COUNT++))
        echo "   Response: $response"
    fi
    echo ""
}

# Auth API 테스트
test_auth() {
    echo -n "Testing Auth Login... "
    
    response=$(curl -s -X POST "$BASE_URL/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"username": "admin", "password": "admin123"}')
    
    if echo "$response" | jq -e '.success == true and .data.token != null' > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}"
        ((PASS_COUNT++))
        TOKEN=$(echo "$response" | jq -r '.data.token')
        echo "   Token: ${TOKEN:0:50}..."
    else
        echo -e "${RED}❌ FAIL${NC}"
        ((FAIL_COUNT++))
        echo "   Response: $response"
    fi
    echo ""
}

echo -e "${BLUE}📰 News API Tests${NC}"
echo "----------------"
test_api "News List" "$BASE_URL/news" "total"
test_api "News Recent" "$BASE_URL/news/recent" "total"

echo -e "${BLUE}🖼️  Gallery API Tests${NC}"
echo "-------------------"
test_api "Gallery List" "$BASE_URL/gallery" "total"
test_api "Gallery Recent" "$BASE_URL/gallery/recent" "total"

echo -e "${BLUE}🔐 Auth API Tests${NC}"
echo "----------------"
test_auth

echo "===================================="
echo -e "${YELLOW}📊 테스트 결과 요약${NC}"
echo "===================================="
echo -e "✅ 성공: ${GREEN}$PASS_COUNT${NC}개"
echo -e "❌ 실패: ${RED}$FAIL_COUNT${NC}개"
echo -e "📈 성공률: $((PASS_COUNT * 100 / (PASS_COUNT + FAIL_COUNT)))%"

if [ $FAIL_COUNT -eq 0 ]; then
    echo ""
    echo -e "${GREEN}🎉 모든 테스트 통과! API 시스템이 완벽하게 작동합니다!${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}⚠️  일부 테스트 실패. 로그를 확인해주세요.${NC}"
    exit 1
fi
