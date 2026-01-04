"""
Dataset collection endpoints.

Provides API for accessing the full dataset catalogue.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.logging_config import get_logger
from src.models.schemas import Dataset
from src.repositories import UnitOfWork

logger = get_logger(__name__)

router = APIRouter(prefix="/datasets", tags=["datasets"])


class DatasetListResponse(BaseModel):
    """Paginated dataset list response."""
    total: int = Field(..., description="Total number of datasets")
    limit: int = Field(..., description="Items returned in this page")
    offset: int = Field(..., description="Starting position")
    datasets: list[Dataset] = Field(default_factory=list, description="Dataset items")


# Dependency Injection
def get_unit_of_work() -> UnitOfWork:
    """Instantiate UnitOfWork."""
    return UnitOfWork()


@router.get("", response_model=DatasetListResponse)
async def list_datasets(
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Starting position"),
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> DatasetListResponse:
    """
    Get paginated list of all datasets.
    
    Args:
        limit: Number of datasets to return (1-100, default 10)
        offset: Starting position for pagination (default 0)
        uow: Injected UnitOfWork for data access
        
    Returns:
        Paginated list of datasets with metadata
        
    Examples:
        ```
        GET /api/datasets?limit=20&offset=0
        
        Response:
        {
            "total": 221,
            "limit": 20,
            "offset": 0,
            "datasets": [
                {
                    "file_identifier": "da123456",
                    "title": "UK Climate Data",
                    "abstract": "Long-term climate measurements...",
                    ...
                },
                ...
            ]
        }
        ```
    """
    try:
        logger.debug(f"Listing datasets: limit={limit} offset={offset}")
        
        # Get total count
        total = uow.datasets.count()
        
        # Get paginated results
        db_datasets = uow.datasets.get_paginated(offset=offset, limit=limit)
        
        # Convert DB models to Pydantic schemas
        datasets = [
            Dataset(
                file_identifier=ds.file_identifier,
                title=ds.title,
                abstract=ds.abstract or "",
                topic_category=ds.topic_category or [],
                keywords=ds.keywords or [],
                lineage=ds.lineage,
                supplemental_info=ds.supplemental_info,
                source_format=ds.source_format,
            )
            for ds in db_datasets
        ]
        
        logger.info(f"Returning {len(datasets)} of {total} datasets")
        
        return DatasetListResponse(
            total=total,
            limit=limit,
            offset=offset,
            datasets=datasets,
        )
        
    except Exception as e:
        logger.error(f"Error listing datasets: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve datasets"
        )


@router.get("/{file_identifier}", response_model=Dataset)
async def get_dataset(
    file_identifier: str,
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> Dataset:
    """
    Get single dataset by file identifier.
    
    Args:
        file_identifier: Unique dataset identifier
        uow: Injected UnitOfWork for data access
        
    Returns:
        Full dataset metadata
        
    Raises:
        HTTPException: 404 if dataset not found
        
    Examples:
        ```
        GET /api/datasets/da123456
        
        Response:
        {
            "file_identifier": "da123456",
            "title": "UK Climate Data",
            "abstract": "Long-term climate measurements...",
            "topic_category": ["climatologyMeteorologyAtmosphere"],
            "keywords": ["climate", "temperature", "UK"],
            "lineage": "Met Office",
            "supplemental_info": null,
            "source_format": "xml"
        }
        ```
    """
    try:
        logger.debug(f"Fetching dataset: {file_identifier}")
        
        # Fetch from database
        db_dataset = uow.datasets.get_by_file_identifier(file_identifier)
        
        if not db_dataset:
            logger.warning(f"Dataset not found: {file_identifier}")
            raise HTTPException(
                status_code=404,
                detail=f"Dataset '{file_identifier}' not found"
            )
        
        # Convert to Pydantic schema
        dataset = Dataset(
            file_identifier=db_dataset.file_identifier,
            title=db_dataset.title,
            abstract=db_dataset.abstract or "",
            topic_category=db_dataset.topic_category or [],
            keywords=db_dataset.keywords or [],
            lineage=db_dataset.lineage,
            supplemental_info=db_dataset.supplemental_info,
            source_format=db_dataset.source_format,
        )
        
        logger.info(f"Retrieved dataset: {file_identifier}")
        
        return dataset
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving dataset {file_identifier}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve dataset"
        )


@router.get("/{file_identifier}/related")
async def get_related_datasets(
    file_identifier: str,
    limit: int = Query(5, ge=1, le=20, description="Number of related datasets"),
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> dict:
    """
    Get datasets related to a given dataset.
    
    Related datasets are determined by shared keywords or topic categories.
    
    Args:
        file_identifier: Base dataset identifier
        limit: Maximum number of related datasets to return
        uow: Injected UnitOfWork for data access
        
    Returns:
        List of related datasets
        
    Note:
        Currently returns empty list. Future enhancement would use:
        - Shared keywords/categories
        - Similar embeddings
        - Citation networks
    """
    try:
        db_dataset = uow.datasets.get_by_file_identifier(file_identifier)
        
        if not db_dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        # TODO: Implement related dataset discovery using:
        # - Shared keywords
        # - Similar topic categories
        # - Vector similarity
        
        return {
            "file_identifier": file_identifier,
            "related": [],
            "count": 0,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching related datasets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch related datasets")
