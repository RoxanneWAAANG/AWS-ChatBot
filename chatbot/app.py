import os
import boto3
import json
from botocore.exceptions import ClientError

# read from environment variables
MODEL_ID = os.getenv("BEDROCK_MODEL_ID")

# use boto3 call Bedrock Runtime
bedrock = boto3.client("bedrock-runtime")

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        user_input = body.get("message", "")
        
        if not user_input:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Message is required"})
            }
        
        # 构建正确的 Claude Messages API 格式的请求
        payload = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": user_input}]
        })
        
        resp = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=payload,
            contentType="application/json",
            accept="application/json"
        )
        
        # 解析 Claude 的响应格式
        data = json.loads(resp["body"].read().decode("utf-8"))
        reply = data["content"][0]["text"]  # Claude 使用 content[0].text 而不是 choices[0].message.content
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"reply": reply})
        }
    except ClientError as e:
        print(f"AWS Client Error: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
    except Exception as e:
        print(f"General Error: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }