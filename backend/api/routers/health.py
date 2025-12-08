"""
Health Router

Handles health checks and system status endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from backend.api.schemas import StandardResponse, success_response
from backend.core.database import get_db
from backend.core.security import security_config
from backend.providers import ProviderFactory

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


def get_template_manager():
    """Get template manager instance (lazy import to avoid circular imports)."""
    from backend.api.routes import template_manager
    return template_manager


@router.get("/",
    summary="API Health Check",
    response_model=StandardResponse)
async def root():
    """Health check endpoint to verify API is running."""
    return success_response(
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


@router.get("/health",
    summary="Detailed Health Status",
    response_model=StandardResponse)
async def health_check(db: Session = Depends(get_db)):
    """Comprehensive health check with database and Celery status."""
    tm = get_template_manager()

    health_data = {
        "api_version": "3.0.0",
        "status": "healthy",
        "providers": tm.get_providers_summary(),
        "security": {
            "authentication": security_config.auth_enabled,
            "rate_limiting": security_config.rate_limit_enabled,
            "environment": security_config.environment
        }
    }

    # Check database
    try:
        db.execute(text("SELECT 1"))
        health_data["database"] = {"status": "connected"}
    except Exception as e:
        health_data["database"] = {"status": "error", "message": str(e)}
        health_data["status"] = "degraded"

    # Check Celery
    try:
        from backend.tasks.celery_app import celery_app
        active_workers = celery_app.control.inspect().active()
        worker_count = len(active_workers) if active_workers else 0
        health_data["celery"] = {
            "status": "connected" if worker_count > 0 else "warning",
            "workers": worker_count
        }
        if worker_count == 0:
            health_data["status"] = "degraded"
    except Exception as e:
        health_data["celery"] = {"status": "error", "message": str(e)}
        health_data["status"] = "degraded"

    return success_response(f"System {health_data['status']}", health_data)


@router.get("/providers",
    summary="List Cloud Providers",
    response_model=StandardResponse,
    tags=["Providers"])
async def list_providers():
    """Get list of available cloud providers with template counts."""
    tm = get_template_manager()
    providers_info = tm.get_providers_summary()
    return success_response(
        message=f"Found {len(providers_info['providers'])} providers",
        data=providers_info
    )
