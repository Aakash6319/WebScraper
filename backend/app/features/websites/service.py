"""
AutoWebAgent - Website Service
================================
CRUD operations for website configurations.
"""

from typing import Optional, List
from datetime import datetime, timezone

from beanie import PydanticObjectId
from loguru import logger

from app.core.security import encrypt_credential, decrypt_credential
from app.core.exceptions import WebsiteNotFoundError, ValidationError
from app.features.websites.models import WebsiteDocument
from app.features.websites.schemas import WebsiteCreateRequest, WebsiteUpdateRequest


class WebsiteService:
    """Manages stored website configurations."""

    @staticmethod
    async def create_website(
        user_id: str, data: WebsiteCreateRequest
    ) -> WebsiteDocument:
        """Create a new website configuration for a user."""
        website = WebsiteDocument(
            user_id=user_id,
            name=data.name,
            url=data.url,
            description=data.description,
            login_url=data.login_url,
            login_username=data.login_username,
            login_password_encrypted=(
                encrypt_credential(data.login_password)
                if data.login_password
                else None
            ),
            login_selector_username=data.login_selector_username,
            login_selector_password=data.login_selector_password,
            login_selector_submit=data.login_selector_submit,
            custom_selectors=data.custom_selectors,
            custom_headers=data.custom_headers,
            blacklist_urls=data.blacklist_urls,
            allowed_domains=data.allowed_domains,
            max_depth=data.max_depth,
            stealth_mode_override=data.stealth_mode_override,
            use_proxy=data.use_proxy,
            proxy_country=data.proxy_country,
            tags=data.tags,
        )
        await website.insert()
        logger.info(f"🌐 Website created: {website.name} ({website.url})")
        return website

    @staticmethod
    async def get_user_websites(
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> tuple[List[WebsiteDocument], int]:
        """List websites for a user with optional filters."""
        query = WebsiteDocument.find(WebsiteDocument.user_id == user_id)

        if search:
            query = query.find(
                {
                    "$or": [
                        {"name": {"$regex": search, "$options": "i"}},
                        {"url": {"$regex": search, "$options": "i"}},
                    ]
                }
            )
        if tag:
            query = query.find({"tags": tag})

        total = await query.count()
        websites = await query.sort("-updated_at") \
            .skip((page - 1) * page_size) \
            .limit(page_size) \
            .to_list()

        return websites, total

    @staticmethod
    async def get_website(website_id: str, user_id: str) -> WebsiteDocument:
        """Get a single website, ensuring ownership."""
        website = await WebsiteDocument.get(PydanticObjectId(website_id))
        if not website or website.user_id != user_id:
            raise WebsiteNotFoundError(website_id)
        return website

    @staticmethod
    async def update_website(
        website_id: str, user_id: str, data: WebsiteUpdateRequest
    ) -> WebsiteDocument:
        """Update a website configuration (partial update)."""
        website = await WebsiteService.get_website(website_id, user_id)

        update_fields = data.model_dump(exclude_unset=True)

        # Encrypt password if provided
        if "login_password" in update_fields:
            if update_fields["login_password"]:
                update_fields["login_password_encrypted"] = encrypt_credential(
                    update_fields.pop("login_password")
                )
            else:
                update_fields["login_password_encrypted"] = None
                del update_fields["login_password"]

        for field, value in update_fields.items():
            if hasattr(website, field):
                setattr(website, field, value)

        website.updated_at = datetime.now(timezone.utc)
        await website.save()

        logger.info(f"🌐 Website updated: {website.name}")
        return website

    @staticmethod
    async def delete_website(website_id: str, user_id: str) -> None:
        """Delete a website configuration."""
        website = await WebsiteService.get_website(website_id, user_id)
        await website.delete()
        logger.info(f"🗑️ Website deleted: {website.name}")

    @staticmethod
    async def record_usage(website_id: str, user_id: str) -> None:
        """Increment use count and update last_used_at."""
        try:
            website = await WebsiteService.get_website(website_id, user_id)
            website.use_count += 1
            website.last_used_at = datetime.now(timezone.utc)
            await website.save()
        except WebsiteNotFoundError:
            pass  # Don't fail if website was deleted
