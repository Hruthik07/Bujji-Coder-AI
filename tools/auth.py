"""
Authentication and Authorization Module
Handles JWT-based authentication, user management, and role-based access control
"""
import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path
import json
import sqlite3
from functools import wraps
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
JWT_REFRESH_EXPIRATION_DAYS = int(os.getenv("JWT_REFRESH_EXPIRATION_DAYS", "7"))

# Export for use in other modules
__all__ = [
    "User", "UserCreate", "UserLogin", "TokenResponse",
    "AuthManager", "get_auth_manager", "get_current_user", "require_role",
    "JWT_EXPIRATION_HOURS", "JWT_REFRESH_EXPIRATION_DAYS"
]

# Security
security = HTTPBearer()


class User(BaseModel):
    """User model"""
    id: str
    username: str
    email: str
    hashed_password: str
    role: str = "user"  # admin, user, guest
    created_at: str
    api_keys: Optional[Dict[str, str]] = None  # Provider -> API key mapping


class UserCreate(BaseModel):
    """User creation model"""
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    """User login model"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthManager:
    """Manages authentication and authorization"""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = Path(".auth.db")
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database for user storage"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                api_keys TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        """)
        
        # Create refresh tokens table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        conn.commit()
        conn.close()
        
        # Create default admin user if no users exist
        if self._get_user_count() == 0:
            self._create_default_admin()
    
    def _get_user_count(self) -> int:
        """Get total user count"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def _create_default_admin(self):
        """Create default admin user"""
        default_password = os.getenv("ADMIN_PASSWORD", "admin123")
        self.create_user(
            username="admin",
            email="admin@bujji-coder.ai",
            password=default_password,
            role="admin"
        )
        print("[WARN] Default admin user created. Please change the password!")
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against a hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def create_user(self, username: str, email: str, password: str, role: str = "user") -> User:
        """Create a new user"""
        import uuid
        from datetime import datetime
        
        # Check if user already exists
        if self.get_user_by_username(username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        
        if self.get_user_by_email(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        
        user_id = str(uuid.uuid4())
        hashed_password = self.hash_password(password)
        created_at = datetime.utcnow().isoformat()
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (id, username, email, hashed_password, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, username, email, hashed_password, role, created_at))
        conn.commit()
        conn.close()
        
        return User(
            id=user_id,
            username=username,
            email=email,
            hashed_password=hashed_password,
            role=role,
            created_at=created_at
        )
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(
                id=row["id"],
                username=row["username"],
                email=row["email"],
                hashed_password=row["hashed_password"],
                role=row["role"],
                created_at=row["created_at"],
                api_keys=json.loads(row["api_keys"]) if row["api_keys"] else None
            )
        return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(
                id=row["id"],
                username=row["username"],
                email=row["email"],
                hashed_password=row["hashed_password"],
                role=row["role"],
                created_at=row["created_at"],
                api_keys=json.loads(row["api_keys"]) if row["api_keys"] else None
            )
        return None
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(
                id=row["id"],
                username=row["username"],
                email=row["email"],
                hashed_password=row["hashed_password"],
                role=row["role"],
                created_at=row["created_at"],
                api_keys=json.loads(row["api_keys"]) if row["api_keys"] else None
            )
        return None
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user"""
        user = self.get_user_by_username(username)
        if not user:
            return None
        
        if not self.verify_password(password, user.hashed_password):
            return None
        
        return user
    
    def create_access_token(self, user: User) -> str:
        """Create JWT access token"""
        payload = {
            "sub": user.id,
            "username": user.username,
            "role": user.role,
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
            "iat": datetime.utcnow(),
            "type": "access"
        }
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    def create_refresh_token(self, user: User) -> str:
        """Create JWT refresh token"""
        payload = {
            "sub": user.id,
            "exp": datetime.utcnow() + timedelta(days=JWT_REFRESH_EXPIRATION_DAYS),
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        # Store refresh token in database
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        expires_at = (datetime.utcnow() + timedelta(days=JWT_REFRESH_EXPIRATION_DAYS)).isoformat()
        cursor.execute("""
            INSERT OR REPLACE INTO refresh_tokens (token, user_id, expires_at)
            VALUES (?, ?, ?)
        """, (token, user.id, expires_at))
        conn.commit()
        conn.close()
        
        return token
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def refresh_access_token(self, refresh_token: str) -> str:
        """Refresh access token using refresh token"""
        # Verify refresh token
        payload = self.verify_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        # Check if refresh token exists in database
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM refresh_tokens WHERE token = ?", (refresh_token,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found"
            )
        
        # Check if token is expired
        expires_at = datetime.fromisoformat(row[2])
        if datetime.utcnow() > expires_at:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired"
            )
        
        # Get user and create new access token
        user = self.get_user_by_id(payload["sub"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return self.create_access_token(user)
    
    def update_user_api_keys(self, user_id: str, api_keys: Dict[str, str]):
        """Update user's API keys"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users
            SET api_keys = ?, updated_at = ?
            WHERE id = ?
        """, (json.dumps(api_keys), datetime.utcnow().isoformat(), user_id))
        conn.commit()
        conn.close()


# Global auth manager instance
_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    """Get or create auth manager instance"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get current authenticated user from JWT token"""
    auth_manager = get_auth_manager()
    token = credentials.credentials
    payload = auth_manager.verify_token(token)
    
    user = auth_manager.get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


def require_role(required_roles: List[str]):
    """Decorator to require specific roles"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get("current_user")
            if not user:
                # Try to get from dependencies
                for arg in args:
                    if isinstance(arg, User):
                        user = arg
                        break
            
            if not user or user.role not in required_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator
