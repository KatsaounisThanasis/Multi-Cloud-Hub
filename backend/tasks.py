"""
Celery Tasks for Async Infrastructure Deployment

This module contains all background tasks for infrastructure deployment and management.
"""

from celery import Task
from backend.celery_app import celery_app
from backend.database import SessionLocal, Deployment, DeploymentStatus, TerraformState
from backend.providers.factory import ProviderFactory
from backend.providers.base import DeploymentError, ProviderConfigurationError
from backend.state_backend_manager import StateBackendManager
from datetime import datetime
import logging
import traceback
import uuid

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task with database session management"""
    _db = None

    @property
    def db(self):
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(bind=True, base=DatabaseTask, name="backend.tasks.deploy_infrastructure")
def deploy_infrastructure(
    self,
    deployment_id: str,
    provider_type: str,
    template_path: str,
    parameters: dict,
    resource_group: str = None,
    provider_config: dict = None
):
    """
    Deploy infrastructure asynchronously

    Args:
        deployment_id: Unique deployment identifier
        provider_type: Provider type (azure, terraform-aws, terraform-gcp, etc.)
        template_path: Path to template file
        parameters: Template parameters
        resource_group: Resource group name (for Azure)
        provider_config: Additional provider configuration (credentials, regions, etc.)

    Returns:
        dict: Deployment result with status and outputs
    """
    db = self.db
    deployment = db.query(Deployment).filter_by(deployment_id=deployment_id).first()

    try:
        # Update deployment status to RUNNING
        if deployment:
            deployment.status = DeploymentStatus.RUNNING
            deployment.started_at = datetime.utcnow()
            deployment.celery_task_id = self.request.id
            db.commit()

        logger.info(f"Starting deployment {deployment_id} with provider {provider_type}")

        # Update task state
        self.update_state(
            state="RUNNING",
            meta={
                "deployment_id": deployment_id,
                "status": "initializing",
                "progress": 10
            }
        )

        # Create provider instance
        # Map template format to cloud provider type
        provider_type_mapping = {
            "bicep": "azure",
            "arm": "azure",
            "terraform-azure": "terraform-azure",
            "terraform-aws": "terraform-aws",
            "terraform-gcp": "terraform-gcp"
        }
        actual_provider_type = provider_type_mapping.get(provider_type, provider_type)

        provider_config = provider_config or {}
        provider = ProviderFactory.create_provider(actual_provider_type, **provider_config)

        logger.info(f"Provider {provider_type} initialized for deployment {deployment_id}")

        # Update progress
        self.update_state(
            state="RUNNING",
            meta={
                "deployment_id": deployment_id,
                "status": "deploying",
                "progress": 30
            }
        )

        # Perform deployment
        # Get location/region from provider_config
        location = provider_config.get("region", "us-east-1")

        # Use asyncio to run the async deploy method
        import asyncio
        result = asyncio.run(provider.deploy(
            template_path=template_path,
            resource_group=resource_group,
            parameters=parameters,
            location=location,
            deployment_id=deployment_id  # Pass deployment_id for remote state
        ))

        logger.info(f"Deployment {deployment_id} completed successfully")

        # Update progress
        self.update_state(
            state="RUNNING",
            meta={
                "deployment_id": deployment_id,
                "status": "finalizing",
                "progress": 90
            }
        )

        # Update deployment record
        if deployment:
            deployment.status = DeploymentStatus.COMPLETED
            deployment.completed_at = datetime.utcnow()
            deployment.outputs = result.outputs if hasattr(result, 'outputs') else {}
            db.commit()

        logger.info(f"Deployment {deployment_id} recorded as completed")

        return {
            "deployment_id": deployment_id,
            "status": "completed",
            "outputs": result.outputs if hasattr(result, 'outputs') else {},
            "message": "Deployment completed successfully"
        }

    except (DeploymentError, ProviderConfigurationError) as e:
        logger.error(f"Deployment {deployment_id} failed: {str(e)}")

        # Update deployment record with error
        if deployment:
            deployment.status = DeploymentStatus.FAILED
            deployment.completed_at = datetime.utcnow()
            deployment.error_message = str(e)
            deployment.logs = traceback.format_exc()
            db.commit()

        # Update task state
        self.update_state(
            state="FAILURE",
            meta={
                "deployment_id": deployment_id,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )

        raise

    except Exception as e:
        logger.error(f"Unexpected error in deployment {deployment_id}: {str(e)}")

        # Update deployment record
        if deployment:
            deployment.status = DeploymentStatus.FAILED
            deployment.completed_at = datetime.utcnow()
            deployment.error_message = f"Unexpected error: {str(e)}"
            deployment.logs = traceback.format_exc()
            db.commit()

        # Update task state
        self.update_state(
            state="FAILURE",
            meta={
                "deployment_id": deployment_id,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )

        raise


@celery_app.task(name="backend.tasks.cleanup_deployment")
def cleanup_deployment(deployment_id: str):
    """
    Clean up deployment resources

    Args:
        deployment_id: Deployment ID to clean up
    """
    db = SessionLocal()
    try:
        deployment = db.query(Deployment).filter_by(deployment_id=deployment_id).first()
        if not deployment:
            logger.warning(f"Deployment {deployment_id} not found for cleanup")
            return

        logger.info(f"Cleaning up deployment {deployment_id}")

        # Clean up Terraform state if applicable
        if deployment.provider_type.startswith("terraform"):
            tf_state = db.query(TerraformState).filter_by(deployment_id=deployment_id).first()
            if tf_state:
                # Here you could add logic to clean up remote state
                logger.info(f"Terraform state found for {deployment_id}")

        # Mark as cleaned up (you might want a separate status for this)
        logger.info(f"Cleanup completed for deployment {deployment_id}")

    finally:
        db.close()


@celery_app.task(name="backend.tasks.cleanup_old_deployments")
def cleanup_old_deployments(days: int = 30):
    """
    Periodic task to clean up old deployments

    Args:
        days: Number of days to keep deployments
    """
    from datetime import timedelta

    db = SessionLocal()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        old_deployments = db.query(Deployment).filter(
            Deployment.completed_at < cutoff_date,
            Deployment.status.in_([DeploymentStatus.COMPLETED, DeploymentStatus.FAILED])
        ).all()

        logger.info(f"Found {len(old_deployments)} old deployments to clean up")

        for deployment in old_deployments:
            # Optionally delete or archive
            logger.info(f"Archiving old deployment {deployment.deployment_id}")

        db.commit()

    finally:
        db.close()


@celery_app.task(bind=True, name="backend.tasks.get_deployment_status")
def get_deployment_status(self, deployment_id: str):
    """
    Get deployment status

    Args:
        deployment_id: Deployment ID to check

    Returns:
        dict: Deployment status information
    """
    db = SessionLocal()
    try:
        deployment = db.query(Deployment).filter_by(deployment_id=deployment_id).first()

        if not deployment:
            return {
                "deployment_id": deployment_id,
                "status": "not_found",
                "error": "Deployment not found"
            }

        return deployment.to_dict()

    finally:
        db.close()
