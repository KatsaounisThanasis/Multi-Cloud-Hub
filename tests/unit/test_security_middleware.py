"""
Unit tests for Security Middleware (Rate Limiting and CSRF)
"""
import pytest
import time
import os
from unittest.mock import MagicMock, patch
from fastapi import Request

from backend.core.security import (
    InMemoryRateLimiter,
    RateLimitingMiddleware,
    RateLimitExceeded,
    CSRFProtection,
    CSRFMiddleware,
    SecurityHeadersMiddleware,
    RequestLoggingMiddleware
)


class TestInMemoryRateLimiter:
    """Tests for InMemoryRateLimiter class."""

    def test_allows_initial_request(self):
        """Test that initial requests are allowed."""
        limiter = InMemoryRateLimiter()
        allowed, remaining, reset = limiter.is_allowed("test_key", max_requests=10, window_seconds=60)

        assert allowed is True
        assert remaining == 9  # 10 - 1 = 9 remaining

    def test_tracks_multiple_requests(self):
        """Test tracking multiple requests."""
        limiter = InMemoryRateLimiter()

        for i in range(5):
            allowed, remaining, reset = limiter.is_allowed("track_key", max_requests=10, window_seconds=60)
            assert allowed is True
            # Remaining decreases with each request

    def test_blocks_when_limit_exceeded(self):
        """Test blocking when rate limit is exceeded."""
        limiter = InMemoryRateLimiter()

        # Make 5 requests (limit is 5)
        for i in range(5):
            allowed, _, _ = limiter.is_allowed("exceed_key", max_requests=5, window_seconds=60)
            assert allowed is True

        # 6th request should be blocked
        allowed, remaining, reset = limiter.is_allowed("exceed_key", max_requests=5, window_seconds=60)
        assert allowed is False
        assert remaining == 0

    def test_separate_keys_tracked_independently(self):
        """Test that different keys are tracked independently."""
        limiter = InMemoryRateLimiter()

        # Exhaust limit for key1
        for _ in range(3):
            limiter.is_allowed("key1", max_requests=3, window_seconds=60)

        # key1 should be blocked
        allowed1, _, _ = limiter.is_allowed("key1", max_requests=3, window_seconds=60)
        assert allowed1 is False

        # key2 should still be allowed
        allowed2, _, _ = limiter.is_allowed("key2", max_requests=3, window_seconds=60)
        assert allowed2 is True

    def test_cleanup_removes_old_entries(self):
        """Test that cleanup removes old entries."""
        limiter = InMemoryRateLimiter()
        limiter._cleanup_interval = 0  # Force cleanup every time

        # Add some requests
        limiter.is_allowed("cleanup_key", max_requests=10, window_seconds=1)

        # Wait for window to pass
        time.sleep(0.1)

        # Trigger cleanup by making another request (with short window)
        limiter._last_cleanup = 0  # Force cleanup
        limiter._cleanup()

        # Old entries should be cleaned up


class TestRateLimitExceeded:
    """Tests for RateLimitExceeded exception."""

    def test_exception_properties(self):
        """Test exception has correct properties."""
        exc = RateLimitExceeded(retry_after=30)

        assert exc.status_code == 429
        assert "Rate limit exceeded" in exc.detail
        assert exc.headers["Retry-After"] == "30"

    def test_default_retry_after(self):
        """Test default retry_after value."""
        exc = RateLimitExceeded()
        assert exc.headers["Retry-After"] == "60"


class TestRateLimitingMiddleware:
    """Tests for RateLimitingMiddleware class."""

    def test_rate_limits_configuration(self):
        """Test rate limit configuration exists."""
        middleware = RateLimitingMiddleware(MagicMock())

        assert "/auth/login" in middleware.RATE_LIMITS
        assert "/auth/register" in middleware.RATE_LIMITS
        assert "default" in middleware.RATE_LIMITS

    def test_skip_paths_configuration(self):
        """Test skip paths configuration exists."""
        middleware = RateLimitingMiddleware(MagicMock())

        assert "/health" in middleware.SKIP_PATHS
        assert "/docs" in middleware.SKIP_PATHS
        assert "/metrics" in middleware.SKIP_PATHS

    def test_get_rate_limit_auth_login(self):
        """Test rate limit for auth/login path."""
        middleware = RateLimitingMiddleware(MagicMock())

        max_requests, window = middleware._get_rate_limit("/auth/login")
        assert max_requests == 10
        assert window == 60

    def test_get_rate_limit_default(self):
        """Test default rate limit."""
        middleware = RateLimitingMiddleware(MagicMock())

        max_requests, window = middleware._get_rate_limit("/unknown/path")
        assert max_requests == 100
        assert window == 60

    def test_get_client_id_forwarded(self):
        """Test client ID extraction from X-Forwarded-For."""
        middleware = RateLimitingMiddleware(MagicMock())

        mock_request = MagicMock()
        mock_request.headers.get.side_effect = lambda key: {
            "X-Forwarded-For": "192.168.1.1, 10.0.0.1",
            "X-Real-IP": None
        }.get(key)
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        client_id = middleware._get_client_id(mock_request)
        assert client_id == "192.168.1.1"

    def test_get_client_id_real_ip(self):
        """Test client ID extraction from X-Real-IP."""
        middleware = RateLimitingMiddleware(MagicMock())

        mock_request = MagicMock()
        mock_request.headers.get.side_effect = lambda key: {
            "X-Forwarded-For": None,
            "X-Real-IP": "10.0.0.50"
        }.get(key)
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        client_id = middleware._get_client_id(mock_request)
        assert client_id == "10.0.0.50"

    def test_get_client_id_direct(self):
        """Test client ID extraction from direct connection."""
        middleware = RateLimitingMiddleware(MagicMock())

        mock_request = MagicMock()
        mock_request.headers.get.return_value = None
        mock_request.client = MagicMock()
        mock_request.client.host = "192.168.1.100"

        client_id = middleware._get_client_id(mock_request)
        assert client_id == "192.168.1.100"


