"""
AutoWebAgent - Proxy Routes
=============================
Proxy management and validation endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from app.features.auth.dependencies import get_current_user
from app.features.auth.models import UserDocument
from app.features.proxy.service import ProxyService
from app.features.auth.service import AuthService

router = APIRouter(prefix="/proxy", tags=["Proxy"])


@router.get("/status")
async def get_proxy_status(
    proxy_host: Optional[str] = Query(None, description="Custom proxy host"),
    proxy_port: Optional[int] = Query(None, description="Custom proxy port"),
    current_user: UserDocument = Depends(get_current_user),
):
    """Check current proxy configuration and validate connection."""
    api_keys = AuthService.get_decrypted_api_keys(current_user)

    result = await ProxyService.validate_proxy(
        proxy_username=api_keys.get("proxy_username"),
        proxy_password=api_keys.get("proxy_password"),
        proxy_host=proxy_host or api_keys.get("proxy_host"),
        proxy_port=proxy_port or api_keys.get("proxy_port"),
    )

    return {
        **result,
        "has_credentials": bool(
            api_keys.get("proxy_username") and api_keys.get("proxy_password")
        ),
    }


@router.get("/validate")
async def validate_proxy(
    proxy_host: Optional[str] = Query(None, description="Custom proxy host"),
    proxy_port: Optional[int] = Query(None, description="Custom proxy port"),
    current_user: UserDocument = Depends(get_current_user),
):
    """Validate proxy connection and return IP details."""
    api_keys = AuthService.get_decrypted_api_keys(current_user)

    result = await ProxyService.validate_proxy(
        proxy_username=api_keys.get("proxy_username"),
        proxy_password=api_keys.get("proxy_password"),
        proxy_host=proxy_host or api_keys.get("proxy_host"),
        proxy_port=proxy_port or api_keys.get("proxy_port"),
    )

    return result
