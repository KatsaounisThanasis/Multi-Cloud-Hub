"""
Deployments Router

Handles deployment creation, status, logs, and management.
"""

from fastapi import APIRouter, HTTPException, Query, Depends, status
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
import uuid
import json
import asyncio
import os
import re
import logging

from backend.api.schemas import StandardResponse, DeploymentRequest, success_response, error_response
from backend.core.database import get_db, Deployment, DeploymentStatus as DBDeploymentStatus, DATABASE_URL
from backend.tasks.deployment_tasks import deploy_infrastructure as deploy_task
from backend.core.exceptions import TemplateNotFoundError, DeploymentNotFoundError, ValidationError, InvalidParameterError, MissingParameterError
from backend.core.security import validate_deployment_parameters, mask_sensitive_data
from backend.utils.validators import DeploymentRequestValidator, ParameterValidator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Deployments"])


def get_template_manager():
    """Get template manager instance."""
    from backend.api.routes import template_manager
    return template_manager


def parse_structured_log(log_line: str) -> dict:
    """Parse structured log line to extract timestamp, level, phase, and message."""
    pattern = r'\[([^\]]+)\]\s*\[([^\]]+)\](?:\s*\[([^\]]+)\])?\s*(.+?)(?:\s*-\s*(\{.+\}))?$'
    match = re.match(pattern, log_line)

    if match:
        timestamp, level, phase, message, details_json = match.groups()
        details = None
        if details_json:
            try:
                details = json.loads(details_json)
            except:
                pass
        return {'timestamp': timestamp, 'level': level, 'phase': phase or 'unknown', 'message': message.strip(), 'details': details}

    return {'timestamp': datetime.utcnow().isoformat(), 'level': 'INFO', 'phase': 'unknown', 'message': log_line, 'details': None}


def _get_subscription_id(request: DeploymentRequest) -> str:
    """
    Resolve subscription ID from request or environment variables.
    
    Raises:
        MissingParameterError: If subscription ID cannot be determined.
    """
    if request.subscription_id:
        return request.subscription_id

    subscription_id = None
    if request.provider_type in ['terraform-azure', 'azure', 'bicep']:
        subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
    elif request.provider_type in ['terraform-gcp', 'gcp']:
        subscription_id = os.getenv('GOOGLE_PROJECT_ID')

    if not subscription_id:
        raise MissingParameterError("subscription_id")
    
    return subscription_id


@router.post("/deploy", summary="Deploy Infrastructure", response_model=StandardResponse, status_code=status.HTTP_202_ACCEPTED)
async def deploy_infrastructure(request: DeploymentRequest, db: Session = Depends(get_db)):
    """Deploy infrastructure using the specified template and provider."""
    try:
        tm = get_template_manager()
        
        # 1. Resolve Configuration
        subscription_id = _get_subscription_id(request)

        # 2. Validate Request & Parameters
        is_valid, error_msg = DeploymentRequestValidator.validate_deployment_request(
            provider_type=request.provider_type,
            template_name=request.template_name,
            resource_group=request.resource_group,
            location=request.location,
            parameters=request.parameters
        )
        if not is_valid:
            raise ValidationError("deployment_request", error_msg)

        is_valid, error_msg = validate_deployment_parameters(request.parameters)
        if not is_valid:
            raise ValidationError("parameters", error_msg)

        _validate_provider_specific_params(request.provider_type, request.parameters)

        # 3. Resolve Template
        template_path = tm.get_template_path(request.template_name, request.provider_type)
        if not template_path:
            raise TemplateNotFoundError(request.template_name, request.provider_type)

        template_meta = tm.get_template(request.template_name, request.provider_type)
        cloud_provider = template_meta.cloud_provider.value if template_meta else "unknown"

        # 4. Create Database Record
        deployment_id = f"deploy-{uuid.uuid4().hex[:12]}"
        deployment = Deployment(
            deployment_id=deployment_id,
            provider_type=request.provider_type,
            cloud_provider=cloud_provider,
            template_name=request.template_name,
            resource_group=request.resource_group,
            status=DBDeploymentStatus.PENDING,
            parameters=request.parameters,
            tags=request.tags or []
        )
        db.add(deployment)
        db.commit()

        logger.info(f"Created deployment {deployment_id} (params: {mask_sensitive_data(request.parameters)})")

        # 5. Queue Background Task
        provider_config = {
            "subscription_id": subscription_id, 
            "region": request.location,
            "cloud_platform": "gcp" if request.provider_type in ("gcp", "terraform-gcp") else "azure"
        }

        task = deploy_task.delay(
            deployment_id=deployment_id,
            provider_type=request.provider_type,
            template_path=str(template_path),
            parameters=request.parameters,
            resource_group=request.resource_group,
            provider_config=provider_config
        )

        return success_response(
            message="Deployment queued successfully",
            data={
                "deployment_id": deployment_id,
                "status": "pending",
                "task_id": task.id,
                "resource_group": request.resource_group,
                "provider": request.provider_type,
                "template": request.template_name
            }
        )

    except (TemplateNotFoundError, ValidationError, InvalidParameterError, MissingParameterError):
        raise
    except Exception as e:
        logger.exception("Error creating deployment")
        return error_response("Failed to queue deployment", str(e), 500)


