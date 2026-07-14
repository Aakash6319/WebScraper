"""
AutoWebAgent - Session Schemas
================================
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    """Create a new browser session."""

    name: Optional[str] = None
    stealth_mode: str = Field(default="ultra", pattern="^(basic|advanced|ultra)$")
    viewport_width: int = Field(default=1920, ge=320, le=3840)
    viewport_height: int = Field(default=1080, ge=240, le=2160)
    locale: str = "en-US"
    timezone_id: str = "America/New_York"
    proxy_country: Optional[str] = None  # e.g., "US"
    user_agent: Optional[str] = None
    website_id: Optional[str] = None  # Pre-load website config


class SessionResponse(BaseModel):
    """Session info for API responses."""

    id: str
    user_id: str
    name: Optional[str] = None
    status: str
    current_url: Optional[str] = None
    page_title: Optional[str] = None
    proxy_country: Optional[str] = None
    user_agent: Optional[str] = None
    viewport_width: int = 1920
    viewport_height: int = 1080
    stealth_mode: str = "ultra"
    pages_visited: int = 0
    captchas_solved: int = 0
    tasks_completed: int = 0
    total_duration_ms: int = 0
    created_at: Optional[str] = None
    last_active_at: Optional[str] = None


class SessionListResponse(BaseModel):
    """List of user sessions."""

    sessions: List[SessionResponse]
    total: int
    active_count: int


class SessionNavigateRequest(BaseModel):
    """Navigate to a URL in a session."""

    url: str
    wait_until: str = Field(default="networkidle", pattern="^(load|domcontentloaded|networkidle)$")
    timeout_ms: int = Field(default=30000, ge=1000, le=120000)


class SessionExecuteRequest(BaseModel):
    """Execute JavaScript or take action in a session."""

    action: str  # 'click', 'type', 'scroll', 'wait', 'screenshot', 'execute_js'
    selector: Optional[str] = None
    value: Optional[str] = None
    delay_ms: Optional[int] = None


class SessionStateResponse(BaseModel):
    """Full session state including cookies and localStorage."""

    id: str
    status: str
    current_url: Optional[str] = None
    page_title: Optional[str] = None
    cookies_count: int = 0
    local_storage_keys: List[str] = []
    screenshot_base64: Optional[str] = None
