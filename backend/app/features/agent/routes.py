"""
AutoWebAgent - Agent Routes
=============================
Direct agent control endpoints — manual execution, status, debugging.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from app.features.auth.dependencies import get_current_user
from app.features.auth.models import UserDocument
from app.features.agent.service import AgentService
from app.features.sessions.service import SessionService

router = APIRouter(prefix="/agent", tags=["Agent"])


class AgentExecuteRequest(BaseModel):
    """Direct agent execution request."""

    prompt: str = Field(..., min_length=10, max_length=5000)
    session_id: Optional[str] = None
    url: Optional[str] = None


class AgentStatusResponse(BaseModel):
    """Current agent status."""

    active_sessions: int
    active_tasks: int
    stealth_mode: str
    headless: bool


@router.post("/execute")
async def execute_agent(
    data: AgentExecuteRequest,
    current_user: UserDocument = Depends(get_current_user),
):
    """
    Execute a task directly via the agent.

    Creates a task and runs it synchronously (or returns task ID for async).
    """
    from app.features.tasks.schemas import TaskCreateRequest
    from app.features.tasks.service import TaskService

    task_data = TaskCreateRequest(
        prompt=data.prompt,
        session_id=data.session_id,
    )

    task = await TaskService.create_task(str(current_user.id), task_data)

    return {
        "message": "Task created and queued",
        "task_id": str(task.id),
        "status": task.status,
    }


@router.get("/status")
async def agent_status(
    current_user: UserDocument = Depends(get_current_user),
):
    """Get current agent and session status."""
    from app.features.tasks.models import TaskDocument, TaskStatus
    from app.features.sessions.models import SessionDocument
    from app.core.config import settings

    active_tasks = await TaskDocument.find(
        TaskDocument.user_id == str(current_user.id),
        {"$or": [
            {TaskDocument.status: TaskStatus.RUNNING},
            {TaskDocument.status: TaskStatus.PENDING},
            {TaskDocument.status: TaskStatus.RETRYING},
            {TaskDocument.status: TaskStatus.WAITING_CAPTCHA},
        ]},
    ).count()

    active_sessions = await SessionDocument.find(
        SessionDocument.user_id == str(current_user.id),
        SessionDocument.status == "active",
    ).count()

    return AgentStatusResponse(
        active_sessions=active_sessions,
        active_tasks=active_tasks,
        stealth_mode=settings.STEALTH_MODE,
        headless=settings.BROWSER_HEADLESS,
    )


@router.get("/sessions/{session_id}/snapshot")
async def debug_page_snapshot(
    session_id: str,
    current_user: UserDocument = Depends(get_current_user),
):
    """
    Debug endpoint: Get the current page HTML snapshot from a session.
    Useful for debugging agent behavior.
    """
    try:
        session = await SessionService.get_session(session_id, str(current_user.id))
        context = SessionService.get_context(session_id)
        pages = context.pages

        if not pages:
            return {"error": "No active page in session"}

        page = pages[-1]
        html = await page.content()
        title = await page.title()

        return {
            "url": page.url,
            "title": title,
            "html_length": len(html),
            "html": html[:50000],  # Truncate for API response
        }
    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=e.message)
        raise HTTPException(status_code=404, detail=str(e))
