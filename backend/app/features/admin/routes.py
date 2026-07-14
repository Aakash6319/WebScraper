"""
AutoWebAgent - Admin Routes
=============================
Superadmin dashboard for user management, global settings,
and session monitoring.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException

from app.features.auth.dependencies import get_current_superadmin
from app.features.auth.models import UserDocument
from app.features.auth.schemas import UserResponse
from app.features.sessions.service import SessionService
from app.core.config import settings

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard")
async def admin_dashboard(
    admin: UserDocument = Depends(get_current_superadmin),
):
    """Superadmin dashboard with system stats."""
    from app.features.auth.models import UserDocument as UD
    from app.features.tasks.models import TaskDocument
    from app.features.sessions.models import SessionDocument

    total_users = await UD.find().count()
    active_users = await UD.find(UD.is_active == True).count()
    total_tasks = await TaskDocument.find().count()
    active_sessions = await SessionDocument.find(
        SessionDocument.status == "active"
    ).count()
    completed_tasks = await TaskDocument.find(
        TaskDocument.status == "completed"
    ).count()
    failed_tasks = await TaskDocument.find(
        TaskDocument.status == "failed"
    ).count()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_tasks": total_tasks,
        "active_sessions": active_sessions,
        "completed_tasks": completed_tasks,
        "failed_tasks": failed_tasks,
        "stealth_mode": settings.STEALTH_MODE,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/sessions")
async def admin_list_all_sessions(
    admin: UserDocument = Depends(get_current_superadmin),
):
    """Superadmin: List all active sessions across all users."""
    from app.features.sessions.models import SessionDocument

    sessions = await SessionDocument.find(
        SessionDocument.status == "active"
    ).sort("-created_at").limit(100).to_list()

    return {
        "sessions": [s.dict_for_response() for s in sessions],
        "total_active": len(sessions),
    }


@router.get("/settings")
async def admin_get_settings(
    admin: UserDocument = Depends(get_current_superadmin),
):
    """Superadmin: View global system settings (keys masked)."""
    from app.utils.helpers import mask_sensitive

    return {
        "stealth_mode": settings.STEALTH_MODE,
        "browser_headless": settings.BROWSER_HEADLESS,
        "max_concurrent_sessions": settings.MAX_CONCURRENT_SESSIONS_PER_USER,
        "rate_limit_per_minute": settings.RATE_LIMIT_PER_MINUTE,
        "deepseek_key_configured": bool(settings.DEEPSEEK_API_KEY),
        "anticaptcha_key_configured": bool(settings.ANTICAPTCHA_API_KEY),
        "proxy_configured": bool(settings.WEBSHARE_PROXY_USERNAME),
        "deepseek_model": settings.DEEPSEEK_MODEL,
        "jwt_expire_minutes": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    }


@router.post("/force-cleanup")
async def admin_force_cleanup(
    admin: UserDocument = Depends(get_current_superadmin),
):
    """Superadmin: Force cleanup of expired sessions."""
    count = await SessionService.cleanup_expired_sessions()
    return {"message": f"Cleaned up {count} expired sessions"}
