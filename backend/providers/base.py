"""
Base classes and interfaces for cloud provider abstraction.

This module defines the abstract base class that all cloud providers must implement,
ensuring a consistent interface across Azure, GCP, and other cloud platforms.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ProviderType(Enum):
    """Supported cloud provider types."""
    AZURE = "azure"
    GCP = "gcp"
    TERRAFORM = "terraform"


class DeploymentStatus(Enum):
    """Deployment status states."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DeploymentResult:
    """
    Standard deployment result returned by all providers.

    Attributes:
        deployment_id: Unique identifier for the deployment
        status: Current status of the deployment
        resource_group: Name of the resource group/stack
        resources_created: List of resource IDs created
        message: Human-readable status message
        outputs: Deployment outputs (if any)
        timestamp: When the deployment was initiated
        provider_metadata: Provider-specific additional data
    """
    deployment_id: str
    status: DeploymentStatus
    resource_group: str
    resources_created: List[str]
    message: str
    outputs: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    provider_metadata: Optional[Dict[str, Any]] = None


@dataclass
class ResourceGroup:
    """
    Standard resource group representation across providers.

    Attributes:
        name: Resource group/stack name
        location: Geographic location/region
        tags: Key-value tags/labels
        resource_count: Number of resources in the group
        provider_id: Provider-specific identifier
    """
    name: str
    location: str
    tags: Optional[Dict[str, str]] = None
    resource_count: int = 0
    provider_id: Optional[str] = None


@dataclass
class CloudResource:
    """
    Standard cloud resource representation.

    Attributes:
        id: Unique resource identifier
        name: Resource name
        type: Resource type (e.g., VirtualMachine, StorageAccount, ComputeInstance)
        location: Geographic location
        resource_group: Parent resource group/stack
        properties: Resource-specific properties
        tags: Resource tags/labels
    """
    id: str
    name: str
    type: str
    location: str
    resource_group: str
    properties: Optional[Dict[str, Any]] = None
    tags: Optional[Dict[str, str]] = None


class CloudProvider(ABC):
    """
    Abstract base class for cloud provider implementations.

    All cloud providers (Azure, GCP) must implement this interface
    to ensure consistent behavior across the application.
    """

    def __init__(self, subscription_id: Optional[str] = None, region: Optional[str] = None):
        """
        Initialize the cloud provider.

        Args:
            subscription_id: Cloud subscription/account ID
            region: Default region for operations
        """
        self.subscription_id = subscription_id
        self.region = region

    @abstractmethod
    async def deploy(
        self,
        template_path: str,
        parameters: Dict[str, Any],
        resource_group: str,
        location: str,
        deployment_name: Optional[str] = None,
        deployment_id: Optional[str] = None
    ) -> DeploymentResult:
        """
        Deploy a template to the cloud provider.

        Args:
            template_path: Path to the template file
            parameters: Deployment parameters
            resource_group: Target resource group/stack name
            location: Deployment location/region
            deployment_name: Optional custom deployment name

        Returns:
            DeploymentResult with deployment details

        Raises:
            DeploymentError: If deployment fails
        """
        pass

    @abstractmethod
    async def get_deployment_status(
        self,
        deployment_id: str,
        resource_group: str
    ) -> DeploymentStatus:
        """
        Get the current status of a deployment.

        Args:
            deployment_id: Deployment identifier
            resource_group: Resource group/stack name

        Returns:
            Current deployment status
        """
        pass

    @abstractmethod
    async def list_resource_groups(self) -> List[ResourceGroup]:
        """
        List all resource groups/stacks in the subscription.

        Returns:
            List of ResourceGroup objects
        """
        pass

    @abstractmethod
    async def create_resource_group(
        self,
        name: str,
        location: str,
        tags: Optional[Dict[str, str]] = None
    ) -> ResourceGroup:
        """
        Create a new resource group/stack.

        Args:
            name: Resource group name
            location: Geographic location
            tags: Optional tags/labels

        Returns:
            Created ResourceGroup object
        """
        pass

    @abstractmethod
    async def delete_resource_group(self, name: str) -> bool:
        """
        Delete a resource group/stack and all contained resources.

        Args:
            name: Resource group/stack name

        Returns:
            True if deletion was initiated successfully
        """
        pass

    @abstractmethod
    async def list_resources(self, resource_group: str) -> List[CloudResource]:
        """
        List all resources within a resource group/stack.

        Args:
            resource_group: Resource group/stack name

        Returns:
            List of CloudResource objects
        """
        pass

    @abstractmethod
    async def validate_template(
        self,
        template_path: str,
        parameters: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate a template before deployment.

        Args:
            template_path: Path to the template file
            parameters: Deployment parameters

        Returns:
            Tuple of (is_valid, error_message)
        """
        pass

    @abstractmethod
    def get_supported_locations(self) -> List[str]:
        """
        Get list of supported regions/locations for this provider.

        Returns:
            List of location identifiers
        """
        pass

    @abstractmethod
    def get_provider_type(self) -> ProviderType:
        """
        Get the provider type.

        Returns:
            ProviderType enum value
        """
        pass

    def format_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format parameters for provider-specific requirements.

        This method can be overridden by providers that need special
        parameter formatting.

        Args:
            parameters: Raw parameters

        Returns:
            Formatted parameters
        """
        return parameters


class DeploymentError(Exception):
    """Exception raised when deployment operations fail."""

    def __init__(self, message: str, provider: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.provider = provider
        self.details = details or {}
        super().__init__(self.message)


class ProviderConfigurationError(Exception):
    """Exception raised when provider configuration is invalid."""

    def __init__(self, message: str, provider: str):
        self.message = message
        self.provider = provider
        super().__init__(self.message)
