"""
Production-Ready REST API for Multi-Cloud Infrastructure Management

This is the main REST API application with proper structure,
documentation, and production-ready features.
"""

from fastapi import FastAPI, HTTPException, Query, Depends, status, Request
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

# Import database and tasks
from backend.database import get_db, init_db, Deployment, DeploymentStatus as DBDeploymentStatus
from backend.tasks import deploy_infrastructure as deploy_task, get_deployment_status as get_status_task
from sqlalchemy.orm import Session
import uuid

# Import security and authentication
from backend.auth import auth_handler, rate_limiter, get_current_user
from backend.security import (
    SecurityHeadersMiddleware,
    RequestLoggingMiddleware,
    get_cors_config,
    get_trusted_hosts,
    validate_deployment_parameters,
    mask_sensitive_data,
    security_config
)

# Import parameter parser
from backend.parameter_parser import TemplateParameterParser

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
    across Azure and Google Cloud Platform.

    ## Features
    * **Multi-Cloud Support**: Deploy to Azure or GCP with one API
    * **Multiple Formats**: Bicep for Azure, Terraform for GCP
    * **Provider Abstraction**: Unified interface across clouds
    * **Template Management**: Automatic template discovery
    * **Real-time Status**: Track deployment progress
    * **Async Deployments**: Background task processing with Celery
    * **Persistent State**: PostgreSQL database and Terraform remote state
    * **Security**: API key authentication, rate limiting, security headers

    ## Authentication
    API key authentication is available for production use.
    Set `API_AUTH_ENABLED=true` and provide `API_KEY` environment variable.

    Include the API key in request headers:
    ```
    X-API-Key: your-api-key-here
    ```

    For cloud operations, cloud provider credentials are required:
    - **Azure**: Azure CLI authentication (`az login`) or service principal
    - **GCP**: Service account JSON key file or gcloud CLI authentication
    """,
    version="3.0.0",
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

# Security Middleware (order matters - applied in reverse order)
# 1. Security Headers (applied last to all responses)
app.add_middleware(SecurityHeadersMiddleware)

# 2. Request Logging (applied second)
app.add_middleware(RequestLoggingMiddleware)

# 3. CORS configuration (applied first)
cors_config = get_cors_config()
app.add_middleware(CORSMiddleware, **cors_config)

# Initialize Template Manager
TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
template_manager = TemplateManager(TEMPLATES_DIR)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables and log startup info"""
    init_db()
    logger.info("Database initialized")
    logger.info(f"API v3.0.0 starting in {security_config.environment} mode")
    logger.info(f"Authentication: {'Enabled' if security_config.auth_enabled else 'Disabled (Development)'}")
    logger.info(f"Rate Limiting: {'Enabled' if security_config.rate_limit_enabled else 'Disabled'}")

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
    provider_type: str = Field(..., description="Cloud provider: 'azure' or 'gcp'")
    subscription_id: str = Field(..., description="Cloud subscription/account/project ID")
    resource_group: str = Field(..., description="Resource group/stack name")
    location: str = Field(..., description="Deployment region/location")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Template parameters")

    class Config:
        json_schema_extra = {
            "example": {
                "template_name": "storage-bucket",
                "provider_type": "gcp",
                "subscription_id": "my-gcp-project-id",
                "resource_group": "my-resources",
                "location": "us-central1",
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
            "version": "3.0.0",
            "status": "healthy",
            "environment": security_config.environment,
            "authentication_enabled": security_config.auth_enabled,
            "rate_limiting_enabled": security_config.rate_limit_enabled,
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
            "api_version": "3.0.0",
            "providers": template_manager.get_providers_summary(),
            "security": {
                "authentication": security_config.auth_enabled,
                "rate_limiting": security_config.rate_limit_enabled,
                "environment": security_config.environment
            },
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


@app.get("/templates/{provider_type}/{template_name}/parameters",
    summary="Get Template Parameters",
    response_model=StandardResponse,
    tags=["Templates"])
async def get_template_parameters(provider_type: str, template_name: str):
    """
    Extract and return parameters from a template.

    Parses the template file and extracts:
    - Parameter names and types
    - Descriptions
    - Default values
    - Validation rules (allowed values, min/max, patterns)
    - Whether parameters are required

    This enables dynamic form generation for deployments.

    **Supported formats:**
    - Bicep (.bicep)
    - Terraform (.tf)
    - ARM templates (.json) - coming soon

    **Example response:**
    ```json
    {
      "parameters": [
        {
          "name": "storageAccountName",
          "type": "string",
          "description": "The name of the storage account",
          "required": true
        },
        {
          "name": "storageAccountType",
          "type": "string",
          "description": "The type of the storage account (SKU)",
          "default": "Standard_LRS",
          "required": false,
          "allowed_values": ["Standard_LRS", "Standard_GRS", "Premium_LRS"]
        }
      ]
    }
    ```
    """
    try:
        # Get template path
        template_path = template_manager.get_template_path(template_name, provider_type)

        if not template_path:
            return create_error_response(
                message=f"Template '{template_name}' not found for provider '{provider_type}'",
                status_code=404
            )

        # Parse parameters
        parameters = TemplateParameterParser.parse_file(str(template_path))

        # Convert to dict format
        parameters_dict = [param.to_dict() for param in parameters]

        return create_success_response(
            message=f"Found {len(parameters)} parameters",
            data={
                "template_name": template_name,
                "provider_type": provider_type,
                "parameters": parameters_dict,
                "count": len(parameters)
            }
        )

    except FileNotFoundError as e:
        return create_error_response(
            message="Template file not found",
            details=str(e),
            status_code=404
        )
    except Exception as e:
        logger.exception(f"Error parsing template parameters: {e}")
        return create_error_response(
            message="Failed to parse template parameters",
            details=str(e),
            status_code=500
        )


@app.post("/deploy",
    summary="Deploy Infrastructure",
    response_model=StandardResponse,
    tags=["Deployments"],
    status_code=status.HTTP_202_ACCEPTED)
async def deploy_infrastructure(
    request: DeploymentRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(rate_limiter),
    _auth: str = Depends(auth_handler)
):
    """
    Deploy infrastructure using the specified template and provider.

    **Security**: This endpoint requires authentication (if enabled) and is rate-limited.

    This endpoint:
    1. Validates authentication and rate limits
    2. Validates deployment parameters for security
    3. Validates the template exists
    4. Creates a deployment record in the database
    5. Queues the deployment task in Celery
    6. Returns immediately with deployment_id for tracking

    The deployment runs asynchronously in the background.
    Use GET /deployments/{deployment_id}/status to check progress.
    """
    try:
        # Validate parameters for security issues
        is_valid, error_msg = validate_deployment_parameters(request.parameters)
        if not is_valid:
            logger.warning(f"Invalid deployment parameters: {error_msg}")
            return create_error_response(
                message="Invalid deployment parameters",
                details=error_msg,
                status_code=400
            )
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

        # Get template metadata for cloud provider
        template_meta = template_manager.get_template(request.template_name, request.provider_type)
        cloud_provider = template_meta.cloud_provider.value if template_meta else "unknown"

        # Generate unique deployment ID
        deployment_id = f"deploy-{uuid.uuid4().hex[:12]}"

        # Create deployment record in database
        deployment = Deployment(
            deployment_id=deployment_id,
            provider_type=request.provider_type,
            cloud_provider=cloud_provider,
            template_name=request.template_name,
            resource_group=request.resource_group,
            status=DBDeploymentStatus.PENDING,
            parameters=request.parameters
        )
        db.add(deployment)
        db.commit()

        # Log with masked sensitive data
        masked_params = mask_sensitive_data(request.parameters)
        logger.info(
            f"Created deployment record {deployment_id} for {request.template_name} "
            f"(provider: {request.provider_type}, params: {masked_params})"
        )

        # Queue deployment task in Celery
        # Build provider config based on provider type
        provider_config = {
            "subscription_id": request.subscription_id,
            "region": request.location
        }

        # Add cloud_platform for GCP (uses Terraform)
        if request.provider_type == "gcp":
            provider_config["cloud_platform"] = "gcp"

        task = deploy_task.delay(
            deployment_id=deployment_id,
            provider_type=request.provider_type,
            template_path=str(template_path),
            parameters=request.parameters,
            resource_group=request.resource_group,
            provider_config=provider_config
        )

        logger.info(f"Queued deployment task {task.id} for deployment {deployment_id}")

        return create_success_response(
            message="Deployment queued successfully",
            data={
                "deployment_id": deployment_id,
                "status": "pending",
                "task_id": task.id,
                "resource_group": request.resource_group,
                "provider": request.provider_type,
                "template": request.template_name,
                "message": "Deployment has been queued and will start shortly. Use the deployment_id to check status."
            }
        )

    except Exception as e:
        logger.exception("Error creating deployment")
        return create_error_response(
            message="Failed to queue deployment",
            details=str(e),
            status_code=500
        )


@app.get("/deployments/{deployment_id}/status",
    summary="Get Deployment Status",
    response_model=StandardResponse,
    tags=["Deployments"])
async def get_deployment_status(deployment_id: str, db: Session = Depends(get_db)):
    """
    Get the current status of a deployment.

    Retrieves deployment status from the database and Celery task status.
    """
    try:
        # Get deployment from database
        deployment = db.query(Deployment).filter_by(deployment_id=deployment_id).first()

        if not deployment:
            return create_error_response(
                message=f"Deployment {deployment_id} not found",
                status_code=404
            )

        # Calculate duration if available
        duration = None
        if deployment.started_at and deployment.completed_at:
            duration = (deployment.completed_at - deployment.started_at).total_seconds()
        elif deployment.started_at:
            duration = (datetime.utcnow() - deployment.started_at).total_seconds()

        return create_success_response(
            message="Deployment status retrieved",
            data={
                **deployment.to_dict(),
                "duration_seconds": duration
            }
        )

    except Exception as e:
        logger.exception(f"Error retrieving deployment status for {deployment_id}")
        return create_error_response(
            message="Failed to get deployment status",
            details=str(e),
            status_code=500
        )


@app.get("/deployments",
    summary="List All Deployments",
    response_model=StandardResponse,
    tags=["Deployments"])
async def list_deployments(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None, description="Filter by status"),
    provider_type: Optional[str] = Query(None, description="Filter by provider"),
    limit: int = Query(50, description="Max number of results", le=100)
):
    """
    List all deployments with optional filtering.

    Returns recent deployments sorted by creation date (newest first).
    """
    try:
        query = db.query(Deployment)

        # Apply filters
        if status:
            query = query.filter(Deployment.status == status)
        if provider_type:
            query = query.filter(Deployment.provider_type == provider_type)

        # Order and limit
        deployments = query.order_by(Deployment.created_at.desc()).limit(limit).all()

        return create_success_response(
            message=f"Found {len(deployments)} deployments",
            data={
                "deployments": [d.to_dict() for d in deployments],
                "total": len(deployments)
            }
        )

    except Exception as e:
        logger.exception("Error listing deployments")
        return create_error_response(
            message="Failed to list deployments",
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