def _validate_provider_specific_params(provider_type: str, parameters: dict):
    """Validate provider-specific parameters."""
    from backend.utils.validators import validate_app_name, validate_gcp_bucket_name

    if 'azure' in provider_type.lower():
        if parameters.get('storage_account_name'):
            ParameterValidator.validate_azure_storage_account_name(parameters['storage_account_name'])
        if parameters.get('resource_group'):
            ParameterValidator.validate_azure_resource_group_name(parameters['resource_group'])

    elif 'gcp' in provider_type.lower():
        if parameters.get('bucket_name'):
            validate_gcp_bucket_name(parameters['bucket_name'])
        if parameters.get('instance_name'):
            ParameterValidator.validate_gcp_resource_name(parameters['instance_name'], 'instance_name')
        if parameters.get('project_id'):
            ParameterValidator.validate_gcp_project_id(parameters['project_id'])

    # Common validations
    if parameters.get('app_name'):
        validate_app_name(parameters['app_name'], 'app_name')
    if parameters.get('name'):
        validate_app_name(parameters['name'], 'name')
    if parameters.get('cidr_block'):
        ParameterValidator.validate_cidr(parameters['cidr_block'])
    if parameters.get('ip_address'):
        ParameterValidator.validate_ip_address(parameters['ip_address'])


@router.get("/deployments/{deployment_id}/status", summary="Get Deployment Status", response_model=StandardResponse)
async def get_deployment_status(deployment_id: str, db: Session = Depends(get_db)):
    """Get the current status of a deployment."""
    deployment = db.query(Deployment).filter_by(deployment_id=deployment_id).first()
    if not deployment:
        raise DeploymentNotFoundError(deployment_id)

    duration = None
    if deployment.started_at:
        end_time = deployment.completed_at or datetime.utcnow()
        duration = (end_time - deployment.started_at).total_seconds()

    return success_response(
        message="Deployment status retrieved",
        data={**deployment.to_dict(), "duration_seconds": duration}
    )


