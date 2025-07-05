#!/bin/bash

# Blog System 종합 API 테스트 스크립트
# 작성일: 2025년 7월 6일

BASE_URL="http://localhost:3001"

echo "🎯 Blog System 종합 API 테스트 시작"
echo "======================================"
echo ""

# 서버 상태 확인
echo "🔍 서버 상태 확인..."
if ! curl -s --max-time 5 "$BASE_URL/news" > /dev/null; then
    echo "❌ SAM Local 서버가 실행되지 않았습니다. (Port 3001)"
    echo "다음 명령으로 서버를 시작하세요: sam local start-api --env-vars env.json --host 0.0.0.0 --port 3001"
    exit 1
fi
echo "✅ SAM Local 서버 정상 작동 중"
echo ""

# 1. News API 테스트
echo "📰 1. News API 테스트"
echo "----------------------"
echo "• News 목록 조회:"
NEWS_RESPONSE=$(curl -s "$BASE_URL/news")
NEWS_SUCCESS=$(echo "$NEWS_RESPONSE" | jq -r '.success // false')
NEWS_TOTAL=$(echo "$NEWS_RESPONSE" | jq -r '.total // 0')
echo "  - 성공: $NEWS_SUCCESS"
echo "  - 총 개수: $NEWS_TOTAL"

echo "• Recent News 조회:"
RECENT_NEWS_RESPONSE=$(curl -s "$BASE_URL/news/recent")
RECENT_NEWS_SUCCESS=$(echo "$RECENT_NEWS_RESPONSE" | jq -r '.success // false')
RECENT_NEWS_TOTAL=$(echo "$RECENT_NEWS_RESPONSE" | jq -r '.total // 0')
echo "  - 성공: $RECENT_NEWS_SUCCESS"
echo "  - 최근 개수: $RECENT_NEWS_TOTAL"
echo ""

# 2. Gallery API 테스트
echo "🖼️  2. Gallery API 테스트"
echo "------------------------"
echo "• Gallery 목록 조회:"
GALLERY_RESPONSE=$(curl -s "$BASE_URL/gallery")
GALLERY_SUCCESS=$(echo "$GALLERY_RESPONSE" | jq -r '.success // false')
GALLERY_TOTAL=$(echo "$GALLERY_RESPONSE" | jq -r '.total // 0')
echo "  - 성공: $GALLERY_SUCCESS"
echo "  - 총 개수: $GALLERY_TOTAL"

echo "• Recent Gallery 조회:"
RECENT_GALLERY_RESPONSE=$(curl -s "$BASE_URL/gallery/recent")
RECENT_GALLERY_SUCCESS=$(echo "$RECENT_GALLERY_RESPONSE" | jq -r '.success // false')
RECENT_GALLERY_TOTAL=$(echo "$RECENT_GALLERY_RESPONSE" | jq -r '.total // 0')
echo "  - 성공: $RECENT_GALLERY_SUCCESS"
echo "  - 최근 개수: $RECENT_GALLERY_TOTAL"
echo ""

# 3. Auth API 테스트
echo "🔐 3. Auth API 테스트"
echo "--------------------"
echo "• 로그인 테스트:"
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}')
LOGIN_SUCCESS=$(echo "$LOGIN_RESPONSE" | jq -r '.success // false')
TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.data.token // ""')
echo "  - 로그인 성공: $LOGIN_SUCCESS"
echo "  - 토큰 생성: $([ -n "$TOKEN" ] && echo "✅" || echo "❌")"

if [ -n "$TOKEN" ]; then
    echo "• 토큰 검증 테스트:"
    VALIDATE_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/validate" \
      -H "Content-Type: application/json" \
      -d "{\"token\": \"$TOKEN\"}")
    VALIDATE_SUCCESS=$(echo "$VALIDATE_RESPONSE" | jq -r '.success // false')
    VALIDATE_VALID=$(echo "$VALIDATE_RESPONSE" | jq -r '.data.valid // false')
    echo "  - 검증 성공: $VALIDATE_SUCCESS"
    echo "  - 토큰 유효: $VALIDATE_VALID"
fi
echo ""

