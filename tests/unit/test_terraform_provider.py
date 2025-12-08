"""
Unit tests for Terraform Provider
"""
import pytest
import os
import json
from unittest.mock import Mock, patch, MagicMock, mock_open
from backend.providers.terraform_provider import TerraformProvider
from backend.providers.base import DeploymentResult, DeploymentStatus, ResourceGroup, CloudResource, ProviderType


@pytest.fixture
def terraform_gcp_provider():
    """Create TerraformProvider instance for GCP"""
    with patch.dict(os.environ, {
        'GOOGLE_PROJECT_ID': 'test-project',
        'GOOGLE_APPLICATION_CREDENTIALS': '/path/to/creds.json'
    }):
        provider = TerraformProvider(cloud_platform="gcp", subscription_id="test-project")
        yield provider


@pytest.fixture
def terraform_azure_provider():
    """Create TerraformProvider instance for Azure"""
    with patch.dict(os.environ, {
        'AZURE_SUBSCRIPTION_ID': 'test-sub',
        'AZURE_TENANT_ID': 'test-tenant',
        'AZURE_CLIENT_ID': 'test-client',
        'AZURE_CLIENT_SECRET': 'test-secret'
    }):
        provider = TerraformProvider(cloud_platform="azure", subscription_id="test-sub")
        yield provider


class TestTerraformProvider:
    """Test cases for TerraformProvider"""

    def test_gcp_initialization(self, terraform_gcp_provider):
        """Test GCP provider initialization"""
        assert terraform_gcp_provider.cloud_platform == "gcp"
        assert terraform_gcp_provider.subscription_id == "test-project"

    def test_azure_initialization(self, terraform_azure_provider):
        """Test Azure (via Terraform) initialization"""
        assert terraform_azure_provider.cloud_platform == "azure"
        assert terraform_azure_provider.subscription_id == "test-sub"

    def test_generate_gcp_provider_block(self, terraform_gcp_provider):
        """Test generating GCP provider block"""
        config = terraform_gcp_provider._generate_provider_block(location="us-central1")

        assert "provider" in config
        assert "google" in config
        assert "test-project" in config

    def test_generate_azure_provider_block(self, terraform_azure_provider):
        """Test generating Azure provider block"""
        config = terraform_azure_provider._generate_provider_block(location="westeurope")

        assert "provider" in config
        assert "azurerm" in config

    @patch('subprocess.run')
    def test_terraform_init_success(self, mock_run, terraform_azure_provider):
        """Test successful Terraform initialization"""
        mock_run.return_value = Mock(returncode=0, stdout="Terraform initialized", stderr="")

        terraform_azure_provider._run_terraform_command(["init"])

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "terraform" in call_args
        assert "init" in call_args

    @patch('subprocess.run')
    def test_terraform_command_failure(self, mock_run, terraform_azure_provider):
        """Test Terraform command failure"""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Error: Invalid configuration"
        )

        output, returncode = terraform_azure_provider._run_terraform_command(["apply"])

        assert returncode == 1
        assert "Error: Invalid configuration" in output

    @pytest.mark.asyncio
    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open, read_data='resource "azurerm_resource_group" "example" {}')
    async def test_deploy_success(self, mock_file, mock_run, terraform_azure_provider):
        """Test successful deployment"""
        # The provider makes multiple subprocess calls:
        # 1. init, 2. plan, 3. apply, 4. output
        # Use return_value for consistent behavior instead of side_effect
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"resource_group_name": {"value": "test-rg"}}',
            stderr=""
        )

        result = await terraform_azure_provider.deploy(
            template_path="/path/to/template.tf",
            parameters={"resource_group_name": "test-rg"},
            resource_group="test-group",
            location="westeurope"
        )

        assert isinstance(result, DeploymentResult)
        assert result.status == DeploymentStatus.SUCCEEDED
        assert "resource_group_name" in result.outputs

    @pytest.mark.asyncio
    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open, read_data='resource "azurerm_resource_group" "example" {}')
    async def test_deploy_failure(self, mock_file, mock_run, terraform_azure_provider):
        """Test deployment failure"""
        # First two calls succeed (init, plan), third fails (apply)
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Error: Resource creation failed"
        )

        with pytest.raises(Exception) as excinfo:
            await terraform_azure_provider.deploy(
                template_path="/path/to/template.tf",
                parameters={},
                resource_group="test-group",
                location="westeurope"
            )

        # Check that the error message contains relevant information
        assert "Terraform" in str(excinfo.value)
        assert "failed" in str(excinfo.value).lower()

    @pytest.mark.asyncio
    async def test_list_resource_groups_azure(self, terraform_azure_provider):
        """Test listing Azure resource groups (returns empty list for now)"""
        result = await terraform_azure_provider.list_resource_groups()
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_create_resource_group_not_implemented(self, terraform_azure_provider):
        """Test that create resource group raises NotImplementedError"""
        with pytest.raises(NotImplementedError):
            await terraform_azure_provider.create_resource_group(
                name="test-group",
                location="westeurope"
            )

    def test_get_provider_type(self, terraform_azure_provider):
        """Test getting provider type"""
        assert terraform_azure_provider.get_provider_type() == ProviderType.TERRAFORM

    def test_get_supported_locations_azure(self, terraform_azure_provider):
        """Test getting supported locations for Azure"""
        locations = terraform_azure_provider.get_supported_locations()
        assert "westeurope" in locations or "eastus" in locations

    def test_get_supported_locations_gcp(self, terraform_gcp_provider):
        """Test getting supported locations for GCP"""
        locations = terraform_gcp_provider.get_supported_locations()
        assert "us-central1" in locations
