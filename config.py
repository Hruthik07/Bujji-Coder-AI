"""
Configuration settings for the AI Coding Assistant
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration class for the assistant"""

    # API Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv(
        "OPENAI_MODEL", "gpt-3.5-turbo"
    )  # Changed to lower cost model
    OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))

    # DeepSeek Configuration
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-coder")

    # Anthropic Configuration
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

    # Hybrid Model Settings
    USE_HYBRID_MODELS = os.getenv("USE_HYBRID_MODELS", "true").lower() == "true"
    DEFAULT_PROVIDER = os.getenv(
        "DEFAULT_PROVIDER", "deepseek"
    )  # deepseek or anthropic

    # Assistant Settings
    ASSISTANT_NAME = "Auto"
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2000"))  # Reduced to save costs

    # Code Analysis Settings
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "100000"))  # bytes
    SUPPORTED_LANGUAGES = [
        "python",
        "javascript",
        "typescript",
        "java",
        "go",
        "rust",
        "cpp",
        "c",
        "ruby",
        "php",
        "swift",
        "kotlin",
    ]

    # Terminal Settings
    DEFAULT_SHELL = os.getenv("SHELL", "powershell" if os.name == "nt" else "bash")

    # Search Settings
    MAX_SEARCH_RESULTS = 50
    SEARCH_CONTEXT_LINES = 5

    # RAG Settings
    EMBEDDING_MODEL = os.getenv(
        "EMBEDDING_MODEL", "text-embedding-3-small"
    )  # Cost-effective embedding model
    VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", ".vector_db")
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))  # Characters per chunk
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
    TOP_K_RETRIEVAL = int(
        os.getenv("TOP_K_RETRIEVAL", "10")
    )  # Number of chunks to retrieve
    ENABLE_RAG = os.getenv("ENABLE_RAG", "true").lower() == "true"

    # Performance Settings
    ENABLE_CACHE = os.getenv("ENABLE_CACHE", "true").lower() == "true"
    CACHE_TTL = int(os.getenv("CACHE_TTL", "604800"))  # 7 days default
    ENABLE_LOGGING = os.getenv("ENABLE_LOGGING", "true").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

    # Context Management Settings
    MAX_CONTEXT_TOKENS = int(
        os.getenv("MAX_CONTEXT_TOKENS", "10000")
    )  # For DeepSeek (16K limit)
    MAX_CONTEXT_TOKENS_CLAUDE = int(
        os.getenv("MAX_CONTEXT_TOKENS_CLAUDE", "150000")
    )  # For Claude (200K limit)
    CONTEXT_SUMMARIZATION_THRESHOLD = float(
        os.getenv("CONTEXT_SUMMARIZATION_THRESHOLD", "0.75")
    )  # Summarize at 75%
    PRESERVE_RECENT_MESSAGES = int(
        os.getenv("PRESERVE_RECENT_MESSAGES", "8")
    )  # Keep last N messages
    ENABLE_MEMORY_DB = os.getenv("ENABLE_MEMORY_DB", "true").lower() == "true"

    # Embedding Provider Settings
    # Options: "openai" (requires OPENAI_API_KEY) | "sentence_transformers" (free, local)
    EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai")
    SENTENCE_TRANSFORMERS_MODEL = os.getenv(
        "SENTENCE_TRANSFORMERS_MODEL", "all-MiniLM-L6-v2"
    )

    # Redis Configuration (optional — rate limiter falls back to in-memory if not set)
    REDIS_URL = os.getenv("REDIS_URL", "")  # e.g. "redis://localhost:6379/0"

    # Cost Tracker Persistence
    COST_DB_PATH = os.getenv("COST_DB_PATH", ".cost_history.db")

    @classmethod
    def validate_on_startup(cls) -> list:
        """Return a list of warning strings for missing or misconfigured keys."""
        warnings = []
        if not cls.OPENAI_API_KEY and cls.EMBEDDING_PROVIDER == "openai":
            warnings.append(
                "OPENAI_API_KEY is not set but EMBEDDING_PROVIDER=openai. "
                "RAG indexing and retrieval will fail. "
                "Set EMBEDDING_PROVIDER=sentence_transformers for a free local alternative."
            )
        # In production, BYOK means missing server-side LLM keys is the *expected*
        # state — visitors bring their own. Only warn outside of production.
        is_prod = os.getenv("ENVIRONMENT", "development").lower() == "production"
        if not is_prod and not any(
            [cls.OPENAI_API_KEY, cls.ANTHROPIC_API_KEY, cls.DEEPSEEK_API_KEY]
        ):
            warnings.append(
                "No LLM API keys configured. "
                "Set at least one of: OPENAI_API_KEY, ANTHROPIC_API_KEY, DEEPSEEK_API_KEY."
            )
        return warnings

    # Placeholder JWT secrets that have appeared in this repo's history; refusing
    # to serve production traffic with any of them prevents shipping the default.
    _JWT_PLACEHOLDER_SECRETS = frozenset(
        {
            "",
            "your-secret-key-change-in-production",
            "your-super-secret-jwt-key-change-this-in-production",
            "change-me-in-production",
            "test-secret-key-for-ci",
        }
    )

    @classmethod
    def validate_for_production(cls) -> list:
        """Return a list of FATAL config errors. Empty list outside production.

        Called once at server startup; if non-empty in prod, refuse to serve."""
        if os.getenv("ENVIRONMENT", "development").lower() != "production":
            return []
        errors = []

        if not os.getenv("CORS_ORIGINS", "").strip():
            errors.append(
                "CORS_ORIGINS must be set in production (e.g. "
                "https://your-frontend.vercel.app,https://your-domain.com). "
                "Refusing to fall back to allow-all."
            )

        jwt_secret = os.getenv("JWT_SECRET_KEY", "")
        if jwt_secret in cls._JWT_PLACEHOLDER_SECRETS:
            errors.append(
                "JWT_SECRET_KEY is missing or set to a known placeholder. "
                "Generate one with: "
                "python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )

        return errors