# 4. 전체 결과 요약
echo "📊 테스트 결과 요약"
echo "=================="
echo "API 엔드포인트 상태:"
echo "┌────────────────────────┬────────┬────────────┐"
echo "│ 서비스                 │ 상태   │ 데이터     │"
echo "├────────────────────────┼────────┼────────────┤"
printf "│ %-22s │ %-6s │ %10s │\n" "📰 News" "$([ "$NEWS_SUCCESS" = "true" ] && echo "✅" || echo "❌")" "${NEWS_TOTAL}개"
printf "│ %-22s │ %-6s │ %10s │\n" "📰 Recent News" "$([ "$RECENT_NEWS_SUCCESS" = "true" ] && echo "✅" || echo "❌")" "${RECENT_NEWS_TOTAL}개"
printf "│ %-22s │ %-6s │ %10s │\n" "🖼️ Gallery" "$([ "$GALLERY_SUCCESS" = "true" ] && echo "✅" || echo "❌")" "${GALLERY_TOTAL}개"
printf "│ %-22s │ %-6s │ %10s │\n" "🖼️ Recent Gallery" "$([ "$RECENT_GALLERY_SUCCESS" = "true" ] && echo "✅" || echo "❌")" "${RECENT_GALLERY_TOTAL}개"
printf "│ %-22s │ %-6s │ %10s │\n" "🔐 Auth Login" "$([ "$LOGIN_SUCCESS" = "true" ] && echo "✅" || echo "❌")" "JWT"
printf "│ %-22s │ %-6s │ %10s │\n" "🔐 Auth Validate" "$([ "$VALIDATE_SUCCESS" = "true" ] && echo "✅" || echo "❌")" "검증"
echo "└────────────────────────┴────────┴────────────┘"
echo ""

# 5. 시스템 상태
echo "🏗️ 시스템 상태"
echo "==============="
echo "• SAM Local API: http://localhost:3001 ✅"
echo "• DynamoDB Local: http://localhost:8000"

# DynamoDB 상태 확인
if curl -s --max-time 3 "http://localhost:8000" > /dev/null 2>&1; then
    echo "  └─ DynamoDB Local: ✅ 실행 중"
else
    echo "  └─ DynamoDB Local: ❌ 실행되지 않음"
fi
echo ""

# 전체 성공률 계산
TOTAL_TESTS=6
SUCCESSFUL_TESTS=0

[ "$NEWS_SUCCESS" = "true" ] && ((SUCCESSFUL_TESTS++))
[ "$RECENT_NEWS_SUCCESS" = "true" ] && ((SUCCESSFUL_TESTS++))
[ "$GALLERY_SUCCESS" = "true" ] && ((SUCCESSFUL_TESTS++))
[ "$RECENT_GALLERY_SUCCESS" = "true" ] && ((SUCCESSFUL_TESTS++))
[ "$LOGIN_SUCCESS" = "true" ] && ((SUCCESSFUL_TESTS++))
[ "$VALIDATE_SUCCESS" = "true" ] && ((SUCCESSFUL_TESTS++))

SUCCESS_RATE=$((SUCCESSFUL_TESTS * 100 / TOTAL_TESTS))

echo "🎯 최종 결과"
echo "============"
echo "성공률: $SUCCESSFUL_TESTS/$TOTAL_TESTS ($SUCCESS_RATE%)"

if [ $SUCCESS_RATE -eq 100 ]; then
    echo "🎉 모든 API가 정상적으로 작동합니다!"
    echo "✨ Blog System 로컬 환경 구축 완료!"
elif [ $SUCCESS_RATE -ge 80 ]; then
    echo "✅ 대부분의 API가 정상 작동합니다."
    echo "⚠️  일부 API에 문제가 있을 수 있습니다."
else
    echo "❌ 여러 API에 문제가 있습니다."
    echo "🔧 서버 및 데이터베이스 상태를 확인해주세요."
    exit 1
fi

echo ""
echo "📞 추가 지원이 필요하시면 문의해주세요!"
echo "🚀 프론트엔드 개발 및 프로덕션 배포 준비 완료!"
