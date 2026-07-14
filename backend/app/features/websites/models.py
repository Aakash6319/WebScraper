"""
AutoWebAgent - Website Models
===============================
Stored website configurations with login credentials and custom settings.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from beanie import Document, Indexed
from pydantic import Field


class WebsiteDocument(Document):
    """
    Website configuration stored per user.

    Allows storing login credentials, custom selectors, and site-specific
    settings that the agent can reference during automation.
    """

    # ── Identity ─────────────────────────────────────────────
    user_id: str  # Owner user ID
    name: str  # Human-readable name
    url: str  # The website URL
    description: Optional[str] = None

    # ── Authentication ───────────────────────────────────────
    login_url: Optional[str] = None
    login_username: Optional[str] = None
    login_password_encrypted: Optional[str] = None  # Encrypted at rest
    login_selector_username: Optional[str] = None  # CSS selector for username field
    login_selector_password: Optional[str] = None  # CSS selector for password field
    login_selector_submit: Optional[str] = None  # CSS selector for submit button

    # ── Custom Settings ──────────────────────────────────────
    custom_selectors: Dict[str, str] = Field(default_factory=dict)
    custom_headers: Dict[str, str] = Field(default_factory=dict)
    blacklist_urls: List[str] = Field(default_factory=list)  # URLs to avoid
    allowed_domains: List[str] = Field(default_factory=list)
    max_depth: int = 5

    # ── Stealth Override ─────────────────────────────────────
    stealth_mode_override: Optional[str] = None  # "basic" | "advanced" | "ultra"
    use_proxy: bool = True
    proxy_country: Optional[str] = None  # e.g., "US", "GB"

    # ── Metadata ─────────────────────────────────────────────
    tags: List[str] = Field(default_factory=list)
    is_favorite: bool = False
    last_used_at: Optional[datetime] = None
    use_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "websites"
        indexes = [
            "user_id",
            "url",
            "name",
        ]

    def dict_for_response(self) -> dict:
        """Safe dict for API response (exclude encrypted password)."""
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "login_url": self.login_url,
            "has_login_credentials": bool(
                self.login_username and self.login_password_encrypted
            ),
            "custom_selectors": self.custom_selectors,
            "blacklist_urls": self.blacklist_urls,
            "allowed_domains": self.allowed_domains,
            "stealth_mode_override": self.stealth_mode_override,
            "use_proxy": self.use_proxy,
            "proxy_country": self.proxy_country,
            "tags": self.tags,
            "is_favorite": self.is_favorite,
            "use_count": self.use_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
