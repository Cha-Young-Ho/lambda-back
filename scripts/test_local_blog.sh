#!/bin/bash

# 🧪 블로그 시스템 빠른 테스트 스크립트

echo "=== 🧪 블로그 시스템 API 테스트 ==="

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_test() {
    echo -e "${BLUE}🔍 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

BASE_URL="http://localhost:3002"

# 서버 상태 확인
print_test "서버 상태 확인"
if curl -s $BASE_URL/board > /dev/null; then
    print_success "API 서버 실행 중"
else
    echo "❌ API 서버가 실행되지 않았습니다"
    echo "먼저 './scripts/start_local_blog.sh'를 실행하세요"
    exit 1
fi

echo ""

# 1. 게시글 목록 조회
print_test "게시글 목록 조회"
echo "GET $BASE_URL/board"
curl -s $BASE_URL/board | jq .
echo ""

# 2. 게시글 상세 조회
print_test "게시글 상세 조회 (ID: 1)"
echo "GET $BASE_URL/board/1"
curl -s $BASE_URL/board/1 | jq .
echo ""

# 3. 관리자 로그인
print_test "관리자 로그인"
echo "POST $BASE_URL/auth/login"
TOKEN_RESPONSE=$(curl -s -X POST $BASE_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}')

echo $TOKEN_RESPONSE | jq .

# 토큰 추출
TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.token')
echo ""

if [ "$TOKEN" != "null" ] && [ "$TOKEN" != "" ]; then
    print_success "로그인 성공, 토큰 획득"
    
    # 4. 새 게시글 생성
    print_test "새 게시글 생성"
    echo "POST $BASE_URL/board"
    
    TITLE="테스트 게시글 $(date '+%Y-%m-%d %H:%M:%S')"
    CONTENT="이것은 자동 테스트로 생성된 게시글입니다.\n\n생성 시간: $(date)\n\n블로그 시스템이 정상적으로 작동하고 있습니다!"
    
    CREATE_RESPONSE=$(curl -s -X POST $BASE_URL/board \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -d "{\"title\": \"$TITLE\", \"content\": \"$CONTENT\"}")
    
    echo $CREATE_RESPONSE | jq .
    
    BOARD_ID=$(echo $CREATE_RESPONSE | jq -r '.boardId')
    echo ""
    
    if [ "$BOARD_ID" != "null" ] && [ "$BOARD_ID" != "" ]; then
        print_success "게시글 생성 성공 (ID: $BOARD_ID)"
        
        # 5. 생성된 게시글 조회
        print_test "생성된 게시글 상세 조회"
        echo "GET $BASE_URL/board/$BOARD_ID"
        curl -s $BASE_URL/board/$BOARD_ID | jq .
        echo ""
        
        # 6. 업데이트된 게시글 목록 조회
        print_test "업데이트된 게시글 목록 확인"
        echo "GET $BASE_URL/board"
        curl -s $BASE_URL/board | jq .
        echo ""
    else
        echo "❌ 게시글 생성 실패"
    fi
else
    echo "❌ 로그인 실패"
fi

print_success "🎉 API 테스트 완료!"
echo ""
echo "💡 추가 테스트 명령어:"
echo "- 게시글 목록: curl -s $BASE_URL/board | jq ."
echo "- 실시간 모니터링: watch 'curl -s $BASE_URL/board | jq .'"
