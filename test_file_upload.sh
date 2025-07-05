#!/bin/bash

# 🚀 S3 파일 업로드 기능 테스트 스크립트
# 사용법: bash test_file_upload.sh

BASE_URL="http://localhost:3001"
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}📁 S3 파일 업로드 기능 테스트${NC}"
echo "=================================="

# 서버 상태 확인
echo -e "\n${BLUE}🔍 서버 상태 확인${NC}"
if curl -s $BASE_URL/gallery/recent > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 서버가 정상적으로 실행 중입니다${NC}"
else
    echo -e "${RED}❌ 서버에 연결할 수 없습니다. SAM 서버가 실행 중인지 확인해주세요${NC}"
    exit 1
fi

# 1. Gallery 파일 업로드 URL 생성 테스트
echo -e "\n${BLUE}🖼️ Gallery 파일 업로드 URL 생성 테스트${NC}"
echo "============================================"

echo "1.1 유효한 이미지 파일 타입으로 URL 생성..."
for content_type in "image/jpeg" "image/png" "image/gif"; do
    echo -e "\n  테스트 중: ${YELLOW}$content_type${NC}"
    
    response=$(curl -s -X POST $BASE_URL/gallery/upload-url \
        -H "Content-Type: application/json" \
        -d "{\"content_type\": \"$content_type\"}")
    
    if echo $response | jq -e '.success' > /dev/null 2>&1; then
        echo -e "  ${GREEN}✅ $content_type URL 생성 성공${NC}"
        
        # URL 정보 출력
        upload_url=$(echo $response | jq -r '.data.upload_url')
        file_url=$(echo $response | jq -r '.data.file_url')
        expires_in=$(echo $response | jq -r '.data.expires_in')
        
        echo -e "    📎 파일 URL: ${file_url}"
        echo -e "    ⏱️  만료 시간: ${expires_in}초"
    else
        echo -e "  ${RED}❌ $content_type URL 생성 실패${NC}"
        echo "     응답: $response"
    fi
done

echo -e "\n1.2 PDF 파일 타입으로 URL 생성..."
response=$(curl -s -X POST $BASE_URL/gallery/upload-url \
    -H "Content-Type: application/json" \
    -d '{"content_type": "application/pdf"}')

if echo $response | jq -e '.success' > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅ PDF URL 생성 성공${NC}"
    file_url=$(echo $response | jq -r '.data.file_url')
    echo -e "    📎 파일 URL: ${file_url}"
else
    echo -e "  ${RED}❌ PDF URL 생성 실패${NC}"
    echo "     응답: $response"
fi

echo -e "\n1.3 허용되지 않는 파일 타입 검증..."
response=$(curl -s -X POST $BASE_URL/gallery/upload-url \
    -H "Content-Type: application/json" \
    -d '{"content_type": "application/javascript"}')

if echo $response | jq -e '.error' > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅ 잘못된 파일 타입 거부 성공${NC}"
else
    echo -e "  ${RED}❌ 잘못된 파일 타입 거부 실패${NC}"
    echo "     응답: $response"
fi

# 2. News 파일 업로드 URL 생성 테스트
echo -e "\n${BLUE}📰 News 파일 업로드 URL 생성 테스트${NC}"
echo "========================================"

echo "2.1 뉴스 이미지 업로드 URL 생성..."
response=$(curl -s -X POST $BASE_URL/news/upload-url \
    -H "Content-Type: application/json" \
    -d '{"content_type": "image/jpeg"}')

if echo $response | jq -e '.success' > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅ News 이미지 URL 생성 성공${NC}"
    file_url=$(echo $response | jq -r '.data.file_url')
    echo -e "    📎 파일 URL: ${file_url}"
    
    # 폴더 구분 확인
    if echo $file_url | grep -q "/news/"; then
        echo -e "    ${GREEN}✅ 올바른 폴더(news)에 저장 예정${NC}"
    else
        echo -e "    ${YELLOW}⚠️  폴더 구분이 명확하지 않음${NC}"
    fi
else
    echo -e "  ${RED}❌ News 이미지 URL 생성 실패${NC}"
    echo "     응답: $response"
fi

echo -e "\n2.2 필수 파라미터 누락 테스트..."
response=$(curl -s -X POST $BASE_URL/news/upload-url \
    -H "Content-Type: application/json" \
    -d '{}')

if echo $response | jq -e '.error' > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅ 필수 파라미터 누락 시 에러 반환 성공${NC}"
else
    echo -e "  ${RED}❌ 필수 파라미터 검증 실패${NC}"
    echo "     응답: $response"
fi

# 3. 파일 업로드 URL 응답 구조 검증
echo -e "\n${BLUE}🔍 업로드 URL 응답 구조 검증${NC}"
echo "================================"

response=$(curl -s -X POST $BASE_URL/gallery/upload-url \
    -H "Content-Type: application/json" \
    -d '{"content_type": "image/png"}')

echo "3.1 필수 필드 존재 확인..."
required_fields=("upload_url" "file_url" "file_key" "expires_in" "expires_at")

for field in "${required_fields[@]}"; do
    if echo $response | jq -e ".data.$field" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✅ $field 필드 존재${NC}"
    else
        echo -e "  ${RED}❌ $field 필드 누락${NC}"
    fi
done

# 4. 엔드포인트 접근성 테스트
echo -e "\n${BLUE}🌐 엔드포인트 접근성 테스트${NC}"
echo "=============================="

echo "4.1 Gallery 업로드 URL 엔드포인트..."
status_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST $BASE_URL/gallery/upload-url \
    -H "Content-Type: application/json" \
    -d '{"content_type": "image/jpeg"}')

if [ "$status_code" = "200" ]; then
    echo -e "  ${GREEN}✅ Gallery 업로드 엔드포인트 접근 가능 (HTTP $status_code)${NC}"
else
    echo -e "  ${RED}❌ Gallery 업로드 엔드포인트 접근 실패 (HTTP $status_code)${NC}"
fi

echo "4.2 News 업로드 URL 엔드포인트..."
status_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST $BASE_URL/news/upload-url \
    -H "Content-Type: application/json" \
    -d '{"content_type": "image/jpeg"}')

if [ "$status_code" = "200" ]; then
    echo -e "  ${GREEN}✅ News 업로드 엔드포인트 접근 가능 (HTTP $status_code)${NC}"
else
    echo -e "  ${RED}❌ News 업로드 엔드포인트 접근 실패 (HTTP $status_code)${NC}"
fi

# 5. 지원 파일 타입 목록 출력
echo -e "\n${BLUE}📋 지원하는 파일 타입${NC}"
echo "===================="
echo -e "${YELLOW}이미지:${NC} image/jpeg, image/png, image/gif, image/webp"
echo -e "${YELLOW}문서:${NC} application/pdf, text/plain"
echo -e "${YELLOW}오피스:${NC} application/msword, application/vnd.openxmlformats-officedocument.wordprocessingml.document"

echo -e "\n${BLUE}🎉 파일 업로드 기능 테스트 완료!${NC}"
echo "=================================="
echo "모든 테스트가 완료되었습니다."
echo "문제가 발생한 항목이 있다면 로그를 확인해주세요."
