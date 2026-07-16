"""
AutoWebAgent - Task Models
============================
Task documents track agent execution — from prompt to completion.
Each task links to a browser session for execution context.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from beanie import Document
from pydantic import Field


class TaskStatus:
    """Task lifecycle states."""
    PENDING = "pending"
    RUNNING = "running"
    WAITING_CAPTCHA = "waiting_captcha"
    WAITING_USER_INPUT = "waiting_user_input"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class TaskDocument(Document):
    """
    Task represents a single agent execution run.

    Contains the original prompt, execution plan, step-by-step results,
    and final outcome with any extracted data.
    """

    # ── Identity ─────────────────────────────────────────────
    user_id: str
    session_id: Optional[str] = None  # Browser session used
    website_id: Optional[str] = None  # Pre-configured website

    # ── Task Definition ──────────────────────────────────────
    prompt: str  # Natural language task description
    status: str = TaskStatus.PENDING
    priority: int = 0  # Higher = more urgent

    # ── Agent Plan ───────────────────────────────────────────
    plan: List[Dict[str, Any]] = Field(default_factory=list)  # LLM-generated action plan
    current_step: int = 0
    total_steps: int = 0

    # ── Execution Results ────────────────────────────────────
    steps_executed: List[Dict[str, Any]] = Field(default_factory=list)
    extracted_data: Optional[Dict[str, Any]] = None
    screenshots: List[str] = Field(default_factory=list)  # Base64 screenshots
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    # ── CAPTCHA Tracking ─────────────────────────────────────
    captcha_detected: bool = False
    captcha_type: Optional[str] = None  # recaptcha_v2, hcaptcha, turnstile, etc.
    captcha_solved: bool = False
    captcha_solve_time_ms: Optional[int] = None

    # ── Human in the Loop (OTP / User Input) ─────────────────
    user_input_required: bool = False
    user_input_prompt: Optional[str] = None
    user_input_value: Optional[str] = None

    # ── Timing ───────────────────────────────────────────────
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    timeout_seconds: int = 300  # Default 5 minutes

    # ── Metadata ─────────────────────────────────────────────
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "tasks"
        indexes = [
            "user_id",
            "status",
            "session_id",
            "created_at",
        ]

    def dict_for_response(self, exclude_screenshots: bool = False) -> dict:
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "session_id": self.session_id,
            "website_id": self.website_id,
            "prompt": self.prompt,
            "status": self.status,
            "priority": self.priority,
            "plan": self.plan,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "steps_executed": self.steps_executed,
            "extracted_data": self.extracted_data,
            "screenshots_count": len(self.screenshots),
            "screenshots": [] if exclude_screenshots else self.screenshots,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "captcha_detected": self.captcha_detected,
            "captcha_solved": self.captcha_solved,
            "captcha_solve_time_ms": self.captcha_solve_time_ms,
            "user_input_required": self.user_input_required,
            "user_input_prompt": self.user_input_prompt,
            "user_input_value": self.user_input_value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
