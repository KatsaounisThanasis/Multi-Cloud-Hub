"""
Security Utilities and Middleware

This module provides security headers, CORS configuration,
rate limiting, CSRF protection, and other security-related utilities for the API.
"""

import os
import time
import secrets
import hashlib
from typing import Optional, List, Dict, Any
from collections import defaultdict
from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Rate Limiting
# =============================================================================

class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""
    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)}
        )


class InMemoryRateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.

    For production with multiple instances, use Redis-based rate limiting.
    """

    def __init__(self):
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._cleanup_interval = 60  # seconds
        self._last_cleanup = time.time()

    def _cleanup(self):
        """Remove old entries to prevent memory leaks."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        cutoff = now - 3600  # Remove entries older than 1 hour
        for key in list(self._requests.keys()):
            self._requests[key] = [t for t in self._requests[key] if t > cutoff]
            if not self._requests[key]:
                del self._requests[key]

        self._last_cleanup = now

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int, int]:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Identifier (IP address, user ID, etc.)
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, remaining_requests, reset_time)
        """
        self._cleanup()

        now = time.time()
        window_start = now - window_seconds

        # Filter to requests within window
        self._requests[key] = [t for t in self._requests[key] if t > window_start]

        current_count = len(self._requests[key])
        remaining = max(0, max_requests - current_count)
        reset_time = int(window_start + window_seconds)

        if current_count >= max_requests:
            return False, 0, reset_time

        # Record this request
        self._requests[key].append(now)
        return True, remaining - 1, reset_time


# Global rate limiter instance
_rate_limiter = InMemoryRateLimiter()


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce rate limiting on API requests.

    Configurable limits:
    - General API: 100 requests per minute
    - Authentication: 10 requests per minute (stricter for brute force protection)
    - Deployment: 20 requests per minute
    """

    # Rate limit configurations per path prefix
    RATE_LIMITS = {
        "/auth/login": (10, 60),      # 10 requests per minute - anti brute force
        "/auth/register": (5, 60),     # 5 requests per minute - anti spam
        "/deploy": (20, 60),           # 20 requests per minute
        "/api/deploy": (20, 60),       # 20 requests per minute
        "default": (100, 60),          # 100 requests per minute
    }

    # Paths to skip rate limiting
    SKIP_PATHS = ["/health", "/docs", "/redoc", "/openapi.json", "/metrics"]

    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting to request."""
        # Skip rate limiting if disabled
        if not os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true":
            return await call_next(request)

        path = request.url.path

        # Skip certain paths
        if any(path.startswith(skip) for skip in self.SKIP_PATHS):
            return await call_next(request)

        # Get client identifier (IP or user ID)
        client_id = self._get_client_id(request)

        # Determine rate limit for this path
        max_requests, window = self._get_rate_limit(path)

        # Check rate limit
        key = f"{client_id}:{path.split('/')[1] if '/' in path else 'default'}"
        allowed, remaining, reset_time = _rate_limiter.is_allowed(key, max_requests, window)

        if not allowed:
            logger.warning(f"Rate limit exceeded for {client_id} on {path}")
            raise RateLimitExceeded(retry_after=window)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from request."""
        # Check for X-Forwarded-For header (behind proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Check for X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"

    def _get_rate_limit(self, path: str) -> tuple[int, int]:
        """Get rate limit configuration for path."""
        for prefix, limits in self.RATE_LIMITS.items():
            if prefix != "default" and path.startswith(prefix):
                return limits
        return self.RATE_LIMITS["default"]


# =============================================================================
# CSRF Protection
# =============================================================================

