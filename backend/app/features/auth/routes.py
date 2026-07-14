"""
AutoWebAgent - Auth Routes
============================
FastAPI router for authentication & user management endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from loguru import logger

from app.features.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenRefreshRequest,
    TokenResponse,
    UserResponse,
    MessageResponse,
    UpdateAPIKeysRequest,
    APIKeysStatusResponse,
    ChangePasswordRequest,
    UpdateProfileRequest,
    UserListResponse,
)
from app.features.auth.service import AuthService
from app.features.auth.models import UserDocument, UserRole
from app.features.auth.dependencies import (
    get_current_user,
    get_current_superadmin,
    get_optional_user,
)
from app.utils.helpers import mask_sensitive
from app.core.security import decrypt_credential

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Public Endpoints ──────────────────────────────────────────

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(data: RegisterRequest):
    """
    Register a new account with email, username, and password.

    Password must contain uppercase, lowercase, and digit (min 8 chars).
    """
    try:
        user = await AuthService.register(data)
        return user.dict_for_response()
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=e.message)
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get JWT tokens",
)
async def login(data: LoginRequest):
    """
    Authenticate with email and password.
    Returns access_token (short-lived) and refresh_token (long-lived).
    """
    try:
        return await AuthService.login(data)
    except Exception as e:
        logger.warning(f"Login failed for {data.email}: {e}")
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=e.message)
        raise HTTPException(status_code=401, detail="Authentication failed")


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh_token(data: TokenRefreshRequest):
    """
    Exchange a valid refresh token for a new access + refresh token pair.
    Old refresh token is invalidated (token rotation).
    """
    try:
        return await AuthService.refresh_access_token(data.refresh_token)
    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=e.message)
        raise HTTPException(status_code=401, detail="Invalid refresh token")


# ── Authenticated Endpoints ───────────────────────────────────

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_me(current_user: UserDocument = Depends(get_current_user)):
    """Returns the authenticated user's profile."""
    return current_user.dict_for_response()


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout current user",
)
async def logout(
    refresh_token: Optional[str] = None,
    current_user: UserDocument = Depends(get_current_user),
):
    """Invalidate refresh token(s) and logout."""
    await AuthService.logout(str(current_user.id), refresh_token)
    return MessageResponse(message="Logged out successfully")


@router.put(
    "/me/profile",
    response_model=UserResponse,
    summary="Update profile",
)
async def update_profile(
    data: UpdateProfileRequest,
    current_user: UserDocument = Depends(get_current_user),
):
    """Update username and/or full name."""
    try:
        user = await AuthService.update_profile(str(current_user.id), data)
        return user.dict_for_response()
    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=e.message)
        raise HTTPException(status_code=400, detail=str(e))


@router.put(
    "/me/password",
    response_model=MessageResponse,
    summary="Change password",
)
async def change_password(
    data: ChangePasswordRequest,
    current_user: UserDocument = Depends(get_current_user),
):
    """Change password. Requires current password verification."""
    try:
        await AuthService.change_password(str(current_user.id), data)
        return MessageResponse(message="Password changed successfully")
    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=e.message)
        raise HTTPException(status_code=400, detail=str(e))


# ── API Key Management ────────────────────────────────────────

@router.get(
    "/me/api-keys",
    response_model=APIKeysStatusResponse,
    summary="Get API keys status",
)
async def get_api_keys_status(
    current_user: UserDocument = Depends(get_current_user),
):
    """Returns which API keys are configured (without revealing values)."""
    return APIKeysStatusResponse(
        has_deepseek_key=bool(current_user.deepseek_api_key_encrypted),
        has_anticaptcha_key=bool(current_user.anticaptcha_api_key_encrypted),
        has_capsolver_key=bool(current_user.capsolver_api_key_encrypted),
        has_proxy_credentials=bool(
            current_user.webshare_proxy_username_encrypted
            and current_user.webshare_proxy_password_encrypted
        ),
        deepseek_key_masked=(
            mask_sensitive(decrypt_credential(current_user.deepseek_api_key_encrypted), 4)
            if current_user.deepseek_api_key_encrypted
            else None
        ),
        anticaptcha_key_masked=(
            mask_sensitive(decrypt_credential(current_user.anticaptcha_api_key_encrypted), 4)
            if current_user.anticaptcha_api_key_encrypted
            else None
        ),
        capsolver_key_masked=(
            mask_sensitive(decrypt_credential(current_user.capsolver_api_key_encrypted), 4)
            if current_user.capsolver_api_key_encrypted
            else None
        ),
        webshare_proxy_username=(
            decrypt_credential(current_user.webshare_proxy_username_encrypted)
            if current_user.webshare_proxy_username_encrypted
            else None
        ),
        proxy_host=current_user.proxy_host,
        proxy_port=current_user.proxy_port,
    )


@router.put(
    "/me/api-keys",
    response_model=MessageResponse,
    summary="Update API keys",
)
async def update_api_keys(
    data: UpdateAPIKeysRequest,
    current_user: UserDocument = Depends(get_current_user),
):
    """
    Update personal API keys for DeepSeek, Anti-Captcha, and Webshare Proxy.
    All keys are encrypted at rest.
    Only provided fields are updated — omit a field to keep current value.
    """
    try:
        await AuthService.update_api_keys(str(current_user.id), data)
        return MessageResponse(message="API keys updated successfully")
    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=e.message)
        raise HTTPException(status_code=400, detail=str(e))


# ── Admin Endpoints ───────────────────────────────────────────

@router.get(
    "/admin/users",
    response_model=UserListResponse,
    summary="[Superadmin] List all users",
)
async def admin_list_users(
    page: int = 1,
    page_size: int = 20,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    _admin: UserDocument = Depends(get_current_superadmin),
):
    """Superadmin only: List and filter all users."""
    users, total = await AuthService.list_users(
        page=page, page_size=page_size, role=role, is_active=is_active
    )
    return UserListResponse(
        users=[u.dict_for_response() for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.put(
    "/admin/users/{user_id}/role",
    response_model=UserResponse,
    summary="[Superadmin] Update user role",
)
async def admin_update_user_role(
    user_id: str,
    role: UserRole,
    _admin: UserDocument = Depends(get_current_superadmin),
):
    """Superadmin only: Change a user's role."""
    try:
        user = await AuthService.update_user_role(user_id, role)
        return user.dict_for_response()
    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=e.message)
        raise HTTPException(status_code=400, detail=str(e))


@router.put(
    "/admin/users/{user_id}/active",
    response_model=UserResponse,
    summary="[Superadmin] Toggle user active status",
)
async def admin_toggle_user_active(
    user_id: str,
    is_active: bool = True,
    _admin: UserDocument = Depends(get_current_superadmin),
):
    """Superadmin only: Activate or deactivate a user."""
    try:
        user = await AuthService.toggle_user_active(user_id, is_active)
        return user.dict_for_response()
    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=e.message)
        raise HTTPException(status_code=400, detail=str(e))
