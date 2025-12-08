"""
Resource Groups Router

Handles resource group creation, listing, and deletion.
"""

from fastapi import APIRouter, Query, status
import logging

from backend.api.schemas import StandardResponse, ResourceGroupCreateRequest, success_response, error_response
from backend.providers import get_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resource-groups", tags=["Resource Groups"])


@router.get("", summary="List Resource Groups", response_model=StandardResponse)
async def list_resource_groups(
    provider_type: str = Query("azure", description="Provider type"),
    subscription_id: str = Query(..., description="Subscription/account ID")
):
    """List all resource groups/stacks in the subscription."""
    try:
        provider = get_provider(provider_type, subscription_id=subscription_id)
        groups = await provider.list_resource_groups()

        return success_response(
            message=f"Found {len(groups)} resource groups",
            data={
                "resource_groups": [
                    {"name": g.name, "location": g.location, "resource_count": g.resource_count, "tags": g.tags}
                    for g in groups
                ],
                "count": len(groups)
            }
        )

    except Exception as e:
        logger.exception(f"Error listing resource groups: {e}")
        return error_response("Failed to list resource groups", str(e), 500)


@router.post("", summary="Create Resource Group", response_model=StandardResponse, status_code=status.HTTP_201_CREATED)
async def create_resource_group(request: ResourceGroupCreateRequest):
    """Create a new resource group/stack."""
    try:
        provider = get_provider(request.provider_type, subscription_id=request.subscription_id)
        group = await provider.create_resource_group(
            name=request.name,
            location=request.location,
            tags=request.tags
        )

        return success_response(
            message=f"Resource group '{request.name}' created",
            data={"name": group.name, "location": group.location, "provider_id": group.provider_id}
        )

    except Exception as e:
        logger.exception(f"Error creating resource group: {e}")
        return error_response("Failed to create resource group", str(e), 500)


@router.delete("/{resource_group_name}", summary="Delete Resource Group", response_model=StandardResponse)
async def delete_resource_group(
    resource_group_name: str,
    provider_type: str = Query("azure", description="Provider type"),
    subscription_id: str = Query(..., description="Subscription/account ID")
):
    """Delete a resource group and all its resources."""
    try:
        provider = get_provider(provider_type, subscription_id=subscription_id)
        success = await provider.delete_resource_group(resource_group_name)

        if success:
            return success_response(
                message=f"Resource group '{resource_group_name}' deletion initiated",
                data={"resource_group": resource_group_name}
            )
        else:
            return error_response(f"Resource group '{resource_group_name}' not found", status_code=404)

    except Exception as e:
        logger.exception(f"Error deleting resource group: {e}")
        return error_response("Failed to delete resource group", str(e), 500)


@router.get("/{resource_group_name}/resources", summary="List Resources in Group", response_model=StandardResponse)
async def list_resources_in_group(
    resource_group_name: str,
    provider_type: str = Query("azure", description="Provider type"),
    subscription_id: str = Query(..., description="Subscription/account ID")
):
    """List all resources within a resource group."""
    try:
        provider = get_provider(provider_type, subscription_id=subscription_id)
        resources = await provider.list_resources(resource_group_name)

        return success_response(
            message=f"Found {len(resources)} resources",
            data={
                "resource_group": resource_group_name,
                "resources": [
                    {"id": r.id, "name": r.name, "type": r.type, "location": r.location, "tags": r.tags}
                    for r in resources
                ],
                "count": len(resources)
            }
        )

    except Exception as e:
        logger.exception(f"Error listing resources: {e}")
        return error_response("Failed to list resources", str(e), 500)
