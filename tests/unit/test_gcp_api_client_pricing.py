"""
Unit tests for GCPAPIClient pricing (static DB) + Compute Engine methods.

Compute API calls are mocked at the client._get boundary (AsyncMock); pricing
methods use the in-code static database, so no network/credentials are needed.
"""
from unittest.mock import AsyncMock

import pytest

from backend.services.gcp_api_client import GCPAPIClient, get_gcp_client


@pytest.fixture
def client():
    c = GCPAPIClient(project_id="proj-1", access_token="token")
    c._get = AsyncMock()
    return c


class TestComputePricing:
    @pytest.mark.asyncio
    async def test_known_machine_type_base_region(self, client):
        result = await client.get_compute_pricing("e2-standard-2", "us-central1")
        assert result["machine_type"] == "e2-standard-2"
        assert result["price_per_month"] == 48.88  # multiplier 1.0
        assert result["vcpu_count"] == 2

    @pytest.mark.asyncio
    async def test_region_multiplier_applied(self, client):
        result = await client.get_compute_pricing("e2-standard-2", "europe-west1")
        assert result["price_per_month"] == pytest.approx(48.88 * 1.08, abs=0.01)

    @pytest.mark.asyncio
    async def test_unknown_region_uses_default_multiplier(self, client):
        result = await client.get_compute_pricing("e2-medium", "narnia")
        assert result["price_per_month"] == 24.44

    @pytest.mark.asyncio
    async def test_unknown_machine_type_returns_none(self, client):
        assert await client.get_compute_pricing("does-not-exist", "us-central1") is None


class TestStoragePricing:
    @pytest.mark.asyncio
    async def test_standard_known_region(self, client):
        result = await client.get_storage_pricing("STANDARD", "asia-southeast1")
        assert result["price_per_gb_month"] == 0.023

    @pytest.mark.asyncio
    async def test_unknown_region_falls_back_to_us_central1(self, client):
        result = await client.get_storage_pricing("NEARLINE", "narnia")
        assert result["price_per_gb_month"] == 0.010

    @pytest.mark.asyncio
    async def test_unknown_class_falls_back_to_default(self, client):
        result = await client.get_storage_pricing("WEIRD", "us-central1")
        assert result["price_per_gb_month"] == 0.020


class TestDiskPricing:
    @pytest.mark.asyncio
    async def test_known_disk_type(self, client):
        result = await client.get_disk_pricing("pd-ssd", "us-central1")
        assert result["price_per_gb_month"] == 0.170

    @pytest.mark.asyncio
    async def test_unknown_disk_type_default(self, client):
        result = await client.get_disk_pricing("pd-mystery", "us-central1")
        assert result["price_per_gb_month"] == 0.100


class TestRegionsZonesMachineTypes:
    @pytest.mark.asyncio
    async def test_regions_transform(self, client):
        client._get.return_value = {
            "items": [
                {
                    "name": "us-central1",
                    "description": "Iowa",
                    "status": "UP",
                    "zones": ["https://x/zones/us-central1-a", "https://x/zones/us-central1-b"],
                }
            ]
        }
        regions = await client.get_regions()
        assert regions[0]["name"] == "us-central1"
        assert regions[0]["zones"] == ["us-central1-a", "us-central1-b"]

    @pytest.mark.asyncio
    async def test_regions_no_project(self):
        c = GCPAPIClient(project_id=None, access_token="t")
        c.project_id = None
        assert await c.get_regions() == []

    @pytest.mark.asyncio
    async def test_zones_filtered_by_region(self, client):
        client._get.return_value = {
            "items": [
                {"name": "us-central1-a", "region": "https://x/regions/us-central1", "status": "UP"},
                {"name": "europe-west1-b", "region": "https://x/regions/europe-west1", "status": "UP"},
            ]
        }
        zones = await client.get_zones(region="us-central1")
        assert len(zones) == 1
        assert zones[0]["name"] == "us-central1-a"
        assert zones[0]["region"] == "us-central1"

    @pytest.mark.asyncio
    async def test_zones_empty_when_no_data(self, client):
        client._get.return_value = None
        assert await client.get_zones() == []

    @pytest.mark.asyncio
    async def test_machine_types_transform(self, client):
        client._get.return_value = {
            "items": [{"name": "e2-standard-2", "guestCpus": 2, "memoryMb": 8192, "description": "desc"}]
        }
        types = await client.get_machine_types(zone="us-central1-a")
        assert types[0]["name"] == "e2-standard-2"
        assert types[0]["vcpus"] == 2
        assert types[0]["memory_gb"] == 8.0
        assert types[0]["zone"] == "us-central1-a"

    @pytest.mark.asyncio
    async def test_machine_types_no_project(self):
        c = GCPAPIClient(project_id=None, access_token="t")
        c.project_id = None
        assert await c.get_machine_types() == []


class TestPublicClientSingleton:
    @pytest.mark.asyncio
    async def test_returns_same_instance(self):
        import backend.services.gcp_api_client as mod

        mod._public_client = None
        a = await get_gcp_client()
        b = await get_gcp_client()
        assert a is b
