"""
Templates Router

Handles template discovery, metadata, parameters, and cost estimation.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
from pathlib import Path
import json
import logging

from backend.api.schemas import StandardResponse, success_response, error_response
from backend.services.parameter_parser import TemplateParameterParser
from backend.core.cost_estimator import estimate_deployment_cost
from backend.core.exceptions import TemplateNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["Templates"])


def get_template_manager():
    """Get template manager instance (lazy import to avoid circular imports)."""
    from backend.api.routes import template_manager
    return template_manager


@router.get("", summary="List Templates", response_model=StandardResponse)
async def list_templates(
    provider_type: Optional[str] = Query(None, description="Filter by provider type"),
    cloud: Optional[str] = Query(None, description="Filter by cloud (azure, gcp)")
):
    """List available deployment templates."""
    tm = get_template_manager()
    templates = tm.list_templates(provider_type=provider_type, cloud=cloud)
    return success_response(
        message=f"Found {len(templates)} templates",
        data={"templates": templates, "count": len(templates)}
    )


@router.get("/{provider_type}/{template_name}", summary="Get Template Details", response_model=StandardResponse)
async def get_template(provider_type: str, template_name: str):
    """Get detailed information about a specific template."""
    tm = get_template_manager()
    template = tm.get_template(template_name, provider_type)

    if not template:
        raise TemplateNotFoundError(template_name, provider_type)

    return success_response(message="Template found", data=template.to_dict())


@router.get("/{provider_type}/{template_name}/content", summary="Get Template Content")
async def get_template_content(provider_type: str, template_name: str):
    """Get the raw content of a template file."""
    tm = get_template_manager()
    content = tm.get_template_content(template_name, provider_type)

    if not content:
        raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")

    return JSONResponse(content={"content": content}, media_type="application/json")


@router.get("/{provider_type}/{template_name}/metadata", summary="Get Template Metadata", response_model=StandardResponse)
async def get_template_metadata(provider_type: str, template_name: str):
    """Get comprehensive metadata for a template."""
    try:
        tm = get_template_manager()
        template_path = tm.get_template_path(template_name, provider_type)

        if not template_path:
            raise TemplateNotFoundError(template_name, provider_type)

        # Check for metadata.json file
        template_file = Path(template_path)
        metadata_file = template_file.parent / f"{template_name}.metadata.json"

        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            return success_response(
                message="Template metadata loaded",
                data={"template_name": template_name, "provider_type": provider_type, "has_metadata": True, "metadata": metadata}
            )
        else:
            return success_response(
                message="No metadata file found, using defaults",
                data={
                    "template_name": template_name,
                    "provider_type": provider_type,
                    "has_metadata": False,
                    "metadata": {
                        "name": template_name,
                        "displayName": template_name.replace("-", " ").title(),
                        "description": f"{template_name} deployment template",
                        "provider": provider_type
                    }
                }
            )

    except TemplateNotFoundError:
        raise
    except Exception as e:
        logger.exception(f"Error loading template metadata: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load template metadata: {str(e)}")


@router.get("/{provider_type}/{template_name}/parameters", summary="Get Template Parameters", response_model=StandardResponse)
async def get_template_parameters(provider_type: str, template_name: str):
    """Extract and return parameters from a template."""
    try:
        tm = get_template_manager()
        template_path = tm.get_template_path(template_name, provider_type)

        if not template_path:
            return error_response(f"Template '{template_name}' not found", status_code=404)

        parameters = TemplateParameterParser.parse_file(str(template_path))
        parameters_dict = [param.to_dict() for param in parameters]

        return success_response(
            message=f"Found {len(parameters)} parameters",
            data={"template_name": template_name, "provider_type": provider_type, "parameters": parameters_dict, "count": len(parameters)}
        )

    except FileNotFoundError as e:
        return error_response("Template file not found", str(e), 404)
    except Exception as e:
        logger.exception(f"Error parsing template parameters: {e}")
        return error_response("Failed to parse template parameters", str(e), 500)


@router.post("/{provider_type}/{template_name}/estimate-cost", summary="Estimate Deployment Cost", response_model=StandardResponse)
async def estimate_cost(provider_type: str, template_name: str, parameters: Dict[str, Any]):
    """Estimate the monthly cost of a deployment."""
    try:
        tm = get_template_manager()
        template_path = tm.get_template_path(template_name, provider_type)

        if not template_path:
            raise TemplateNotFoundError(template_name, provider_type)

        cost_estimate = await estimate_deployment_cost(
            template_name=template_name,
            provider_type=provider_type,
            parameters=parameters
        )

        return success_response(message="Cost estimate calculated", data=cost_estimate)

    except TemplateNotFoundError:
        raise
    except Exception as e:
        logger.exception(f"Error estimating cost: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to estimate cost: {str(e)}")
