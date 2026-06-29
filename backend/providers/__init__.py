"""
Cloud Provider Abstraction Layer

This package provides a unified interface for deploying and managing
cloud resources across multiple cloud providers (Azure and GCP).
"""

from .base import CloudProvider, CloudResource, DeploymentResult, ProviderType, ResourceGroup
from .factory import ProviderFactory, get_provider
from .terraform_provider import TerraformProvider

__all__ = [
    "CloudProvider",
    "DeploymentResult",
    "ResourceGroup",
    "CloudResource",
    "ProviderType",
    "ProviderFactory",
    "get_provider",
    "TerraformProvider",
]
