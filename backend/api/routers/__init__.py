"""
API Routers Module

This module contains all the API routers split by domain:
- auth: Authentication and user management
- health: Health checks and system status
- templates: Template discovery and management
- deployments: Deployment creation, status, and management
- azure: Azure-specific dynamic options
- gcp: GCP-specific dynamic options
- resource_groups: Resource group management
"""

from .auth import router as auth_router
from .health import router as health_router
from .templates import router as templates_router
from .deployments import router as deployments_router
from .azure import router as azure_router
from .gcp import router as gcp_router
from .resource_groups import router as resource_groups_router
from .cloud_accounts import router as cloud_accounts_router

__all__ = [
    'auth_router',
    'health_router',
    'templates_router',
    'deployments_router',
    'azure_router',
    'gcp_router',
    'resource_groups_router',
    'cloud_accounts_router'
]
