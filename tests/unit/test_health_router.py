"""
Unit tests for Health Router
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from backend.api.routes import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_root_endpoint(self, client):
        """Test root health check endpoint."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "version" in data["data"]
        assert data["data"]["status"] == "healthy"

    def test_health_endpoint_healthy(self, client):
        """Test detailed health check when all services are healthy."""
        with patch('backend.api.routers.health.get_db') as mock_db, \
             patch('backend.api.routers.health.get_template_manager') as mock_tm:

            # Mock database session
            mock_session = MagicMock()
            mock_db.return_value = mock_session

            # Mock template manager
            mock_tm_instance = MagicMock()
            mock_tm_instance.get_providers_summary.return_value = {
                'providers': ['azure', 'gcp'],
                'total_templates': 35
            }
            mock_tm.return_value = mock_tm_instance

            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_providers_endpoint(self, client):
        """Test providers list endpoint."""
        with patch('backend.api.routers.health.get_template_manager') as mock_tm:
            mock_tm_instance = MagicMock()
            mock_tm_instance.get_providers_summary.return_value = {
                'providers': [
                    {'name': 'azure', 'template_count': 22},
                    {'name': 'gcp', 'template_count': 13}
                ],
                'total_templates': 35
            }
            mock_tm.return_value = mock_tm_instance

            response = client.get("/providers")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "providers" in data["data"]
