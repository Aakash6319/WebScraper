"""
AutoWebAgent - Auth Service
=============================
Business logic for registration, login, token management,
and API key encryption/decryption.
"""

from typing import Optional, List
from datetime import datetime, timezone

from beanie import PydanticObjectId
from loguru import logger

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    encrypt_credential,
    decrypt_credential,
)
from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    UserNotFoundError,
    UserAlreadyExistsError,
    ValidationError,
)
from app.features.auth.models import UserDocument, UserRole
from app.features.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    UpdateAPIKeysRequest,
    ChangePasswordRequest,
    UpdateProfileRequest,
    TokenResponse,
    UserResponse,
)


class AuthService:
    """Handles all authentication and user management logic."""

    # ── Registration ───────────────────────────────────────────

    @staticmethod
    async def register(data: RegisterRequest) -> UserDocument:
        """
        Register a new user.

        Checks for duplicate email, hashes password, and creates the document.

        Raises:
            UserAlreadyExistsError: If email is already registered.
        """
        # Check duplicate
        existing = await UserDocument.find_one(
            UserDocument.email == data.email
        )
        if existing:
            raise UserAlreadyExistsError(email=data.email)

        # Also check username uniqueness
        existing_username = await UserDocument.find_one(
            UserDocument.username == data.username
        )
        if existing_username:
            raise ValidationError(message="Username already taken")

        user = UserDocument(
            email=data.email,
            username=data.username,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role=UserRole.NORMAL,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        await user.insert()
        logger.info(f"✅ New user registered: {user.email} (id={user.id})")
        return user

    # ── Login ──────────────────────────────────────────────────

    @staticmethod
    async def login(data: LoginRequest) -> TokenResponse:
        """
        Authenticate a user and return JWT token pair.

        Validates credentials, updates last_login, and generates tokens.

        Raises:
            AuthenticationError: If credentials are invalid.
            AuthorizationError: If account is inactive.
        """
        user = await UserDocument.find_one(UserDocument.email == data.email)
        if not user:
            raise AuthenticationError("Invalid email or password")

        if not verify_password(data.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthorizationError("Account is deactivated. Contact support.")

        # Update login stats
        user.last_login_at = datetime.now(timezone.utc)
        await user.save()

        # Generate tokens
        access_token = create_access_token(
            subject=str(user.id),
            extra_claims={
                "email": user.email,
                "role": user.role.value,
            },
        )
        refresh_token = create_refresh_token(
            subject=str(user.id),
            extra_claims={
                "email": user.email,
                "role": user.role.value,
            },
        )

        # Store refresh token hash
        user.refresh_tokens.append(refresh_token)
        # Keep only last 5 refresh tokens
        if len(user.refresh_tokens) > 5:
            user.refresh_tokens = user.refresh_tokens[-5:]
        await user.save()

        logger.info(f"🔑 User logged in: {user.email}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # ── Token Refresh ──────────────────────────────────────────

    @staticmethod
    async def refresh_access_token(refresh_token: str) -> TokenResponse:
        """
        Validate a refresh token and issue a new access token.

        The refresh token is rotated (old one invalidated).

        Raises:
            AuthenticationError: If refresh token is invalid or expired.
        """
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise AuthenticationError("Invalid refresh token")

        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Invalid refresh token payload")

        user = await UserDocument.get(PydanticObjectId(user_id))
        if not user:
            raise UserNotFoundError(user_id)

        # Verify this refresh token was issued to this user
        if refresh_token not in user.refresh_tokens:
            raise AuthenticationError("Refresh token has been revoked")

        # Remove old refresh token (rotation)
        user.refresh_tokens.remove(refresh_token)

        # Issue new tokens
        new_access_token = create_access_token(
            subject=str(user.id),
            extra_claims={
                "email": user.email,
                "role": user.role.value,
            },
        )
        new_refresh_token = create_refresh_token(
            subject=str(user.id),
            extra_claims={
                "email": user.email,
                "role": user.role.value,
            },
        )

        user.refresh_tokens.append(new_refresh_token)
        await user.save()

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # ── Logout ─────────────────────────────────────────────────

    @staticmethod
    async def logout(user_id: str, refresh_token: Optional[str] = None) -> None:
        """
        Logout user — invalidates refresh token if provided.

        If no token provided, invalidates ALL refresh tokens.
        """
        user = await UserDocument.get(PydanticObjectId(user_id))
        if not user:
            return

        if refresh_token and refresh_token in user.refresh_tokens:
            user.refresh_tokens.remove(refresh_token)
        else:
            user.refresh_tokens = []

        await user.save()
        logger.info(f"👋 User logged out: {user.email}")

    # ── Get Current User ───────────────────────────────────────

    @staticmethod
    async def get_user_by_id(user_id: str) -> UserDocument:
        """Fetch a user by ID. Raises UserNotFoundError if not found."""
        user = await UserDocument.get(PydanticObjectId(user_id))
        if not user:
            raise UserNotFoundError(user_id)
        return user

    @staticmethod
    async def get_user_by_email(email: str) -> Optional[UserDocument]:
        """Fetch a user by email. Returns None if not found."""
        return await UserDocument.find_one(UserDocument.email == email)

    # ── API Key Management ─────────────────────────────────────

    @staticmethod
    async def update_api_keys(
        user_id: str, data: UpdateAPIKeysRequest
    ) -> UserDocument:
        """
        Encrypt and store user's personal API keys.
        Only updates keys that are provided (partial update).
        """
        user = await AuthService.get_user_by_id(user_id)

        if data.deepseek_api_key is not None:
            user.deepseek_api_key_encrypted = encrypt_credential(data.deepseek_api_key)
        if data.anticaptcha_api_key is not None:
            user.anticaptcha_api_key_encrypted = encrypt_credential(data.anticaptcha_api_key)
        if data.capsolver_api_key is not None:
            user.capsolver_api_key_encrypted = encrypt_credential(data.capsolver_api_key)
        if data.webshare_proxy_username is not None:
            user.webshare_proxy_username_encrypted = encrypt_credential(data.webshare_proxy_username)
        if data.webshare_proxy_password is not None:
            user.webshare_proxy_password_encrypted = encrypt_credential(data.webshare_proxy_password)
        if data.proxy_host is not None:
            user.proxy_host = data.proxy_host
        if data.proxy_port is not None:
            user.proxy_port = data.proxy_port

        user.updated_at = datetime.now(timezone.utc)
        await user.save()

        logger.info(f"🔑 API keys updated for user: {user.email}")
        return user

    @staticmethod
    def get_decrypted_api_keys(user: UserDocument) -> dict:
        """
        Decrypt user's stored API keys.

        Returns dict with decrypted values. Superadmin global keys
        take precedence if configured.
        """
        return {
            "deepseek_api_key": (
                settings.DEEPSEEK_API_KEY
                or decrypt_credential(user.deepseek_api_key_encrypted or "")
            ),
            "anticaptcha_api_key": (
                settings.ANTICAPTCHA_API_KEY
                or decrypt_credential(user.anticaptcha_api_key_encrypted or "")
            ),
            "capsolver_api_key": (
                settings.CAPSOLVER_API_KEY
                or decrypt_credential(user.capsolver_api_key_encrypted or "")
            ),
            "proxy_username": (
                settings.WEBSHARE_PROXY_USERNAME
                or decrypt_credential(user.webshare_proxy_username_encrypted or "")
            ),
            "proxy_password": (
                settings.WEBSHARE_PROXY_PASSWORD
                or decrypt_credential(user.webshare_proxy_password_encrypted or "")
            ),
            "proxy_host": user.proxy_host or settings.WEBSHARE_PROXY_HOST,
            "proxy_port": user.proxy_port or settings.WEBSHARE_PROXY_PORT,
        }

    # ── Password Management ────────────────────────────────────

    @staticmethod
    async def change_password(
        user_id: str, data: ChangePasswordRequest
    ) -> None:
        """Change user password after verifying current password."""
        user = await AuthService.get_user_by_id(user_id)

        if not verify_password(data.current_password, user.hashed_password):
            raise AuthenticationError("Current password is incorrect")

        user.hashed_password = hash_password(data.new_password)
        # Invalidate all refresh tokens for security
        user.refresh_tokens = []
        user.updated_at = datetime.now(timezone.utc)
        await user.save()

        logger.info(f"🔐 Password changed for user: {user.email}")

    # ── Profile Management ─────────────────────────────────────

    @staticmethod
    async def update_profile(
        user_id: str, data: UpdateProfileRequest
    ) -> UserDocument:
        """Update user profile fields."""
        user = await AuthService.get_user_by_id(user_id)

        if data.full_name is not None:
            user.full_name = data.full_name
        if data.username is not None:
            # Check username uniqueness
            existing = await UserDocument.find_one(
                UserDocument.username == data.username,
                UserDocument.id != user.id,
            )
            if existing:
                raise ValidationError(message="Username already taken")
            user.username = data.username

        user.updated_at = datetime.now(timezone.utc)
        await user.save()

        logger.info(f"📝 Profile updated for user: {user.email}")
        return user

    # ── Admin: User Management ─────────────────────────────────

    @staticmethod
    async def list_users(
        page: int = 1,
        page_size: int = 20,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[List[UserDocument], int]:
        """
        List users with optional filters (admin only).
        Returns (users_list, total_count).
        """
        query = {}
        if role:
            query["role"] = role
        if is_active is not None:
            query["is_active"] = is_active

        total = await UserDocument.find(query).count()
        users = await UserDocument.find(query) \
            .sort("-created_at") \
            .skip((page - 1) * page_size) \
            .limit(page_size) \
            .to_list()

        return users, total

    @staticmethod
    async def update_user_role(
        target_user_id: str,
        new_role: UserRole,
    ) -> UserDocument:
        """Update a user's role (superadmin only)."""
        user = await AuthService.get_user_by_id(target_user_id)
        user.role = new_role
        user.updated_at = datetime.now(timezone.utc)
        await user.save()
        logger.info(f"👑 Role updated: {user.email} → {new_role.value}")
        return user

    @staticmethod
    async def toggle_user_active(target_user_id: str, is_active: bool) -> UserDocument:
        """Activate/deactivate a user (superadmin only)."""
        user = await AuthService.get_user_by_id(target_user_id)
        user.is_active = is_active
        user.updated_at = datetime.now(timezone.utc)
        # Invalidate all sessions if deactivating
        if not is_active:
            user.refresh_tokens = []
        await user.save()
        logger.info(f"🔄 User {'activated' if is_active else 'deactivated'}: {user.email}")
        return user
