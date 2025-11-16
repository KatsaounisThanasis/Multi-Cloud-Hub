"""
Azure Native Provider Implementation

This provider uses Azure Bicep templates and Azure SDK for Python
to manage Azure resources natively.
"""

import os
import json
import logging
import subprocess
import shutil
from typing import Dict, List, Any, Optional
from datetime import datetime

from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError

from .base import (
    CloudProvider,
    ProviderType,
    DeploymentResult,
    DeploymentStatus,
    ResourceGroup,
    CloudResource,
    DeploymentError,
    ProviderConfigurationError
)

logger = logging.getLogger(__name__)


class AzureNativeProvider(CloudProvider):
    """
    Azure native implementation using Bicep templates and Azure SDK.

    This provider supports:
    - Bicep template compilation and deployment
    - ARM template deployment
    - Resource group management
    - Resource listing and management
    """

    def __init__(self, subscription_id: Optional[str] = None, region: Optional[str] = None):
        """
        Initialize Azure provider.

        Args:
            subscription_id: Azure subscription ID
            region: Default Azure region (e.g., 'eastus', 'westeurope')
        """
        super().__init__(subscription_id, region)

        try:
            self.credential = DefaultAzureCredential()
            logger.info("Azure credentials initialized successfully")
        except Exception as e:
            raise ProviderConfigurationError(
                f"Failed to initialize Azure credentials: {str(e)}",
                provider="azure"
            )

        if subscription_id:
            self.resource_client = ResourceManagementClient(
                self.credential,
                subscription_id
            )
        else:
            self.resource_client = None
            logger.warning("No subscription ID provided. Some operations may fail.")

    def _ensure_client(self):
        """Ensure resource client is initialized."""
        if not self.resource_client:
            raise ProviderConfigurationError(
                "Resource client not initialized. Please provide a subscription_id.",
                provider="azure"
            )

    def _get_azure_cli_path(self) -> str:
        """Get path to Azure CLI executable."""
        az_path = shutil.which('az')
        if not az_path:
            # Try common Windows locations
            az_path = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
            if not os.path.exists(az_path):
                az_path = r"C:\Program Files (x86)\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
                if not os.path.exists(az_path):
                    raise ProviderConfigurationError(
                        "Azure CLI not found. Please ensure it is installed and in your PATH.",
                        provider="azure"
                    )
        return az_path

    def _run_azure_cli_command(self, command: List[str]) -> tuple[Any, int]:
        """
        Execute an Azure CLI command.

        Args:
            command: Command arguments (without 'az' prefix)

        Returns:
            Tuple of (output, return_code)
        """
        try:
            az_path = self._get_azure_cli_path()
            full_command = [az_path]

            if command[0] == 'bicep':
                full_command.append('bicep')
                full_command.extend(command[1:])
            else:
                if self.subscription_id:
                    full_command.extend(["--subscription", self.subscription_id])
                full_command.extend(command)

            logger.info(f"Running Azure CLI command: {' '.join(full_command)}")
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                shell=False
            )

            if result.stdout:
                logger.debug(f"Azure CLI stdout: {result.stdout.strip()}")
            if result.stderr:
                logger.warning(f"Azure CLI stderr: {result.stderr.strip()}")

            if result.returncode == 0 and result.stdout.strip():
                stdout_str = result.stdout.strip()
                # Try to parse as JSON
                for start_char, end_char in [('[', ']'), ('{', '}')]:
                    start_idx = stdout_str.find(start_char)
                    end_idx = stdout_str.rfind(end_char)
                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        json_string = stdout_str[start_idx:end_idx + 1]
                        try:
                            return json.loads(json_string), result.returncode
                        except json.JSONDecodeError:
                            continue
                return stdout_str, result.returncode
            else:
                return result.stderr.strip(), result.returncode

        except Exception as e:
            logger.error(f"Error executing Azure CLI command: {e}")
            raise DeploymentError(
                f"Azure CLI command failed: {str(e)}",
                provider="azure"
            )

    def _compile_bicep_template(self, template_path: str) -> Dict[str, Any]:
        """
        Compile Bicep template to ARM JSON.

        Args:
            template_path: Path to .bicep file

        Returns:
            Compiled ARM template as dict
        """
        build_command = ['bicep', 'build', '--file', template_path, '--stdout']
        arm_output, returncode = self._run_azure_cli_command(build_command)

        if returncode != 0:
            raise DeploymentError(
                f"Failed to compile Bicep template: {template_path}",
                provider="azure",
                details={"returncode": returncode, "output": arm_output}
            )

        # Parse JSON output
        if isinstance(arm_output, dict):
            return arm_output
        elif isinstance(arm_output, str):
            # If output contains WARNING, extract JSON part
            if "WARNING:" in arm_output:
                # Find JSON start (after warnings)
                json_start = arm_output.find('{')
                if json_start != -1:
                    arm_output = arm_output[json_start:]

            try:
                return json.loads(arm_output)
            except json.JSONDecodeError as e:
                raise DeploymentError(
                    f"Failed to parse Bicep compilation output: {str(e)}",
                    provider="azure",
                    details={"output": arm_output[:500]}  # First 500 chars for debugging
                )

        return arm_output

    async def deploy(
        self,
        template_path: str,
        parameters: Dict[str, Any],
        resource_group: str,
        location: str,
        deployment_name: Optional[str] = None,
        deployment_id: Optional[str] = None
    ) -> DeploymentResult:
        """Deploy a Bicep or ARM template to Azure."""
        self._ensure_client()

        # Create resource group if it doesn't exist
        try:
            self.resource_client.resource_groups.create_or_update(
                resource_group,
                {"location": location}
            )
            logger.info(f"Resource group '{resource_group}' created/verified")
        except Exception as e:
            raise DeploymentError(
                f"Failed to create/verify resource group: {str(e)}",
                provider="azure"
            )

        # Compile Bicep template if needed
        if template_path.endswith('.bicep'):
            arm_template = self._compile_bicep_template(template_path)
        else:
            # Load ARM template directly
            try:
                with open(template_path, 'r') as f:
                    arm_template = json.load(f)
            except Exception as e:
                raise DeploymentError(
                    f"Failed to load ARM template: {str(e)}",
                    provider="azure"
                )

        # Format parameters for Azure
        azure_parameters = {"location": {"value": location}}
        template_params = arm_template.get("parameters", {})

        for param_name, param_value in parameters.items():
            if param_value is not None:
                # Unwrap nested {"value": ...} structures
                actual_value = param_value
                while isinstance(actual_value, dict) and "value" in actual_value:
                    actual_value = actual_value["value"]

                # Type conversion based on template definition
                param_def = template_params.get(param_name, {})
                expected_type = param_def.get("type", "").lower()

                try:
                    if expected_type == "array":
                        if isinstance(actual_value, str):
                            try:
                                actual_value = json.loads(actual_value)
                                if not isinstance(actual_value, list):
                                    actual_value = [actual_value]
                            except json.JSONDecodeError:
                                actual_value = [item.strip() for item in actual_value.split(",")] if "," in actual_value else [actual_value]
                        elif not isinstance(actual_value, list):
                            actual_value = [actual_value]
                    elif expected_type == "object":
                        if isinstance(actual_value, str):
                            try:
                                actual_value = json.loads(actual_value)
                            except json.JSONDecodeError:
                                actual_value = {}
                    elif expected_type == "bool":
                        if isinstance(actual_value, str):
                            actual_value = actual_value.lower() in ("true", "yes", "1", "on")
                        else:
                            actual_value = bool(actual_value)
                    elif expected_type == "int":
                        actual_value = int(actual_value) if actual_value != "" else 0
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to convert parameter '{param_name}': {str(e)}")

                azure_parameters[param_name] = {"value": actual_value}

        # Generate deployment name
        if not deployment_name:
            deployment_name = f"deployment-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        deployment_properties = {
            "template": arm_template,
            "parameters": azure_parameters,
            "mode": "Incremental"
        }

        # Execute deployment
        try:
            deployment = self.resource_client.deployments.begin_create_or_update(
                resource_group,
                deployment_name,
                {"properties": deployment_properties}
            ).result()

            logger.info(f"Deployment '{deployment_name}' completed successfully")

            return DeploymentResult(
                deployment_id=deployment.id,
                status=DeploymentStatus.SUCCEEDED,
                resource_group=resource_group,
                resources_created=[],  # Azure SDK doesn't provide this directly
                message=f"Deployment completed successfully",
                outputs=deployment.properties.outputs if hasattr(deployment.properties, 'outputs') else None,
                timestamp=datetime.now(),
                provider_metadata={
                    "deployment_name": deployment_name,
                    "provisioning_state": deployment.properties.provisioning_state
                }
            )

        except Exception as e:
            logger.error(f"Deployment failed: {str(e)}")
            raise DeploymentError(
                f"Deployment failed: {str(e)}",
                provider="azure",
                details={
                    "deployment_name": deployment_name,
                    "resource_group": resource_group
                }
            )

    async def get_deployment_status(
        self,
        deployment_id: str,
        resource_group: str
    ) -> DeploymentStatus:
        """Get deployment status."""
        self._ensure_client()

        try:
            # Extract deployment name from ID
            deployment_name = deployment_id.split('/')[-1]
            deployment = self.resource_client.deployments.get(
                resource_group,
                deployment_name
            )

            state = deployment.properties.provisioning_state.lower()
            status_map = {
                "succeeded": DeploymentStatus.SUCCEEDED,
                "failed": DeploymentStatus.FAILED,
                "canceled": DeploymentStatus.CANCELLED,
                "running": DeploymentStatus.IN_PROGRESS,
                "accepted": DeploymentStatus.IN_PROGRESS
            }

            return status_map.get(state, DeploymentStatus.PENDING)

        except Exception as e:
            logger.error(f"Failed to get deployment status: {str(e)}")
            return DeploymentStatus.FAILED

    async def list_resource_groups(self) -> List[ResourceGroup]:
        """List all resource groups."""
        self._ensure_client()

        try:
            groups = list(self.resource_client.resource_groups.list())
            return [
                ResourceGroup(
                    name=group.name,
                    location=group.location,
                    tags=group.tags,
                    resource_count=0,  # We could enhance this with a separate API call
                    provider_id=group.id
                )
                for group in groups
            ]
        except Exception as e:
            logger.error(f"Failed to list resource groups: {str(e)}")
            raise DeploymentError(
                f"Failed to list resource groups: {str(e)}",
                provider="azure"
            )

    async def create_resource_group(
        self,
        name: str,
        location: str,
        tags: Optional[Dict[str, str]] = None
    ) -> ResourceGroup:
        """Create a new resource group."""
        self._ensure_client()

        try:
            parameters = {"location": location}
            if tags:
                parameters["tags"] = tags

            rg = self.resource_client.resource_groups.create_or_update(name, parameters)

            logger.info(f"Resource group '{name}' created successfully")

            return ResourceGroup(
                name=rg.name,
                location=rg.location,
                tags=rg.tags,
                resource_count=0,
                provider_id=rg.id
            )

        except Exception as e:
            logger.error(f"Failed to create resource group: {str(e)}")
            raise DeploymentError(
                f"Failed to create resource group: {str(e)}",
                provider="azure"
            )

    async def delete_resource_group(self, name: str) -> bool:
        """Delete a resource group."""
        self._ensure_client()

        try:
            # Check if exists
            try:
                self.resource_client.resource_groups.get(name)
            except ResourceNotFoundError:
                logger.warning(f"Resource group '{name}' not found")
                return False

            # Initiate deletion
            delete_operation = self.resource_client.resource_groups.begin_delete(name)
            logger.info(f"Resource group '{name}' deletion initiated. Status: {delete_operation.status()}")

            return True

        except Exception as e:
            logger.error(f"Failed to delete resource group: {str(e)}")
            raise DeploymentError(
                f"Failed to delete resource group: {str(e)}",
                provider="azure"
            )

    async def list_resources(self, resource_group: str) -> List[CloudResource]:
        """List all resources in a resource group."""
        self._ensure_client()

        try:
            resources = list(self.resource_client.resources.list_by_resource_group(resource_group))

            return [
                CloudResource(
                    id=resource.id,
                    name=resource.name,
                    type=resource.type,
                    location=resource.location if hasattr(resource, 'location') else "",
                    resource_group=resource_group,
                    properties={},
                    tags=resource.tags if hasattr(resource, 'tags') else None
                )
                for resource in resources
            ]

        except Exception as e:
            logger.error(f"Failed to list resources: {str(e)}")
            raise DeploymentError(
                f"Failed to list resources: {str(e)}",
                provider="azure"
            )

    async def validate_template(
        self,
        template_path: str,
        parameters: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Validate a template."""
        try:
            if template_path.endswith('.bicep'):
                # Compile to validate
                self._compile_bicep_template(template_path)
            else:
                # Load ARM template
                with open(template_path, 'r') as f:
                    json.load(f)

            return True, None

        except Exception as e:
            return False, str(e)

    def get_supported_locations(self) -> List[str]:
        """Get supported Azure regions."""
        return [
            "eastus",
            "eastus2",
            "westus",
            "westus2",
            "westus3",
            "centralus",
            "northcentralus",
            "southcentralus",
            "northeurope",
            "westeurope",
            "uksouth",
            "ukwest",
            "francecentral",
            "francesouth",
            "germanywestcentral",
            "norwayeast",
            "switzerlandnorth",
            "swedencentral",
            "southeastasia",
            "eastasia",
            "australiaeast",
            "australiasoutheast",
            "japaneast",
            "japanwest",
            "koreacentral",
            "koreasouth",
            "canadacentral",
            "canadaeast",
            "brazilsouth",
            "southafricanorth",
            "uaenorth",
            "centralindia",
            "westindia",
            "southindia"
        ]

    def get_provider_type(self) -> ProviderType:
        """Get provider type."""
        return ProviderType.AZURE
