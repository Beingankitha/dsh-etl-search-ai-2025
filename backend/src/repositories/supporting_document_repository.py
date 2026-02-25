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

    def upsert_by_url(self, entity: SupportingDocument) -> SupportingDocument:
        """
        Insert or update a supporting document by URL.
        
        Prevents duplicates by checking if (dataset_id, document_url) combination exists.
        If exists: updates the document with new text_content and other fields.
        If not exists: inserts a new document.

        Args:
            entity: SupportingDocument entity to upsert

        Returns:
            The inserted/updated SupportingDocument entity with ID

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            # Check if document already exists for this dataset and URL
            query = f"""
                SELECT * FROM {self.table_name} 
                WHERE dataset_id = ? AND document_url = ?
            """
            cursor = self.connection.execute(
                query, 
                (entity.dataset_id, entity.document_url)
            )
            existing_row = cursor.fetchone()

            if existing_row:
                # Update existing document
                existing_entity = self._map_row_to_entity(existing_row)
                entity.id = existing_entity.id  # Preserve ID
                entity.created_at = existing_entity.created_at  # Preserve creation time
                
                update_query = f"""
                    UPDATE {self.table_name} 
                    SET text_content = ?, 
                        title = ?, 
                        file_extension = ?, 
                        downloaded_path = ?, 
                        embedding_id = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """
                self.connection.execute(
                    update_query,
                    (
                        entity.text_content,
                        entity.title,
                        entity.file_extension,
                        entity.downloaded_path,
                        entity.embedding_id,
                        entity.id
                    )
                )
                logger.debug(f"Updated supporting document: {entity.document_url} (ID: {entity.id})")
            else:
                # Insert new document
                insert_query = f"""
                    INSERT INTO {self.table_name}
                    (dataset_id, document_url, title, file_extension, 
                     downloaded_path, text_content, embedding_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
                cursor = self.connection.execute(
                    insert_query,
                    (
                        entity.dataset_id,
                        entity.document_url,
                        entity.title,
                        entity.file_extension,
                        entity.downloaded_path,
                        entity.text_content,
                        entity.embedding_id
                    )
                )
                entity.id = cursor.lastrowid
                logger.debug(f"Inserted supporting document: {entity.document_url} (ID: {entity.id})")

            return entity

        except sqlite3.IntegrityError as e:
            logger.error(f"Integrity error during upsert: {e}")
            raise RepositoryError(f"Upsert failed due to constraint violation: {e}") from e
        except sqlite3.Error as e:
            logger.error(f"Upsert failed: {e}")
            raise RepositoryError(f"Upsert failed: {e}") from e