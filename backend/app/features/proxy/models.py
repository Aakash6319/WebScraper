"""
AutoWebAgent - Proxy Models
=============================
Proxy configuration with rotation tracking.
"""

from datetime import datetime, timezone
from typing import Optional

from beanie import Document
from pydantic import Field


class ProxyConfigDocument(Document):
    """
    Tracks proxy usage and rotation.

    Webshare rotating residential proxies are used by default.
    Each proxy binding is tracked for fingerprint consistency.
    """

    # ── Configuration ─────────────────────────────────────────
    user_id: Optional[str] = None  # None = global/superadmin config
    proxy_host: str = "p.webshare.io"
    proxy_port: int = 80
    proxy_username_encrypted: str = ""
    proxy_password_encrypted: str = ""

    # ── Rotation Tracking ─────────────────────────────────────
    current_ip: Optional[str] = None
    last_rotation_at: Optional[datetime] = None
    rotation_count: int = 0
    sticky_session_enabled: bool = True  # Keep same IP for a session

    # ── Stats ─────────────────────────────────────────────────
    total_requests: int = 0
    failed_requests: int = 0
    last_used_at: Optional[datetime] = None

    # ── Metadata ──────────────────────────────────────────────
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "proxy_configs"
        indexes = ["user_id", "is_active"]
