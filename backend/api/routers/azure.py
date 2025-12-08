"""
Azure Router

Handles Azure-specific dynamic options endpoints (VM sizes, locations, resource groups).
"""

from fastapi import APIRouter, Query
import os
import logging

from backend.api.schemas import StandardResponse, success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/azure", tags=["Azure"])

# Fallback data when Azure credentials are not available
FALLBACK_VM_SIZES = [
    {"name": "Standard_B1s", "vcpus": 1, "memory_gb": 1, "description": "1 vCPU, 1 GB RAM (Burstable)"},
    {"name": "Standard_B2s", "vcpus": 2, "memory_gb": 4, "description": "2 vCPUs, 4 GB RAM (Burstable)"},
    {"name": "Standard_B2ms", "vcpus": 2, "memory_gb": 8, "description": "2 vCPUs, 8 GB RAM (Burstable)"},
    {"name": "Standard_D2s_v3", "vcpus": 2, "memory_gb": 8, "description": "2 vCPUs, 8 GB RAM (General Purpose)"},
    {"name": "Standard_D4s_v3", "vcpus": 4, "memory_gb": 16, "description": "4 vCPUs, 16 GB RAM (General Purpose)"},
    {"name": "Standard_E2s_v3", "vcpus": 2, "memory_gb": 16, "description": "2 vCPUs, 16 GB RAM (Memory Optimized)"},
    {"name": "Standard_F2s_v2", "vcpus": 2, "memory_gb": 4, "description": "2 vCPUs, 4 GB RAM (Compute Optimized)"},
]

FALLBACK_LOCATIONS = [
    {"name": "norwayeast", "display_name": "Norway East"},
    {"name": "swedencentral", "display_name": "Sweden Central"},
    {"name": "westeurope", "display_name": "West Europe"},
    {"name": "northeurope", "display_name": "North Europe"},
    {"name": "eastus", "display_name": "East US"},
    {"name": "eastus2", "display_name": "East US 2"},
    {"name": "westus2", "display_name": "West US 2"},
    {"name": "centralus", "display_name": "Central US"},
]


def _has_valid_credentials() -> bool:
    """Check if valid Azure credentials are configured."""
    sub_id = os.getenv("AZURE_SUBSCRIPTION_ID")
    return bool(sub_id and not sub_id.startswith("00000000"))


@router.get("/vm-sizes", summary="Get Azure VM Sizes", response_model=StandardResponse)
async def get_azure_vm_sizes(location: str = Query(..., description="Azure location")):
    """Get available VM sizes for a specific Azure region."""
    if not _has_valid_credentials():
        return success_response(
            f"Available VM sizes for {location} (fallback)",
            {"location": location, "vm_sizes": FALLBACK_VM_SIZES, "count": len(FALLBACK_VM_SIZES)}
        )

    try:
        from backend.services.azure_api_client import AzureAPIClient
        async with AzureAPIClient() as client:
            vm_sizes_raw = await client.get_vm_sizes_for_region(location)

        if not vm_sizes_raw:
            return success_response(
                f"Available VM sizes for {location} (fallback)",
                {"location": location, "vm_sizes": FALLBACK_VM_SIZES, "count": len(FALLBACK_VM_SIZES)}
            )

        vm_sizes = [
            {
                "name": vm.get("name"),
                "vcpus": vm.get("number_of_cores", 0),
                "memory_gb": round(vm.get("memory_in_mb", 0) / 1024, 1),
                "description": f"{vm.get('number_of_cores', 0)} vCPUs, {round(vm.get('memory_in_mb', 0) / 1024, 1)} GB RAM"
            }
            for vm in vm_sizes_raw
        ]

        return success_response(
            f"Available VM sizes for {location}",
            {"location": location, "vm_sizes": vm_sizes, "count": len(vm_sizes)}
        )

    except Exception as e:
        logger.warning(f"Error fetching Azure VM sizes: {e}")
        return success_response(
            f"Available VM sizes for {location} (fallback)",
            {"location": location, "vm_sizes": FALLBACK_VM_SIZES, "count": len(FALLBACK_VM_SIZES)}
        )


@router.get("/locations", summary="Get Azure Locations", response_model=StandardResponse)
async def get_azure_locations():
    """Get all available Azure locations/regions."""
    if not _has_valid_credentials():
        return success_response(
            "Available Azure locations (fallback)",
            {"locations": FALLBACK_LOCATIONS, "count": len(FALLBACK_LOCATIONS)}
        )

    try:
        from backend.services.azure_api_client import AzureAPIClient
        async with AzureAPIClient() as client:
            locations_raw = await client.get_locations()

        if not locations_raw:
            return success_response(
                "Available Azure locations (fallback)",
                {"locations": FALLBACK_LOCATIONS, "count": len(FALLBACK_LOCATIONS)}
            )

        locations = [
            {"name": loc.get("name"), "display_name": loc.get("display_name") or loc.get("regional_display_name")}
            for loc in locations_raw
        ]

        return success_response(
            "Available Azure locations",
            {"locations": locations, "count": len(locations)}
        )

    except Exception as e:
        logger.warning(f"Error fetching Azure locations: {e}")
        return success_response(
            "Available Azure locations (fallback)",
            {"locations": FALLBACK_LOCATIONS, "count": len(FALLBACK_LOCATIONS)}
        )


@router.get("/resource-groups", summary="Get Azure Resource Groups", response_model=StandardResponse)
async def get_azure_resource_groups():
    """Get all Resource Groups in the Azure subscription."""
    if not _has_valid_credentials():
        return success_response(
            "Azure credentials not configured",
            {"resource_groups": [], "count": 0, "can_create_new": True}
        )

    try:
        import aiohttp
        from azure.identity import ClientSecretCredential

        subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        credential = ClientSecretCredential(
            tenant_id=os.getenv("AZURE_TENANT_ID"),
            client_id=os.getenv("AZURE_CLIENT_ID"),
            client_secret=os.getenv("AZURE_CLIENT_SECRET")
        )
        token = credential.get_token("https://management.azure.com/.default")

        url = f"https://management.azure.com/subscriptions/{subscription_id}/resourcegroups?api-version=2021-04-01"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={"Authorization": f"Bearer {token.token}"}) as response:
                if response.status == 200:
                    data = await response.json()
                    resource_groups = [
                        {"name": rg.get("name"), "location": rg.get("location")}
                        for rg in data.get("value", [])
                    ]
                    return success_response(
                        "Azure resource groups",
                        {"resource_groups": resource_groups, "count": len(resource_groups), "can_create_new": True}
                    )

        return success_response(
            "Could not fetch resource groups",
            {"resource_groups": [], "count": 0, "can_create_new": True}
        )

    except Exception as e:
        logger.warning(f"Error fetching Azure resource groups: {e}")
        return success_response(
            "Error fetching resource groups",
            {"resource_groups": [], "count": 0, "can_create_new": True}
        )
