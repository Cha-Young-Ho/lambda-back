#!/bin/bash

# GitHub 태그 완전 삭제 및 초기화 스크립트
# 주의: 이 스크립트는 모든 태그를 삭제합니다. 신중하게 사용하세요.

echo "🚨 모든 Git 태그를 삭제합니다..."
echo "계속하시겠습니까? (y/N)"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "📋 현재 태그 목록:"
    git tag -l
    
    echo ""
    echo "🗑️  로컬 태그 삭제 중..."
    
    # 로컬의 모든 태그 삭제
    git tag -l | xargs -n 1 git tag -d
    
    echo ""
    echo "🌐 원격(GitHub)의 모든 태그 삭제 중..."
    
    # 원격의 모든 태그 삭제
    git tag -l | xargs -n 1 -I {} git push --delete origin {}
    
    echo ""
    echo "✅ 모든 태그가 삭제되었습니다!"
    
    echo ""
    echo "📝 새로운 태그 생성 예시:"
    echo "git tag v1.0.0"
    echo "git push origin v1.0.0"
    
else
    echo "❌ 취소되었습니다."
fi
