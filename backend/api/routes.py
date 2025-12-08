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
    resource_groups_router
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

# 2. Request Logging (applied second)
app.add_middleware(RequestLoggingMiddleware)

# 3. CORS configuration (applied first)
cors_config = get_cors_config()
app.add_middleware(CORSMiddleware, **cors_config)


# ================================================================
# Global Exception Handlers
# ================================================================

@app.exception_handler(MultiCloudException)
async def multicloud_exception_handler(request: Request, exc: MultiCloudException):
    """Handle all MultiCloudException instances with consistent format."""
    logger.error(f"MultiCloudException: {exc.code} - {exc.message}", exc_info=True)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "error": exc.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unexpected exceptions."""
    logger.exception(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "An unexpected error occurred",
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "details": str(exc) if os.getenv("ENVIRONMENT") == "development" else None
            },
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

@app.on_event("startup")
async def startup_event():
    """Initialize database tables and log startup info"""
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


# ================================================================
# Main Entry Point
# ================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