class CSRFProtection:
    """
    CSRF protection using double-submit cookie pattern.

    - Generates a CSRF token and stores it in a cookie
    - Validates that the token in the header matches the cookie
    - Safe methods (GET, HEAD, OPTIONS) are exempt
    """

    COOKIE_NAME = "csrf_token"
    HEADER_NAME = "X-CSRF-Token"
    TOKEN_LENGTH = 32

    @classmethod
    def generate_token(cls) -> str:
        """Generate a cryptographically secure CSRF token."""
        return secrets.token_urlsafe(cls.TOKEN_LENGTH)

    @classmethod
    def get_token_from_cookie(cls, request: Request) -> Optional[str]:
        """Get CSRF token from cookie."""
        return request.cookies.get(cls.COOKIE_NAME)

    @classmethod
    def get_token_from_header(cls, request: Request) -> Optional[str]:
        """Get CSRF token from header."""
        return request.headers.get(cls.HEADER_NAME)

    @classmethod
    def validate(cls, request: Request) -> bool:
        """Validate CSRF token."""
        cookie_token = cls.get_token_from_cookie(request)
        header_token = cls.get_token_from_header(request)

        if not cookie_token or not header_token:
            return False

        # Constant-time comparison to prevent timing attacks
        return secrets.compare_digest(cookie_token, header_token)


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce CSRF protection.

    - Sets CSRF cookie on all responses
    - Validates CSRF token on state-changing requests (POST, PUT, DELETE, PATCH)
    - API endpoints can be exempt if they use other auth (e.g., API keys, JWT)
    """

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

    # Paths exempt from CSRF (API endpoints using JWT/API key auth)
    EXEMPT_PATHS = [
        "/auth",
        "/health",
        "/docs",
        "/templates",
        "/deploy",
        "/api",
        "/redoc",
        "/openapi.json",
        "/metrics",
    ]

    async def dispatch(self, request: Request, call_next):
        """Apply CSRF protection."""
        # Skip CSRF protection if disabled
        if not os.getenv("CSRF_PROTECTION_ENABLED", "true").lower() == "true":
            return await call_next(request)

        path = request.url.path
        method = request.method

        # Safe methods don't need CSRF validation
        if method in self.SAFE_METHODS:
            response = await call_next(request)
            self._set_csrf_cookie(response)
            return response

        # Check exempt paths
        if any(path.startswith(exempt) for exempt in self.EXEMPT_PATHS):
            response = await call_next(request)
            self._set_csrf_cookie(response)
            return response

        # Check for API key or JWT auth (exempt from CSRF)
        if self._has_api_auth(request):
            response = await call_next(request)
            self._set_csrf_cookie(response)
            return response

        # Validate CSRF token
        if not CSRFProtection.validate(request):
            logger.warning(f"CSRF validation failed for {method} {path}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token missing or invalid"
            )

        response = await call_next(request)
        self._set_csrf_cookie(response)
        return response

    def _set_csrf_cookie(self, response: Response):
        """Set CSRF token cookie on response."""
        # Only set if not already present
        token = CSRFProtection.generate_token()
        response.set_cookie(
            key=CSRFProtection.COOKIE_NAME,
            value=token,
            httponly=False,  # JavaScript needs to read this
            secure=os.getenv("ENVIRONMENT", "development") == "production",
            samesite="strict",
            max_age=3600  # 1 hour
        )

    def _has_api_auth(self, request: Request) -> bool:
        """Check if request has API authentication (exempt from CSRF)."""
        # Check for Authorization header (JWT)
        if request.headers.get("Authorization", "").startswith("Bearer "):
            return True

        # Check for API key
        if request.headers.get("X-API-Key"):
            return True

        return False


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Headers added:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security: max-age=31536000; includeSubDomains
    - Content-Security-Policy: default-src 'self'
    - Referrer-Policy: strict-origin-when-cross-origin
    """

    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Enable XSS filter
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Force HTTPS (only in production)
        if os.getenv("ENVIRONMENT", "development") == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self';"
        )

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Remove server header (if exists)
        if "Server" in response.headers:
            del response.headers["Server"]

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all incoming requests.

    Logs:
    - Request method and path
    - Client IP address
    - User agent
    - Response status code
    - Request duration
    """

    async def dispatch(self, request: Request, call_next):
        """Log request details."""
        import time

        # Get client info
        client_host = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For", "")
        user_agent = request.headers.get("User-Agent", "")

        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"from {forwarded_for or client_host}"
        )

        # Process request and measure time
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        # Log response
        logger.info(
            f"Response: {response.status_code} for {request.method} {request.url.path} "
            f"({duration:.3f}s)"
        )

        # Add custom header with request duration
        response.headers["X-Request-Duration"] = f"{duration:.3f}s"

        return response


def get_cors_config() -> dict:
    """
    Get CORS configuration from environment variables.

    Environment variables:
    - CORS_ORIGINS: Comma-separated list of allowed origins (default: *)
    - CORS_CREDENTIALS: Allow credentials (default: true)
    - CORS_METHODS: Allowed methods (default: *)
    - CORS_HEADERS: Allowed headers (default: *)

    Returns:
        Dictionary with CORS configuration
    """
    origins_str = os.getenv("CORS_ORIGINS", "*")

    # Parse origins
    if origins_str == "*":
        origins = ["*"]
    else:
        origins = [origin.strip() for origin in origins_str.split(",")]

    credentials = os.getenv("CORS_CREDENTIALS", "true").lower() == "true"
    methods_str = os.getenv("CORS_METHODS", "*")
    headers_str = os.getenv("CORS_HEADERS", "*")

    methods = ["*"] if methods_str == "*" else [m.strip() for m in methods_str.split(",")]
    headers = ["*"] if headers_str == "*" else [h.strip() for h in headers_str.split(",")]

    logger.info(f"CORS configuration: origins={origins}, credentials={credentials}")

    return {
        "allow_origins": origins,
        "allow_credentials": credentials,
        "allow_methods": methods,
        "allow_headers": headers,
        "expose_headers": [
            "X-Request-Duration",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset"
        ],
        "max_age": 3600,  # Cache preflight requests for 1 hour
    }


def get_trusted_hosts() -> Optional[List[str]]:
    """
    Get list of trusted hosts from environment.

    Environment variables:
    - TRUSTED_HOSTS: Comma-separated list of trusted hosts

    Returns:
        List of trusted hosts or None to disable host validation
    """
    hosts_str = os.getenv("TRUSTED_HOSTS", "")

    if not hosts_str:
        # No host validation in development
        if os.getenv("ENVIRONMENT", "development") == "development":
            return None
        # In production, at least validate localhost
        return ["localhost", "127.0.0.1"]

    hosts = [host.strip() for host in hosts_str.split(",")]
    logger.info(f"Trusted hosts: {hosts}")
    return hosts


def validate_deployment_parameters(parameters: dict) -> tuple[bool, Optional[str]]:
    """
    Validate deployment parameters for security issues.

    Checks for:
    - Command injection attempts
    - Path traversal attempts
    - Excessive parameter sizes
    - Dangerous parameter names

    Args:
        parameters: Deployment parameters to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    import re

    # Dangerous patterns for general parameters
    dangerous_patterns = [
        (r'[;&|`]', "shell metacharacters (;, &, |, `)"),  # Shell metacharacters (excluding $ for passwords)
        (r'\.\./|\.\.\\', "path traversal patterns (../)"),  # Path traversal
        (r'<script', "script tags"),  # XSS attempts
        (r'DROP\s+TABLE', "SQL injection patterns"),  # SQL injection attempts
        (r'eval\s*\(', "code execution patterns"),  # Code execution
    ]

    # Parameters that are allowed to have special characters (like $ for passwords)
    # These are only checked for the most dangerous patterns
    sensitive_param_patterns = ['password', 'secret', 'key', 'token', 'credential']

    # Maximum sizes
    MAX_PARAM_NAME_LENGTH = 100
    MAX_PARAM_VALUE_LENGTH = 10000
    MAX_PARAMS_COUNT = 100

    # Check parameter count
    if len(parameters) > MAX_PARAMS_COUNT:
        return False, f"Too many parameters (max: {MAX_PARAMS_COUNT})"

    for key, value in parameters.items():
        # Check parameter name length
        if len(key) > MAX_PARAM_NAME_LENGTH:
            return False, f"Parameter name too long: {key[:50]}..."

        # Check for sensitive parameter names (warning only)
        key_lower = key.lower()
        is_sensitive_param = any(pattern in key_lower for pattern in sensitive_param_patterns)
        if is_sensitive_param:
            logger.debug(f"Sensitive parameter detected: {key}")

        # Convert value to string for checking
        value_str = str(value)

        # Check value length
        if len(value_str) > MAX_PARAM_VALUE_LENGTH:
            return False, f"Parameter value too long for '{key}'"

        # For sensitive params (passwords etc), only check the most dangerous patterns
        # Skip shell metacharacter check since passwords need special chars like $ ! @ #
        if is_sensitive_param:
            restricted_patterns = [
                (r'\.\./|\.\.\\', "path traversal patterns (../)"),
                (r'<script', "script tags"),
                (r'DROP\s+TABLE', "SQL injection patterns"),
                (r'eval\s*\(', "code execution patterns"),
            ]
            for pattern, description in restricted_patterns:
                if re.search(pattern, value_str, re.IGNORECASE):
                    return False, f"Invalid content in '{key}': contains {description}"
        else:
            # For non-sensitive params, check all dangerous patterns
            for pattern, description in dangerous_patterns:
                if re.search(pattern, value_str, re.IGNORECASE):
                    return False, f"Invalid content in '{key}': contains {description}"

    return True, None


