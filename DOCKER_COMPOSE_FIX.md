# Docker Compose Command Fix

## 🚨 문제 상황
GitHub Actions에서 다음 오류가 발생:
```
docker-compose: command not found
Error: Process completed with exit code 127
```

## 🔧 해결책
GitHub Actions의 최신 runner들은 `docker-compose` 대신 `docker compose` (하이픈 없이)를 사용합니다.

## 📝 수정된 파일들

### 1. `.github/workflows/deploy.yml`
- `docker-compose` → `docker compose` 변경
- 대체 명령어 지원 로직 추가
- 테스트 실패 시 디버깅 정보 수집 단계 추가

### 2. `run_tests.sh`
- 로컬/CI 환경 모두 지원하도록 개선
- `docker-compose`와 `docker compose` 자동 감지

### 3. 문서 파일들
- `README.md`
- `FINAL_PROJECT_STATUS.md`
- `API_DOCUMENTATION.md`
- `local-setup/README.md`

## 🎯 호환성 로직

```bash
# 두 방식 모두 지원
if command -v docker-compose >/dev/null 2>&1; then
    echo "Using docker-compose"
    docker-compose -f docker-compose.test.yml up -d
else
    echo "Using docker compose"
    docker compose -f docker-compose.test.yml up -d
fi
```

## ✅ 결과
- ✅ GitHub Actions에서 정상 작동
- ✅ 로컬 환경에서도 기존대로 작동
- ✅ 미래 호환성 확보
- ✅ 자동 디버깅 정보 수집

## 📋 테스트 방법

### 로컬 테스트
```bash
./run_tests.sh --unit
```

### GitHub Actions 테스트
```bash
# 태그 푸시로 워크플로우 트리거
git tag v1.0.1
git push origin v1.0.1
```

---
**수정 완료일**: 2025-07-06  
**적용 범위**: GitHub Actions, 로컬 환경, 문서화
