"""
Production-Ready REST API for Multi-Cloud Infrastructure Management

This is the main REST API application that imports and registers all routers.
The actual endpoint implementations are in the routers/ directory.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import os
import logging

# Import security middleware
from backend.core.security import (
    SecurityHeadersMiddleware,
    RequestLoggingMiddleware,
    RateLimitingMiddleware,
    CSRFMiddleware,
    get_cors_config,
    security_config
)

# Import exception classes
from backend.core.exceptions import MultiCloudException

# Import database initialization
from backend.core.database import init_db

# Import auth initialization
from backend.core.auth import initialize_default_users

# Import template manager
from backend.services.template_manager import TemplateManager

# Import routers
from backend.api.routers import (
    auth_router,
    health_router,
    templates_router,
    deployments_router,
    azure_router,
    gcp_router,
    resource_groups_router,
    cloud_accounts_router,
    metrics_router
)

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
        "name": "Apache 2.0 License",
        "url": "https://www.apache.org/licenses/LICENSE-2.0"
    }
)

# ================================================================
# Middleware Configuration (order matters - applied in reverse order)
# ================================================================

# 1. Security Headers (applied last to all responses)
app.add_middleware(SecurityHeadersMiddleware)

# 2. CSRF Protection (applied after security headers)
app.add_middleware(CSRFMiddleware)

# 3. Rate Limiting (applied before CSRF)
app.add_middleware(RateLimitingMiddleware)

# 4. Request Logging (applied early)
app.add_middleware(RequestLoggingMiddleware)

# 5. CORS configuration (applied first)
cors_config = get_cors_config()
app.add_middleware(CORSMiddleware, **cors_config)


# Import DeploymentError for handler
from backend.providers.base import DeploymentError

# ================================================================
# Global Exception Handlers
# ================================================================

@app.exception_handler(DeploymentError)
async def deployment_error_handler(request: Request, exc: DeploymentError):
    """Handle deployment errors with user-friendly messages."""
    friendly = exc.get_friendly_error()
    logger.error(f"DeploymentError: {friendly.get('title')} - {friendly.get('message')}")
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "message": exc.get_friendly_message(),
            "error": friendly,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(MultiCloudException)
async def multicloud_exception_handler(request: Request, exc: MultiCloudException):
    """Handle all MultiCloudException instances with user-friendly format."""
    friendly = exc.get_friendly_error()
    logger.error(f"MultiCloudException: {friendly.get('title')} - {friendly.get('message')}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.get_friendly_message(),
            "error": friendly,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unexpected exceptions."""
    from backend.core.error_parser import parse_terraform_error

    logger.exception(f"Unhandled exception: {str(exc)}")

    # Try to parse the error for a friendlier message
    error_text = str(exc)
    friendly = parse_terraform_error(error_text)
    friendly['code'] = "INTERNAL_SERVER_ERROR"

    # In development, include more details
    if os.getenv("ENVIRONMENT") == "development":
        friendly['original'] = error_text

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": f"{friendly.get('title', 'Error')} | {friendly.get('message', 'An unexpected error occurred')}",
            "error": friendly,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# ================================================================
# Initialize Template Manager (shared across routers)
# ================================================================

TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "templates"))
template_manager = TemplateManager(TEMPLATES_DIR)


# ================================================================
# Startup Event
# ================================================================

def validate_environment():
    """Validate required environment variables for production"""
    env = os.getenv("ENVIRONMENT", "development")
    warnings = []

    # Check JWT secret
    if not os.getenv("JWT_SECRET_KEY"):
        if env == "production":
            raise RuntimeError("JWT_SECRET_KEY is required in production mode")
        warnings.append("JWT_SECRET_KEY not set - using random key (sessions won't persist)")

    # Check database
    if not os.getenv("DATABASE_URL"):
        warnings.append("DATABASE_URL not set - using default")

    # Check CORS in production
    cors_origins = os.getenv("CORS_ORIGINS", "*")
    if env == "production" and cors_origins == "*":
        warnings.append("CORS_ORIGINS is set to '*' - consider restricting for production")

    # Log warnings
    for warning in warnings:
        logger.warning(f"⚠️  {warning}")

    return len(warnings) == 0


@app.on_event("startup")
async def startup_event():
    """Initialize database tables and log startup info"""
    # Validate environment
    validate_environment()

    init_db()
    logger.info("Database initialized")
    logger.info(f"API v3.0.0 starting in {security_config.environment} mode")
    logger.info(f"Authentication: {'Enabled' if security_config.auth_enabled else 'Disabled (Development)'}")
    logger.info(f"Rate Limiting: {'Enabled' if security_config.rate_limit_enabled else 'Disabled'}")

    # Initialize default users for RBAC
    initialize_default_users()


# ================================================================
# Register Routers
# ================================================================

# Authentication routes
app.include_router(auth_router)

# Health and providers routes (no prefix - includes /, /health, /providers)
app.include_router(health_router)

# Template routes
app.include_router(templates_router)

# Deployment routes
app.include_router(deployments_router)

# Azure dynamic options routes
app.include_router(azure_router)

# GCP dynamic options routes
app.include_router(gcp_router)

# Resource group routes
app.include_router(resource_groups_router)

# Cloud accounts routes
app.include_router(cloud_accounts_router)

# Metrics routes (for Prometheus scraping)
app.include_router(metrics_router)


# ================================================================
# Main Entry Point
# ================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
