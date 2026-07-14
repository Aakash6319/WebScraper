"""
AutoWebAgent - Task Schemas
=============================
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TaskCreateRequest(BaseModel):
    """Create a new automation task."""

    prompt: str = Field(..., min_length=10, max_length=5000)
    session_id: Optional[str] = None  # Use existing session
    website_id: Optional[str] = None  # Use pre-configured website
    max_retries: int = Field(default=3, ge=0, le=10)
    timeout_seconds: int = Field(default=300, ge=10, le=3600)
    priority: int = Field(default=0, ge=0, le=10)


class TaskResponse(BaseModel):
    """Task details response."""

    id: str
    user_id: str
    session_id: Optional[str] = None
    website_id: Optional[str] = None
    prompt: str
    status: str
    priority: int = 0
    plan: List[Dict[str, Any]] = []
    current_step: int = 0
    total_steps: int = 0
    steps_executed: List[Dict[str, Any]] = []
    extracted_data: Optional[Dict[str, Any]] = None
    screenshots_count: int = 0
    screenshots: List[str] = []
    error_message: Optional[str] = None
    retry_count: int = 0
    captcha_detected: bool = False
    captcha_solved: bool = False
    captcha_solve_time_ms: Optional[int] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: Optional[str] = None


class TaskListResponse(BaseModel):
    """Paginated task list."""

    tasks: List[TaskResponse]
    total: int
    page: int
    page_size: int


class TaskCancelRequest(BaseModel):
    """Cancel a running task."""

    reason: Optional[str] = None
