"""
Python Client Example for Multi-Cloud Infrastructure Management API

This demonstrates how to interact with the API using Python requests library.
"""

import requests
import json
from typing import Dict, Any, Optional


class MultiCloudClient:
    """
    Python client for Multi-Cloud Infrastructure Management API.

    Example usage:
        client = MultiCloudClient("http://localhost:8000")

        # List providers
        providers = client.list_providers()

        # Deploy to AWS
        result = client.deploy(
            template_name="storage-bucket",
            provider_type="terraform-aws",
            subscription_id="123456789012",
            resource_group="my-resources",
            location="us-east-1",
            parameters={"bucket_name": "my-unique-bucket"}
        )
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize client.

        Args:
            base_url: Base URL of the API
        """
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request."""
        url = f"{self.base_url}{endpoint}"
        response = self.session.request(method, url, **kwargs)

        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}")
            print(f"Response: {response.text}")
            raise

    def health_check(self) -> Dict[str, Any]:
        """Check API health."""
        return self._request("GET", "/health")

    def list_providers(self) -> Dict[str, Any]:
        """List available cloud providers."""
        return self._request("GET", "/providers")

    def list_templates(
        self,
        provider_type: Optional[str] = None,
        cloud: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List available templates.

        Args:
            provider_type: Filter by provider (e.g., "terraform-aws")
            cloud: Filter by cloud (e.g., "aws")
        """
        params = {}
        if provider_type:
            params["provider_type"] = provider_type
        if cloud:
            params["cloud"] = cloud

        return self._request("GET", "/templates", params=params)

    def get_template(self, provider_type: str, template_name: str) -> Dict[str, Any]:
        """Get template details."""
        return self._request("GET", f"/templates/{provider_type}/{template_name}")

    def get_template_content(self, provider_type: str, template_name: str) -> str:
        """Get template file content."""
        result = self._request("GET", f"/templates/{provider_type}/{template_name}/content")
        return result.get("content", "")

    def deploy(
        self,
        template_name: str,
        provider_type: str,
        subscription_id: str,
        resource_group: str,
        location: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Deploy infrastructure.

        Args:
            template_name: Name of template to deploy
            provider_type: Cloud provider (azure, terraform-aws, terraform-gcp)
            subscription_id: Subscription/account/project ID
            resource_group: Resource group/stack name
            location: Region/location
            parameters: Template parameters

        Returns:
            Deployment result with deployment_id
        """
        payload = {
            "template_name": template_name,
            "provider_type": provider_type,
            "subscription_id": subscription_id,
            "resource_group": resource_group,
            "location": location,
            "parameters": parameters
        }

        return self._request("POST", "/deploy", json=payload)

    def get_deployment_status(
        self,
        deployment_id: str,
        provider_type: str,
        subscription_id: str,
        resource_group: str
    ) -> Dict[str, Any]:
        """Get deployment status."""
        params = {
            "provider_type": provider_type,
            "subscription_id": subscription_id,
            "resource_group": resource_group
        }

        return self._request("GET", f"/deployments/{deployment_id}/status", params=params)

    def list_resource_groups(
        self,
        provider_type: str,
        subscription_id: str
    ) -> Dict[str, Any]:
        """List resource groups."""
        params = {
            "provider_type": provider_type,
            "subscription_id": subscription_id
        }

        return self._request("GET", "/resource-groups", params=params)

    def create_resource_group(
        self,
        name: str,
        location: str,
        subscription_id: str,
        provider_type: str = "azure",
        tags: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create resource group."""
        payload = {
            "name": name,
            "location": location,
            "subscription_id": subscription_id,
            "provider_type": provider_type,
            "tags": tags or {}
        }

        return self._request("POST", "/resource-groups", json=payload)

    def delete_resource_group(
        self,
        resource_group_name: str,
        provider_type: str,
        subscription_id: str
    ) -> Dict[str, Any]:
        """Delete resource group."""
        params = {
            "provider_type": provider_type,
            "subscription_id": subscription_id
        }

        return self._request("DELETE", f"/resource-groups/{resource_group_name}", params=params)

    def list_resources(
        self,
        resource_group_name: str,
        provider_type: str,
        subscription_id: str
    ) -> Dict[str, Any]:
        """List resources in resource group."""
        params = {
            "provider_type": provider_type,
            "subscription_id": subscription_id
        }

        return self._request("GET", f"/resource-groups/{resource_group_name}/resources", params=params)


# ==================== Usage Examples ====================

def example_1_health_check():
    """Example 1: Check API health."""
    print("=" * 50)
    print("Example 1: Health Check")
    print("=" * 50)

    client = MultiCloudClient()
    health = client.health_check()

    print(json.dumps(health, indent=2))


def example_2_list_providers():
    """Example 2: List available providers."""
    print("\n" + "=" * 50)
    print("Example 2: List Providers")
    print("=" * 50)

    client = MultiCloudClient()
    providers = client.list_providers()

    print(f"Success: {providers['success']}")
    print(f"Message: {providers['message']}")
    print("\nProviders:")
    for provider in providers['data']['providers']:
        print(f"  - {provider['id']}: {provider['name']} ({provider['template_count']} templates)")


def example_3_list_templates():
    """Example 3: List templates for AWS."""
    print("\n" + "=" * 50)
    print("Example 3: List AWS Templates")
    print("=" * 50)

    client = MultiCloudClient()
    templates = client.list_templates(cloud="aws")

    print(f"Found {templates['data']['count']} templates for AWS:")
    for template in templates['data']['templates']:
        print(f"  - {template['name']}: {template['display_name']}")
        print(f"    Format: {template['format']}, Icon: {template['icon']}")


def example_4_deploy_to_aws():
    """Example 4: Deploy S3 bucket to AWS."""
    print("\n" + "=" * 50)
    print("Example 4: Deploy to AWS")
    print("=" * 50)

    client = MultiCloudClient()

    # Deploy S3 bucket
    result = client.deploy(
        template_name="storage-bucket",
        provider_type="terraform-aws",
        subscription_id="123456789012",  # Your AWS account ID
        resource_group="my-app-stack",
        location="us-east-1",
        parameters={
            "bucket_name": "my-unique-test-bucket-12345",
            "enable_versioning": True
        }
    )

    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")

    if result['success']:
        deployment_id = result['data']['deployment_id']
        print(f"Deployment ID: {deployment_id}")
        print(f"Status: {result['data']['status']}")


def example_5_multi_cloud_comparison():
    """Example 5: Compare storage across clouds."""
    print("\n" + "=" * 50)
    print("Example 5: Multi-Cloud Storage Comparison")
    print("=" * 50)

    client = MultiCloudClient()

    clouds = {
        "Azure": ("terraform-azure", "storage-account"),
        "AWS": ("terraform-aws", "storage-bucket"),
        "GCP": ("terraform-gcp", "storage-bucket")
    }

    for cloud_name, (provider, template) in clouds.items():
        templates = client.list_templates(provider_type=provider)
        template_info = None

        for t in templates['data']['templates']:
            if t['name'] == template:
                template_info = t
                break

        if template_info:
            print(f"\n{cloud_name}:")
            print(f"  Template: {template_info['display_name']}")
            print(f"  Format: {template_info['format']}")
            print(f"  Path: {template_info['path']}")


if __name__ == "__main__":
    """Run all examples."""
    print("Multi-Cloud API Client Examples")
    print("================================\n")

    try:
        example_1_health_check()
        example_2_list_providers()
        example_3_list_templates()

        # Uncomment to run deployment examples (requires credentials)
        # example_4_deploy_to_aws()

        example_5_multi_cloud_comparison()

        print("\n" + "=" * 50)
        print("Examples completed successfully!")
        print("=" * 50)

    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to API.")
        print("Make sure the API is running:")
        print("  cd backend")
        print("  uvicorn api_rest:app --reload")
    except Exception as e:
        print(f"ERROR: {e}")
