"""
GCP API Client

Client for interacting with various GCP REST APIs:
- Cloud Billing Catalog API (for pricing)
- Compute Engine API (for machine types, zones, etc.)
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from backend.services.base_api_client import BaseCloudAPIClient

logger = logging.getLogger(__name__)

# Try to import Google auth libraries
try:
    from google.auth import default as google_auth_default
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False
    logger.warning("google-auth not installed - GCP Management API calls will be limited")

# GCP API endpoints
GCP_COMPUTE_API = "https://compute.googleapis.com/compute/v1"


class GCPAPIClient(BaseCloudAPIClient):
    """Client for GCP REST APIs"""

    def __init__(self, project_id: Optional[str] = None, access_token: Optional[str] = None):
        """
        Initialize GCP API client.

        Args:
            project_id: GCP project ID
            access_token: GCP access token (optional, will be auto-obtained)
        """
        super().__init__(timeout=30.0)

        self.project_id = project_id or os.getenv("GOOGLE_PROJECT_ID")
        self.access_token = access_token

        # Initialize Google credentials if available
        if not self.access_token and GOOGLE_AUTH_AVAILABLE:
            self._initialize_credentials()

    def _initialize_credentials(self):
        """Initialize Google credentials for authentication."""
        try:
            credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

            if credentials_path and os.path.exists(credentials_path):
                logger.info("Initializing GCP authentication with service account JSON")
                self._credentials = service_account.Credentials.from_service_account_file(
                    credentials_path,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
            else:
                logger.info("Initializing GCP authentication with Application Default Credentials")
                self._credentials, project = google_auth_default(
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
                if not self.project_id and project:
                    self.project_id = project

        except Exception as e:
            logger.warning(f"Failed to initialize GCP credentials: {e}")
            self._credentials = None

    def _get_access_token(self) -> Optional[str]:
        """Get or refresh GCP access token."""
        if self.access_token:
            return self.access_token

        if not self._credentials:
            return None

        try:
            if not self._credentials.valid:
                self._credentials.refresh(Request())
            return self._credentials.token
        except Exception as e:
            logger.error(f"Failed to get GCP access token: {e}")
            return None

    # ==================== GCP Pricing (Static Database) ====================

    async def get_compute_pricing(
        self,
        machine_type: str,
        region: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get pricing for GCP Compute Engine instance.
        Uses simplified static pricing database.
        """
        # Simplified pricing database for common machine types
        base_pricing = {
            # E2 series (cost-optimized)
            "e2-micro": {"vcpu": 0.25, "memory_gb": 1, "price_per_month": 6.11},
            "e2-small": {"vcpu": 0.5, "memory_gb": 2, "price_per_month": 12.22},
            "e2-medium": {"vcpu": 1, "memory_gb": 4, "price_per_month": 24.44},
            "e2-standard-2": {"vcpu": 2, "memory_gb": 8, "price_per_month": 48.88},
            "e2-standard-4": {"vcpu": 4, "memory_gb": 16, "price_per_month": 97.76},
            "e2-standard-8": {"vcpu": 8, "memory_gb": 32, "price_per_month": 195.52},
            # N1 series
            "n1-standard-1": {"vcpu": 1, "memory_gb": 3.75, "price_per_month": 24.95},
            "n1-standard-2": {"vcpu": 2, "memory_gb": 7.5, "price_per_month": 49.90},
            "n1-standard-4": {"vcpu": 4, "memory_gb": 15, "price_per_month": 99.80},
            "n1-standard-8": {"vcpu": 8, "memory_gb": 30, "price_per_month": 199.60},
            # N2 series
            "n2-standard-2": {"vcpu": 2, "memory_gb": 8, "price_per_month": 60.74},
            "n2-standard-4": {"vcpu": 4, "memory_gb": 16, "price_per_month": 121.48},
            "n2-standard-8": {"vcpu": 8, "memory_gb": 32, "price_per_month": 242.96},
        }

        pricing_info = base_pricing.get(machine_type.lower())
        if not pricing_info:
            logger.warning(f"No pricing found for machine type: {machine_type}")
            return None

        # Regional pricing adjustments
        region_multipliers = {
            "us-central1": 1.0, "us-east1": 1.0, "us-west1": 1.0,
            "europe-west1": 1.08, "europe-west2": 1.10,
            "asia-southeast1": 1.12, "asia-northeast1": 1.15,
        }

        multiplier = region_multipliers.get(region, 1.0)
        adjusted_price = pricing_info["price_per_month"] * multiplier

        return {
            "machine_type": machine_type,
            "region": region,
            "vcpu_count": pricing_info["vcpu"],
            "memory_gb": pricing_info["memory_gb"],
            "price_per_month": round(adjusted_price, 2),
            "price_per_hour": round(adjusted_price / 730, 4),
            "currency": "USD",
            "notes": [
                "Sustained use discounts may apply (up to 30% savings)",
                "Committed use discounts available for 1-3 year terms",
                "Preemptible VMs available at ~70-80% discount"
            ],
            "last_updated": self._format_timestamp()
        }

    async def get_storage_pricing(
        self,
        storage_class: str,
        region: str
    ) -> Optional[Dict[str, Any]]:
        """Get pricing for GCP Cloud Storage."""
        storage_pricing = {
            "STANDARD": {"us-central1": 0.020, "us-east1": 0.020, "europe-west1": 0.020, "asia-southeast1": 0.023},
            "NEARLINE": {"us-central1": 0.010, "us-east1": 0.010, "europe-west1": 0.010, "asia-southeast1": 0.013},
            "COLDLINE": {"us-central1": 0.004, "us-east1": 0.004, "europe-west1": 0.004, "asia-southeast1": 0.007},
            "ARCHIVE": {"us-central1": 0.0012, "us-east1": 0.0012, "europe-west1": 0.0012, "asia-southeast1": 0.0025},
        }

        class_pricing = storage_pricing.get(storage_class.upper(), {})
        price_per_gb = class_pricing.get(region, class_pricing.get("us-central1", 0.020))

        return {
            "storage_class": storage_class,
            "region": region,
            "price_per_gb_month": price_per_gb,
            "currency": "USD",
            "notes": ["Operations and network egress charges apply separately"],
            "last_updated": self._format_timestamp()
        }

    async def get_disk_pricing(
        self,
        disk_type: str,
        region: str
    ) -> Optional[Dict[str, Any]]:
        """Get pricing for GCP Persistent Disks."""
        disk_pricing = {
            "pd-standard": 0.040,
            "pd-balanced": 0.100,
            "pd-ssd": 0.170,
            "pd-extreme": 0.125,
        }

        price_per_gb = disk_pricing.get(disk_type, 0.100)

        return {
            "disk_type": disk_type,
            "region": region,
            "price_per_gb_month": price_per_gb,
            "currency": "USD",
            "notes": [
                "Regional persistent disks cost 2x of zonal disks",
                "Snapshots are billed separately at $0.026 per GB/month"
            ],
            "last_updated": self._format_timestamp()
        }

    # ==================== GCP Compute Engine API (Authenticated) ====================

    async def get_regions(self) -> List[Dict[str, Any]]:
        """Get all available GCP regions from Compute Engine API."""
        if not self.project_id:
            logger.warning("Project ID not set, returning empty regions list")
            return []

        self._log_api_call("Fetching GCP regions")

        url = f"{GCP_COMPUTE_API}/projects/{self.project_id}/regions"
        data = await self._get(url)

        if not data:
            return []

        return [
            {
                "name": region.get("name"),
                "display_name": region.get("description", region.get("name")),
                "status": region.get("status"),
                "zones": [z.split("/")[-1] for z in region.get("zones", [])]
            }
            for region in data.get("items", [])
        ]

    async def get_zones(self, region: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all available GCP zones, optionally filtered by region."""
        if not self.project_id:
            logger.warning("Project ID not set, returning empty zones list")
            return []

        self._log_api_call("Fetching GCP zones", region=region)

        url = f"{GCP_COMPUTE_API}/projects/{self.project_id}/zones"
        data = await self._get(url)

        if not data:
            return []

        zones = data.get("items", [])

        # Filter by region if specified
        if region:
            zones = [z for z in zones if z.get("region", "").endswith(f"/{region}")]

        return [
            {
                "name": zone.get("name"),
                "region": zone.get("region", "").split("/")[-1],
                "status": zone.get("status"),
                "description": zone.get("description")
            }
            for zone in zones
        ]

    async def get_machine_types(self, zone: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get available machine types, optionally filtered by zone."""
        if not self.project_id:
            logger.warning("Project ID not set, returning empty machine types list")
            return []

        target_zone = zone or "us-central1-a"
        self._log_api_call("Fetching GCP machine types", zone=target_zone)

        url = f"{GCP_COMPUTE_API}/projects/{self.project_id}/zones/{target_zone}/machineTypes"
        data = await self._get(url)

        if not data:
            return []

        return [
            {
                "name": mt.get("name"),
                "vcpus": mt.get("guestCpus", 0),
                "memory_gb": round(mt.get("memoryMb", 0) / 1024, 2),
                "description": mt.get("description", f"{mt.get('guestCpus', 0)} vCPUs, {round(mt.get('memoryMb', 0) / 1024, 1)} GB RAM"),
                "zone": target_zone
            }
            for mt in data.get("items", [])
        ]


# Global client instance
_public_client: Optional[GCPAPIClient] = None


async def get_gcp_client() -> GCPAPIClient:
    """Get or create GCP API client."""
    global _public_client
    if _public_client is None:
        _public_client = GCPAPIClient()
    return _public_client
