"""
Unit tests for Templates Router
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from pathlib import Path
import json
import tempfile
import os

from backend.api.routes import app


@pytest.fixture
def client():
    """Create test client."""
    # Add Authorization header to bypass CSRF check for API requests
    return TestClient(app, headers={"Authorization": "Bearer test-token"})


@pytest.fixture
def mock_template():
    """Create mock template object."""
    template = MagicMock()
    template.name = "storage-account"
    template.provider_type = "terraform"
    template.cloud = "azure"
    template.to_dict.return_value = {
        "name": "storage-account",
        "provider_type": "terraform",
        "cloud": "azure",
        "description": "Azure Storage Account"
    }
    return template


class TestListTemplates:
    """Tests for listing templates."""

    def test_list_all_templates(self, client):
        """Test listing all templates."""
        with patch('backend.api.routers.templates.get_template_manager') as mock_tm:
            mock_instance = MagicMock()
            mock_instance.list_templates.return_value = [
                {"name": "storage", "cloud": "azure"},
                {"name": "vm", "cloud": "azure"},
                {"name": "gke", "cloud": "gcp"}
            ]
            mock_tm.return_value = mock_instance

            response = client.get("/templates")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["count"] == 3

    def test_list_templates_by_provider(self, client):
        """Test listing templates filtered by provider."""
        with patch('backend.api.routers.templates.get_template_manager') as mock_tm:
            mock_instance = MagicMock()
            mock_instance.list_templates.return_value = [
                {"name": "storage", "provider_type": "terraform"}
            ]
            mock_tm.return_value = mock_instance

            response = client.get("/templates?provider_type=terraform")

            assert response.status_code == 200
            mock_instance.list_templates.assert_called_once_with(
                provider_type="terraform", cloud=None
            )

    def test_list_templates_by_cloud(self, client):
        """Test listing templates filtered by cloud."""
        with patch('backend.api.routers.templates.get_template_manager') as mock_tm:
            mock_instance = MagicMock()
            mock_instance.list_templates.return_value = [
                {"name": "gke", "cloud": "gcp"}
            ]
            mock_tm.return_value = mock_instance

            response = client.get("/templates?cloud=gcp")

            assert response.status_code == 200
            mock_instance.list_templates.assert_called_once_with(
                provider_type=None, cloud="gcp"
            )


class TestGetTemplate:
    """Tests for getting template details."""

    def test_get_template_success(self, client, mock_template):
        """Test getting template details."""
        with patch('backend.api.routers.templates.get_template_manager') as mock_tm:
            mock_instance = MagicMock()
            mock_instance.get_template.return_value = mock_template
            mock_tm.return_value = mock_instance

            response = client.get("/templates/terraform/storage-account")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["name"] == "storage-account"

    def test_get_template_not_found(self, client):
        """Test getting non-existent template."""
        with patch('backend.api.routers.templates.get_template_manager') as mock_tm:
            mock_instance = MagicMock()
            mock_instance.get_template.return_value = None
            mock_tm.return_value = mock_instance

            response = client.get("/templates/terraform/nonexistent")

            assert response.status_code == 404


class TestGetTemplateContent:
    """Tests for getting template content."""

    def test_get_template_content_success(self, client):
        """Test getting template content."""
        with patch('backend.api.routers.templates.get_template_manager') as mock_tm:
            mock_instance = MagicMock()
            mock_instance.get_template_content.return_value = "resource \"azure_storage\" {}"
            mock_tm.return_value = mock_instance

            response = client.get("/templates/terraform/storage-account/content")

            assert response.status_code == 200
            assert "content" in response.json()

    def test_get_template_content_not_found(self, client):
        """Test getting content of non-existent template."""
        with patch('backend.api.routers.templates.get_template_manager') as mock_tm:
            mock_instance = MagicMock()
            mock_instance.get_template_content.return_value = None
            mock_tm.return_value = mock_instance

            response = client.get("/templates/terraform/nonexistent/content")

            assert response.status_code == 404


class TestGetTemplateMetadata:
    """Tests for getting template metadata."""

    def test_get_metadata_with_file(self, client):
        """Test getting metadata when metadata file exists."""
        with patch('backend.api.routers.templates.get_template_manager') as mock_tm, \
             tempfile.TemporaryDirectory() as tmpdir:

            # Create mock template and metadata files
            template_path = Path(tmpdir) / "storage-account.tf"
            template_path.write_text("resource {}")
            metadata_path = Path(tmpdir) / "storage-account.metadata.json"
            metadata_path.write_text(json.dumps({
                "displayName": "Storage Account",
                "description": "Create storage"
            }))

            mock_instance = MagicMock()
            mock_instance.get_template_path.return_value = str(template_path)
            mock_tm.return_value = mock_instance

            response = client.get("/templates/terraform/storage-account/metadata")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["has_metadata"] is True

    def test_get_metadata_without_file(self, client):
        """Test getting metadata when no metadata file exists."""
        with patch('backend.api.routers.templates.get_template_manager') as mock_tm, \
             tempfile.TemporaryDirectory() as tmpdir:

            # Create only template file, no metadata
            template_path = Path(tmpdir) / "storage-account.tf"
            template_path.write_text("resource {}")

            mock_instance = MagicMock()
            mock_instance.get_template_path.return_value = str(template_path)
            mock_tm.return_value = mock_instance

            response = client.get("/templates/terraform/storage-account/metadata")

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["has_metadata"] is False

    def test_get_metadata_template_not_found(self, client):
        """Test getting metadata for non-existent template."""
        with patch('backend.api.routers.templates.get_template_manager') as mock_tm:
            mock_instance = MagicMock()
            mock_instance.get_template_path.return_value = None
            mock_tm.return_value = mock_instance

            response = client.get("/templates/terraform/nonexistent/metadata")

            assert response.status_code == 404


class TestGetTemplateParameters:
    """Tests for getting template parameters."""

    def test_get_parameters_success(self, client):
        """Test getting template parameters."""
        with patch('backend.api.routers.templates.get_template_manager') as mock_tm, \
             patch('backend.api.routers.templates.TemplateParameterParser') as mock_parser:

            mock_instance = MagicMock()
            mock_instance.get_template_path.return_value = "/path/to/template.tf"
            mock_tm.return_value = mock_instance

            mock_param = MagicMock()
            mock_param.to_dict.return_value = {
                "name": "location",
                "type": "string",
                "default": "eastus"
            }
            mock_parser.parse_file.return_value = [mock_param]

            response = client.get("/templates/terraform/storage-account/parameters")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["count"] == 1

    def test_get_parameters_template_not_found(self, client):
        """Test getting parameters for non-existent template."""
        with patch('backend.api.routers.templates.get_template_manager') as mock_tm:
            mock_instance = MagicMock()
            mock_instance.get_template_path.return_value = None
            mock_tm.return_value = mock_instance

            response = client.get("/templates/terraform/nonexistent/parameters")

            assert response.status_code == 404


class TestEstimateCost:
    """Tests for cost estimation."""

    def test_estimate_cost_success(self, client):
        """Test successful cost estimation."""
        with patch('backend.api.routers.templates.get_template_manager') as mock_tm, \
             patch('backend.api.routers.templates.estimate_deployment_cost') as mock_estimate:

            mock_instance = MagicMock()
            mock_instance.get_template_path.return_value = "/path/to/template.tf"
            mock_tm.return_value = mock_instance

            mock_estimate.return_value = {
                "monthly_cost": 25.00,
                "currency": "USD",
                "components": []
            }

            response = client.post(
                "/templates/terraform/storage-account/estimate-cost",
                json={"location": "eastus", "sku": "Standard_LRS"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "monthly_cost" in data["data"]

    def test_estimate_cost_template_not_found(self, client):
        """Test cost estimation for non-existent template."""
        with patch('backend.api.routers.templates.get_template_manager') as mock_tm:
            mock_instance = MagicMock()
            mock_instance.get_template_path.return_value = None
            mock_tm.return_value = mock_instance

            response = client.post(
                "/templates/terraform/nonexistent/estimate-cost",
                json={"param": "value"}
            )

            assert response.status_code == 404
