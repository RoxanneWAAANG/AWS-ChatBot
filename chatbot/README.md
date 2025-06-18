# Serverless Claude Chat Backend

## Project Overview
A serverless chatbot backend using AWS Bedrock and Claude Sonnet 4, deployed with AWS SAM.

## Architecture
- **AWS Lambda**: Handles chat requests
- **API Gateway**: REST API endpoint
- **AWS Bedrock**: Claude model integration
- **CloudWatch**: Logging and monitoring

## Deployment
```bash
# Deploy the serverless application
sam deploy --guided

# Test the API
curl -X POST https://qo83onnpe0.execute-api.us-east-2.amazonaws.com/Prod/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello Claude!"}'
```

## API Endpoint
- **URL**: `https://qo83onnpe0.execute-api.us-east-2.amazonaws.com/Prod/chat`
- **Method**: POST
- **Body**: `{"message": "Your question here"}`
- **Response**: `{"reply": "Claude's response"}`

## Key Learnings
1. **AWS Bedrock Setup**: Learned to request model access and use inference profiles
2. **Serverless Architecture**: Deployed Lambda functions with SAM templates
3. **LLM Integration**: Successfully connected to Claude Sonnet 4 via AWS Bedrock
4. **API Design**: Created RESTful endpoint for chat functionality

## Cost Considerations
- Lambda: Pay per request (~$0.20/1M requests)
- API Gateway: ~$1.00/1M requests
- Bedrock: Pay per token (~$3/1M input tokens for Claude Sonnet 4)

## Files
- `template.yaml`: SAM deployment configuration
- `chatbot/app.py`: Lambda function code
- `README.md`: This documentation

## Future Enhancements
- Add conversation history
- Build web frontend
- Implement advanced prompt engineering
- Add user authentication