@router.get("/tasks/{task_id}/status", summary="Get Task Status", response_model=StandardResponse, tags=["Tasks"])
async def get_task_status(task_id: str):
    """Get the current status of a Celery task."""
    try:
        from backend.tasks.celery_app import celery_app
        task = celery_app.AsyncResult(task_id)
        info = task.info if isinstance(task.info, dict) else {}

        return success_response(
            message="Task status retrieved",
            data={
                "task_id": task_id,
                "state": task.state,
                "phase": info.get('phase', 'unknown'),
                "progress": info.get('progress', 0),
                "status": info.get('status', ''),
                "info": info
            }
        )
    except Exception as e:
        logger.exception(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deployments/{deployment_id}/logs", summary="Stream Deployment Logs (SSE)")
async def stream_deployment_logs(deployment_id: str, db: Session = Depends(get_db)):
    """Stream real-time deployment logs using Server-Sent Events (SSE)."""
    async def event_generator():
        try:
            deployment = db.query(Deployment).filter_by(deployment_id=deployment_id).first()
            if not deployment:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Deployment not found'})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'status', 'status': deployment.status.value})}\n\n"

            last_log_length = 0
            for iteration in range(300):  # Max 5 minutes
                db.refresh(deployment)

                # Send new logs
                if deployment.logs and len(deployment.logs) > last_log_length:
                    new_logs = deployment.logs[last_log_length:]
                    for line in new_logs.split('\n'):
                        if line.strip():
                            yield f"data: {json.dumps({'type': 'log', **parse_structured_log(line)})}\n\n"
                    last_log_length = len(deployment.logs)

                # Send progress for running deployments
                if deployment.status == DBDeploymentStatus.RUNNING:
                    progress = min(30 + (iteration * 2), 90)
                    if deployment.celery_task_id:
                        try:
                            from backend.tasks.celery_app import celery_app
                            task_info = celery_app.AsyncResult(deployment.celery_task_id).info
                            if isinstance(task_info, dict):
                                progress = task_info.get('progress', progress)
                        except:
                            pass
                    yield f"data: {json.dumps({'type': 'progress', 'progress': progress, 'status': 'running'})}\n\n"

                # Check if done
                if deployment.status in [DBDeploymentStatus.COMPLETED, DBDeploymentStatus.FAILED]:
                    if deployment.status == DBDeploymentStatus.COMPLETED:
                        yield f"data: {json.dumps({'type': 'complete', 'message': 'Deployment completed', 'outputs': deployment.outputs or {}})}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'error', 'message': deployment.error_message or 'Deployment failed'})}\n\n"
                    break

                await asyncio.sleep(1)

            yield f"data: {json.dumps({'type': 'done', 'message': 'Stream ended'})}\n\n"

        except Exception as e:
            logger.exception(f"Error streaming logs: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )


@router.get("/deployments", summary="List All Deployments", response_model=StandardResponse)
async def list_deployments(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None),
    provider_type: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    limit: int = Query(50, le=100)
):
    """List all deployments with optional filtering."""
    try:
        query = db.query(Deployment)

        if status:
            query = query.filter(Deployment.status == status)
        if provider_type:
            query = query.filter(Deployment.provider_type == provider_type)

        if tag:
            # Simple tag filter for SQLite compatibility
            all_deployments = query.order_by(Deployment.created_at.desc()).all()
            deployments = [d for d in all_deployments if tag in (d.tags or [])][:limit]
        else:
            deployments = query.order_by(Deployment.created_at.desc()).limit(limit).all()

        return success_response(
            message=f"Found {len(deployments)} deployments",
            data={"deployments": [d.to_dict() for d in deployments], "total": len(deployments)}
        )

    except Exception as e:
        logger.exception("Error listing deployments")
        return error_response("Failed to list deployments", str(e), 500)


@router.put("/deployments/{deployment_id}/tags", summary="Update Deployment Tags", response_model=StandardResponse)
async def update_deployment_tags(deployment_id: str, tags: List[str], db: Session = Depends(get_db)):
    """Update tags for a specific deployment."""
    deployment = db.query(Deployment).filter_by(deployment_id=deployment_id).first()
    if not deployment:
        return error_response(f"Deployment {deployment_id} not found", status_code=404)

    deployment.tags = tags
    db.commit()
    return success_response("Tags updated", deployment.to_dict())


@router.get("/deployments/tags", summary="Get All Available Tags", response_model=StandardResponse)
async def get_all_tags(db: Session = Depends(get_db)):
    """Get a list of all unique tags used across all deployments."""
    deployments = db.query(Deployment).all()
    all_tags = set()
    for d in deployments:
        if d.tags:
            all_tags.update(d.tags)

    return success_response(f"Found {len(all_tags)} unique tags", {"tags": sorted(all_tags), "total": len(all_tags)})


@router.delete("/deployments/{deployment_id}", summary="Delete Deployment", response_model=StandardResponse)
async def delete_deployment(deployment_id: str, db: Session = Depends(get_db)):
    """Delete a deployment record."""
    deployment = db.query(Deployment).filter_by(deployment_id=deployment_id).first()
    if not deployment:
        return error_response(f"Deployment {deployment_id} not found", status_code=404)

    db.delete(deployment)
    db.commit()
    logger.info(f"Deleted deployment {deployment_id}")
    return success_response("Deployment deleted", {"deployment_id": deployment_id})


@router.get("/deployments/{deployment_id}", summary="Get Deployment Details", response_model=StandardResponse)
async def get_deployment_details(deployment_id: str, db: Session = Depends(get_db)):
    """Get detailed information about a specific deployment."""
    deployment = db.query(Deployment).filter_by(deployment_id=deployment_id).first()
    if not deployment:
        return error_response(f"Deployment {deployment_id} not found", status_code=404)

    duration = None
    if deployment.started_at:
        end_time = deployment.completed_at or datetime.utcnow()
        duration = (end_time - deployment.started_at).total_seconds()

    return success_response(
        message="Deployment details retrieved",
        data={**deployment.to_dict(), "duration_seconds": duration, "logs": deployment.logs}
    )
