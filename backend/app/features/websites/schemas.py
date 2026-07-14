"""
AutoWebAgent - Website Schemas
================================
"""

from typing import Optional, List, Dict
from pydantic import BaseModel, Field, HttpUrl


class WebsiteCreateRequest(BaseModel):
    """Create a new website configuration."""

    name: str = Field(..., min_length=1, max_length=200)
    url: str = Field(..., min_length=1)
    description: Optional[str] = Field(None, max_length=1000)
    login_url: Optional[str] = None
    login_username: Optional[str] = None
    login_password: Optional[str] = None
    login_selector_username: Optional[str] = None
    login_selector_password: Optional[str] = None
    login_selector_submit: Optional[str] = None
    custom_selectors: Dict[str, str] = Field(default_factory=dict)
    custom_headers: Dict[str, str] = Field(default_factory=dict)
    blacklist_urls: List[str] = Field(default_factory=list)
    allowed_domains: List[str] = Field(default_factory=list)
    max_depth: int = Field(default=5, ge=1, le=50)
    stealth_mode_override: Optional[str] = None
    use_proxy: bool = True
    proxy_country: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class WebsiteUpdateRequest(BaseModel):
    """Partial update for website configuration."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    url: Optional[str] = None
    description: Optional[str] = Field(None, max_length=1000)
    login_url: Optional[str] = None
    login_username: Optional[str] = None
    login_password: Optional[str] = None
    login_selector_username: Optional[str] = None
    login_selector_password: Optional[str] = None
    login_selector_submit: Optional[str] = None
    custom_selectors: Optional[Dict[str, str]] = None
    custom_headers: Optional[Dict[str, str]] = None
    blacklist_urls: Optional[List[str]] = None
    allowed_domains: Optional[List[str]] = None
    max_depth: Optional[int] = Field(None, ge=1, le=50)
    stealth_mode_override: Optional[str] = None
    use_proxy: Optional[bool] = None
    proxy_country: Optional[str] = None
    tags: Optional[List[str]] = None
    is_favorite: Optional[bool] = None


class WebsiteResponse(BaseModel):
    """Website configuration response."""

    id: str
    user_id: str
    name: str
    url: str
    description: Optional[str] = None
    login_url: Optional[str] = None
    has_login_credentials: bool = False
    custom_selectors: Dict[str, str] = {}
    blacklist_urls: List[str] = []
    allowed_domains: List[str] = []
    stealth_mode_override: Optional[str] = None
    use_proxy: bool = True
    proxy_country: Optional[str] = None
    tags: List[str] = []
    is_favorite: bool = False
    use_count: int = 0
    last_used_at: Optional[str] = None
    created_at: Optional[str] = None


class WebsiteListResponse(BaseModel):
    """Paginated website list."""

    websites: List[WebsiteResponse]
    total: int
    page: int
    page_size: int
