"""
AutoWebAgent - Logging Configuration
======================================
Uses Loguru for structured, colorized logging.
Supports JSON format for production log aggregation.
"""

import sys
import json
from loguru import logger

from app.core.config import settings


def setup_logging() -> None:
    """
    Configure Loguru with appropriate format and level.

    In production, outputs JSON for ELK/Loki ingestion.
    In development, uses colorized human-readable output.
    """
    # Remove default handler
    logger.remove()

    if settings.LOG_FORMAT == "json":
        # JSON format for structured logging (production)
        def json_sink(message) -> None:
            record = message.record
            log_data = {
                "time": record["time"].isoformat(),
                "level": record["level"].name,
                "message": record["message"],
                "module": record["module"],
                "function": record["function"],
                "line": record["line"],
            }
            sys.stdout.write(json.dumps(log_data) + "\n")

        logger.add(
            json_sink,
            level=settings.LOG_LEVEL,
        )
    else:
        # Human-readable format (development)
        logger.add(
            sys.stderr,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
            level=settings.LOG_LEVEL,
            colorize=True,
        )

    # Also log to file for persistent storage
    logger.add(
        "logs/autowebagent_{time:YYYY-MM-DD}.log",
        rotation="00:00",  # Rotate at midnight
        retention="30 days",
        compression="gz",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
    )

    logger.info(f"🚀 AutoWebAgent v{settings.APP_VERSION} starting")
    logger.info(f"📝 Log level: {settings.LOG_LEVEL}, format: {settings.LOG_FORMAT}")
