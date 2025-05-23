def lambda_handler(event, context):
    print("Received event:", event)

    # queryStringParameters가 None일 수도 있으므로 기본값 {} 처리
    query = event.get("queryStringParameters") or {}
    name = query.get("name", "World")

    return {
        "statusCode": 200,
        "body": f"Hello, {name}!"
    }

