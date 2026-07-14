"""
AutoWebAgent - Auth Models (Beanie ODM)
=========================================
User document with roles, encrypted API keys, and session tracking.
"""

from datetime import datetime, timezone
from typing import Optional, List
from enum import Enum

from beanie import Document, Indexed
from pydantic import Field, EmailStr


class UserRole(str, Enum):
    """User role hierarchy: normal → premium → superadmin."""

    NORMAL = "normal"
    PREMIUM = "premium"
    SUPERADMIN = "superadmin"


class UserDocument(Document):
    """
    User document stored in MongoDB.

    Contains authentication data, role, and encrypted third-party API keys.
    Each user can bring their own DeepSeek, Anti-Captcha, and Proxy keys.
    Superadmin can override with global keys.
    """

    # ── Identity ─────────────────────────────────────────────
    email: Indexed(str, unique=True)  # type: ignore
    username: str
    hashed_password: str
    full_name: Optional[str] = None

    # ── Role & Status ────────────────────────────────────────
    role: UserRole = UserRole.NORMAL
    is_active: bool = True
    is_verified: bool = False
    email_verified_at: Optional[datetime] = None

    # ── User's Own API Keys (Encrypted) ──────────────────────
    deepseek_api_key_encrypted: Optional[str] = None
    anticaptcha_api_key_encrypted: Optional[str] = None
    capsolver_api_key_encrypted: Optional[str] = None
    webshare_proxy_username_encrypted: Optional[str] = None
    webshare_proxy_password_encrypted: Optional[str] = None
    proxy_host: Optional[str] = None
    proxy_port: Optional[int] = None

    # ── Session & Stats ──────────────────────────────────────
    active_sessions: int = 0
    total_tasks_executed: int = 0
    last_login_at: Optional[datetime] = None

    # ── Refresh Token Tracking ───────────────────────────────
    refresh_tokens: List[str] = Field(default_factory=list)

    # ── Metadata ─────────────────────────────────────────────
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "users"
        use_state_management = True
        indexes = [
            "email",
            "username",
            "role",
        ]

    def is_superadmin(self) -> bool:
        return self.role == UserRole.SUPERADMIN

    def is_premium_or_above(self) -> bool:
        return self.role in (UserRole.PREMIUM, UserRole.SUPERADMIN)

    def has_api_keys_configured(self) -> bool:
        """Check if user has configured their own API keys."""
        return bool(self.deepseek_api_key_encrypted)

    def dict_for_response(self) -> dict:
        """Return a safe dict for API response (no passwords, no encrypted keys)."""
        return {
            "id": str(self.id),
            "email": self.email,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role.value,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "active_sessions": self.active_sessions,
            "total_tasks_executed": self.total_tasks_executed,
            "has_deepseek_key": bool(self.deepseek_api_key_encrypted),
            "has_anticaptcha_key": bool(self.anticaptcha_api_key_encrypted),
            "has_capsolver_key": bool(self.capsolver_api_key_encrypted),
            "has_proxy_credentials": bool(
                self.webshare_proxy_username_encrypted
                and self.webshare_proxy_password_encrypted
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }
