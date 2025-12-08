"""
GCP Router

Handles GCP-specific dynamic options endpoints (machine types, zones, regions).
"""

from fastapi import APIRouter, Query
from typing import Optional
import os
import logging

from backend.api.schemas import StandardResponse, success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gcp", tags=["GCP"])

# Fallback data when GCP credentials are not available
FALLBACK_MACHINE_TYPES = [
    {"name": "e2-micro", "vcpus": 0.25, "memory_gb": 1, "description": "0.25 vCPU, 1 GB RAM (Shared-core)"},
    {"name": "e2-small", "vcpus": 0.5, "memory_gb": 2, "description": "0.5 vCPU, 2 GB RAM (Shared-core)"},
    {"name": "e2-medium", "vcpus": 1, "memory_gb": 4, "description": "1 vCPU, 4 GB RAM (Shared-core)"},
    {"name": "n1-standard-1", "vcpus": 1, "memory_gb": 3.75, "description": "1 vCPU, 3.75 GB RAM"},
    {"name": "n1-standard-2", "vcpus": 2, "memory_gb": 7.5, "description": "2 vCPUs, 7.5 GB RAM"},
    {"name": "n2-standard-2", "vcpus": 2, "memory_gb": 8, "description": "2 vCPUs, 8 GB RAM"},
    {"name": "n2-standard-4", "vcpus": 4, "memory_gb": 16, "description": "4 vCPUs, 16 GB RAM"},
]

FALLBACK_ZONES = [
    {"name": "us-central1-a", "region": "us-central1", "description": "US Central (Iowa) - Zone A"},
    {"name": "us-central1-b", "region": "us-central1", "description": "US Central (Iowa) - Zone B"},
    {"name": "us-east1-b", "region": "us-east1", "description": "US East (South Carolina) - Zone B"},
    {"name": "europe-west1-b", "region": "europe-west1", "description": "Europe West (Belgium) - Zone B"},
    {"name": "europe-west2-a", "region": "europe-west2", "description": "Europe West (London) - Zone A"},
    {"name": "europe-north1-a", "region": "europe-north1", "description": "Europe North (Finland) - Zone A"},
    {"name": "asia-east1-a", "region": "asia-east1", "description": "Asia East (Taiwan) - Zone A"},
]

FALLBACK_REGIONS = [
    {"name": "us-central1", "display_name": "US Central (Iowa)"},
    {"name": "us-east1", "display_name": "US East (South Carolina)"},
    {"name": "us-west1", "display_name": "US West (Oregon)"},
    {"name": "europe-west1", "display_name": "Europe West (Belgium)"},
    {"name": "europe-west2", "display_name": "Europe West (London)"},
    {"name": "europe-north1", "display_name": "Europe North (Finland)"},
    {"name": "asia-east1", "display_name": "Asia East (Taiwan)"},
    {"name": "asia-southeast1", "display_name": "Asia Southeast (Singapore)"},
]


def _has_valid_credentials() -> bool:
    """Check if valid GCP credentials are configured."""
    project_id = os.getenv("GOOGLE_PROJECT_ID")
    return bool(project_id and not project_id.startswith("your-"))


@router.get("/projects", summary="Get GCP Projects", response_model=StandardResponse)
async def get_gcp_projects():
    """Get available GCP projects."""
    project_id = os.getenv("GOOGLE_PROJECT_ID")

    if not project_id or project_id.startswith("your-"):
        return success_response("GCP project not configured", {"projects": [], "count": 0})

    return success_response(
        "GCP projects",
        {"projects": [{"name": project_id, "display_name": project_id}], "count": 1}
    )


@router.get("/machine-types", summary="Get GCP Machine Types", response_model=StandardResponse)
async def get_gcp_machine_types(
    zone: Optional[str] = Query(None, description="GCP zone"),
    region: Optional[str] = Query(None, description="GCP region")
):
    """Get available GCP machine types."""
    if not _has_valid_credentials():
        return success_response(
            "Available GCP machine types (fallback)",
            {"zone": zone, "region": region, "machine_types": FALLBACK_MACHINE_TYPES, "count": len(FALLBACK_MACHINE_TYPES)}
        )

    try:
        from backend.services.gcp_api_client import GCPAPIClient
        async with GCPAPIClient() as client:
            # Get zone from region if needed
            target_zone = zone
            if not target_zone and region:
                zones = await client.get_zones(region=region)
                if zones:
                    target_zone = zones[0].get("name")

            machine_types = await client.get_machine_types(zone=target_zone)

        if not machine_types:
            return success_response(
                "Available GCP machine types (fallback)",
                {"zone": zone, "region": region, "machine_types": FALLBACK_MACHINE_TYPES, "count": len(FALLBACK_MACHINE_TYPES)}
            )

        return success_response(
            "Available GCP machine types",
            {"zone": target_zone, "region": region, "machine_types": machine_types, "count": len(machine_types)}
        )

    except Exception as e:
        logger.warning(f"Error fetching GCP machine types: {e}")
        return success_response(
            "Available GCP machine types (fallback)",
            {"zone": zone, "region": region, "machine_types": FALLBACK_MACHINE_TYPES, "count": len(FALLBACK_MACHINE_TYPES)}
        )


@router.get("/zones", summary="Get GCP Zones", response_model=StandardResponse)
async def get_gcp_zones(region: Optional[str] = Query(None, description="Filter by region")):
    """Get all available GCP zones."""
    if not _has_valid_credentials():
        zones = [z for z in FALLBACK_ZONES if not region or z["region"] == region]
        return success_response(
            f"Available GCP zones (fallback){f' in {region}' if region else ''}",
            {"zones": zones, "count": len(zones)}
        )

    try:
        from backend.services.gcp_api_client import GCPAPIClient
        async with GCPAPIClient() as client:
            zones = await client.get_zones(region=region)

        if not zones:
            zones = [z for z in FALLBACK_ZONES if not region or z["region"] == region]
            return success_response(
                f"Available GCP zones (fallback){f' in {region}' if region else ''}",
                {"zones": zones, "count": len(zones)}
            )

        return success_response(
            f"Available GCP zones{f' in {region}' if region else ''}",
            {"zones": zones, "count": len(zones)}
        )

    except Exception as e:
        logger.warning(f"Error fetching GCP zones: {e}")
        zones = [z for z in FALLBACK_ZONES if not region or z["region"] == region]
        return success_response(
            f"Available GCP zones (fallback){f' in {region}' if region else ''}",
            {"zones": zones, "count": len(zones)}
        )


@router.get("/regions", summary="Get GCP Regions", response_model=StandardResponse)
async def get_gcp_regions():
    """Get all available GCP regions."""
    if not _has_valid_credentials():
        return success_response(
            "Available GCP regions (fallback)",
            {"regions": FALLBACK_REGIONS, "count": len(FALLBACK_REGIONS)}
        )

    try:
        from backend.services.gcp_api_client import GCPAPIClient
        async with GCPAPIClient() as client:
            regions = await client.get_regions()

        if not regions:
            return success_response(
                "Available GCP regions (fallback)",
                {"regions": FALLBACK_REGIONS, "count": len(FALLBACK_REGIONS)}
            )

        return success_response(
            "Available GCP regions",
            {"regions": regions, "count": len(regions)}
        )

    except Exception as e:
        logger.warning(f"Error fetching GCP regions: {e}")
        return success_response(
            "Available GCP regions (fallback)",
            {"regions": FALLBACK_REGIONS, "count": len(FALLBACK_REGIONS)}
        )
