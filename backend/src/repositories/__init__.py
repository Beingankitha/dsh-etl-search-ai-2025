"""
Repository layer for data access patterns.

Provides repositories for all entity types and Unit of Work pattern
for transaction management.
"""

# Import base classes
from .base_repository import BaseRepository, RepositoryError

# Import specific repositories
from .dataset_repository import DatasetRepository
from .metadata_document_repository import MetadataDocumentRepository
from .data_file_repository import DataFileRepository
from .supporting_document_repository import SupportingDocumentRepository

# Import Unit of Work (after all repositories are available)
from .unit_of_work import UnitOfWork, UnitOfWorkError

__all__ = [
    "BaseRepository",
    "RepositoryError",
    "DatasetRepository",
    "MetadataDocumentRepository",
    "DataFileRepository",
    "SupportingDocumentRepository",
    "UnitOfWork",
    "UnitOfWorkError",
]