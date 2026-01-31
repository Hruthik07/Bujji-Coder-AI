"""
Security Utilities
Input validation, sanitization, and security helpers
"""
import os
import re
from pathlib import Path
from typing import Optional, List
from urllib.parse import quote, unquote


def sanitize_file_path(file_path: str, workspace_root: str = ".") -> str:
    """
    Sanitize file path to prevent directory traversal attacks
    Returns: Sanitized absolute path within workspace
    Raises: ValueError if path is outside workspace
    """
    workspace_root = Path(workspace_root).resolve()
    file_path = Path(file_path).resolve()
    
    # Check if path is within workspace
    try:
        file_path.relative_to(workspace_root)
    except ValueError:
        raise ValueError(f"Path {file_path} is outside workspace {workspace_root}")
    
    return str(file_path)


def validate_file_extension(file_path: str, allowed_extensions: Optional[List[str]] = None) -> bool:
    """Validate file extension against allowed list"""
    if allowed_extensions is None:
        # Default allowed extensions
        allowed_extensions = [
            ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
            ".cpp", ".c", ".h", ".hpp", ".rb", ".php", ".swift", ".kt",
            ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
            ".md", ".txt", ".csv", ".xml", ".html", ".css", ".scss",
            ".sh", ".bash", ".ps1", ".bat", ".dockerfile", ".gitignore"
        ]
    
    file_ext = Path(file_path).suffix.lower()
    return file_ext in allowed_extensions


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """
    Sanitize user input to prevent injection attacks
    - Remove null bytes
    - Limit length
    - Remove control characters (except newlines and tabs)
    """
    if not isinstance(text, str):
        raise ValueError("Input must be a string")
    
    # Remove null bytes
    text = text.replace("\x00", "")
    
    # Limit length
    if len(text) > max_length:
        text = text[:max_length]
    
    # Remove control characters (keep newlines, tabs, carriage returns)
    text = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F]", "", text)
    
    return text


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_username(username: str) -> bool:
    """Validate username format (alphanumeric, underscore, hyphen, 3-30 chars)"""
    pattern = r"^[a-zA-Z0-9_-]{3,30}$"
    return bool(re.match(pattern, username))


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength
    Returns: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if len(password) > 128:
        return False, "Password must be less than 128 characters"
    
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"
    
    return True, ""


def escape_html(text: str) -> str:
    """Escape HTML special characters"""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def generate_secure_token(length: int = 32) -> str:
    """Generate a secure random token"""
    import secrets
    return secrets.token_urlsafe(length)


def validate_api_key_format(api_key: str, provider: str) -> bool:
    """Validate API key format for different providers"""
    if provider.lower() == "openai":
        # OpenAI keys start with "sk-"
        return api_key.startswith("sk-") and len(api_key) > 20
    elif provider.lower() == "anthropic":
        # Anthropic keys start with "sk-ant-"
        return api_key.startswith("sk-ant-") and len(api_key) > 20
    elif provider.lower() == "deepseek":
        # DeepSeek keys are typically long alphanumeric strings
        return len(api_key) > 20
    return False


def mask_secret(secret: str, visible_chars: int = 4) -> str:
    """Mask a secret value, showing only last N characters"""
    if len(secret) <= visible_chars:
        return "*" * len(secret)
    return "*" * (len(secret) - visible_chars) + secret[-visible_chars:]


def is_safe_filename(filename: str) -> bool:
    """Check if filename is safe (no path traversal, no dangerous characters)"""
    # Check for path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        return False
    
    # Check for dangerous characters
    dangerous_chars = ["<", ">", ":", '"', "|", "?", "*"]
    if any(char in filename for char in dangerous_chars):
        return False
    
    # Check for reserved names (Windows)
    reserved_names = [
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    ]
    if filename.upper() in reserved_names:
        return False
    
    return True


def get_cors_origins() -> List[str]:
    """Get CORS allowed origins from environment"""
    origins_env = os.getenv("CORS_ORIGINS", "")
    if origins_env:
        # Split by comma and strip whitespace
        origins = [origin.strip() for origin in origins_env.split(",") if origin.strip()]
        return origins
    
    # Default: allow localhost for development
    if os.getenv("ENVIRONMENT", "development") == "development":
        return ["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001"]
    
    # Production: no default origins (must be set explicitly)
    return []
