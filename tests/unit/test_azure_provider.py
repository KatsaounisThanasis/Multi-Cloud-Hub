"""
Unit tests for Azure Native Provider
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime
from backend.providers.azure_native import AzureNativeProvider
from backend.providers.base import DeploymentResult, ResourceGroup, CloudResource


@pytest.fixture
def mock_azure_credentials():
    """Mock Azure credentials"""
    with patch('backend.providers.azure_native.DefaultAzureCredential') as mock_cred:
        mock_cred.return_value = Mock()
        yield mock_cred


@pytest.fixture
def mock_resource_client():
    """Mock Azure ResourceManagementClient"""
    with patch('backend.providers.azure_native.ResourceManagementClient') as mock_client:
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def azure_provider(mock_azure_credentials, mock_resource_client):
    """Create AzureNativeProvider instance with mocked dependencies"""
    provider = AzureNativeProvider(
        subscription_id="test-subscription-id",
        tenant_id="test-tenant-id"
    )
    return provider


class TestAzureNativeProvider:
    """Test cases for AzureNativeProvider"""

    def test_initialization(self, mock_azure_credentials, mock_resource_client):
        """Test provider initialization"""
        provider = AzureNativeProvider(
            subscription_id="test-sub-id",
            tenant_id="test-tenant-id"
        )

        assert provider.subscription_id == "test-sub-id"
        assert provider.tenant_id == "test-tenant-id"
        mock_azure_credentials.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_resource_groups(self, azure_provider, mock_resource_client):
        """Test listing resource groups"""
        # Mock resource groups
        mock_rg1 = Mock()
        mock_rg1.name = "rg-test-1"
        mock_rg1.location = "eastus"
        mock_rg1.id = "/subscriptions/test/resourceGroups/rg-test-1"
        mock_rg1.tags = {"env": "test"}
        mock_rg1.properties = Mock(provisioning_state="Succeeded")

        mock_rg2 = Mock()
        mock_rg2.name = "rg-test-2"
        mock_rg2.location = "westus"
        mock_rg2.id = "/subscriptions/test/resourceGroups/rg-test-2"
        mock_rg2.tags = {}
        mock_rg2.properties = Mock(provisioning_state="Succeeded")

        mock_resource_client.resource_groups.list.return_value = [mock_rg1, mock_rg2]

        result = await azure_provider.list_resource_groups()

        assert len(result) == 2
        assert all(isinstance(rg, ResourceGroup) for rg in result)
        assert result[0].name == "rg-test-1"
        assert result[0].location == "eastus"
        assert result[1].name == "rg-test-2"

    @pytest.mark.asyncio
    async def test_create_resource_group(self, azure_provider, mock_resource_client):
        """Test creating a resource group"""
        mock_rg = Mock()
        mock_rg.name = "new-rg"
        mock_rg.location = "eastus"
        mock_rg.id = "/subscriptions/test/resourceGroups/new-rg"
        mock_rg.tags = {"purpose": "testing"}
        mock_rg.properties = Mock(provisioning_state="Succeeded")

        mock_resource_client.resource_groups.create_or_update.return_value = mock_rg

        result = await azure_provider.create_resource_group(
            name="new-rg",
            location="eastus",
            tags={"purpose": "testing"}
        )

        assert isinstance(result, ResourceGroup)
        assert result.name == "new-rg"
        assert result.location == "eastus"
        assert result.tags["purpose"] == "testing"

    @pytest.mark.asyncio
    async def test_delete_resource_group(self, azure_provider, mock_resource_client):
        """Test deleting a resource group"""
        mock_poller = Mock()
        mock_poller.result.return_value = None
        mock_resource_client.resource_groups.begin_delete.return_value = mock_poller

        await azure_provider.delete_resource_group("test-rg")

        mock_resource_client.resource_groups.begin_delete.assert_called_once_with("test-rg")
        mock_poller.result.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_resources(self, azure_provider, mock_resource_client):
        """Test listing resources in a resource group"""
        mock_resource1 = Mock()
        mock_resource1.name = "storage-account-1"
        mock_resource1.type = "Microsoft.Storage/storageAccounts"
        mock_resource1.location = "eastus"
        mock_resource1.id = "/subscriptions/test/resourceGroups/test-rg/providers/Microsoft.Storage/storageAccounts/storage-account-1"
        mock_resource1.tags = {"type": "storage"}

        mock_resource2 = Mock()
        mock_resource2.name = "vm-1"
        mock_resource2.type = "Microsoft.Compute/virtualMachines"
        mock_resource2.location = "eastus"
        mock_resource2.id = "/subscriptions/test/resourceGroups/test-rg/providers/Microsoft.Compute/virtualMachines/vm-1"
        mock_resource2.tags = {}

        mock_resource_client.resources.list_by_resource_group.return_value = [mock_resource1, mock_resource2]

        result = await azure_provider.list_resources("test-rg")

        assert len(result) == 2
        assert all(isinstance(r, CloudResource) for r in result)
        assert result[0].name == "storage-account-1"
        assert result[0].type == "Microsoft.Storage/storageAccounts"
        assert result[1].name == "vm-1"

    def test_compile_bicep_template(self, azure_provider):
        """Test Bicep template compilation"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout='{"$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#"}',
                stderr=""
            )

            result = azure_provider._compile_bicep_template("/path/to/template.bicep")

            assert isinstance(result, dict)
            assert "$schema" in result
            mock_run.assert_called_once()

    def test_compile_bicep_template_error(self, azure_provider):
        """Test Bicep compilation error handling"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stdout="",
                stderr="Compilation error"
            )

            with pytest.raises(RuntimeError, match="Failed to compile Bicep template"):
                azure_provider._compile_bicep_template("/path/to/template.bicep")

    @pytest.mark.asyncio
    async def test_deploy_bicep_template(self, azure_provider, mock_resource_client):
        """Test deploying a Bicep template"""
        # Mock the Bicep compilation
        with patch.object(azure_provider, '_compile_bicep_template') as mock_compile:
            mock_compile.return_value = {
                "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
                "resources": []
            }

            # Mock the deployment
            mock_deployment = Mock()
            mock_deployment.name = "test-deployment"
            mock_deployment.properties = Mock(
                provisioning_state="Succeeded",
                timestamp=datetime.now(),
                outputs={"storageAccountName": {"value": "teststorage123"}}
            )

            mock_poller = Mock()
            mock_poller.result.return_value = mock_deployment
            mock_resource_client.deployments.begin_create_or_update.return_value = mock_poller

            result = await azure_provider.deploy(
                template_path="/path/to/template.bicep",
                parameters={"storageAccountName": "teststorage123"},
                resource_group="test-rg",
                location="eastus"
            )

            assert isinstance(result, DeploymentResult)
            assert result.success is True
            assert result.deployment_id == "test-deployment"
            assert "storageAccountName" in result.outputs

    @pytest.mark.asyncio
    async def test_deploy_failure(self, azure_provider, mock_resource_client):
        """Test deployment failure handling"""
        with patch.object(azure_provider, '_compile_bicep_template') as mock_compile:
            mock_compile.return_value = {"resources": []}

            mock_poller = Mock()
            mock_poller.result.side_effect = Exception("Deployment failed")
            mock_resource_client.deployments.begin_create_or_update.return_value = mock_poller

            result = await azure_provider.deploy(
                template_path="/path/to/template.bicep",
                parameters={},
                resource_group="test-rg",
                location="eastus"
            )

            assert result.success is False
            assert "Deployment failed" in result.error

    def test_get_provider_type(self, azure_provider):
        """Test getting provider type"""
        assert azure_provider.get_provider_type() == "azure"

    def test_get_cloud_name(self, azure_provider):
        """Test getting cloud name"""
        assert azure_provider.get_cloud_name() == "Azure"
