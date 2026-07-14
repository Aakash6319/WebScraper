"""
AutoWebAgent - Website Routes
===============================
CRUD endpoints for website configurations.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException

from app.features.auth.dependencies import get_current_user
from app.features.auth.models import UserDocument
from app.features.websites.schemas import (
    WebsiteCreateRequest,
    WebsiteUpdateRequest,
    WebsiteResponse,
    WebsiteListResponse,
)
from app.features.websites.service import WebsiteService

router = APIRouter(prefix="/websites", tags=["Websites"])


@router.post("", response_model=WebsiteResponse, status_code=201)
async def create_website(
    data: WebsiteCreateRequest,
    current_user: UserDocument = Depends(get_current_user),
):
    """Create a new website configuration."""
    try:
        website = await WebsiteService.create_website(
            str(current_user.id), data
        )
        return website.dict_for_response()
    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=e.message)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=WebsiteListResponse)
async def list_websites(
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    tag: Optional[str] = None,
    current_user: UserDocument = Depends(get_current_user),
):
    """List user's websites with optional search and tag filter."""
    websites, total = await WebsiteService.get_user_websites(
        str(current_user.id), page, page_size, search, tag
    )
    return WebsiteListResponse(
        websites=[w.dict_for_response() for w in websites],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{website_id}", response_model=WebsiteResponse)
async def get_website(
    website_id: str,
    current_user: UserDocument = Depends(get_current_user),
):
    """Get a single website by ID."""
    try:
        website = await WebsiteService.get_website(
            website_id, str(current_user.id)
        )
        return website.dict_for_response()
    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=e.message)
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{website_id}", response_model=WebsiteResponse)
async def update_website(
    website_id: str,
    data: WebsiteUpdateRequest,
    current_user: UserDocument = Depends(get_current_user),
):
    """Update a website configuration (partial update)."""
    try:
        website = await WebsiteService.update_website(
            website_id, str(current_user.id), data
        )
        return website.dict_for_response()
    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=e.message)
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{website_id}")
async def delete_website(
    website_id: str,
    current_user: UserDocument = Depends(get_current_user),
):
    """Delete a website configuration."""
    try:
        await WebsiteService.delete_website(website_id, str(current_user.id))
        return {"message": "Website deleted successfully"}
    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=e.message)
        raise HTTPException(status_code=400, detail=str(e))
