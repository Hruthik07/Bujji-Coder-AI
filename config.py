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
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")  # Changed to lower cost model
    OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    
    # DeepSeek Configuration
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-coder")
    
    # Anthropic Configuration
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    
    # Hybrid Model Settings
    USE_HYBRID_MODELS = os.getenv("USE_HYBRID_MODELS", "true").lower() == "true"
    DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "deepseek")  # deepseek or anthropic
    
    # Assistant Settings
    ASSISTANT_NAME = "Auto"
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2000"))  # Reduced to save costs
    
    # Code Analysis Settings
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "100000"))  # bytes
    SUPPORTED_LANGUAGES = [
        "python", "javascript", "typescript", "java", "go", 
        "rust", "cpp", "c", "ruby", "php", "swift", "kotlin"
    ]
    
    # Terminal Settings
    DEFAULT_SHELL = os.getenv("SHELL", "powershell" if os.name == "nt" else "bash")
    
    # Search Settings
    MAX_SEARCH_RESULTS = 50
    SEARCH_CONTEXT_LINES = 5
    
    # RAG Settings
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")  # Cost-effective embedding model
    VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", ".vector_db")
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))  # Characters per chunk
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
    TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", "10"))  # Number of chunks to retrieve
    ENABLE_RAG = os.getenv("ENABLE_RAG", "true").lower() == "true"
    
    # Performance Settings
    ENABLE_CACHE = os.getenv("ENABLE_CACHE", "true").lower() == "true"
    CACHE_TTL = int(os.getenv("CACHE_TTL", "604800"))  # 7 days default
    ENABLE_LOGGING = os.getenv("ENABLE_LOGGING", "true").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Context Management Settings
    MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", "10000"))  # For DeepSeek (16K limit)
    MAX_CONTEXT_TOKENS_CLAUDE = int(os.getenv("MAX_CONTEXT_TOKENS_CLAUDE", "150000"))  # For Claude (200K limit)
    CONTEXT_SUMMARIZATION_THRESHOLD = float(os.getenv("CONTEXT_SUMMARIZATION_THRESHOLD", "0.75"))  # Summarize at 75%
    PRESERVE_RECENT_MESSAGES = int(os.getenv("PRESERVE_RECENT_MESSAGES", "8"))  # Keep last N messages
    ENABLE_MEMORY_DB = os.getenv("ENABLE_MEMORY_DB", "true").lower() == "true"