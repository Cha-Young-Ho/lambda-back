# My API Server (SAM + Python)

## 실행 방법

```bash
sam build
sam local start-api
```

## 배포 방법

This project is configured with GitHub Actions for automatic deployment.
When you push to the `main` branch, the workflow will:
1. Build the SAM application
2. Deploy it to AWS using the configured credentials

### 필요한 GitHub Secrets:
- `AWS_ACCESS_KEY_ID`: AWS 액세스 키
- `AWS_SECRET_ACCESS_KEY`: AWS 시크릿 키
- `AWS_REGION`: 배포할 AWS 리전
- `AWS_ROLE_TO_ASSUME`: 배포에 사용할 AWS IAM 역할 ARN

