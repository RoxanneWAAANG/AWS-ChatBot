import os
import boto3
import json
import time
import hashlib
import logging
from botocore.exceptions import ClientError
from typing import List, Dict, Optional
from dataclasses import dataclass

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

@dataclass
class ChatMessage:
    role: str
    content: str
    timestamp: float
    token_count: Optional[int] = None

class ConversationManager:
    """
    Manages conversation history with O(1) access and O(n) memory complexity.
    Uses LRU-like eviction strategy for memory management.
    """
    
    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self._conversation_cache = {}  # O(1) lookup by conversation_id
    
    def add_message(self, conversation_id: str, message: ChatMessage) -> None:
        """
        Time Complexity: O(1) average case
        Space Complexity: O(n) where n is number of messages
        """
        if conversation_id not in self._conversation_cache:
            self._conversation_cache[conversation_id] = []
        
        history = self._conversation_cache[conversation_id]
        history.append(message)
        
        # Maintain max history size - O(1) operation
        if len(history) > self.max_history:
            history.pop(0)  # Remove oldest message
    
    def get_history(self, conversation_id: str) -> List[Dict[str, str]]:
        """
        Time Complexity: O(m) where m is number of messages in conversation
        Space Complexity: O(m)
        """
        if conversation_id not in self._conversation_cache:
            return []
        
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self._conversation_cache[conversation_id]
        ]

class TokenCounter:
    """
    Estimates token count using approximation algorithm.
    Time Complexity: O(n) where n is text length
    Space Complexity: O(1)
    """
    
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Approximate token counting: ~4 characters per token
        This is a simplified heuristic for demonstration
        """
        return max(1, len(text) // 4)

class RateLimiter:
    """
    Token bucket algorithm for rate limiting.
    Time Complexity: O(1) for each check
    Space Complexity: O(k) where k is number of unique identifiers
    """
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets = {}
    
    def is_allowed(self, identifier: str) -> bool:
        """
        Time Complexity: O(1)
        Space Complexity: O(1) per identifier
        """
        current_time = time.time()
        
        if identifier not in self._buckets:
            self._buckets[identifier] = []
        
        # Remove old requests outside the window - O(k) worst case where k <= max_requests
        bucket = self._buckets[identifier]
        self._buckets[identifier] = [
            req_time for req_time in bucket 
            if current_time - req_time < self.window_seconds
        ]
        
        # Check if under limit
        if len(self._buckets[identifier]) < self.max_requests:
            self._buckets[identifier].append(current_time)
            return True
        
        return False

# Global instances
MODEL_ID = os.getenv("BEDROCK_MODEL_ID")
bedrock = boto3.client("bedrock-runtime")
conversation_manager = ConversationManager()
token_counter = TokenCounter()
rate_limiter = RateLimiter()

def generate_conversation_id(event: dict) -> str:
    """
    Generate conversation ID from source IP and user agent.
    Time Complexity: O(1)
    Space Complexity: O(1)
    """
    source_ip = event.get('requestContext', {}).get('identity', {}).get('sourceIp', 'unknown')
    user_agent = event.get('headers', {}).get('User-Agent', 'unknown')
    
    # Create hash for privacy and uniqueness
    identifier = f"{source_ip}:{user_agent}"
    return hashlib.md5(identifier.encode()).hexdigest()[:16]

def validate_input(message: str) -> Dict[str, any]:
    """
    Input validation with complexity analysis.
    Time Complexity: O(n) where n is message length
    Space Complexity: O(1)
    """
    if not message:
        return {"valid": False, "error": "Message cannot be empty"}
    
    if len(message) > 2000:
        return {"valid": False, "error": "Message too long (max 2000 characters)"}
    
    # Check for potential prompt injection patterns - O(n)
    dangerous_patterns = ["ignore previous instructions", "system:", "assistant:"]
    message_lower = message.lower()
    
    for pattern in dangerous_patterns:
        if pattern in message_lower:
            logger.warning(f"Potential prompt injection detected: {pattern}")
    
    estimated_tokens = token_counter.estimate_tokens(message)
    
    return {
        "valid": True,
        "estimated_tokens": estimated_tokens,
        "length": len(message)
    }

def lambda_handler(event, context):
    """
    Main handler with comprehensive error handling and performance tracking.
    Overall Time Complexity: O(n + m) where n=message length, m=conversation history
    Space Complexity: O(m) where m=conversation history size
    """
    start_time = time.time()
    conversation_id = generate_conversation_id(event)
    
    try:
        # Rate limiting check - O(1)
        if not rate_limiter.is_allowed(conversation_id):
            return {
                "statusCode": 429,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "error": "Rate limit exceeded. Please wait before sending another message."
                })
            }
        
        # Parse and validate input - O(n)
        body = json.loads(event.get("body", "{}"))
        user_input = body.get("message", "")
        
        validation_result = validate_input(user_input)
        if not validation_result["valid"]:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": validation_result["error"]})
            }
        
        # Get conversation history - O(m)
        history = conversation_manager.get_history(conversation_id)
        messages = history + [{"role": "user", "content": user_input}]
        
        # Add user message to conversation
        user_message = ChatMessage(
            role="user",
            content=user_input,
            timestamp=time.time(),
            token_count=validation_result["estimated_tokens"]
        )
        conversation_manager.add_message(conversation_id, user_message)
        
        # Call Bedrock API
        payload = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": messages
        })
        
        bedrock_start = time.time()
        resp = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=payload,
            contentType="application/json",
            accept="application/json"
        )
        bedrock_duration = time.time() - bedrock_start
        
        # Parse response
        data = json.loads(resp["body"].read().decode("utf-8"))
        reply = data["content"][0]["text"]
        
        # Add assistant message to conversation
        assistant_message = ChatMessage(
            role="assistant",
            content=reply,
            timestamp=time.time(),
            token_count=token_counter.estimate_tokens(reply)
        )
        conversation_manager.add_message(conversation_id, assistant_message)
        
        # Performance metrics
        total_duration = time.time() - start_time
        
        # Log performance metrics
        logger.info(f"Request processed - Total: {total_duration:.3f}s, Bedrock: {bedrock_duration:.3f}s, "
                   f"Input tokens: ~{validation_result['estimated_tokens']}, "
                   f"Conversation length: {len(history) + 2}")
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "X-Response-Time": str(total_duration),
                "X-Bedrock-Time": str(bedrock_duration)
            },
            "body": json.dumps({
                "reply": reply,
                "metadata": {
                    "conversation_id": conversation_id,
                    "response_time_ms": int(total_duration * 1000),
                    "estimated_tokens": {
                        "input": validation_result["estimated_tokens"],
                        "output": token_counter.estimate_tokens(reply)
                    }
                }
            })
        }
        
    except ClientError as e:
        logger.error(f"AWS Client Error: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Service temporarily unavailable"})
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Internal server error"})
        }
