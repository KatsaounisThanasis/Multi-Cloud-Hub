"""
Metrics Router

Exposes application metrics in Prometheus format at /metrics endpoint.
"""

from fastapi import APIRouter, Response
from backend.core.metrics import get_metrics_text

router = APIRouter(tags=["Monitoring"])


@router.get(
    "/metrics",
    summary="Get Prometheus metrics",
    description="Returns application metrics in Prometheus text format for scraping.",
    response_class=Response
)
async def get_metrics():
    """
    Expose metrics in Prometheus format.

    This endpoint returns metrics that can be scraped by Prometheus,
    including:
    - HTTP request counts and latencies
    - Deployment counts and durations
    - Authentication attempts
    - Rate limit hits
    - System gauges (active deployments, connected users)
    """
    metrics_text = get_metrics_text()
    return Response(
        content=metrics_text,
        media_type="text/plain; charset=utf-8"
    )
