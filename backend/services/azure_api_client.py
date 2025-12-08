"""
Azure API Client

Client for interacting with various Azure REST APIs:
- Azure Retail Prices API (public, no auth)
- Azure Management API (requires authentication)
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from backend.services.base_api_client import BaseCloudAPIClient

logger = logging.getLogger(__name__)

# Try to import Azure Identity for authentication
try:
    from azure.identity import ClientSecretCredential, DefaultAzureCredential
    AZURE_IDENTITY_AVAILABLE = True
except ImportError:
    AZURE_IDENTITY_AVAILABLE = False
    logger.warning("azure-identity not installed - Management API calls will be limited")

# Azure API endpoints
AZURE_RETAIL_PRICES_API = "https://prices.azure.com/api/retail/prices"
AZURE_MANAGEMENT_API = "https://management.azure.com"


class AzureAPIClient(BaseCloudAPIClient):
    """Client for Azure REST APIs"""

    def __init__(self, subscription_id: Optional[str] = None, access_token: Optional[str] = None):
        """
        Initialize Azure API client.

        Args:
            subscription_id: Azure subscription ID (for Management API)
            access_token: Azure access token (optional, will be auto-obtained)
        """
        super().__init__(timeout=30.0)

        self.subscription_id = subscription_id or os.getenv("AZURE_SUBSCRIPTION_ID")
        self.access_token = access_token

        # Initialize Azure credential if available
        if not self.access_token and AZURE_IDENTITY_AVAILABLE:
            self._initialize_credentials()

    def _initialize_credentials(self):
        """Initialize Azure credential for authentication."""
        try:
            tenant_id = os.getenv("AZURE_TENANT_ID")
            client_id = os.getenv("AZURE_CLIENT_ID")
            client_secret = os.getenv("AZURE_CLIENT_SECRET")

            if tenant_id and client_id and client_secret:
                logger.info("Initializing Azure authentication with Service Principal")
                self._credentials = ClientSecretCredential(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    client_secret=client_secret
                )
            else:
                logger.info("Initializing Azure authentication with DefaultAzureCredential")
                self._credentials = DefaultAzureCredential()

        except Exception as e:
            logger.warning(f"Failed to initialize Azure credential: {e}")
            self._credentials = None

    def _get_access_token(self) -> Optional[str]:
        """Get or refresh Azure access token."""
        if self.access_token:
            return self.access_token

        if not self._credentials:
            return None

        try:
            token = self._credentials.get_token("https://management.azure.com/.default")
            return token.token
        except Exception as e:
            logger.error(f"Failed to get Azure access token: {e}")
            return None

    # ==================== Azure Retail Prices API (Public) ====================

    async def get_vm_pricing(
        self,
        vm_size: str,
        region: str,
        operating_system: str = "Linux"
    ) -> Optional[Dict[str, Any]]:
        """
        Get real-time pricing for Azure VM from Retail Prices API.
        This is a PUBLIC API - no authentication required!
        """
        self._log_api_call("Fetching Azure VM pricing", vm_size=vm_size, region=region)

        filter_query = (
            f"serviceName eq 'Virtual Machines' "
            f"and armSkuName eq '{vm_size}' "
            f"and armRegionName eq '{region}' "
            f"and priceType eq 'Consumption'"
        )

        if operating_system.lower() == "windows":
            filter_query += " and productName contains 'Windows'"
        else:
            filter_query += " and productName contains 'Linux'"

        data = await self._get(
            AZURE_RETAIL_PRICES_API,
            params={"$filter": filter_query, "currencyCode": "USD"},
            require_auth=False
        )

        if not data:
            return None

        items = data.get("Items", [])
        if not items:
            logger.warning(f"No pricing found for {vm_size} in {region}")
            return None

        pricing = items[0]
        return {
            "vm_size": vm_size,
            "region": region,
            "operating_system": operating_system,
            "retail_price_per_hour": pricing.get("retailPrice", 0.0),
            "retail_price_per_month": pricing.get("retailPrice", 0.0) * 730,
            "unit_of_measure": pricing.get("unitOfMeasure", "1 Hour"),
            "currency": pricing.get("currencyCode", "USD"),
            "product_name": pricing.get("productName", ""),
            "sku_name": pricing.get("skuName", ""),
            "meter_name": pricing.get("meterName", ""),
            "last_updated": self._format_timestamp()
        }

    async def get_storage_pricing(
        self,
        storage_type: str,
        region: str,
        redundancy: str = "LRS"
    ) -> Optional[Dict[str, Any]]:
        """Get real-time pricing for Azure Storage."""
        regions_to_try = [region, "westeurope", "eastus"]

        for try_region in regions_to_try:
            result = await self._fetch_storage_pricing(storage_type, try_region, redundancy)
            if result:
                if try_region != region:
                    result["note"] = f"Pricing from {try_region} (not available for {region})"
                return result

        return None

    async def _fetch_storage_pricing(
        self,
        storage_type: str,
        region: str,
        redundancy: str
    ) -> Optional[Dict[str, Any]]:
        """Internal method to fetch storage pricing."""
        self._log_api_call("Fetching Azure Storage pricing", storage_type=storage_type, region=region, redundancy=redundancy)

        filter_query = (
            f"serviceName eq 'Storage' "
            f"and armRegionName eq '{region}' "
            f"and priceType eq 'Consumption'"
        )

        data = await self._get(
            AZURE_RETAIL_PRICES_API,
            params={"$filter": filter_query, "currencyCode": "USD"},
            require_auth=False
        )

        if not data:
            return None

        items = data.get("Items", [])
        if not items:
            return None

        # Filter based on storage type and redundancy
        if storage_type.lower() == "premium":
            matching_items = [
                item for item in items
                if "Premium" in item.get("skuName", "")
                and redundancy in item.get("skuName", "")
                and "Data Stored" in item.get("meterName", "")
            ]
        else:
            sku_prefix = f"Hot {redundancy}"
            matching_items = [
                item for item in items
                if "Block Blob" in item.get("productName", "")
                and "Data Stored" in item.get("meterName", "")
                and item.get("skuName", "").startswith(sku_prefix)
            ]

        if not matching_items:
            matching_items = [
                item for item in items
                if "Data Stored" in item.get("meterName", "")
                and redundancy in item.get("skuName", "")
            ]

        if not matching_items:
            return None

        pricing = matching_items[0]
        return {
            "storage_type": storage_type,
            "redundancy": redundancy,
            "region": region,
            "price_per_gb_month": pricing.get("retailPrice", 0.0),
            "unit_of_measure": pricing.get("unitOfMeasure", "1 GB/Month"),
            "currency": pricing.get("currencyCode", "USD"),
            "product_name": pricing.get("productName", ""),
            "sku_name": pricing.get("skuName", ""),
            "meter_name": pricing.get("meterName", ""),
            "last_updated": self._format_timestamp()
        }

    async def get_disk_pricing(
        self,
        disk_type: str,
        region: str,
        size_gb: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get real-time pricing for Azure Managed Disks."""
        self._log_api_call("Fetching Azure Disk pricing", disk_type=disk_type, region=region)

        disk_service_map = {
            "Standard_LRS": "Standard HDD Managed Disks",
            "StandardSSD_LRS": "Standard SSD Managed Disks",
            "Premium_LRS": "Premium SSD Managed Disks",
            "PremiumV2_LRS": "Premium SSD v2 Managed Disks"
        }

        service_name = disk_service_map.get(disk_type, "Standard SSD Managed Disks")

        filter_query = (
            f"serviceName eq '{service_name}' "
            f"and armRegionName eq '{region}' "
            f"and priceType eq 'Consumption'"
        )

        data = await self._get(
            AZURE_RETAIL_PRICES_API,
            params={"$filter": filter_query, "currencyCode": "USD"},
            require_auth=False
        )

        if not data:
            return None

        items = data.get("Items", [])
        if not items:
            return None

        pricing = items[0]
        if size_gb:
            for item in items:
                if "Provisioned" in item.get("meterName", "") or "Disk" in item.get("meterName", ""):
                    pricing = item
                    break

        return {
            "disk_type": disk_type,
            "region": region,
            "price_per_month": pricing.get("retailPrice", 0.0),
            "unit_of_measure": pricing.get("unitOfMeasure", "1/Month"),
            "currency": pricing.get("currencyCode", "USD"),
            "product_name": pricing.get("productName", ""),
            "sku_name": pricing.get("skuName", ""),
            "meter_name": pricing.get("meterName", ""),
            "last_updated": self._format_timestamp()
        }

    # ==================== Azure Management API (Authenticated) ====================

    async def get_vm_sizes_for_region(self, location: str) -> List[Dict[str, Any]]:
        """Get available VM sizes for a specific region."""
        if not self.subscription_id:
            raise ValueError("Subscription ID required")

        self._log_api_call("Fetching VM sizes", location=location)

        url = (
            f"{AZURE_MANAGEMENT_API}/subscriptions/{self.subscription_id}"
            f"/providers/Microsoft.Compute/locations/{location}/vmSizes"
        )

        data = await self._get(url, params={"api-version": "2023-03-01"})

        if not data:
            return []

        return [
            {
                "name": vm.get("name"),
                "number_of_cores": vm.get("numberOfCores"),
                "memory_in_mb": vm.get("memoryInMB"),
                "max_data_disk_count": vm.get("maxDataDiskCount"),
                "os_disk_size_in_mb": vm.get("osDiskSizeInMB"),
                "resource_disk_size_in_mb": vm.get("resourceDiskSizeInMB")
            }
            for vm in data.get("value", [])
        ]

    async def get_locations(self) -> List[Dict[str, Any]]:
        """Get all available Azure locations/regions."""
        if not self.subscription_id:
            raise ValueError("Subscription ID required")

        self._log_api_call("Fetching Azure locations")

        url = f"{AZURE_MANAGEMENT_API}/subscriptions/{self.subscription_id}/locations"

        data = await self._get(url, params={"api-version": "2022-12-01"})

        if not data:
            return []

        return [
            {
                "name": loc.get("name"),
                "display_name": loc.get("displayName"),
                "regional_display_name": loc.get("regionalDisplayName")
            }
            for loc in data.get("value", [])
        ]


# Global client instance
_public_client: Optional[AzureAPIClient] = None


async def get_azure_public_client() -> AzureAPIClient:
    """Get or create Azure public API client (for Retail Prices API)."""
    global _public_client
    if _public_client is None:
        _public_client = AzureAPIClient()
    return _public_client
