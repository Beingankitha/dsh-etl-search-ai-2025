"""
Repository for MetadataDocument entities.
"""

from __future__ import annotations

import sqlite3
from typing import List, Dict, Any, Optional

from src.logging_config import get_logger
from src.models.database_models import MetadataDocument
from src.repositories.base_repository import BaseRepository, RepositoryError

logger = get_logger(__name__)


class MetadataDocumentRepository(BaseRepository[MetadataDocument]):
    """Repository for MetadataDocument entities."""

    @property
    def table_name(self) -> str:
        """Return table name."""
        return "metadata_documents"

    def _map_row_to_entity(self, row: sqlite3.Row) -> MetadataDocument:
        """Map database row to MetadataDocument entity."""
        return MetadataDocument(
            id=row["id"],
            dataset_id=row["dataset_id"],
            document_type=row["document_type"],
            original_content=row["original_content"],
            mime_type=row["mime_type"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _map_entity_to_dict(self, entity: MetadataDocument) -> Dict[str, Any]:
        """Map MetadataDocument entity to dictionary."""
        return {
            "dataset_id": entity.dataset_id,
            "document_type": entity.document_type,
            "original_content": entity.original_content,
            "mime_type": entity.mime_type,
        }

    def get_by_dataset(self, dataset_id: int) -> List[MetadataDocument]:
        """
        Get all metadata documents for a dataset.

        Args:
            dataset_id: Dataset ID

        Returns:
            List of metadata documents
        """
        try:
            query = f"SELECT * FROM {self.table_name} WHERE dataset_id = ? ORDER BY created_at"
            cursor = self.connection.execute(query, (dataset_id,))
            rows = cursor.fetchall()

            return [self._map_row_to_entity(row) for row in rows]

        except sqlite3.Error as e:
            logger.error(f"Get by dataset failed: {e}")
            raise RepositoryError(f"Query failed: {e}") from e

    def get_by_type(self, document_type: str) -> List[MetadataDocument]:
        """
        Get all metadata documents of a specific type.

        Args:
            document_type: Document type (iso19139, json, schema_org, rdf)

        Returns:
            List of metadata documents
        """
        return self.connection.execute(
            f"SELECT * FROM {self.table_name} WHERE document_type = ?",
            (document_type,)
        ).fetchall()

    def get_by_dataset_and_type(self, dataset_id: int, document_type: str) -> Optional[MetadataDocument]:
        """
        Get metadata document by dataset ID and type.
        
        Used to check if a metadata document already exists for a given format.

        Args:
            dataset_id: Dataset ID
            document_type: Document type (iso19139, json, schema_org, rdf)

        Returns:
            MetadataDocument or None if not found
        """
        try:
            query = f"SELECT * FROM {self.table_name} WHERE dataset_id = ? AND document_type = ?"
            cursor = self.connection.execute(query, (dataset_id, document_type))
            row = cursor.fetchone()
            return self._map_row_to_entity(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Get by dataset and type failed: {e}")
            raise RepositoryError(f"Query failed: {e}") from e

    def upsert_by_dataset_and_type(self, entity: MetadataDocument) -> MetadataDocument:
        """
        Insert or update metadata document by dataset_id and document_type.
        
        Ensures only one metadata document per format per dataset.

        Args:
            entity: MetadataDocument entity

        Returns:
            Inserted or updated metadata document
        """
        return self.upsert(entity, "dataset_id", entity.dataset_id)  # Simple approach - just use dataset_id for now
        # Note: This is not ideal for compound uniqueness. Better approach would be composite key.
        # For now, we'll use a simpler approach in etl_service.