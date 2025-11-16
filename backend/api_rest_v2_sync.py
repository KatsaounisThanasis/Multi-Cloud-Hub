"""
Production-Ready REST API for Multi-Cloud Infrastructure Management

This is the main REST API application with proper structure,
documentation, and production-ready features.
"""

from fastapi import FastAPI, HTTPException, Query, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import os
import logging
from datetime import datetime

# Import our provider abstraction
from backend.providers import get_provider, ProviderFactory, ProviderType
from backend.providers.base import DeploymentError, ProviderConfigurationError, DeploymentStatus
from backend.template_manager import TemplateManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI with metadata
app = FastAPI(
    title="Multi-Cloud Infrastructure Management API",
    description="""
    Production-ready REST API for deploying and managing cloud infrastructure
    across Azure, AWS, and Google Cloud Platform.

    ## Features
    * **Multi-Cloud Support**: Deploy to Azure, AWS, or GCP with one API
    * **Multiple Formats**: Bicep, Terraform, ARM templates
    * **Provider Abstraction**: Unified interface across clouds
    * **Template Management**: Automatic template discovery
    * **Real-time Status**: Track deployment progress

    ## Authentication
    Currently uses cloud provider credentials (Azure CLI, AWS CLI, gcloud).
    API key authentication can be added for production use.
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "GitHub Repository",
        "url": "https://github.com/KatsaounisThanasis/Azure-Resource-Manager-Portal"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Template Manager
TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
template_manager = TemplateManager(TEMPLATES_DIR)

# ==================== Request/Response Models ====================

class StandardResponse(BaseModel):
    """Standard API response format."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class DeploymentRequest(BaseModel):
    """Request model for deployments."""
    template_name: str = Field(..., description="Name of the template to deploy")
    provider_type: str = Field(..., description="Cloud provider (azure, terraform-aws, terraform-gcp)")
    subscription_id: str = Field(..., description="Cloud subscription/account/project ID")
    resource_group: str = Field(..., description="Resource group/stack name")
    location: str = Field(..., description="Deployment region/location")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Template parameters")

    class Config:
        json_schema_extra = {
            "example": {
                "template_name": "storage-bucket",
                "provider_type": "terraform-aws",
                "subscription_id": "123456789012",
                "resource_group": "my-resources",
                "location": "us-east-1",
                "parameters": {
                    "bucket_name": "my-unique-bucket-name"
                }
            }
        }


class ResourceGroupCreateRequest(BaseModel):
    """Request model for creating resource groups."""
    name: str = Field(..., description="Resource group/stack name")
    location: str = Field(..., description="Region/location")
    subscription_id: str = Field(..., description="Subscription/account/project ID")
    provider_type: str = Field(default="azure", description="Cloud provider")
    tags: Optional[Dict[str, str]] = Field(default=None, description="Tags/labels")


# ==================== Helper Functions ====================

def create_success_response(message: str, data: Any = None) -> StandardResponse:
    """Create standardized success response."""
    return StandardResponse(
        success=True,
        message=message,
        data=data if isinstance(data, dict) else {"result": data}
    )


def create_error_response(message: str, details: Any = None, status_code: int = 500) -> JSONResponse:
    """Create standardized error response."""
    response = StandardResponse(
        success=False,
        message=message,
        error={"details": details, "status_code": status_code}
    )
    return JSONResponse(
        status_code=status_code,
        content=response.dict()
    )


# ==================== API Endpoints ====================

@app.get("/",
    summary="API Health Check",
    response_model=StandardResponse,
    tags=["Health"])
async def root():
    """
    Health check endpoint to verify API is running.

    Returns basic information about the API and available providers.
    """
    return create_success_response(
        message="Multi-Cloud Infrastructure Management API is running",
        data={
            "version": "2.0.0",
            "status": "healthy",
            "available_providers": ProviderFactory.get_available_providers(),
            "docs_url": "/docs"
        }
    )


@app.get("/health",
    summary="Detailed Health Status",
    response_model=StandardResponse,
    tags=["Health"])
async def health_check():
    """
    Detailed health check with provider and template information.
    """
    return create_success_response(
        message="System healthy",
        data={
            "api_version": "2.0.0",
            "providers": template_manager.get_providers_summary(),
            "uptime": "N/A"  # Could add actual uptime tracking
        }
    )


@app.get("/providers",
    summary="List Cloud Providers",
    response_model=StandardResponse,
    tags=["Providers"])
async def list_providers():
    """
    Get list of available cloud providers with template counts.

    Returns information about each supported cloud provider including:
    - Provider ID and name
    - Supported format (Bicep, Terraform)
    - Cloud platform (Azure, AWS, GCP)
    - Number of available templates
    """
    providers_info = template_manager.get_providers_summary()
    return create_success_response(
        message=f"Found {len(providers_info['providers'])} providers",
        data=providers_info
    )


@app.get("/templates",
    summary="List Templates",
    response_model=StandardResponse,
    tags=["Templates"])
async def list_templates(
    provider_type: Optional[str] = Query(None, description="Filter by provider type"),
    cloud: Optional[str] = Query(None, description="Filter by cloud (azure, aws, gcp)")
):
    """
    List available deployment templates.

    Can be filtered by:
    - **provider_type**: Specific provider (e.g., "terraform-aws")
    - **cloud**: Cloud platform (e.g., "aws")

    Returns template metadata including name, format, cloud, and path.
    """
    templates = template_manager.list_templates(
        provider_type=provider_type,
        cloud=cloud
    )

    return create_success_response(
        message=f"Found {len(templates)} templates",
        data={"templates": templates, "count": len(templates)}
    )


@app.get("/templates/{provider_type}/{template_name}",
    summary="Get Template Details",
    response_model=StandardResponse,
    tags=["Templates"])
async def get_template(provider_type: str, template_name: str):
    """
    Get detailed information about a specific template.

    Returns template metadata and optionally the template content.
    """
    template = template_manager.get_template(template_name, provider_type)

    if not template:
        return create_error_response(
            message=f"Template '{template_name}' not found for provider '{provider_type}'",
            status_code=404
        )

    return create_success_response(
        message="Template found",
        data=template.to_dict()
    )


@app.get("/templates/{provider_type}/{template_name}/content",
    summary="Get Template Content",
    tags=["Templates"])
async def get_template_content(provider_type: str, template_name: str):
    """
    Get the raw content of a template file.

    Returns the template as plain text (Bicep, Terraform, etc.).
    """
    content = template_manager.get_template_content(template_name, provider_type)

    if not content:
        raise HTTPException(
            status_code=404,
            detail=f"Template '{template_name}' not found"
        )

    return JSONResponse(
        content={"content": content},
        media_type="application/json"
    )


@app.post("/deploy",
    summary="Deploy Infrastructure",
    response_model=StandardResponse,
    tags=["Deployments"],
    status_code=status.HTTP_202_ACCEPTED)
async def deploy_infrastructure(request: DeploymentRequest):
    """
    Deploy infrastructure using the specified template and provider.

    This endpoint:
    1. Validates the template exists
    2. Creates the appropriate cloud provider instance
    3. Initiates deployment
    4. Returns deployment details

    The deployment runs asynchronously. Use the deployment_id to check status.
    """
    try:
        # Get template path
        template_path = template_manager.get_template_path(
            request.template_name,
            request.provider_type
        )

        if not template_path:
            return create_error_response(
                message=f"Template '{request.template_name}' not found for provider '{request.provider_type}'",
                status_code=404
            )

        # Create provider
        provider = get_provider(
            provider_type=request.provider_type,
            subscription_id=request.subscription_id,
            region=request.location
        )

        logger.info(f"Deploying {request.template_name} using {request.provider_type}")

        # Deploy
        result = await provider.deploy(
            template_path=template_path,
            parameters=request.parameters,
            resource_group=request.resource_group,
            location=request.location
        )

        return create_success_response(
            message="Deployment initiated successfully",
            data={
                "deployment_id": result.deployment_id,
                "status": result.status.value,
                "resource_group": result.resource_group,
                "provider": request.provider_type,
                "message": result.message,
                "outputs": result.outputs
            }
        )

    except ProviderConfigurationError as e:
        logger.error(f"Provider configuration error: {e}")
        return create_error_response(
            message="Provider configuration error",
            details=str(e),
            status_code=400
        )

    except DeploymentError as e:
        logger.error(f"Deployment error: {e}")
        return create_error_response(
            message="Deployment failed",
            details=str(e),
            status_code=500
        )

    except Exception as e:
        logger.exception("Unexpected error during deployment")
        return create_error_response(
            message="Unexpected error occurred",
            details=str(e),
            status_code=500
        )


@app.get("/deployments/{deployment_id}/status",
    summary="Get Deployment Status",
    response_model=StandardResponse,
    tags=["Deployments"])
async def get_deployment_status(
    deployment_id: str,
    provider_type: str = Query(..., description="Provider type"),
    subscription_id: str = Query(..., description="Subscription/account ID"),
    resource_group: str = Query(..., description="Resource group/stack name")
):
    """
    Get the current status of a deployment.

    Checks with the cloud provider for the latest deployment status.
    """
    try:
        provider = get_provider(provider_type, subscription_id=subscription_id)

        status = await provider.get_deployment_status(deployment_id, resource_group)

        return create_success_response(
            message="Deployment status retrieved",
            data={
                "deployment_id": deployment_id,
                "status": status.value,
                "resource_group": resource_group
            }
        )

    except Exception as e:
        return create_error_response(
            message="Failed to get deployment status",
            details=str(e),
            status_code=500
        )


@app.get("/resource-groups",
    summary="List Resource Groups",
    response_model=StandardResponse,
    tags=["Resource Groups"])
async def list_resource_groups(
    provider_type: str = Query("azure", description="Provider type"),
    subscription_id: str = Query(..., description="Subscription/account ID")
):
    """
    List all resource groups/stacks in the subscription.

    Returns resource groups for the specified cloud provider.
    """
    try:
        provider = get_provider(provider_type, subscription_id=subscription_id)
        groups = await provider.list_resource_groups()

        return create_success_response(
            message=f"Found {len(groups)} resource groups",
            data={
                "resource_groups": [
                    {
                        "name": group.name,
                        "location": group.location,
                        "resource_count": group.resource_count,
                        "tags": group.tags
                    }
                    for group in groups
                ],
                "count": len(groups)
            }
        )

    except Exception as e:
        return create_error_response(
            message="Failed to list resource groups",
            details=str(e),
            status_code=500
        )


@app.post("/resource-groups",
    summary="Create Resource Group",
    response_model=StandardResponse,
    tags=["Resource Groups"],
    status_code=status.HTTP_201_CREATED)
async def create_resource_group(request: ResourceGroupCreateRequest):
    """
    Create a new resource group/stack.

    Creates a logical container for resources in the specified cloud.
    """
    try:
        provider = get_provider(
            request.provider_type,
            subscription_id=request.subscription_id
        )

        group = await provider.create_resource_group(
            name=request.name,
            location=request.location,
            tags=request.tags
        )

        return create_success_response(
            message=f"Resource group '{request.name}' created successfully",
            data={
                "name": group.name,
                "location": group.location,
                "provider_id": group.provider_id
            }
        )

    except Exception as e:
        return create_error_response(
            message="Failed to create resource group",
            details=str(e),
            status_code=500
        )


@app.delete("/resource-groups/{resource_group_name}",
    summary="Delete Resource Group",
    response_model=StandardResponse,
    tags=["Resource Groups"])
async def delete_resource_group(
    resource_group_name: str,
    provider_type: str = Query("azure", description="Provider type"),
    subscription_id: str = Query(..., description="Subscription/account ID")
):
    """
    Delete a resource group and all its contained resources.

    **Warning**: This is a destructive operation that cannot be undone!
    """
    try:
        provider = get_provider(provider_type, subscription_id=subscription_id)

        success = await provider.delete_resource_group(resource_group_name)

        if success:
            return create_success_response(
                message=f"Resource group '{resource_group_name}' deletion initiated",
                data={"resource_group": resource_group_name}
            )
        else:
            return create_error_response(
                message=f"Resource group '{resource_group_name}' not found",
                status_code=404
            )

    except Exception as e:
        return create_error_response(
            message="Failed to delete resource group",
            details=str(e),
            status_code=500
        )


@app.get("/resource-groups/{resource_group_name}/resources",
    summary="List Resources in Group",
    response_model=StandardResponse,
    tags=["Resource Groups"])
async def list_resources_in_group(
    resource_group_name: str,
    provider_type: str = Query("azure", description="Provider type"),
    subscription_id: str = Query(..., description="Subscription/account ID")
):
    """
    List all resources within a resource group.

    Returns detailed information about each resource including
    type, location, and properties.
    """
    try:
        provider = get_provider(provider_type, subscription_id=subscription_id)
        resources = await provider.list_resources(resource_group_name)

        return create_success_response(
            message=f"Found {len(resources)} resources",
            data={
                "resource_group": resource_group_name,
                "resources": [
                    {
                        "id": resource.id,
                        "name": resource.name,
                        "type": resource.type,
                        "location": resource.location,
                        "tags": resource.tags
                    }
                    for resource in resources
                ],
                "count": len(resources)
            }
        )

    except Exception as e:
        return create_error_response(
            message="Failed to list resources",
            details=str(e),
            status_code=500
        )


# ==================== Error Handlers ====================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.exception("Unhandled exception")
    return create_error_response(
        message="An unexpected error occurred",
        details=str(exc),
        status_code=500
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
