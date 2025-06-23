import json
import jwt
import datetime
from common.config import config_manager

def lambda_handler(event, context):
    """
    관리자 로그인 함수 - 실제 설정과 JWT 연동
    """
    try:
        print("=== Auth Function ===")
        print(f"Event: {event}")
        
        method = event.get("httpMethod", "")
        
        # CORS 처리
        if method == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type,Authorization",
                    "Access-Control-Allow-Methods": "POST,OPTIONS"
                },
                "body": ""
            }
        
        # POST 로그인 처리
        if method == "POST":
            try:
                body = json.loads(event.get("body", "{}"))
                username = body.get("username")
                password = body.get("password")
                
                if not username or not password:
                    return {
                        "statusCode": 400,
                        "headers": {
                            "Content-Type": "application/json",
                            "Access-Control-Allow-Origin": "*"
                        },
                        "body": json.dumps({"error": "Username and password are required"})
                    }
                
                # 설정에서 관리자 자격증명 확인
                config = config_manager.get_config()
                admin_config = config.get("admin", {})
                
                admin_username = admin_config.get("username", "admin")
                admin_password = admin_config.get("password", "admin123")
                jwt_secret = admin_config.get("jwt_secret", "local_jwt_secret_key_for_testing_minimum_32_chars")
                
                if username != admin_username or password != admin_password:
                    return {
                        "statusCode": 401,
                        "headers": {
                            "Content-Type": "application/json",
                            "Access-Control-Allow-Origin": "*"
                        },
                        "body": json.dumps({"error": "Invalid credentials"})
                    }
                
                # JWT 토큰 생성
                payload = {
                    "username": username,
                    "role": "admin",
                    "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
                    "iat": datetime.datetime.utcnow()
                }
                
                token = jwt.encode(payload, jwt_secret, algorithm="HS256")
                
                return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*"
                    },
                    "body": json.dumps({
                        "message": "Login successful",
                        "token": token,
                        "expires_in": 86400
                    })
                }
                
            except json.JSONDecodeError:
                return {
                    "statusCode": 400,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*"
                    },
                    "body": json.dumps({"error": "Invalid JSON"})
                }
        
        return {
            "statusCode": 405,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"error": "Method not allowed"})
        }
        
    except Exception as e:
        print(f"Error in auth function: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"error": "Internal server error"})
        }

def verify_admin_token(token, config):
    """JWT 토큰 검증 함수"""
    try:
        admin_config = config.get("admin", {})
        jwt_secret = admin_config.get("jwt_secret", "local_jwt_secret_key_for_testing_minimum_32_chars")
        
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        
        if payload.get("role") != "admin":
            return None
            
        return payload
        
    except jwt.ExpiredSignatureError:
        print("Token expired")
        return None
    except jwt.InvalidTokenError:
        print("Invalid token")
        return None
    except Exception as e:
        print(f"Token verification error: {str(e)}")
        return None
