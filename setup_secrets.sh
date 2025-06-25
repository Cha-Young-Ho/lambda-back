#!/bin/bash
# AWS Secrets Manager 설정 스크립트

echo "🔐 Setting up AWS Secrets Manager..."
echo

# Dev 환경 Secret 생성
echo "📝 Creating dev environment secret..."
aws secretsmanager create-secret \
  --name "blog/dev/config" \
  --description "Blog configuration for dev environment" \
  --secret-string '{
    "admin": {
      "username": "admin",
      "password": "dev_password_change_me"
    },
    "jwt_secret": "dev_jwt_secret_key_32_characters_long_change_me"
  }' \
  --tags '[
    {"Key": "Environment", "Value": "dev"},
    {"Key": "Project", "Value": "Blog"}
  ]' 2>/dev/null && echo "✅ Created blog/dev/config" || echo "⚠️  Secret blog/dev/config already exists or failed to create"

echo

# Prod 환경 Secret 생성
echo "📝 Creating prod environment secret..."
aws secretsmanager create-secret \
  --name "blog/prod/config" \
  --description "Blog configuration for prod environment" \
  --secret-string '{
    "admin": {
      "username": "admin", 
      "password": "prod_secure_password_change_me"
    },
    "jwt_secret": "prod_jwt_secret_key_32_characters_long_change_me"
  }' \
  --tags '[
    {"Key": "Environment", "Value": "prod"},
    {"Key": "Project", "Value": "Blog"}
  ]' 2>/dev/null && echo "✅ Created blog/prod/config" || echo "⚠️  Secret blog/prod/config already exists or failed to create"

echo
echo "✅ Secrets setup completed!"
echo
echo "⚠️  WARNING: Please change the default passwords and JWT secrets!"
echo "   Update secrets using:"
echo "   aws secretsmanager update-secret --secret-id blog/dev/config --secret-string '{...}'"
echo "   aws secretsmanager update-secret --secret-id blog/prod/config --secret-string '{...}'"
