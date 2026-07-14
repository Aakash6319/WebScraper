"""
AutoWebAgent - Auth Dependencies
==================================
FastAPI dependency injection for authentication & authorization.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

from app.core.security import decode_token
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.features.auth.models import UserDocument, UserRole

# Bearer token extraction
security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> UserDocument:
    """
    FastAPI dependency: Extract and validate JWT, return authenticated user.

    Raises:
        401 if no token or invalid token.
        401 if user not found.
        403 if account deactivated.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Refresh tokens can't be used as access tokens
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    from beanie import PydanticObjectId
    user = await UserDocument.get(PydanticObjectId(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return user


async def get_current_superadmin(
    current_user: UserDocument = Depends(get_current_user),
) -> UserDocument:
    """
    FastAPI dependency: Ensure the current user is a superadmin.

    Chain: get_current_user → get_current_superadmin.
    Raises 403 if user is not superadmin.
    """
    if current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required",
        )
    return current_user


async def get_current_premium_user(
    current_user: UserDocument = Depends(get_current_user),
) -> UserDocument:
    """
    FastAPI dependency: Ensure user is premium or superadmin.
    """
    if current_user.role not in (UserRole.PREMIUM, UserRole.SUPERADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required",
        )
    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Optional[UserDocument]:
    """
    FastAPI dependency: Optionally authenticate user.
    Returns None if no valid token, otherwise returns user.
    Useful for endpoints that work both authenticated and unauthenticated.
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
