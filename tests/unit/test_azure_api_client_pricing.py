"""
Unit tests for AzureAPIClient pricing + management methods.

All HTTP is mocked at the client._get boundary (AsyncMock), so these tests
exercise the request-building and response-transforming logic without any
network access or Azure credentials.
"""
from unittest.mock import AsyncMock

import pytest

from backend.services.azure_api_client import AzureAPIClient, get_azure_public_client


@pytest.fixture
def client():
    c = AzureAPIClient(subscription_id="sub-123", access_token="token")
    c._get = AsyncMock()
    return c


class TestVMPricing:
    @pytest.mark.asyncio
    async def test_returns_transformed_pricing(self, client):
        client._get.return_value = {
            "Items": [
                {
                    "retailPrice": 0.1,
                    "unitOfMeasure": "1 Hour",
                    "currencyCode": "USD",
                    "productName": "Virtual Machines Dv3 Series Linux",
                    "skuName": "D2s v3",
                    "meterName": "D2s v3",
                }
            ]
        }
        result = await client.get_vm_pricing("Standard_D2s_v3", "eastus")
        assert result["vm_size"] == "Standard_D2s_v3"
        assert result["retail_price_per_hour"] == 0.1
        assert result["retail_price_per_month"] == pytest.approx(0.1 * 730)
        assert result["currency"] == "USD"

    @pytest.mark.asyncio
    async def test_windows_filter_branch(self, client):
        client._get.return_value = {"Items": [{"retailPrice": 0.2}]}
        await client.get_vm_pricing("Standard_D2s_v3", "eastus", operating_system="Windows")
        # The $filter param should ask for Windows products
        _, kwargs = client._get.call_args
        assert "Windows" in kwargs["params"]["$filter"]

    @pytest.mark.asyncio
    async def test_no_items_returns_none(self, client):
        client._get.return_value = {"Items": []}
        assert await client.get_vm_pricing("x", "eastus") is None

    @pytest.mark.asyncio
    async def test_no_data_returns_none(self, client):
        client._get.return_value = None
        assert await client.get_vm_pricing("x", "eastus") is None


class TestStoragePricing:
    @pytest.mark.asyncio
    async def test_standard_lrs_matches(self, client):
        client._get.return_value = {
            "Items": [
                {
                    "productName": "Blob Storage Block Blob",
                    "meterName": "Hot LRS Data Stored",
                    "skuName": "Hot LRS",
                    "retailPrice": 0.02,
                }
            ]
        }
        result = await client.get_storage_pricing("standard", "eastus", "LRS")
        assert result["price_per_gb_month"] == 0.02
        assert result["redundancy"] == "LRS"

    @pytest.mark.asyncio
    async def test_premium_branch(self, client):
        client._get.return_value = {
            "Items": [
                {
                    "productName": "Premium Block Blob",
                    "meterName": "LRS Data Stored",
                    "skuName": "Premium LRS",
                    "retailPrice": 0.15,
                }
            ]
        }
        result = await client.get_storage_pricing("premium", "eastus", "LRS")
        assert result["price_per_gb_month"] == 0.15

    @pytest.mark.asyncio
    async def test_falls_back_through_regions_then_none(self, client):
        # Always empty -> tries region, westeurope, eastus, then returns None
        client._get.return_value = {"Items": []}
        assert await client.get_storage_pricing("standard", "narnia", "LRS") is None
        assert client._get.await_count == 3

    @pytest.mark.asyncio
    async def test_note_added_when_region_differs(self, client):
        # First region empty, second (westeurope) returns a match
        responses = [
            {"Items": []},
            {
                "Items": [
                    {
                        "productName": "Block Blob",
                        "meterName": "Hot LRS Data Stored",
                        "skuName": "Hot LRS",
                        "retailPrice": 0.02,
                    }
                ]
            },
        ]
        client._get = AsyncMock(side_effect=responses)
        result = await client.get_storage_pricing("standard", "narnia", "LRS")
        assert "note" in result
        assert "westeurope" in result["note"]


class TestDiskPricing:
    @pytest.mark.asyncio
    async def test_disk_pricing_transform(self, client):
        client._get.return_value = {
            "Items": [
                {
                    "retailPrice": 5.0,
                    "unitOfMeasure": "1/Month",
                    "skuName": "P10 LRS Disk",
                    "meterName": "P10 LRS Disk",
                    "productName": "Premium SSD Managed Disks",
                }
            ]
        }
        result = await client.get_disk_pricing("Premium_LRS", "eastus")
        assert result["price_per_month"] == 5.0
        assert result["disk_type"] == "Premium_LRS"

    @pytest.mark.asyncio
    async def test_disk_pricing_no_items(self, client):
        client._get.return_value = {"Items": []}
        assert await client.get_disk_pricing("Premium_LRS", "eastus") is None


class TestManagementApi:
    @pytest.mark.asyncio
    async def test_vm_sizes_requires_subscription(self):
        c = AzureAPIClient(subscription_id=None, access_token="t")
        c.subscription_id = None
        with pytest.raises(ValueError):
            await c.get_vm_sizes_for_region("eastus")

    @pytest.mark.asyncio
    async def test_vm_sizes_transform(self, client):
        client._get.return_value = {
            "value": [
                {"name": "Standard_D2", "numberOfCores": 2, "memoryInMB": 8192, "maxDataDiskCount": 4},
            ]
        }
        sizes = await client.get_vm_sizes_for_region("eastus")
        assert sizes[0]["name"] == "Standard_D2"
        assert sizes[0]["number_of_cores"] == 2

    @pytest.mark.asyncio
    async def test_vm_sizes_empty(self, client):
        client._get.return_value = None
        assert await client.get_vm_sizes_for_region("eastus") == []

    @pytest.mark.asyncio
    async def test_locations_transform(self, client):
        client._get.return_value = {
            "value": [{"name": "eastus", "displayName": "East US", "regionalDisplayName": "(US) East US"}]
        }
        locs = await client.get_locations()
        assert locs[0]["name"] == "eastus"
        assert locs[0]["display_name"] == "East US"

    @pytest.mark.asyncio
    async def test_locations_empty(self, client):
        client._get.return_value = None
        assert await client.get_locations() == []


class TestPublicClientSingleton:
    @pytest.mark.asyncio
    async def test_returns_same_instance(self):
        import backend.services.azure_api_client as mod

        mod._public_client = None
        a = await get_azure_public_client()
        b = await get_azure_public_client()
        assert a is b
