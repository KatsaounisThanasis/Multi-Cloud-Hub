"""
Base Cloud API Client

Shared base class for Azure and GCP API clients.
Provides common functionality for HTTP requests, authentication, and error handling.
"""

import logging
import httpx
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseCloudAPIClient(ABC):
    """
    Abstract base class for cloud API clients.

    Provides common functionality for:
    - HTTP client management
    - Authentication token handling
    - Request headers construction
    - Error handling and logging
    """

    def __init__(self, timeout: float = 30.0):
        """
        Initialize base cloud API client.

        Args:
            timeout: HTTP request timeout in seconds
        """
        self.client = httpx.AsyncClient(timeout=timeout)
        self._credentials = None
        self.access_token: Optional[str] = None

    async def close(self):
        """Close HTTP client and release resources."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    @abstractmethod
    def _initialize_credentials(self):
        """
        Initialize cloud-specific credentials.
        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    def _get_access_token(self) -> Optional[str]:
        """
        Get or refresh access token.
        Must be implemented by subclasses.

        Returns:
            Access token string or None if unavailable
        """
        pass

    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Get authorization headers for API requests.

        Returns:
            Dict with Authorization header if token is available
        """
        headers = {"Content-Type": "application/json"}

        access_token = self._get_access_token()
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        return headers

    async def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        require_auth: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Make an HTTP request with error handling.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            url: Request URL
            params: Query parameters
            json_data: JSON body data
            headers: Additional headers (merged with auth headers)
            require_auth: Whether to include auth headers

        Returns:
            Response JSON or None on error
        """
        try:
            # Build headers
            request_headers = self._get_auth_headers() if require_auth else {"Content-Type": "application/json"}
            if headers:
                request_headers.update(headers)

            # Make request
            response = await self.client.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=request_headers
            )
            response.raise_for_status()

            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} error for {method} {url}: {e.response.text}")
            return None
        except httpx.HTTPError as e:
            logger.error(f"HTTP error for {method} {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error for {method} {url}: {e}")
            return None

    async def _get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        require_auth: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Convenience method for GET requests."""
        return await self._make_request("GET", url, params=params, require_auth=require_auth)

    async def _post(
        self,
        url: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        require_auth: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Convenience method for POST requests."""
        return await self._make_request("POST", url, params=params, json_data=json_data, require_auth=require_auth)

    async def _put(
        self,
        url: str,
        json_data: Optional[Dict[str, Any]] = None,
        require_auth: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Convenience method for PUT requests."""
        return await self._make_request("PUT", url, json_data=json_data, require_auth=require_auth)

    async def _delete(
        self,
        url: str,
        require_auth: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Convenience method for DELETE requests."""
        return await self._make_request("DELETE", url, require_auth=require_auth)

    @staticmethod
    def _format_timestamp() -> str:
        """Get current UTC timestamp in ISO format."""
        return datetime.utcnow().isoformat()

    def _log_api_call(self, operation: str, **kwargs):
        """Log API call with context."""
        context = ", ".join(f"{k}={v}" for k, v in kwargs.items() if v)
        logger.info(f"{operation}: {context}" if context else operation)