def mask_sensitive_data(data: dict) -> dict:
    """
    Mask sensitive data in dictionaries for logging.

    Args:
        data: Dictionary potentially containing sensitive data

    Returns:
        Dictionary with sensitive values masked
    """
    import copy

    # Sensitive keys to mask
    sensitive_keys = [
        'password', 'secret', 'token', 'api_key', 'private_key',
        'client_secret', 'access_token', 'refresh_token',
        'credentials', 'auth', 'authorization'
    ]

    masked = copy.deepcopy(data)

    def mask_dict(d):
        """Recursively mask sensitive keys."""
        if not isinstance(d, dict):
            return d

        for key, value in d.items():
            key_lower = key.lower()

            # Check if key is sensitive
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                if isinstance(value, str) and len(value) > 4:
                    # Show first and last 2 characters
                    d[key] = value[:2] + "***" + value[-2:]
                else:
                    d[key] = "***"
            elif isinstance(value, dict):
                # Recursively mask nested dictionaries
                d[key] = mask_dict(value)
            elif isinstance(value, list):
                # Handle lists of dictionaries
                d[key] = [mask_dict(item) if isinstance(item, dict) else item for item in value]

        return d

    return mask_dict(masked)


class SecurityConfig:
    """
    Central security configuration.

    Loads security settings from environment variables
    and provides a unified interface for security features.
    """

    def __init__(self):
        """Initialize security configuration."""
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"

        # Authentication
        self.auth_enabled = os.getenv("API_AUTH_ENABLED", "false").lower() == "true"
        self.api_key = os.getenv("API_KEY", "")

        # Rate limiting
        self.rate_limit_enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
        self.rate_limit_requests = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))

        # CORS
        self.cors_origins = os.getenv("CORS_ORIGINS", "*")

        # Trusted hosts
        self.trusted_hosts = get_trusted_hosts()

        # Key vault (for production)
        self.use_key_vault = os.getenv("USE_KEY_VAULT", "false").lower() == "true"
        self.key_vault_url = os.getenv("KEY_VAULT_URL", "")

        self._log_config()

    def _log_config(self):
        """Log security configuration (without sensitive data)."""
        logger.info("=" * 60)
        logger.info("Security Configuration:")
        logger.info(f"  Environment: {self.environment}")
        logger.info(f"  Debug Mode: {self.debug}")
        logger.info(f"  Authentication: {'Enabled' if self.auth_enabled else 'Disabled'}")
        logger.info(f"  Rate Limiting: {'Enabled' if self.rate_limit_enabled else 'Disabled'}")
        logger.info(f"  CORS Origins: {self.cors_origins}")
        logger.info(f"  Key Vault: {'Enabled' if self.use_key_vault else 'Disabled'}")
        logger.info("=" * 60)

    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"


# Global security configuration
security_config = SecurityConfig()
