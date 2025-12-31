"""
Repository for SupportingDocument entities.
"""

from __future__ import annotations

import sqlite3
from typing import List, Dict, Any, Optional

from src.logging_config import get_logger
from src.models.database_models import SupportingDocument
from src.repositories.base_repository import BaseRepository, RepositoryError

logger = get_logger(__name__)


class SupportingDocumentRepository(BaseRepository[SupportingDocument]):
    """Repository for SupportingDocument entities."""

    @property
    def table_name(self) -> str:
        """Return table name."""
        return "supporting_documents"

    def _map_row_to_entity(self, row: sqlite3.Row) -> SupportingDocument:
        """Map database row to SupportingDocument entity."""
        return SupportingDocument(
            id=row["id"],
            dataset_id=row["dataset_id"],
            document_url=row["document_url"],
            title=row["title"],
            file_extension=row["file_extension"],
            downloaded_path=row["downloaded_path"],
            text_content=row["text_content"],
            embedding_id=row["embedding_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _map_entity_to_dict(self, entity: SupportingDocument) -> Dict[str, Any]:
        """Map SupportingDocument entity to dictionary."""
        return {
            "dataset_id": entity.dataset_id,
            "document_url": entity.document_url,
            "title": entity.title,
            "file_extension": entity.file_extension,
            "downloaded_path": entity.downloaded_path,
            "text_content": entity.text_content,
            "embedding_id": entity.embedding_id,
        }

    def get_by_dataset(self, dataset_id: int) -> List[SupportingDocument]:
        """
        Get all supporting documents for a dataset.

        Args:
            dataset_id: Dataset ID

        Returns:
            List of supporting documents
        """
        try:
            query = f"SELECT * FROM {self.table_name} WHERE dataset_id = ? ORDER BY created_at"
            cursor = self.connection.execute(query, (dataset_id,))
            rows = cursor.fetchall()

            return [self._map_row_to_entity(row) for row in rows]

        except sqlite3.Error as e:
            logger.error(f"Get by dataset failed: {e}")
            raise RepositoryError(f"Query failed: {e}") from e

    def get_with_text_content(self) -> List[SupportingDocument]:
        """
        Get all supporting documents that have extracted text content.

        Returns:
            List of documents with text
        """
        try:
            query = f"SELECT * FROM {self.table_name} WHERE text_content IS NOT NULL ORDER BY created_at"
            cursor = self.connection.execute(query)
            rows = cursor.fetchall()

            return [self._map_row_to_entity(row) for row in rows]

        except sqlite3.Error as e:
            logger.error(f"Get with text failed: {e}")
            raise RepositoryError(f"Query failed: {e}") from e

    def count_by_dataset(self, dataset_id: int) -> int:
        """
        Count supporting documents for a dataset.

        Args:
            dataset_id: Dataset ID

        Returns:
            Document count
        """
        try:
            query = f"SELECT COUNT(*) as cnt FROM {self.table_name} WHERE dataset_id = ?"
            cursor = self.connection.execute(query, (dataset_id,))
            row = cursor.fetchone()
            return row["cnt"] if row else 0

        except sqlite3.Error as e:
            logger.error(f"Count failed: {e}")
            raise RepositoryError(f"Query failed: {e}") from e