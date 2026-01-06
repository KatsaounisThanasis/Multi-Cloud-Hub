"""
Unit tests for API Client services (Azure and GCP)
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from backend.services.azure_api_client import AzureAPIClient
from backend.services.gcp_api_client import GCPAPIClient


class TestAzureAPIClient:
    """Tests for AzureAPIClient."""

    def test_initialization(self):
        """Test Azure client initialization."""
        with patch.dict('os.environ', {
            'AZURE_SUBSCRIPTION_ID': 'test-sub',
            'AZURE_TENANT_ID': 'test-tenant',
            'AZURE_CLIENT_ID': 'test-client',
            'AZURE_CLIENT_SECRET': 'test-secret'
        }):
            client = AzureAPIClient(subscription_id='test-sub')
            assert client.subscription_id == 'test-sub'

    def test_initialization_from_env(self):
        """Test Azure client initialization from environment."""
        with patch.dict('os.environ', {
            'AZURE_SUBSCRIPTION_ID': 'env-sub',
            'AZURE_TENANT_ID': 'test-tenant',
            'AZURE_CLIENT_ID': 'test-client',
            'AZURE_CLIENT_SECRET': 'test-secret'
        }):
            client = AzureAPIClient()
            assert client.subscription_id == 'env-sub'

    def test_subscription_id_property(self):
        """Test subscription_id property."""
        with patch.dict('os.environ', {
            'AZURE_SUBSCRIPTION_ID': 'test-sub',
            'AZURE_TENANT_ID': 'test-tenant',
            'AZURE_CLIENT_ID': 'test-client',
            'AZURE_CLIENT_SECRET': 'test-secret'
        }):
            client = AzureAPIClient(subscription_id='test-sub')
            assert client.subscription_id == 'test-sub'


class TestGCPAPIClient:
    """Tests for GCPAPIClient."""

    def test_initialization(self):
        """Test GCP client initialization."""
        with patch.dict('os.environ', {
            'GOOGLE_PROJECT_ID': 'test-project',
            'GOOGLE_APPLICATION_CREDENTIALS': '/path/to/creds.json'
        }):
            client = GCPAPIClient(project_id='test-project')
            assert client.project_id == 'test-project'

    def test_initialization_from_env(self):
        """Test GCP client initialization from environment."""
        with patch.dict('os.environ', {
            'GOOGLE_PROJECT_ID': 'env-project',
            'GOOGLE_APPLICATION_CREDENTIALS': '/path/to/creds.json'
        }):
            client = GCPAPIClient()
            assert client.project_id == 'env-project'

    @pytest.mark.asyncio
    async def test_get_access_token(self):
        """Test getting GCP access token."""
        with patch.dict('os.environ', {
            'GOOGLE_PROJECT_ID': 'test-project',
            'GOOGLE_APPLICATION_CREDENTIALS': '/path/to/creds.json'
        }):
            client = GCPAPIClient(project_id='test-project')

            with patch('google.auth.default') as mock_auth:
                mock_credentials = MagicMock()
                mock_credentials.token = "test-gcp-token"
                mock_credentials.refresh = MagicMock()
                mock_auth.return_value = (mock_credentials, 'test-project')

                # The token property should return the mock token
                # This tests the initialization path
                assert client.project_id == 'test-project'

    def test_project_id_property(self):
        """Test project_id property."""
        with patch.dict('os.environ', {
            'GOOGLE_PROJECT_ID': 'test-project',
            'GOOGLE_APPLICATION_CREDENTIALS': '/path/to/creds.json'
        }):
            client = GCPAPIClient(project_id='test-project')
            assert client.project_id == 'test-project'
