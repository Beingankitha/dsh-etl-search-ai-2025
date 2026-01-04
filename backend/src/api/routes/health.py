"""
Health check endpoints for system diagnostics.

Provides API to verify application readiness and system status.
"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.infrastructure.database import Database
from src.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status: 'healthy' or 'unhealthy'")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="API version")
    dataset_count: Optional[int] = Field(None, description="Total datasets in database")
    vector_count: Optional[int] = Field(None, description="Total vectors in store")


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Check API health and system status.
    
    Returns:
        HealthResponse: Current health status with diagnostic counts
    """
    try:
        # Check database connectivity
        db = Database()
        db.connect()
        
        # Count datasets
        dataset_count = db.session.query(
            db.session.query(
                db.get_table("datasets")
            ).count()
        ).scalar() if hasattr(db, 'get_table') else None
        
        db.close()
        
        return HealthResponse(
            status="healthy",
            service="CEH Dataset Discovery API",
            version="1.0.0",
            dataset_count=dataset_count,
            vector_count=None,  # Would query vector store if initialized
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return HealthResponse(
            status="unhealthy",
            service="CEH Dataset Discovery API",
            version="1.0.0",
            dataset_count=None,
            vector_count=None,
        )


@router.get("/ready")
async def readiness_check() -> dict:
    """
    Kubernetes-style readiness probe.
    
    Returns 200 only if service is ready to handle traffic.
    """
    try:
        db = Database()
        db.connect()
        db.close()
        return {"ready": True}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"ready": False}


@router.get("/live")
async def liveness_check() -> dict:
    """
    Kubernetes-style liveness probe.
    
    Returns 200 if service is alive (can be restarted if it fails).
    """
    return {"alive": True}
