"""
AutoWebAgent - Utility Helpers
================================
Common helper functions used across the application.
"""

import time
import uuid
import hashlib
from typing import Any, Optional
from datetime import datetime, timezone
from functools import wraps


def generate_id() -> str:
    """Generate a unique ID (UUID4)."""
    return str(uuid.uuid4())


def generate_short_id(length: int = 12) -> str:
    """Generate a short unique ID from UUID4 hex."""
    return uuid.uuid4().hex[:length]


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def utc_timestamp() -> float:
    """Get current UTC timestamp."""
    return time.time()


def hash_string(value: str, algorithm: str = "sha256") -> str:
    """Hash a string with the given algorithm."""
    h = hashlib.new(algorithm)
    h.update(value.encode("utf-8"))
    return h.hexdigest()


def mask_sensitive(value: str, visible_chars: int = 4) -> str:
    """
    Mask a sensitive string, showing only a fixed number of asterisks and the last few characters.

    Example: mask_sensitive("sk-abc123xyz") → "********3xyz"
    """
    if not value:
        return ""
    if len(value) <= visible_chars:
        return "*" * 8
    return "*" * 8 + value[-visible_chars:]


def truncate_string(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """Truncate a string to max_length, adding suffix if truncated."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def safe_json_parse(text: str, default: Any = None) -> Any:
    """Safely parse JSON, returning default on failure."""
    import json
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def chunk_list(items: list, chunk_size: int) -> list[list]:
    """Split a list into chunks of specified size."""
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def retry_async(
    max_retries: int = 3,
    delay_seconds: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """
    Decorator for retrying async functions with exponential backoff.

    Usage:
        @retry_async(max_retries=5, exceptions=(ConnectionError,))
        async def my_func():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay_seconds

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        import asyncio
                        from loguru import logger
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {e}"
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff_factor

            raise last_exception  # type: ignore

        return wrapper
    return decorator


def build_proxy_url(
    username: str,
    password: str,
    host: str = "p.webshare.io",
    port: int = 80,
) -> str:
    """
    Build a proxy URL string for Webshare rotating residential proxies.

    Returns: http://username:password@host:port
    """
    return f"http://{username}:{password}@{host}:{port}"


def extract_domain(url: str) -> str:
    """Extract the domain from a URL."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return parsed.netloc or parsed.path.split("/")[0]


def sanitize_filename(filename: str) -> str:
    """Remove unsafe characters from a filename."""
    import re
    return re.sub(r'[<>:"/\\|?*]', "_", filename)
