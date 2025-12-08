"""
Shared API Schemas and Response Helpers

This module contains shared Pydantic models and helper functions
used across all API routers for consistent response formatting.
"""

from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime


# ==================== Response Models ====================

class StandardResponse(BaseModel):
    """
    Standard API response format used across all endpoints.

    All API endpoints should return responses in this format
    for consistency and ease of client-side handling.
    """
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ==================== Response Helpers ====================

def success_response(message: str, data: Any = None) -> StandardResponse:
    """
    Create a standardized success response.

    Args:
        message: Human-readable success message
        data: Response data (will be wrapped in dict if not already)

    Returns:
        StandardResponse with success=True
    """
    return StandardResponse(
        success=True,
        message=message,
        data=data if isinstance(data, dict) else {"result": data} if data is not None else None
    )


def error_response(
    message: str,
    details: Any = None,
    status_code: int = 500
) -> JSONResponse:
    """
    Create a standardized error response as JSONResponse.

    Args:
        message: Human-readable error message
        details: Additional error details
        status_code: HTTP status code

    Returns:
        JSONResponse with appropriate status code
    """
    response = StandardResponse(
        success=False,
        message=message,
        error={"details": details, "status_code": status_code}
    )
    return JSONResponse(
        status_code=status_code,
        content=response.dict()
    )


# ==================== Request Models ====================

class DeploymentRequest(BaseModel):
    """Request model for infrastructure deployments."""
    template_name: str = Field(..., description="Name of the template to deploy")
    provider_type: str = Field(..., description="Cloud provider: 'bicep', 'terraform-azure', or 'terraform-gcp'")
    subscription_id: Optional[str] = Field(None, description="Cloud subscription/project ID")
    resource_group: str = Field(..., description="Resource group/stack name")
    location: str = Field(..., description="Deployment region/location")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Template parameters")
    tags: List[str] = Field(default_factory=list, description="Tags for organizing deployments")


class ResourceGroupCreateRequest(BaseModel):
    """Request model for creating resource groups."""
    name: str = Field(..., description="Resource group/stack name")
    location: str = Field(..., description="Region/location")
    subscription_id: str = Field(..., description="Subscription/project ID")
    provider_type: str = Field(default="azure", description="Cloud provider")
    tags: Optional[Dict[str, str]] = Field(default=None, description="Tags/labels")
