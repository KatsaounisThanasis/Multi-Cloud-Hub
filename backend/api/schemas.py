"""
Shared API Schemas and Response Helpers

This module contains shared Pydantic models and helper functions
used across all API routers for consistent response formatting.
"""

from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, Optional, List
from datetime import datetime
import re


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
    template_name: str = Field(..., description="Name of the template to deploy", min_length=1, max_length=100)
    provider_type: str = Field(..., description="Cloud provider: 'bicep', 'terraform-azure', or 'terraform-gcp'")
    subscription_id: Optional[str] = Field(None, description="Cloud subscription/project ID")
    resource_group: str = Field(..., description="Resource group/stack name", min_length=1, max_length=90)
    location: str = Field(..., description="Deployment region/location", min_length=1, max_length=50)
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Template parameters")
    tags: List[str] = Field(default_factory=list, description="Tags for organizing deployments")

    @field_validator('template_name')
    @classmethod
    def validate_template_name(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9\-_]*$', v):
            raise ValueError('Template name must start with letter, contain only alphanumerics, hyphens, underscores')
        return v

    @field_validator('resource_group')
    @classmethod
    def validate_resource_group(cls, v: str) -> str:
        if v.endswith('.'):
            raise ValueError('Resource group cannot end with a period')
        if not re.match(r'^[\w\-\.\(\)]+$', v):
            raise ValueError('Resource group can only contain alphanumerics, underscores, hyphens, periods, parentheses')
        return v

    @field_validator('provider_type')
    @classmethod
    def validate_provider_type(cls, v: str) -> str:
        allowed = ['bicep', 'terraform-azure', 'terraform-gcp', 'azure', 'gcp']
        if v.lower() not in allowed:
            raise ValueError(f'Provider must be one of: {", ".join(allowed)}')
        return v.lower()

    @field_validator('parameters')
    @classmethod
    def validate_parameters(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameters content dynamically."""
        # Import here to avoid circular imports
        from backend.utils.validators import validate_app_name, InvalidParameterError

        # Check for app_name or name in parameters
        for param in ['app_name', 'name']:
            if param in v:
                try:
                    validate_app_name(v[param], param)
                except InvalidParameterError as e:
                    # Convert internal exception to Pydantic validation error
                    raise ValueError(str(e))
        return v


class ResourceGroupCreateRequest(BaseModel):
    """Request model for creating resource groups."""
    name: str = Field(..., description="Resource group/stack name", min_length=1, max_length=90)
    location: str = Field(..., description="Region/location", min_length=1, max_length=50)
    subscription_id: str = Field(..., description="Subscription/project ID", min_length=1)
    provider_type: str = Field(default="azure", description="Cloud provider")
    tags: Optional[Dict[str, str]] = Field(default=None, description="Tags/labels")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if v.endswith('.'):
            raise ValueError('Name cannot end with a period')
        if not re.match(r'^[\w\-\.\(\)]+$', v):
            raise ValueError('Name can only contain alphanumerics, underscores, hyphens, periods, parentheses')
        return v
