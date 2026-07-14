"""
AutoWebAgent - Session Models
===============================
Isolated browser session storage — each session is tied to one user.
Stores cookies, localStorage, and proxy fingerprint for persistence.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from beanie import Document
from pydantic import Field


class SessionDocument(Document):
    """
    A browser session represents one isolated Playwright browser context.

    Key design goals:
    - Complete user isolation — sessions are never shared across users
    - Persistent state across restarts via cookies + localStorage
    - Fingerprint consistency — same canvas/WebGL fingerprint within a session
    - Proxy binding — each session bound to one proxy IP for consistency
    """

    # ── Ownership ─────────────────────────────────────────────
    user_id: str
    name: Optional[str] = None

    # ── Session State ─────────────────────────────────────────
    status: str = "active"  # active | idle | closed | error
    browser_context_id: Optional[str] = None  # Playwright context ID

    # ── Persisted Browser State ───────────────────────────────
    cookies: List[Dict[str, Any]] = Field(default_factory=list)
    local_storage: Dict[str, str] = Field(default_factory=dict)
    session_storage: Dict[str, str] = Field(default_factory=dict)

    # ── Current Page State ────────────────────────────────────
    current_url: Optional[str] = None
    page_title: Optional[str] = None

    # ── Proxy & Fingerprint ───────────────────────────────────
    proxy_ip: Optional[str] = None
    proxy_country: Optional[str] = None
    user_agent: Optional[str] = None
    fingerprint_id: Optional[str] = None  # Consistent fingerprint ID
    viewport_width: int = 1920
    viewport_height: int = 1080
    locale: str = "en-US"
    timezone_id: str = "America/New_York"

    # ── Stealth & Anti-Detection ──────────────────────────────
    stealth_mode: str = "ultra"  # basic | advanced | ultra
    canvas_noise_seed: Optional[str] = None
    webgl_vendor: Optional[str] = None
    webgl_renderer: Optional[str] = None
    hardware_concurrency: int = 8
    device_memory: int = 8

    # ── Stats ─────────────────────────────────────────────────
    pages_visited: int = 0
    captchas_solved: int = 0
    tasks_completed: int = 0
    total_duration_ms: int = 0

    # ── Metadata ──────────────────────────────────────────────
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_active_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None

    class Settings:
        name = "browser_sessions"
        indexes = [
            "user_id",
            "status",
            "created_at",
        ]

    def dict_for_response(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "name": self.name,
            "status": self.status,
            "current_url": self.current_url,
            "page_title": self.page_title,
            "proxy_country": self.proxy_country,
            "user_agent": self.user_agent,
            "viewport_width": self.viewport_width,
            "viewport_height": self.viewport_height,
            "stealth_mode": self.stealth_mode,
            "pages_visited": self.pages_visited,
            "captchas_solved": self.captchas_solved,
            "tasks_completed": self.tasks_completed,
            "total_duration_ms": self.total_duration_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
        }
