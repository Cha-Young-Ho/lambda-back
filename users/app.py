import json

def lambda_handler(event, context):
    print("Received users API event:", event)
    
    # HTTP 메서드 확인
    http_method = event.get("httpMethod", "")
    
    # 경로 파라미터 처리
    path_parameters = event.get("pathParameters") or {}
    user_id = path_parameters.get("userId")
    
    # 쿼리 파라미터 처리
    query = event.get("queryStringParameters") or {}
    detail = query.get("detail", "basic")
    
    # 샘플 사용자 데이터 (실제 구현에서는 데이터베이스 조회)
    users_db = {
        "1": {"id": "1", "name": "John Doe", "email": "john@example.com", "created_at": "2023-01-01"},
        "2": {"id": "2", "name": "Jane Smith", "email": "jane@example.com", "created_at": "2023-02-15"},
        "3": {"id": "3", "name": "Bob Johnson", "email": "bob@example.com", "created_at": "2023-03-20"}
    }
    
    # 응답 데이터 준비
    if user_id:
        # 특정 사용자 정보 조회
        if user_id in users_db:
            user_data = users_db[user_id]
            if detail == "basic":
                # 기본 정보만 반환
                response_data = {
                    "id": user_data["id"],
                    "name": user_data["name"]
                }
            else:
                # 모든 정보 반환
                response_data = user_data
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(response_data)
            }
        else:
            # 사용자를 찾을 수 없음
            return {
                "statusCode": 404,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "User not found"})
            }
    else:
        # 모든 사용자 목록 반환
        if detail == "basic":
            # 기본 정보만 포함된 목록
            users_list = [{"id": u["id"], "name": u["name"]} for u in users_db.values()]
        else:
            # 전체 정보가 포함된 목록
            users_list = list(users_db.values())
            
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(users_list)
        }
