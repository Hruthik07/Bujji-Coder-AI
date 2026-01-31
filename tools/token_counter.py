"""
Token Counter Utility
Counts tokens for multiple LLM models using tiktoken
"""
import tiktoken
from typing import List, Dict, Optional


class TokenCounter:
    """Count tokens for different LLM models"""
    
    # Model encoding mappings
    ENCODING_MAP = {
        "gpt-3.5-turbo": "cl100k_base",
        "gpt-4": "cl100k_base",
        "gpt-4-turbo": "cl100k_base",
        "deepseek-coder": "cl100k_base",  # DeepSeek uses OpenAI-compatible encoding
        "claude-3-5-sonnet-20241022": "cl100k_base",  # Claude uses similar encoding
        "claude-3-opus": "cl100k_base",
        "claude-3-sonnet": "cl100k_base",
    }
    
    def __init__(self):
        self._encodings = {}
    
    def _get_encoding(self, model: str) -> tiktoken.Encoding:
        """Get or create encoding for model"""
        encoding_name = self.ENCODING_MAP.get(model, "cl100k_base")
        
        if encoding_name not in self._encodings:
            try:
                self._encodings[encoding_name] = tiktoken.get_encoding(encoding_name)
            except Exception:
                # Fallback to cl100k_base
                self._encodings[encoding_name] = tiktoken.get_encoding("cl100k_base")
        
        return self._encodings[encoding_name]
    
    def count_tokens(self, text: str, model: str = "gpt-3.5-turbo") -> int:
        """Count tokens in text for given model"""
        encoding = self._get_encoding(model)
        return len(encoding.encode(text))
    
    def count_messages(self, messages: List[Dict[str, str]], model: str = "gpt-3.5-turbo") -> int:
        """Count total tokens in message list"""
        encoding = self._get_encoding(model)
        total = 0
        
        for msg in messages:
            # Count role
            total += len(encoding.encode(msg.get("role", "")))
            # Count content
            total += len(encoding.encode(msg.get("content", "")))
            # Add overhead for message structure (approximately 4 tokens per message)
            total += 4
        
        return total
    
    def estimate_context_size(self, messages: List[Dict[str, str]], model: str = "gpt-3.5-turbo") -> Dict[str, int]:
        """Estimate context size breakdown"""
        encoding = self._get_encoding(model)
        
        system_tokens = 0
        user_tokens = 0
        assistant_tokens = 0
        
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            tokens = len(encoding.encode(content)) + 4  # +4 for message overhead
            
            if role == "system":
                system_tokens += tokens
            elif role == "user":
                user_tokens += tokens
            elif role == "assistant":
                assistant_tokens += tokens
        
        return {
            "total": system_tokens + user_tokens + assistant_tokens,
            "system": system_tokens,
            "user": user_tokens,
            "assistant": assistant_tokens
        }






