"""
API Authentication and Authorization Module

This module provides API key authentication, role-based access control,
and security utilities for the Multi-Cloud Infrastructure API.
"""

import os
import secrets
import hashlib
from typing import Optional, List
from datetime import datetime, timedelta
from functools import wraps

from fastapi import HTTPException, Security, status, Depends, Request
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

import logging

logger = logging.getLogger(__name__)

# Security Schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticationError(Exception):
    """Raised when authentication fails"""
    pass


class AuthorizationError(Exception):
    """Raised when authorization fails"""
    pass


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for secure storage.

    Args:
        api_key: Plain text API key

    Returns:
        SHA-256 hash of the API key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key(length: int = 32) -> str:
    """
    Generate a secure random API key.

    Args:
        length: Length of the API key (default: 32)

    Returns:
        Secure random API key string
    """
    return secrets.token_urlsafe(length)


def verify_api_key(provided_key: str, stored_key_hash: str) -> bool:
    """
    Verify an API key against a stored hash.

    Args:
        provided_key: API key provided by the client
        stored_key_hash: Stored hash of the valid API key

    Returns:
        True if the key is valid, False otherwise
    """
    provided_hash = hash_api_key(provided_key)
    return secrets.compare_digest(provided_hash, stored_key_hash)


class APIKeyAuth:
    """
    API Key Authentication Handler

    Supports multiple authentication methods:
    - Environment variable (simple, for development)
    - Database (advanced, for production with multiple keys)
    - Header-based API key validation
    """

    def __init__(self, env_key: str = "API_KEY"):
        """
        Initialize API key authentication.

        Args:
            env_key: Environment variable name for the API key
        """
        self.env_key = env_key
        self.master_key = os.getenv(env_key)
        self.master_key_hash = hash_api_key(self.master_key) if self.master_key else None
        self.enabled = os.getenv("API_AUTH_ENABLED", "false").lower() == "true"

        if self.enabled and not self.master_key:
            logger.warning(
                f"API authentication enabled but {env_key} not set. "
                "All authenticated requests will fail!"
            )
        elif self.enabled:
            logger.info("API key authentication enabled")
        else:
            logger.info("API key authentication disabled (development mode)")

    def validate_key(self, api_key: Optional[str]) -> bool:
        """
        Validate an API key.

        Args:
            api_key: API key to validate

        Returns:
            True if valid, False otherwise
        """
        if not self.enabled:
            # Authentication disabled - allow all requests
            return True

        if not api_key:
            return False

        # Check against master key
        if self.master_key_hash:
            return verify_api_key(api_key, self.master_key_hash)

        return False

    async def __call__(self, api_key: Optional[str] = Security(api_key_header)) -> str:
        """
        FastAPI dependency for API key authentication.

        Args:
            api_key: API key from request header

        Returns:
            Validated API key

        Raises:
            HTTPException: If authentication fails
        """
        if not self.enabled:
            # Authentication disabled - allow request
            return "development"

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required. Provide X-API-Key header.",
                headers={"WWW-Authenticate": "ApiKey"},
            )

        if not self.validate_key(api_key):
            logger.warning(f"Invalid API key attempt from request")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )

        return api_key


# Global authentication handler
auth_handler = APIKeyAuth()


def require_auth(func):
    """
    Decorator to require authentication for a route.

    Usage:
        @app.get("/protected")
        @require_auth
        async def protected_route():
            return {"message": "Access granted"}
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Authentication is handled by FastAPI dependency injection
        return await func(*args, **kwargs)
    return wrapper


class RateLimiter:
    """
    Simple in-memory rate limiter.

    For production, consider using Redis-based rate limiting
    for distributed deployments.
    """

    def __init__(self, requests_per_minute: int = 60):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute per client
        """
        self.requests_per_minute = requests_per_minute
        self.requests: dict[str, List[datetime]] = {}
        self.enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"

        if self.enabled:
            logger.info(f"Rate limiting enabled: {requests_per_minute} requests/minute")
        else:
            logger.info("Rate limiting disabled")

    def _get_client_id(self, request: Request) -> str:
        """
        Get a unique identifier for the client.

        Args:
            request: FastAPI request object

        Returns:
            Client identifier (IP address or API key)
        """
        # Try to get API key first
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"key:{api_key[:8]}"  # Use first 8 chars for privacy

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"

        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"

    def _clean_old_requests(self, client_id: str):
        """Remove requests older than 1 minute."""
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)

        if client_id in self.requests:
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id]
                if req_time > cutoff
            ]

    def is_allowed(self, request: Request) -> tuple[bool, Optional[int]]:
        """
        Check if a request is allowed based on rate limits.

        Args:
            request: FastAPI request object

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        if not self.enabled:
            return True, None

        client_id = self._get_client_id(request)
        now = datetime.now()

        # Clean old requests
        self._clean_old_requests(client_id)

        # Initialize client if not exists
        if client_id not in self.requests:
            self.requests[client_id] = []

        # Check rate limit
        if len(self.requests[client_id]) >= self.requests_per_minute:
            # Calculate retry after
            oldest_request = min(self.requests[client_id])
            retry_after = int((oldest_request + timedelta(minutes=1) - now).total_seconds())
            return False, max(retry_after, 1)

        # Add current request
        self.requests[client_id].append(now)
        return True, None

    async def __call__(self, request: Request):
        """
        FastAPI dependency for rate limiting.

        Args:
            request: FastAPI request object

        Raises:
            HTTPException: If rate limit exceeded
        """
        is_allowed, retry_after = self.is_allowed(request)

        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded for client {self._get_client_id(request)}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)}
            )


# Global rate limiter (60 requests per minute)
rate_limiter = RateLimiter(requests_per_minute=60)


def get_current_user(api_key: str = Depends(auth_handler)) -> dict:
    """
    Get current authenticated user information.

    This is a placeholder that can be extended to return
    user details from a database.

    Args:
        api_key: Validated API key from auth_handler

    Returns:
        User information dictionary
    """
    return {
        "authenticated": True,
        "api_key": api_key[:8] + "..." if api_key != "development" else "dev",
        "role": "admin"  # Placeholder - extend with actual role system
    }
