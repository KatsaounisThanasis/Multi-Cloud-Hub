"""
Live API Integration Tests
Tests that run against the actual running API (localhost:8000)
Requires Docker services to be running: docker compose up -d
"""
import pytest
import requests
import os

# Base URL for the live API
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def api_is_available():
    """Check if the API is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


# Skip all tests in this module if API is not available
pytestmark = pytest.mark.skipif(
    not api_is_available(),
    reason="Live API not available at localhost:8000 - start with 'docker compose up -d'"
)


class TestLiveHealthEndpoint:
    """Test health check against live API"""

    def test_health_check_healthy(self):
        """Test GET /health returns healthy status"""
        response = requests.get(f"{API_BASE_URL}/health")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "healthy"
        assert data["data"]["api_version"] == "3.0.0"

    def test_health_database_connected(self):
        """Test database is connected"""
        response = requests.get(f"{API_BASE_URL}/health")
        data = response.json()

        assert data["data"]["database"]["status"] == "connected"

    def test_health_celery_active(self):
        """Test Celery workers are active"""
        response = requests.get(f"{API_BASE_URL}/health")
        data = response.json()

        assert data["data"]["celery"]["status"] == "connected"
        assert data["data"]["celery"]["workers"] >= 1


class TestLiveProvidersEndpoint:
    """Test providers endpoint against live API"""

    def test_list_providers(self):
        """Test GET /providers returns all providers"""
        response = requests.get(f"{API_BASE_URL}/providers")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        providers = data["data"]["providers"]
        assert len(providers) == 3  # bicep, terraform-azure, terraform-gcp

        provider_ids = [p["id"] for p in providers]
        assert "terraform-azure" in provider_ids
        assert "terraform-gcp" in provider_ids

    def test_total_templates_count(self):
        """Test total templates count is correct"""
        response = requests.get(f"{API_BASE_URL}/providers")
        data = response.json()

        assert data["data"]["total_templates"] == 35  # 22 Azure + 13 GCP


class TestLiveTemplatesEndpoint:
    """Test templates endpoint against live API"""

    def test_list_all_templates(self):
        """Test GET /templates returns all templates"""
        response = requests.get(f"{API_BASE_URL}/templates")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "templates" in data["data"]

    def test_get_azure_storage_template(self):
        """Test GET /templates/terraform-azure/storage-account"""
        response = requests.get(f"{API_BASE_URL}/templates/terraform-azure/storage-account")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "storage-account"
        assert data["data"]["cloud_provider"] == "azure"
        assert "parameters" in data["data"]

    def test_get_gcp_storage_template(self):
        """Test GET /templates/terraform-gcp/storage-bucket"""
        response = requests.get(f"{API_BASE_URL}/templates/terraform-gcp/storage-bucket")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "storage-bucket"
        assert data["data"]["cloud_provider"] == "gcp"

    def test_get_nonexistent_template(self):
        """Test 404 for non-existent template"""
        response = requests.get(f"{API_BASE_URL}/templates/terraform-azure/nonexistent")
        assert response.status_code == 404


class TestLiveAzureEndpoints:
    """Test Azure-specific endpoints against live API with real credentials"""

    def test_azure_locations(self):
        """Test GET /api/azure/locations returns Azure regions"""
        response = requests.get(f"{API_BASE_URL}/api/azure/locations")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "locations" in data["data"]

        locations = data["data"]["locations"]
        assert len(locations) > 0
        # Check common Azure regions exist
        location_names = [loc["name"] for loc in locations]
        assert "westeurope" in location_names or "eastus" in location_names

    def test_azure_resource_groups(self):
        """Test GET /api/azure/resource-groups returns resource groups"""
        response = requests.get(f"{API_BASE_URL}/api/azure/resource-groups")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "resource_groups" in data["data"]

        # We should have at least some resource groups from previous tests
        rgs = data["data"]["resource_groups"]
        assert isinstance(rgs, list)

    def test_azure_vm_sizes(self):
        """Test GET /api/azure/vm-sizes returns VM sizes for a location"""
        response = requests.get(f"{API_BASE_URL}/api/azure/vm-sizes?location=westeurope")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "vm_sizes" in data["data"]

        vm_sizes = data["data"]["vm_sizes"]
        assert len(vm_sizes) > 0
        # Check common VM sizes exist
        size_names = [s["name"] for s in vm_sizes]
        assert any("Standard" in name for name in size_names)


class TestLiveGCPEndpoints:
    """Test GCP-specific endpoints against live API with real credentials"""

    def test_gcp_regions(self):
        """Test GET /api/gcp/regions returns GCP regions"""
        response = requests.get(f"{API_BASE_URL}/api/gcp/regions")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "regions" in data["data"]

        regions = data["data"]["regions"]
        assert len(regions) > 0
        # Check common GCP regions exist
        region_names = [r["name"] for r in regions]
        assert "us-central1" in region_names or "europe-west1" in region_names

    def test_gcp_zones(self):
        """Test GET /api/gcp/zones returns zones for a region"""
        response = requests.get(f"{API_BASE_URL}/api/gcp/zones?region=us-central1")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "zones" in data["data"]

        zones = data["data"]["zones"]
        assert len(zones) > 0

    def test_gcp_machine_types(self):
        """Test GET /api/gcp/machine-types returns machine types"""
        response = requests.get(f"{API_BASE_URL}/api/gcp/machine-types?zone=us-central1-a")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "machine_types" in data["data"]

        machine_types = data["data"]["machine_types"]
        assert len(machine_types) > 0


class TestLiveDeploymentsEndpoint:
    """Test deployments endpoint against live API with real database"""

    def test_list_deployments(self):
        """Test GET /deployments returns deployment history"""
        response = requests.get(f"{API_BASE_URL}/deployments")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "deployments" in data["data"]
        assert "total" in data["data"]

        # We should have deployments from previous testing
        assert data["data"]["total"] >= 0

    def test_deployment_has_required_fields(self):
        """Test deployments have all required fields"""
        response = requests.get(f"{API_BASE_URL}/deployments")
        data = response.json()

        if data["data"]["total"] > 0:
            deployment = data["data"]["deployments"][0]
            required_fields = [
                "deployment_id", "provider_type", "template_name",
                "resource_group", "status", "created_at"
            ]
            for field in required_fields:
                assert field in deployment, f"Missing field: {field}"

    def test_deploy_validation_error(self):
        """Test POST /deploy returns validation error for incomplete data"""
        payload = {"template_name": "storage-account"}  # Missing required fields

        response = requests.post(f"{API_BASE_URL}/deploy", json=payload)
        assert response.status_code == 422


class TestLiveCostEstimation:
    """Test cost estimation against live API"""

    def test_azure_storage_cost_estimate(self):
        """Test cost estimation for Azure storage account"""
        payload = {
            "location": "westeurope",
            "parameters": {
                "storage_account_name": "testestimate123"
            }
        }

        response = requests.post(
            f"{API_BASE_URL}/templates/terraform-azure/storage-account/estimate-cost",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "total_monthly_cost" in data["data"]
        assert "currency" in data["data"]
        assert data["data"]["currency"] == "USD"

    def test_gcp_storage_cost_estimate(self):
        """Test cost estimation for GCP storage bucket"""
        payload = {
            "location": "us-central1",
            "parameters": {
                "bucket_name": "testestimate123",
                "storage_class": "STANDARD"
            }
        }

        response = requests.post(
            f"{API_BASE_URL}/templates/terraform-gcp/storage-bucket/estimate-cost",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "total_monthly_cost" in data["data"]


class TestLiveOpenAPIDocumentation:
    """Test API documentation against live API"""

    def test_openapi_json(self):
        """Test OpenAPI JSON schema is available"""
        response = requests.get(f"{API_BASE_URL}/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert data["openapi"].startswith("3.")
        assert "Multi-Cloud Infrastructure" in data["info"]["title"]
        assert "paths" in data
        assert len(data["paths"]) > 10  # Should have many endpoints

    def test_swagger_ui_available(self):
        """Test Swagger UI is accessible"""
        response = requests.get(f"{API_BASE_URL}/docs")

        assert response.status_code == 200
        assert "swagger" in response.text.lower()

    def test_redoc_available(self):
        """Test ReDoc documentation is accessible"""
        response = requests.get(f"{API_BASE_URL}/redoc")

        assert response.status_code == 200


class TestLiveErrorHandling:
    """Test error handling against live API"""

    def test_404_not_found(self):
        """Test 404 for non-existent endpoint"""
        response = requests.get(f"{API_BASE_URL}/nonexistent-endpoint")
        assert response.status_code == 404

    def test_method_not_allowed(self):
        """Test 405 for wrong HTTP method"""
        response = requests.delete(f"{API_BASE_URL}/health")
        assert response.status_code == 405

    def test_invalid_json_body(self):
        """Test 422 for invalid JSON in request body"""
        response = requests.post(
            f"{API_BASE_URL}/deploy",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
