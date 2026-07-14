"""
AutoWebAgent - Security & Encryption
=======================================
JWT token handling, password hashing, credential encryption.
Uses Fernet symmetric encryption for stored API keys.
"""

import os
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

import bcrypt
from jose import JWTError, jwt
from cryptography.fernet import Fernet
from loguru import logger

from app.core.config import settings

# ── Password Hashing ──────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


# ── JWT Token Handling ────────────────────────────────────────────

def create_access_token(
    subject: str,
    extra_claims: Optional[dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        subject: Typically the user ID (as string).
        extra_claims: Additional claims like role, email etc.
        expires_delta: Custom expiry; defaults to config setting.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_delta,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    subject: str,
    extra_claims: Optional[dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT refresh token with longer expiry."""
    if expires_delta is None:
        expires_delta = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_delta,
        "type": "refresh",
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """
    Decode and validate a JWT token.
    Returns the payload dict or None if invalid/expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode failed: {e}")
        return None


# ── Credential Encryption (Fernet) ─────────────────────────────────

def _get_fernet() -> Fernet:
    """
    Derive a 32-byte Fernet key from the configured ENCRYPTION_KEY.
    If the key is not exactly 32 url-safe base64 bytes, pad/derive it.
    """
    key = settings.ENCRYPTION_KEY
    # Fernet requires a 32-byte urlsafe-base64-encoded key
    if len(key) == 44 and key.endswith("="):
        # Already looks like valid Fernet key
        return Fernet(key.encode())

    # Derive a valid key: take first 32 bytes, base64 encode
    derived = base64.urlsafe_b64encode(key.encode()[:32].ljust(32, b"\x00"))
    return Fernet(derived)


def encrypt_credential(plaintext: str) -> str:
    """
    Encrypt a sensitive credential string (API key, proxy password etc.)
    using Fernet symmetric encryption.

    Args:
        plaintext: The secret to encrypt.

    Returns:
        Encrypted string (base64-encoded).
    """
    if not plaintext:
        return ""
    fernet = _get_fernet()
    encrypted = fernet.encrypt(plaintext.encode())
    return encrypted.decode()


def decrypt_credential(ciphertext: str) -> str:
    """
    Decrypt a Fernet-encrypted credential string.

    Args:
        ciphertext: The encrypted value (base64-encoded).

    Returns:
        Original plaintext string.
    """
    if not ciphertext:
        return ""
    try:
        fernet = _get_fernet()
        decrypted = fernet.decrypt(ciphertext.encode())
        return decrypted.decode()
    except Exception as e:
        logger.error(f"Failed to decrypt credential: {e}")
        return ""


def generate_api_key() -> str:
    """Generate a random API key string."""
    return base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("=")


def generate_session_token() -> str:
    """Generate a random session token."""
    return base64.urlsafe_b64encode(os.urandom(48)).decode()
