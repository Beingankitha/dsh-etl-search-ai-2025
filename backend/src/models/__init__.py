"""
Models module - API schemas and database entities.

Contains two types of models:
- API Schemas (schemas.py): Request/response models used by REST API
- Database Models (database_models.py): ORM entities for data persistence
"""

from .schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    Dataset,
    SearchRequest,
    SearchResponse,
    SearchResult,
)

from .database_models import (
    Dataset as DatasetEntity,
    MetadataDocument,
    DataFile,
    SupportingDocument,
)

__all__ = [
    # API Schemas
    "Dataset",
    "SearchResult",
    "SearchRequest",
    "SearchResponse",
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    # Database Models
    "DatasetEntity",
    "MetadataDocument",
    "DataFile",
    "SupportingDocument",
]