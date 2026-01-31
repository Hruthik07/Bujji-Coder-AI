"""
LLM Provider Abstraction Layer
Supports multiple LLM providers (OpenAI, Anthropic, DeepSeek) with unified interface
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Standardized LLM response"""
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    finish_reason: str


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> LLMResponse:
        """Generate chat completion"""
        pass
    
    @abstractmethod
    def create_embedding(self, text: str, model: str) -> List[float]:
        """Create embedding for text"""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI implementation"""
    
    def __init__(self, api_key: str):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> LLMResponse:
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return LLMResponse(
            content=response.choices[0].message.content,
            model=model,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            finish_reason=response.choices[0].finish_reason
        )
    
    def create_embedding(self, text: str, model: str = "text-embedding-3-small") -> List[float]:
        response = self.client.embeddings.create(
            model=model,
            input=text
        )
        return response.data[0].embedding


class DeepSeekProvider(LLMProvider):
    """DeepSeek Coder implementation - OpenAI compatible API"""
    
    def __init__(self, api_key: str):
        from openai import OpenAI
        # DeepSeek uses OpenAI-compatible API
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "deepseek-coder",
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> LLMResponse:
        """Generate chat completion using DeepSeek"""
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Validate response
        if not response.choices or len(response.choices) == 0:
            raise RuntimeError("Empty response from DeepSeek API")
        
        message_content = response.choices[0].message.content
        if message_content is None:
            raise RuntimeError("Response content is None from DeepSeek API")
        
        return LLMResponse(
            content=message_content,
            model=model,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            finish_reason=response.choices[0].finish_reason
        )
    
    def create_embedding(self, text: str, model: str = None) -> List[float]:
        # DeepSeek doesn't have embeddings API - use OpenAI
        raise NotImplementedError("DeepSeek doesn't support embeddings. Use OpenAI for embeddings.")


class AnthropicProvider(LLMProvider):
    """Anthropic Claude implementation"""
    
    def __init__(self, api_key: str):
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError("anthropic package required. Install with: pip install anthropic")
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> LLMResponse:
        # Convert OpenAI format to Anthropic format
        system_message = None
        conversation = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                # Anthropic uses "user" and "assistant" roles
                role = msg["role"]
                if role not in ["user", "assistant"]:
                    role = "user"  # Default to user for other roles
                conversation.append({
                    "role": role,
                    "content": msg["content"]
                })
        
        response = self.client.messages.create(
            model=model,
            system=system_message or "",
            messages=conversation,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Validate response
        if not response.content or len(response.content) == 0:
            raise RuntimeError("Empty response from Anthropic API")
        
        message_text = response.content[0].text
        if message_text is None:
            raise RuntimeError("Response content is None from Anthropic API")
        
        return LLMResponse(
            content=message_text,
            model=model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            finish_reason=response.stop_reason
        )
    
    def create_embedding(self, text: str, model: str = None) -> List[float]:
        # Anthropic doesn't have embeddings API yet
        raise NotImplementedError("Anthropic doesn't support embeddings. Use OpenAI for embeddings.")


def get_provider(provider: str, api_key: Optional[str] = None) -> LLMProvider:
    """Factory function to get LLM provider"""
    from config import Config
    
    if provider == "deepseek":
        return DeepSeekProvider(api_key or Config.DEEPSEEK_API_KEY)
    elif provider == "anthropic" or provider == "claude":
        return AnthropicProvider(api_key or Config.ANTHROPIC_API_KEY)
    elif provider == "openai":
        return OpenAIProvider(api_key or Config.OPENAI_API_KEY)
    else:
        raise ValueError(f"Unknown provider: {provider}")






