"""
BYOK (Bring Your Own Key) request-scoped credentials.

Public deploys of Bujji do not hold LLM API keys server-side. Visitors paste
their own Anthropic / OpenAI / DeepSeek keys into the Settings modal in the
browser; the frontend sends them on every request as headers. This module
exposes a FastAPI dependency that reads those headers into a UserKeys
dataclass plus factory helpers that build per-request LLMProvider instances.

In local dev the server's own .env keys are used as a fallback so the CLI
(main.py) and tests keep working without a header set.

Header contract:
    X-Anthropic-Key: <user's Anthropic key>
    X-OpenAI-Key:    <user's OpenAI key>
    X-DeepSeek-Key:  <user's DeepSeek key>

WebSocket fallback (browsers can't set arbitrary headers on the WS handshake):
    /ws/chat?anthropic_key=...&openai_key=...&deepseek_key=...
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from fastapi import Header, HTTPException, status

from config import Config
from tools.llm_provider import (
    AnthropicProvider,
    DeepSeekProvider,
    LLMProvider,
    OpenAIProvider,
)


PROD_ENV = os.getenv("ENVIRONMENT", "development").lower() == "production"


@dataclass(frozen=True)
class UserKeys:
    """Per-request LLM credentials sourced from request headers (or env in dev)."""

    anthropic: Optional[str] = None
    openai: Optional[str] = None
    deepseek: Optional[str] = None

    def has_any(self) -> bool:
        return bool(self.anthropic or self.openai or self.deepseek)

    def require_any(self) -> None:
        """Raise 400 if no provider key is available for this request."""
        if not self.has_any():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "No API key provided. Open Settings and paste at least one "
                    "of: Anthropic, OpenAI, or DeepSeek."
                ),
            )

    def provider_for(self, name: str) -> LLMProvider:
        """Build a fresh LLMProvider for the named provider using this request's key."""
        name = name.lower()
        if name == "anthropic":
            key = self.anthropic
            if not key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Anthropic key not provided for this request.",
                )
            return AnthropicProvider(api_key=key)
        if name == "openai":
            key = self.openai
            if not key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="OpenAI key not provided for this request.",
                )
            return OpenAIProvider(api_key=key)
        if name == "deepseek":
            key = self.deepseek
            if not key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="DeepSeek key not provided for this request.",
                )
            return DeepSeekProvider(api_key=key)
        raise ValueError(f"Unknown provider: {name}")


def _dev_fallback() -> UserKeys:
    """In non-prod, fall back to server env so CLI/tests keep working."""
    if PROD_ENV:
        return UserKeys()
    return UserKeys(
        anthropic=Config.ANTHROPIC_API_KEY or None,
        openai=Config.OPENAI_API_KEY or None,
        deepseek=Config.DEEPSEEK_API_KEY or None,
    )


def get_user_keys(
    x_anthropic_key: Optional[str] = Header(default=None, alias="X-Anthropic-Key"),
    x_openai_key: Optional[str] = Header(default=None, alias="X-OpenAI-Key"),
    x_deepseek_key: Optional[str] = Header(default=None, alias="X-DeepSeek-Key"),
) -> UserKeys:
    """FastAPI dependency: read BYOK headers, with dev-env fallback."""
    keys = UserKeys(
        anthropic=x_anthropic_key,
        openai=x_openai_key,
        deepseek=x_deepseek_key,
    )
    if keys.has_any():
        return keys
    return _dev_fallback()


def user_keys_from_ws_query(
    anthropic_key: Optional[str] = None,
    openai_key: Optional[str] = None,
    deepseek_key: Optional[str] = None,
) -> UserKeys:
    """WebSocket fallback: browsers cannot set headers on the WS handshake, so
    the client appends keys as query params on /ws/chat. Same dev fallback rules."""
    keys = UserKeys(
        anthropic=anthropic_key,
        openai=openai_key,
        deepseek=deepseek_key,
    )
    if keys.has_any():
        return keys
    return _dev_fallback()
