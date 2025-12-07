"""
Integration tests for REST API endpoints
Updated for the new API structure (v3.0)
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from backend.api.routes import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint"""

    def test_health_check(self, client):
        """Test GET /health"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "healthy"
        assert "api_version" in data["data"]


class TestProvidersEndpoint:
    """Test providers endpoint"""

    def test_list_providers(self, client):
        """Test GET /providers"""
        response = client.get("/providers")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "providers" in data["data"]

        providers = data["data"]["providers"]
        assert isinstance(providers, list)
        assert len(providers) > 0

    def test_providers_have_required_fields(self, client):
        """Test providers have required fields"""
        response = client.get("/providers")
        data = response.json()

        for provider in data["data"]["providers"]:
            assert "id" in provider
            assert "name" in provider
            assert "format" in provider
            assert "cloud" in provider


class TestTemplatesEndpoint:
    """Test templates endpoint"""

    def test_list_templates(self, client):
        """Test GET /templates"""
        response = client.get("/templates")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "templates" in data["data"]

    def test_get_azure_template(self, client):
        """Test GET /templates/terraform-azure/storage-account"""
        response = client.get("/templates/terraform-azure/storage-account")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "storage-account"

    def test_get_gcp_template(self, client):
        """Test GET /templates/terraform-gcp/storage-bucket"""
        response = client.get("/templates/terraform-gcp/storage-bucket")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "storage-bucket"

    def test_get_nonexistent_template(self, client):
        """Test GET /templates with non-existent template"""
        response = client.get("/templates/terraform-azure/nonexistent-template")

        assert response.status_code == 404


class TestAzureEndpoints:
    """Test Azure-specific endpoints"""

    def test_azure_locations(self, client):
        """Test GET /api/azure/locations"""
        response = client.get("/api/azure/locations")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "locations" in data["data"]

    def test_azure_resource_groups(self, client):
        """Test GET /api/azure/resource-groups"""
        response = client.get("/api/azure/resource-groups")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "resource_groups" in data["data"]

    def test_azure_vm_sizes(self, client):
        """Test GET /api/azure/vm-sizes"""
        response = client.get("/api/azure/vm-sizes?location=westeurope")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "vm_sizes" in data["data"]


class TestGCPEndpoints:
    """Test GCP-specific endpoints"""

    def test_gcp_regions(self, client):
        """Test GET /api/gcp/regions"""
        response = client.get("/api/gcp/regions")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "regions" in data["data"]

    def test_gcp_zones(self, client):
        """Test GET /api/gcp/zones"""
        response = client.get("/api/gcp/zones?region=us-central1")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "zones" in data["data"]

    def test_gcp_machine_types(self, client):
        """Test GET /api/gcp/machine-types"""
        response = client.get("/api/gcp/machine-types?zone=us-central1-a")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "machine_types" in data["data"]


class TestDeploymentsEndpoint:
    """Test deployments endpoint"""

    def test_list_deployments(self, client):
        """Test GET /deployments"""
        response = client.get("/deployments")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "deployments" in data["data"]

    def test_deploy_missing_fields(self, client):
        """Test POST /deploy with missing required fields"""
        payload = {
            "template_name": "storage-account"
            # Missing other required fields
        }

        response = client.post("/deploy", json=payload)

        assert response.status_code == 422  # Validation error


class TestCostEstimation:
    """Test cost estimation endpoint"""

    def test_cost_estimate(self, client):
        """Test POST /templates/{provider}/{template}/estimate-cost"""
        payload = {
            "location": "westeurope",
            "parameters": {
                "storage_account_name": "test"
            }
        }

        response = client.post(
            "/templates/terraform-azure/storage-account/estimate-cost",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "total_monthly_cost" in data["data"]


class TestOpenAPIDocumentation:
    """Test OpenAPI/Swagger documentation"""

    def test_openapi_json(self, client):
        """Test OpenAPI JSON is available"""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data

    def test_swagger_ui(self, client):
        """Test Swagger UI is available"""
        response = client.get("/docs")

        assert response.status_code == 200


class TestErrorHandling:
    """Test error handling"""

    def test_404_not_found(self, client):
        """Test 404 error for non-existent endpoint"""
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404

    def test_invalid_json(self, client):
        """Test handling of invalid JSON"""
        response = client.post(
            "/deploy",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
