"""
AutoWebAgent - Database Connection & Initialization
=====================================================
Uses Motor (async MongoDB driver) + Beanie ODM for type-safe documents.
"""

from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from beanie import init_beanie
from loguru import logger

from app.core.config import settings

# Global database client & database instances
_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


async def get_database() -> AsyncIOMotorDatabase:
    """Returns the active MongoDB database instance."""
    global _db
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db


async def init_database() -> None:
    """
    Initialize MongoDB connection and register all Beanie document models.

    Order matters: connect → register models → verify.
    """
    global _client, _db

    logger.info(f"🔌 Connecting to MongoDB: {settings.MONGODB_URI}")

    # Create async Motor client with connection pooling
    _client = AsyncIOMotorClient(
        settings.MONGODB_URI,
        maxPoolSize=50,
        minPoolSize=5,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
    )

    _db = _client[settings.MONGODB_DB_NAME]

    # ── Register ALL Beanie document models ─────────────────────
    # Import models here to avoid circular imports
    from app.features.auth.models import UserDocument
    from app.features.websites.models import WebsiteDocument
    from app.features.sessions.models import SessionDocument
    from app.features.tasks.models import TaskDocument
    from app.features.proxy.models import ProxyConfigDocument

    document_models = [
        UserDocument,
        WebsiteDocument,
        SessionDocument,
        TaskDocument,
        ProxyConfigDocument,
    ]

    await init_beanie(
        database=_db,
        document_models=document_models,
    )

    # Verify connection
    await _client.admin.command("ping")
    logger.success("✅ MongoDB connected & Beanie models registered")


async def close_database() -> None:
    """Gracefully close the MongoDB connection."""
    global _client
    if _client:
        _client.close()
        logger.info("🔌 MongoDB connection closed")
        _client = None


def get_client() -> Optional[AsyncIOMotorClient]:
    """Returns the raw Motor client (for advanced queries)."""
    return _client
