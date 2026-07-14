"""
AutoWebAgent - Session Routes
===============================
Browser session management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.features.auth.dependencies import get_current_user
from app.features.auth.models import UserDocument
from app.features.sessions.schemas import (
    SessionCreateRequest,
    SessionResponse,
    SessionListResponse,
    SessionNavigateRequest,
    SessionExecuteRequest,
    SessionStateResponse,
)
from app.features.sessions.service import SessionService
from app.features.auth.service import AuthService

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    data: SessionCreateRequest,
    current_user: UserDocument = Depends(get_current_user),
):
    """Create a new isolated browser session."""
    try:
        user_api_keys = AuthService.get_decrypted_api_keys(current_user)
        session = await SessionService.create_session(
            str(current_user.id), data, user_api_keys
        )
        return session.dict_for_response()
    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=e.message)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    current_user: UserDocument = Depends(get_current_user),
):
    """List all browser sessions for current user."""
    sessions, total, active = await SessionService.list_user_sessions(
        str(current_user.id)
    )
    return SessionListResponse(
        sessions=[s.dict_for_response() for s in sessions],
        total=total,
        active_count=active,
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user: UserDocument = Depends(get_current_user),
):
    """Get session details."""
    try:
        session = await SessionService.get_session(session_id, str(current_user.id))
        return session.dict_for_response()
    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=e.message)
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{session_id}/navigate")
async def navigate_session(
    session_id: str,
    data: SessionNavigateRequest,
    current_user: UserDocument = Depends(get_current_user),
):
    """Navigate to a URL in the session."""
    try:
        result = await SessionService.navigate(
            session_id, str(current_user.id), data
        )
        return result
    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=e.message)
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/execute")
async def execute_action(
    session_id: str,
    data: SessionExecuteRequest,
    current_user: UserDocument = Depends(get_current_user),
):
    """Execute an action (click, type, scroll, etc.) in the session."""
    try:
        result = await SessionService.execute_action(
            session_id, str(current_user.id), data
        )
        return result
    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=e.message)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{session_id}/state", response_model=SessionStateResponse)
async def get_session_state(
    session_id: str,
    current_user: UserDocument = Depends(get_current_user),
):
    """Get current session state (cookies, screenshot, etc.)."""
    try:
        state = await SessionService.get_session_state(
            session_id, str(current_user.id)
        )
        return state
    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=e.message)
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{session_id}")
async def close_session(
    session_id: str,
    current_user: UserDocument = Depends(get_current_user),
):
    """Close and clean up a browser session."""
    try:
        await SessionService.close_session(session_id, str(current_user.id))
        return {"message": "Session closed successfully"}
    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=e.message)
        raise HTTPException(status_code=400, detail=str(e))
