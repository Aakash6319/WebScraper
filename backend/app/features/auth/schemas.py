"""
AutoWebAgent - Auth Schemas (Pydantic)
========================================
Request/Response validation schemas for Auth endpoints.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator
import re


# ── Request Schemas ────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """User registration payload."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=100)

    @validator("password")
    def password_strength(cls, v: str) -> str:
        """Ensure password has at least one uppercase, lowercase, digit."""
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    """Login payload."""

    email: EmailStr
    password: str


class TokenRefreshRequest(BaseModel):
    """Refresh token payload."""

    refresh_token: str


class UpdateAPIKeysRequest(BaseModel):
    """Update user's personal API keys."""

    deepseek_api_key: Optional[str] = Field(None, min_length=1)
    anticaptcha_api_key: Optional[str] = Field(None, min_length=1)
    capsolver_api_key: Optional[str] = Field(None, min_length=1)
    webshare_proxy_username: Optional[str] = Field(None, min_length=1)
    webshare_proxy_password: Optional[str] = Field(None, min_length=1)
    proxy_host: Optional[str] = Field(None, min_length=1)
    proxy_port: Optional[int] = Field(None, ge=1, le=65535)


class ChangePasswordRequest(BaseModel):
    """Change password payload."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @validator("new_password")
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class UpdateProfileRequest(BaseModel):
    """Update user profile."""

    full_name: Optional[str] = Field(None, max_length=100)
    username: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")


# ── Response Schemas ───────────────────────────────────────────

class TokenResponse(BaseModel):
    """JWT token pair response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserResponse(BaseModel):
    """Public user profile response."""

    id: str
    email: str
    username: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    is_verified: bool
    active_sessions: int
    total_tasks_executed: int
    has_deepseek_key: bool
    has_anticaptcha_key: bool
    has_capsolver_key: bool
    has_proxy_credentials: bool
    created_at: Optional[str] = None
    last_login_at: Optional[str] = None


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
    detail: Optional[str] = None


class APIKeysStatusResponse(BaseModel):
    """Status of user's API keys."""

    has_deepseek_key: bool
    has_anticaptcha_key: bool
    has_capsolver_key: bool
    has_proxy_credentials: bool
    deepseek_key_masked: Optional[str] = None
    anticaptcha_key_masked: Optional[str] = None
    capsolver_key_masked: Optional[str] = None
    webshare_proxy_username: Optional[str] = None
    proxy_host: Optional[str] = None
    proxy_port: Optional[int] = None


class UserListResponse(BaseModel):
    """Paginated user list (admin)."""

    users: list[UserResponse]
    total: int
    page: int
    page_size: int
