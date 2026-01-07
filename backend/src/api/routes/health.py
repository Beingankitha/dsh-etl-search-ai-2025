"""
Health check endpoints for system diagnostics.

Provides API to verify application readiness and system status.
"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.infrastructure.database import Database
from src.services.embeddings import VectorStore
from src.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    """Health check response model with comprehensive system status."""
    status: str = Field(
        ..., 
        description="Service status: 'healthy' or 'unhealthy'",
        example="healthy"
    )
    service: str = Field(
        ..., 
        description="Service name",
        example="CEH Dataset Discovery API"
    )
    version: str = Field(
        ..., 
        description="API version",
        example="1.0.0"
    )
    # Database counts
    dataset_count: Optional[int] = Field(
        None, 
        description="Total datasets in database",
        example=200
    )
    metadata_documents_count: Optional[int] = Field(
        None, 
        description="Total parsed metadata documents",
        example=200
    )
    data_files_count: Optional[int] = Field(
        None, 
        description="Total data files associated with datasets",
        example=452
    )
    supporting_documents_count: Optional[int] = Field(
        None, 
        description="Total supporting documents discovered",
        example=1694
    )
    # Vector store counts
    vector_dataset_count: Optional[int] = Field(
        None, 
        description="Total dataset vectors in vector store",
        example=200
    )
    vector_supporting_docs_count: Optional[int] = Field(
        None, 
        description="Total supporting document vectors in vector store",
        example=0
    )


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Check API health and system status with comprehensive diagnostics.
    
    Returns:
        HealthResponse: Current health status with all diagnostic counts
            - Database counts: datasets, metadata_documents, data_files, supporting_documents
            - Vector store counts: dataset vectors, supporting doc vectors
    """
    try:
        # Check database connectivity and get counts
        db = Database()
        db.connect()
        
        cursor = db.connection.cursor()
        
        # Count all database tables
        cursor.execute("SELECT COUNT(*) FROM datasets")
        dataset_count = cursor.fetchone()[0] if cursor else 0
        
        cursor.execute("SELECT COUNT(*) FROM metadata_documents")
        metadata_count = cursor.fetchone()[0] if cursor else 0
        
        cursor.execute("SELECT COUNT(*) FROM data_files")
        data_files_count = cursor.fetchone()[0] if cursor else 0
        
        cursor.execute("SELECT COUNT(*) FROM supporting_documents")
        supporting_docs_count = cursor.fetchone()[0] if cursor else 0
        
        db.close()
        
        # Check vector store and get vector counts
        vector_dataset_count = None
        vector_supporting_docs_count = None
        try:
            vector_store = VectorStore()
            vector_dataset_count = vector_store.get_dataset_count()
            vector_supporting_docs_count = vector_store.get_supporting_docs_count()
            logger.debug(
                f"Vector store health: datasets={vector_dataset_count}, "
                f"supporting_docs={vector_supporting_docs_count}"
            )
        except Exception as e:
            logger.warning(f"Vector store not fully available: {e}")
        
        return HealthResponse(
            status="healthy",
            service="CEH Dataset Discovery API",
            version="1.0.0",
            dataset_count=dataset_count,
            metadata_documents_count=metadata_count,
            data_files_count=data_files_count,
            supporting_documents_count=supporting_docs_count,
            vector_dataset_count=vector_dataset_count,
            vector_supporting_docs_count=vector_supporting_docs_count,
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return HealthResponse(
            status="unhealthy",
            service="CEH Dataset Discovery API",
            version="1.0.0",
            dataset_count=None,
            metadata_documents_count=None,
            data_files_count=None,
            supporting_documents_count=None,
            vector_dataset_count=None,
            vector_supporting_docs_count=None,
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