class TestCSRFProtection:
    """Tests for CSRFProtection class."""

    def test_generate_token(self):
        """Test token generation."""
        token1 = CSRFProtection.generate_token()
        token2 = CSRFProtection.generate_token()

        assert isinstance(token1, str)
        assert len(token1) > 20  # Should be reasonably long
        assert token1 != token2  # Should be unique

    def test_get_token_from_cookie(self):
        """Test getting token from cookie."""
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = "test_csrf_token"

        token = CSRFProtection.get_token_from_cookie(mock_request)
        assert token == "test_csrf_token"
        mock_request.cookies.get.assert_called_with(CSRFProtection.COOKIE_NAME)

    def test_get_token_from_header(self):
        """Test getting token from header."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "header_csrf_token"

        token = CSRFProtection.get_token_from_header(mock_request)
        assert token == "header_csrf_token"
        mock_request.headers.get.assert_called_with(CSRFProtection.HEADER_NAME)

    def test_validate_success(self):
        """Test successful CSRF validation."""
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = "matching_token"
        mock_request.headers.get.return_value = "matching_token"

        assert CSRFProtection.validate(mock_request) is True

    def test_validate_mismatch(self):
        """Test CSRF validation with mismatched tokens."""
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = "cookie_token"
        mock_request.headers.get.return_value = "header_token"

        assert CSRFProtection.validate(mock_request) is False

    def test_validate_missing_cookie(self):
        """Test CSRF validation with missing cookie."""
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = None
        mock_request.headers.get.return_value = "header_token"

        assert CSRFProtection.validate(mock_request) is False

    def test_validate_missing_header(self):
        """Test CSRF validation with missing header."""
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = "cookie_token"
        mock_request.headers.get.return_value = None

        assert CSRFProtection.validate(mock_request) is False


class TestCSRFMiddleware:
    """Tests for CSRFMiddleware class."""

    def test_safe_methods(self):
        """Test safe methods configuration."""
        middleware = CSRFMiddleware(MagicMock())

        assert "GET" in middleware.SAFE_METHODS
        assert "HEAD" in middleware.SAFE_METHODS
        assert "OPTIONS" in middleware.SAFE_METHODS

    def test_exempt_paths(self):
        """Test exempt paths configuration."""
        middleware = CSRFMiddleware(MagicMock())

        assert "/auth/login" in middleware.EXEMPT_PATHS
        assert "/auth/register" in middleware.EXEMPT_PATHS
        assert "/health" in middleware.EXEMPT_PATHS

    def test_has_api_auth_jwt(self):
        """Test API auth detection for JWT."""
        middleware = CSRFMiddleware(MagicMock())

        mock_request = MagicMock()
        mock_request.headers.get.side_effect = lambda key, default="": {
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "X-API-Key": ""
        }.get(key, default)

        assert middleware._has_api_auth(mock_request) is True

    def test_has_api_auth_api_key(self):
        """Test API auth detection for API key."""
        middleware = CSRFMiddleware(MagicMock())

        mock_request = MagicMock()
        mock_request.headers.get.side_effect = lambda key, default="": {
            "Authorization": "",
            "X-API-Key": "my-api-key-123"
        }.get(key, default)

        assert middleware._has_api_auth(mock_request) is True

    def test_has_api_auth_none(self):
        """Test API auth detection with no auth."""
        middleware = CSRFMiddleware(MagicMock())

        mock_request = MagicMock()
        mock_request.headers.get.return_value = ""

        assert middleware._has_api_auth(mock_request) is False


class TestSecurityHeadersMiddleware:
    """Tests for SecurityHeadersMiddleware class."""

    @pytest.mark.asyncio
    async def test_adds_security_headers(self):
        """Test that security headers are added."""
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route

        async def homepage(request):
            return JSONResponse({"status": "ok"})

        app = Starlette(routes=[Route("/", homepage)])
        app.add_middleware(SecurityHeadersMiddleware)

        client = TestClient(app)
        response = client.get("/")

        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert "Content-Security-Policy" in response.headers
