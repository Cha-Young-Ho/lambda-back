#!/usr/bin/env python3
"""
로컬 환경 설정 스크립트
env.json 파일을 생성하여 로컬 테스트 환경을 설정합니다.
"""

import json
import os

def setup_local_env():
    """로컬 환경을 위한 env.json 파일 생성"""
    
    # 로컬 테스트용 설정
    local_config = {
        "local": {
            "admin": {
                "username": "admin",
                "password": "local_password"
            },
            "jwt_secret": "local_jwt_secret_key_for_testing_only"
        }
    }
    
    env_file_path = "env.json"
    
    try:
        # env.json 파일 생성/업데이트
        with open(env_file_path, 'w') as f:
            json.dump(local_config, f, indent=2)
        
        print(f"✅ Created local environment file: {env_file_path}")
        print()
        print("📁 Local configuration:")
        print(f"   Username: {local_config['local']['admin']['username']}")
        print(f"   Password: {local_config['local']['admin']['password']}")
        print()
        print("🚀 You can now run: sam local start-api")
        
    except Exception as e:
        print(f"❌ Error creating local environment file: {str(e)}")

def main():
    """메인 함수"""
    
    print("🔧 Setting up LOCAL environment for testing...")
    print()
    print("ℹ️  This script only sets up LOCAL testing environment.")
    print("   For dev/prod environments, please manually configure:")
    print("   - AWS Secrets Manager: blog/dev/config, blog/prod/config")
    print("   - DynamoDB Tables: blog-table-dev, blog-table-prod")
    print()
    
    setup_local_env()
    
    print()
    print("📋 Next steps:")
    print("   1. Setup DynamoDB table: python3 setup_local_table.py")
    print("   2. Run 'sam local start-api' for local testing")
    print("   3. For AWS deployment, manually set up Secrets Manager and DynamoDB")
    print("   4. Run 'sam deploy --parameter-overrides Stage=dev' for dev deployment")
    print()
    print("🔧 Required AWS Secrets Manager structure for dev/prod:")
    print(json.dumps({
        "admin": {
            "username": "admin",
            "password": "your_secure_password"
        },
        "jwt_secret": "your_32_character_jwt_secret_key"
    }, indent=2))

if __name__ == "__main__":
    main()
