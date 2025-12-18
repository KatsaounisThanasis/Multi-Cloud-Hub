"""
Custom Exception Classes for Multi-Cloud Infrastructure Management

This module defines a unified exception hierarchy for consistent error handling.
"""

from typing import Optional, Dict, Any


class MultiCloudException(Exception):
    """
    Base exception for all multi-cloud manager errors.

    Provides a consistent error structure across the application.
    """
    def __init__(
        self,
        message: str,
        code: str,
        details: Optional[str] = None,
        status_code: int = 500
    ):
        self.message = message
        self.code = code
        self.details = details
        self.status_code = status_code
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API response"""
        error_dict = {
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            error_dict["details"] = self.details
        return error_dict


# ================================================================
# Template Errors
# ================================================================

class TemplateNotFoundError(MultiCloudException):
    """Raised when a requested template cannot be found."""
    def __init__(self, template_name: str, provider: str):
        super().__init__(
            message=f"Template '{template_name}' not found for provider '{provider}'",
            code="TEMPLATE_NOT_FOUND",
            details=f"Available templates can be listed via GET /templates?provider={provider}",
            status_code=404
        )


# ================================================================
# Parameter Errors
# ================================================================

class InvalidParameterError(MultiCloudException):
    """Raised when template parameters are invalid."""
    def __init__(self, parameter_name: str, reason: str):
        super().__init__(
            message=f"Invalid parameter '{parameter_name}': {reason}",
            code="INVALID_PARAMETER",
            details=reason,
            status_code=400
        )


class MissingParameterError(MultiCloudException):
    """Raised when required parameters are missing."""
    def __init__(self, parameter_name: str):
        super().__init__(
            message=f"Required parameter '{parameter_name}' is missing",
            code="MISSING_PARAMETER",
            details=f"Please provide '{parameter_name}' in the request parameters",
            status_code=400
        )


# ================================================================
# Deployment Errors
# ================================================================

class DeploymentNotFoundError(MultiCloudException):
    """Raised when a deployment cannot be found."""
    def __init__(self, deployment_id: str):
        super().__init__(
            message=f"Deployment '{deployment_id}' not found",
            code="DEPLOYMENT_NOT_FOUND",
            details="The deployment may have been deleted or the ID is incorrect",
            status_code=404
        )


# ================================================================
# Validation Errors
# ================================================================

class ValidationError(MultiCloudException):
    """Raised when request validation fails."""
    def __init__(self, field: str, reason: str):
        super().__init__(
            message=f"Validation failed for field '{field}'",
            code="VALIDATION_ERROR",
            details=reason,
            status_code=422
        )
