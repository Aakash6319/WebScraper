"""
AutoWebAgent - Main FastAPI Application
=========================================
Entry point that wires together all feature modules,
middleware, and lifecycle events.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger

from app.core.config import settings
from app.core.database import init_database, close_database
from app.core.exceptions import AutoWebAgentException
from app.utils.logging import setup_logging
from app.middleware.setup import setup_middleware


# ── Application Lifespan ─────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle startup and shutdown events.

    Startup: Configure logging, connect DB, warm up browser.
    Shutdown: Close DB, close browser, cleanup.
    """
    # ── STARTUP ───────────────────────────────────────────
    setup_logging()
    logger.info("=" * 60)
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} starting...")
    logger.info(f"📍 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🔒 Stealth mode: {settings.STEALTH_MODE}")
    logger.info("=" * 60)

    # Initialize database
    await init_database()

    # Clean up stale active/idle sessions in DB from previous run
    try:
        from app.features.sessions.models import SessionDocument
        await SessionDocument.find(
            SessionDocument.status == "active"
        ).update({"$set": {"status": "closed"}})
        await SessionDocument.find(
            SessionDocument.status == "idle"
        ).update({"$set": {"status": "closed"}})
        logger.info(f"🧹 Cleaned up stale active/idle sessions on startup.")
    except Exception as e:
        logger.warning(f"Failed to clean up stale active sessions on startup: {e}")

    # Clean up stale running/pending tasks in DB from previous run
    try:
        from app.features.tasks.models import TaskDocument, TaskStatus
        await TaskDocument.find(
            TaskDocument.status == TaskStatus.RUNNING
        ).update({"$set": {"status": TaskStatus.FAILED, "error_message": "Server restarted during execution"}})
        await TaskDocument.find(
            TaskDocument.status == TaskStatus.PENDING
        ).update({"$set": {"status": TaskStatus.FAILED, "error_message": "Server restarted during execution"}})
        logger.info(f"🧹 Cleaned up stale running/pending tasks on startup.")
    except Exception as e:
        logger.warning(f"Failed to clean up stale tasks on startup: {e}")

    # Warm up: pre-launch browser (optional, saves first-request latency)
    # from app.features.sessions.service import SessionService
    # await SessionService._get_or_create_browser()

    logger.success("✅ AutoWebAgent is ready!")

    yield  # ── Application runs here ──

    # ── SHUTDOWN ──────────────────────────────────────────
    logger.info("🛑 Shutting down AutoWebAgent...")

    # Close all active browser sessions
    try:
        from app.features.sessions.service import SessionService
        for session_id, context in list(SessionService._active_contexts.items()):
            try:
                await context.close()
            except Exception:
                pass
        SessionService._active_contexts.clear()

        if SessionService._browser_instance:
            await SessionService._browser_instance.close()
    except Exception as e:
        logger.warning(f"Browser cleanup error: {e}")

    # Close database
    await close_database()

    logger.info("👋 AutoWebAgent shut down complete")


# ── Create FastAPI App ───────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-grade AI Web Automation SaaS with Ultra Stealth",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
    redirect_slashes=False,
)


# ── Middleware ──────────────────────────────────────────────

setup_middleware(app)


# ── Exception Handlers ──────────────────────────────────────

@app.exception_handler(AutoWebAgentException)
async def autowebagent_exception_handler(request: Request, exc: AutoWebAgentException):
    """Convert our domain exceptions to proper HTTP responses."""
    logger.warning(f"⚠️ {exc.__class__.__name__}: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.message,
            "type": exc.__class__.__name__,
            **(exc.detail if exc.detail else {}),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions."""
    logger.error(f"💥 Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": "InternalError",
        },
    )


# ── Health Check ────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "stealth_mode": settings.STEALTH_MODE,
    }


@app.get("/api/v1/health", tags=["Health"])
async def api_health_check():
    """API health check with DB status."""
    try:
        from app.core.database import get_database
        db = await get_database()
        await db.command("ping")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {
        "status": "healthy",
        "database": db_status,
        "version": settings.APP_VERSION,
    }


# ── Register Feature Routers ─────────────────────────────────

from app.features.auth.routes import router as auth_router
from app.features.websites.routes import router as websites_router
from app.features.sessions.routes import router as sessions_router
from app.features.tasks.routes import router as tasks_router
from app.features.agent.routes import router as agent_router
from app.features.proxy.routes import router as proxy_router
from app.features.admin.routes import router as admin_router

api_prefix = settings.API_PREFIX

app.include_router(auth_router, prefix=api_prefix)
app.include_router(websites_router, prefix=api_prefix)
app.include_router(sessions_router, prefix=api_prefix)
app.include_router(tasks_router, prefix=api_prefix)
app.include_router(agent_router, prefix=api_prefix)
app.include_router(proxy_router, prefix=api_prefix)
app.include_router(admin_router, prefix=api_prefix)


# ── Root Redirect ────────────────────────────────────────────

@app.get("/", tags=["Root"])
async def root():
    """Welcome endpoint."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "api_prefix": settings.API_PREFIX,
    }


# ── Run (Development) ────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
