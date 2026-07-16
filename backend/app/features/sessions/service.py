"""
AutoWebAgent - Session Service
================================
Manages isolated Playwright browser contexts per user.
Handles session lifecycle: create, navigate, execute, persist, close.
"""

import asyncio
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from beanie import PydanticObjectId
from loguru import logger

from app.core.config import settings
from app.core.exceptions import (
    SessionNotFoundError,
    SessionLimitExceededError,
    BrowserLaunchError,
)
from app.features.sessions.models import SessionDocument
from app.features.sessions.schemas import (
    SessionCreateRequest,
    SessionNavigateRequest,
    SessionExecuteRequest,
)
from app.features.proxy.service import ProxyService
from app.features.agent.stealth import StealthManager


class SessionService:
    """
    Manages browser sessions with complete user isolation.

    Each user gets their own Playwright browser contexts — no cross-user leakage.
    Sessions persist cookies + localStorage for continuity across tasks.
    """

    # In-memory store of active Playwright browser contexts
    # Key: session_id, Value: BrowserContext
    _active_contexts: Dict[str, Any] = {}
    _browser_instance: Any = None  # Shared browser instance
    _lock = asyncio.Lock()

    @classmethod
    async def _get_or_create_browser(cls):
        """Get or create the shared Playwright browser instance."""
        if cls._browser_instance is None:
            from playwright.async_api import async_playwright
            playwright = await async_playwright().start()

            launch_options = {
                "headless": settings.BROWSER_HEADLESS,
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-infobars",
                    "--disable-dev-shm-usage",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-background-networking",
                    "--disable-sync",
                    "--disable-translate",
                    "--hide-scrollbars",
                    "--metrics-recording-only",
                    "--mute-audio",
                    "--disable-component-update",
                    "--disable-domain-reliability",
                    "--disable-print-preview",
                    "--disable-notifications",
                ],
            }

            cls._browser_instance = await playwright.chromium.launch(**launch_options)
            logger.info("🚀 Playwright browser launched (shared instance)")

        return cls._browser_instance

    @classmethod
    async def create_session(
        cls,
        user_id: str,
        data: SessionCreateRequest,
        user_api_keys: Optional[Dict[str, str]] = None,
    ) -> SessionDocument:
        """
        Create a new isolated browser session for a user.

        1. Check session limit (max concurrent per user).
        2. Generate consistent fingerprint for this session.
        3. Configure proxy if user has credentials.
        4. Create Playwright browser context with stealth patches.
        5. Persist session metadata to MongoDB.
        """
        # Check session limit
        active_count = await SessionDocument.find(
            SessionDocument.user_id == user_id,
            SessionDocument.status == "active",
        ).count()

        if active_count >= settings.MAX_CONCURRENT_SESSIONS_PER_USER:
            raise SessionLimitExceededError(
                limit=settings.MAX_CONCURRENT_SESSIONS_PER_USER
            )

        # Generate consistent fingerprint for this session
        fingerprint = StealthManager.generate_consistent_fingerprint(
            viewport_width=data.viewport_width,
            viewport_height=data.viewport_height,
            locale=data.locale,
            timezone_id=data.timezone_id,
        )

        # Get proxy configuration
        proxy_username = None
        proxy_password = None
        proxy_host = None
        proxy_port = None
        if user_api_keys:
            proxy_username = user_api_keys.get("proxy_username")
            proxy_password = user_api_keys.get("proxy_password")
            proxy_host = user_api_keys.get("proxy_host")
            proxy_port = user_api_keys.get("proxy_port")

        proxy_config = await ProxyService.get_proxy_config(
            proxy_username=proxy_username,
            proxy_password=proxy_password,
            proxy_host=proxy_host,
            proxy_port=proxy_port,
            country=data.proxy_country
        )

        # Create browser context with stealth
        browser = await cls._get_or_create_browser()

        context_options: Dict[str, Any] = {
            "viewport": {
                "width": data.viewport_width,
                "height": data.viewport_height,
            },
            "locale": data.locale,
            "timezone_id": data.timezone_id,
            "user_agent": data.user_agent or fingerprint["user_agent"],
            "permissions": ["geolocation"],
            "geolocation": fingerprint.get("geolocation", {
                "latitude": 40.7128,
                "longitude": -74.0060,
            }),
        }

        if proxy_config:
            context_options["proxy"] = {
                "server": proxy_config["server"],
                "username": proxy_config.get("username"),
                "password": proxy_config.get("password"),
            }

        # Create the context
        context = await browser.new_context(**context_options)
        
        # Attach the selected proxy configuration so it's accessible from the context
        context._proxy_config = proxy_config

        # Inject stealth scripts
        await StealthManager.inject_stealth_scripts(context)

        # Override fingerprint properties
        await StealthManager.apply_fingerprint_overrides(context, fingerprint)

        # Create session document
        session = SessionDocument(
            user_id=user_id,
            name=data.name,
            status="active",
            stealth_mode=data.stealth_mode,
            viewport_width=data.viewport_width,
            viewport_height=data.viewport_height,
            locale=data.locale,
            timezone_id=data.timezone_id,
            user_agent=fingerprint["user_agent"],
            fingerprint_id=fingerprint["fingerprint_id"],
            canvas_noise_seed=fingerprint.get("canvas_seed"),
            webgl_vendor=fingerprint.get("webgl_vendor"),
            webgl_renderer=fingerprint.get("webgl_renderer"),
            hardware_concurrency=fingerprint.get("hardware_concurrency", 8),
            device_memory=fingerprint.get("device_memory", 8),
            proxy_ip=proxy_config.get("host") if proxy_config else None,
            proxy_country=data.proxy_country,
        )

        await session.insert()

        # Store context reference
        cls._active_contexts[str(session.id)] = context

        logger.info(
            f"🆕 Session created: {session.id} "
            f"for user {user_id} (stealth={data.stealth_mode})"
        )

        return session

    @classmethod
    async def get_session(cls, session_id: str, user_id: str) -> SessionDocument:
        """Get session, verifying ownership."""
        session = await SessionDocument.get(PydanticObjectId(session_id))
        if not session or session.user_id != user_id:
            raise SessionNotFoundError(session_id)
        return session

    @classmethod
    def get_context(cls, session_id: str) -> Any:
        """Get the Playwright browser context for a session."""
        context = cls._active_contexts.get(session_id)
        if not context:
            raise SessionNotFoundError(session_id)
        return context

    @classmethod
    async def navigate(
        cls, session_id: str, user_id: str, data: SessionNavigateRequest
    ) -> Dict[str, Any]:
        """Navigate to a URL in the session's browser context."""
        session = await cls.get_session(session_id, user_id)
        context = cls.get_context(session_id)

        page = await context.new_page()
        await page.goto(data.url, wait_until=data.wait_until, timeout=data.timeout_ms)

        # Update session state
        session.current_url = page.url
        session.page_title = await page.title()
        session.pages_visited += 1
        session.last_active_at = datetime.now(timezone.utc)
        await session.save()

        # Get page snapshot
        content = await page.content()
        title = await page.title()

        return {
            "url": page.url,
            "title": title,
            "content_length": len(content),
        }

    @classmethod
    async def execute_action(
        cls, session_id: str, user_id: str, data: SessionExecuteRequest
    ) -> Dict[str, Any]:
        """Execute a single action in the session."""
        session = await cls.get_session(session_id, user_id)
        context = cls.get_context(session_id)

        pages = context.pages
        if not pages:
            page = await context.new_page()
        else:
            page = pages[-1]

        result = {"action": data.action, "success": True}

        try:
            if data.action == "click":
                if data.selector:
                    await page.click(data.selector, delay=data.delay_ms or 100)
            elif data.action == "type":
                if data.selector and data.value is not None:
                    await page.fill(data.selector, data.value)
            elif data.action == "scroll":
                await page.evaluate(f"window.scrollBy(0, {data.value or 500})")
            elif data.action == "wait":
                await asyncio.sleep(float(data.value or 1))
            elif data.action == "screenshot":
                screenshot = await page.screenshot(type="png", full_page=False)
                import base64
                result["screenshot_base64"] = base64.b64encode(screenshot).decode()
            elif data.action == "execute_js":
                if data.value:
                    js_result = await page.evaluate(data.value)
                    result["js_result"] = js_result

            session.last_active_at = datetime.now(timezone.utc)
            await session.save()

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            logger.error(f"Action '{data.action}' failed in session {session_id}: {e}")

        return result

    @classmethod
    async def get_session_state(cls, session_id: str, user_id: str) -> Dict[str, Any]:
        """Get current state of a session (cookies, localStorage, screenshot)."""
        session = await cls.get_session(session_id, user_id)
        context = cls.get_context(session_id)

        pages = context.pages
        screenshot_base64 = None
        if pages:
            page = pages[-1]
            screenshot = await page.screenshot(type="png", full_page=False)
            import base64
            screenshot_base64 = base64.b64encode(screenshot).decode()

            # Update cookies
            cookies = await context.cookies()
            session.cookies = cookies
            await session.save()

        return {
            "id": str(session.id),
            "status": session.status,
            "current_url": session.current_url,
            "page_title": session.page_title,
            "cookies_count": len(session.cookies),
            "local_storage_keys": list(session.local_storage.keys()),
            "screenshot_base64": screenshot_base64,
        }

    @classmethod
    async def rotate_session_proxy(
        cls,
        session_id: str,
        user_id: str,
        user_api_keys: Optional[Dict[str, str]] = None,
        target_url: Optional[str] = None,
    ) -> Any:
        """
        Rotates the proxy of an active session by closing the old context,
        fetching a fresh verified proxy, and recreating the context with restored state.
        """
        session = await cls.get_session(session_id, user_id)

        # 1. Close old context
        old_context = cls._active_contexts.get(session_id)
        if old_context:
            try:
                cookies = await old_context.cookies()
                if cookies:
                    session.cookies = cookies
                    await session.save()
                await old_context.close()
            except Exception as e:
                logger.warning(f"Error closing old context during proxy rotation: {e}")
            cls._active_contexts.pop(session_id, None)

        # 2. Get a new rotated verified proxy
        proxy_username = None
        proxy_password = None
        if user_api_keys:
            proxy_username = user_api_keys.get("proxy_username")
            proxy_password = user_api_keys.get("proxy_password")

        proxy_config = await ProxyService.rotate_proxy(
            proxy_username=proxy_username,
            proxy_password=proxy_password,
            target_url=target_url,
        )

        if proxy_config:
            session.proxy_ip = proxy_config.get("host")
            await session.save()

        # 3. Create context options
        browser = await cls._get_or_create_browser()
        context_options: Dict[str, Any] = {
            "viewport": {
                "width": session.viewport_width,
                "height": session.viewport_height,
            },
            "locale": session.locale,
            "timezone_id": session.timezone_id,
            "user_agent": session.user_agent,
            "permissions": ["geolocation"],
        }

        if proxy_config:
            context_options["proxy"] = {
                "server": proxy_config["server"],
                "username": proxy_config.get("username"),
                "password": proxy_config.get("password"),
            }

        # 4. Recreate context and restore cookies
        context = await browser.new_context(**context_options)
        if session.cookies:
            await context.add_cookies(session.cookies)

        cls._active_contexts[session_id] = context
        logger.info(f"🔄 Session {session_id} successfully rotated to fresh proxy: {session.proxy_ip}")
        return context

    @classmethod
    async def close_session(cls, session_id: str, user_id: str) -> None:
        """Close a session and clean up Playwright context."""
        session = await cls.get_session(session_id, user_id)

        context = cls._active_contexts.pop(session_id, None)
        if context:
            await context.close()
            logger.info(f"🔒 Browser context closed for session {session_id}")

        session.status = "closed"
        session.last_active_at = datetime.now(timezone.utc)
        await session.save()

        logger.info(f"🚪 Session closed: {session_id}")

    @classmethod
    async def list_user_sessions(cls, user_id: str) -> tuple[List[SessionDocument], int, int]:
        """List all sessions for a user with counts."""
        sessions = await SessionDocument.find(
            SessionDocument.user_id == user_id
        ).sort("-created_at").to_list()

        active = sum(1 for s in sessions if s.status == "active")
        return sessions, len(sessions), active

    @classmethod
    async def cleanup_expired_sessions(cls) -> int:
        """Close sessions that have exceeded their expiry. Returns count cleaned."""
        count = 0
        now = datetime.now(timezone.utc)
        expired = await SessionDocument.find(
            SessionDocument.expires_at is not None,
            SessionDocument.expires_at < now,
            SessionDocument.status == "active",
        ).to_list()

        for session in expired:
            context = cls._active_contexts.pop(str(session.id), None)
            if context:
                await context.close()
            session.status = "expired"
            await session.save()
            count += 1

        if count > 0:
            logger.info(f"🧹 Cleaned up {count} expired sessions")

        return count
