"""
Unit tests for Provider Factory
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.providers.factory import ProviderFactory
from backend.providers.azure_native import AzureNativeProvider
from backend.providers.terraform_provider import TerraformProvider


class TestProviderFactory:
    """Test cases for ProviderFactory"""

    def test_get_available_providers(self):
        """Test getting list of available providers"""
        providers = ProviderFactory.get_available_providers()

        assert isinstance(providers, list)
        assert "azure" in providers
        assert "terraform-aws" in providers
        assert "terraform-gcp" in providers
        assert "terraform-azure" in providers

    @patch('backend.providers.azure_native.AzureNativeProvider.__init__', return_value=None)
    def test_create_azure_provider(self, mock_init):
        """Test creating Azure native provider"""
        provider = ProviderFactory.create_provider(
            "azure",
            subscription_id="test-sub-id",
            tenant_id="test-tenant-id"
        )

        assert isinstance(provider, AzureNativeProvider)
        mock_init.assert_called_once()

    @patch('backend.providers.terraform_provider.TerraformProvider.__init__', return_value=None)
    def test_create_terraform_aws_provider(self, mock_init):
        """Test creating Terraform AWS provider"""
        provider = ProviderFactory.create_provider(
            "terraform-aws",
            cloud="aws",
            region="us-east-1"
        )

        assert isinstance(provider, TerraformProvider)
        mock_init.assert_called_once()

    @patch('backend.providers.terraform_provider.TerraformProvider.__init__', return_value=None)
    def test_create_terraform_gcp_provider(self, mock_init):
        """Test creating Terraform GCP provider"""
        provider = ProviderFactory.create_provider(
            "terraform-gcp",
            cloud="gcp",
            project_id="test-project"
        )

        assert isinstance(provider, TerraformProvider)
        mock_init.assert_called_once()

    def test_create_invalid_provider(self):
        """Test that invalid provider raises ProviderConfigurationError"""
        from backend.providers.base import ProviderConfigurationError
        with pytest.raises(ProviderConfigurationError, match="Unsupported provider type"):
            ProviderFactory.create_provider("invalid-provider")

    def test_register_custom_provider(self):
        """Test registering a custom provider"""
        from backend.providers.base import CloudProvider

        # Create a mock provider class
        class MockProvider(CloudProvider):
            async def deploy(self, *args, **kwargs):
                pass
            async def list_resource_groups(self):
                pass
            async def create_resource_group(self, *args, **kwargs):
                pass
            async def delete_resource_group(self, *args, **kwargs):
                pass
            async def list_resources(self, *args, **kwargs):
                pass
            def get_provider_type(self):
                return "mock"
            def get_cloud_name(self):
                return "Mock"

        # Register it
        ProviderFactory.register_provider("custom-provider", MockProvider)

        # Verify it's registered
        providers = ProviderFactory.get_available_providers()
        assert "custom-provider" in providers

        # Cleanup
        ProviderFactory._providers.pop("custom-provider", None)

    def test_provider_count(self):
        """Test that we have the expected number of providers"""
        providers = ProviderFactory.get_available_providers()
        assert len(providers) >= 4  # At least azure, terraform-aws, terraform-gcp, terraform-azure

    def test_cloud_categorization(self):
        """Test that providers are correctly categorized by cloud"""
        providers = ProviderFactory.get_available_providers()

        # Check we have Azure providers
        azure_providers = [p for p in providers if "azure" in p.lower()]
        # Check we have AWS providers
        aws_providers = [p for p in providers if "aws" in p.lower()]
        # Check we have GCP providers
        gcp_providers = [p for p in providers if "gcp" in p.lower()]

        assert len(azure_providers) >= 1
        assert len(aws_providers) >= 1
        assert len(gcp_providers) >= 1
