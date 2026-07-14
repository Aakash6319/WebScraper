"""
AutoWebAgent - Custom Exceptions
===================================
Domain-specific exceptions for clean error handling across the app.
"""

from typing import Optional, Any


class AutoWebAgentException(Exception):
    """Base exception for all AutoWebAgent errors."""

    def __init__(
        self,
        message: str = "An error occurred",
        status_code: int = 500,
        detail: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(self.message)


# ── Auth Exceptions ──────────────────────────────────────────────

class AuthenticationError(AutoWebAgentException):
    """Invalid credentials or token."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message=message, status_code=401)


class AuthorizationError(AutoWebAgentException):
    """Insufficient permissions."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message=message, status_code=403)


class UserNotFoundError(AutoWebAgentException):
    """User does not exist."""

    def __init__(self, user_id: str = ""):
        super().__init__(
            message=f"User not found: {user_id}" if user_id else "User not found",
            status_code=404,
        )


class UserAlreadyExistsError(AutoWebAgentException):
    """Email already registered."""

    def __init__(self, email: str = ""):
        super().__init__(
            message=f"User already exists: {email}" if email else "User already exists",
            status_code=409,
        )


# ── Session Exceptions ───────────────────────────────────────────

class SessionNotFoundError(AutoWebAgentException):
    """Browser session not found."""

    def __init__(self, session_id: str = ""):
        super().__init__(
            message=f"Session not found: {session_id}" if session_id else "Session not found",
            status_code=404,
        )


class SessionLimitExceededError(AutoWebAgentException):
    """User has too many active sessions."""

    def __init__(self, limit: int = 5):
        super().__init__(
            message=f"Session limit exceeded (max {limit})",
            status_code=429,
        )


class BrowserLaunchError(AutoWebAgentException):
    """Failed to launch browser."""

    def __init__(self, reason: str = ""):
        super().__init__(
            message=f"Failed to launch browser: {reason}",
            status_code=500,
        )


# ── Agent Exceptions ─────────────────────────────────────────────

class AgentExecutionError(AutoWebAgentException):
    """Agent failed to execute a task."""

    def __init__(self, task_id: str = "", reason: str = ""):
        super().__init__(
            message=f"Agent execution failed for task {task_id}: {reason}",
            status_code=500,
        )


class CaptchaSolveError(AutoWebAgentException):
    """CAPTCHA could not be solved."""

    def __init__(self, captcha_type: str = "", reason: str = ""):
        super().__init__(
            message=f"Failed to solve {captcha_type} CAPTCHA: {reason}",
            status_code=422,
        )


class StealthConfigurationError(AutoWebAgentException):
    """Stealth / fingerprint setup failed."""

    def __init__(self, reason: str = ""):
        super().__init__(
            message=f"Stealth configuration error: {reason}",
            status_code=500,
        )


# ── Proxy Exceptions ─────────────────────────────────────────────

class ProxyError(AutoWebAgentException):
    """Proxy connection or configuration error."""

    def __init__(self, reason: str = ""):
        super().__init__(
            message=f"Proxy error: {reason}",
            status_code=502,
        )


class ProxyNotConfiguredError(AutoWebAgentException):
    """No proxy credentials available."""

    def __init__(self):
        super().__init__(
            message="No proxy configured. Add Webshare credentials.",
            status_code=400,
        )


# ── Task Exceptions ──────────────────────────────────────────────

class TaskNotFoundError(AutoWebAgentException):
    """Task not found in database."""

    def __init__(self, task_id: str = ""):
        super().__init__(
            message=f"Task not found: {task_id}" if task_id else "Task not found",
            status_code=404,
        )


class TaskExecutionTimeoutError(AutoWebAgentException):
    """Task took too long to complete."""

    def __init__(self, timeout_seconds: int = 300):
        super().__init__(
            message=f"Task timed out after {timeout_seconds}s",
            status_code=408,
        )


# ── Website Exceptions ───────────────────────────────────────────

class WebsiteNotFoundError(AutoWebAgentException):
    """Website configuration not found."""

    def __init__(self, website_id: str = ""):
        super().__init__(
            message=f"Website not found: {website_id}" if website_id else "Website not found",
            status_code=404,
        )


# ── Rate Limiting ────────────────────────────────────────────────

class RateLimitExceededError(AutoWebAgentException):
    """Too many requests."""

    def __init__(self, retry_after: int = 60):
        super().__init__(
            message=f"Rate limit exceeded. Retry after {retry_after}s",
            status_code=429,
            detail={"retry_after": retry_after},
        )


# ── Validation ──────────────────────────────────────────────────

class ValidationError(AutoWebAgentException):
    """Invalid input data."""

    def __init__(self, message: str = "Validation error", errors: Optional[list] = None):
        super().__init__(
            message=message,
            status_code=422,
            detail={"errors": errors or []},
        )
