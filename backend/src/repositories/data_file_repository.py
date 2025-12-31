"""
Repository for DataFile entities.
"""

from __future__ import annotations

import sqlite3
from typing import List, Dict, Any, Optional

from src.logging_config import get_logger
from src.models.database_models import DataFile
from src.repositories.base_repository import BaseRepository, RepositoryError

logger = get_logger(__name__)


class DataFileRepository(BaseRepository[DataFile]):
    """Repository for DataFile entities."""

    @property
    def table_name(self) -> str:
        """Return table name."""
        return "data_files"

    def _map_row_to_entity(self, row: sqlite3.Row) -> DataFile:
        """Map database row to DataFile entity."""
        return DataFile(
            id=row["id"],
            dataset_id=row["dataset_id"],
            filename=row["filename"],
            file_path=row["file_path"],
            file_size=row["file_size"],
            mime_type=row["mime_type"],
            created_at=row["created_at"],
        )

    def _map_entity_to_dict(self, entity: DataFile) -> Dict[str, Any]:
        """Map DataFile entity to dictionary."""
        return {
            "dataset_id": entity.dataset_id,
            "filename": entity.filename,
            "file_path": entity.file_path,
            "file_size": entity.file_size,
            "mime_type": entity.mime_type,
        }

    def get_by_dataset(self, dataset_id: int) -> List[DataFile]:
        """
        Get all data files for a dataset.

        Args:
            dataset_id: Dataset ID

        Returns:
            List of data files
        """
        try:
            query = f"SELECT * FROM {self.table_name} WHERE dataset_id = ? ORDER BY filename"
            cursor = self.connection.execute(query, (dataset_id,))
            rows = cursor.fetchall()

            return [self._map_row_to_entity(row) for row in rows]

        except sqlite3.Error as e:
            logger.error(f"Get by dataset failed: {e}")
            raise RepositoryError(f"Query failed: {e}") from e

    def count_by_dataset(self, dataset_id: int) -> int:
        """
        Count data files for a dataset.

        Args:
            dataset_id: Dataset ID

        Returns:
            File count
        """
        try:
            query = f"SELECT COUNT(*) as cnt FROM {self.table_name} WHERE dataset_id = ?"
            cursor = self.connection.execute(query, (dataset_id,))
            row = cursor.fetchone()
            return row["cnt"] if row else 0

        except sqlite3.Error as e:
            logger.error(f"Count failed: {e}")
            raise RepositoryError(f"Query failed: {e}") from e