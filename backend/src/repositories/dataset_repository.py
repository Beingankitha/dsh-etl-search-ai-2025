"""
Repository for Dataset entities.

Handles CRUD operations for datasets with specific methods
for dataset-related queries.
"""

from __future__ import annotations

import sqlite3
from typing import Optional, List, Dict, Any

from src.logging_config import get_logger
from src.models.database_models import Dataset
from src.repositories.base_repository import BaseRepository, RepositoryError

logger = get_logger(__name__)


class DatasetRepository(BaseRepository[Dataset]):
    """Repository for Dataset entities."""

    @property
    def table_name(self) -> str:
        """Return table name."""
        return "datasets"

    def _map_row_to_entity(self, row: sqlite3.Row) -> Dataset:
        """Map database row to Dataset entity."""
        return Dataset(
            id=row["id"],
            file_identifier=row["file_identifier"],
            title=row["title"],
            abstract=row["abstract"],
            topic_category=row["topic_category"],
            keywords=row["keywords"],
            lineage=row["lineage"],
            supplemental_info=row["supplemental_info"],
            source_format=row["source_format"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _map_entity_to_dict(self, entity: Dataset) -> Dict[str, Any]:
        """Map Dataset entity to dictionary for database insertion."""
        return {
            "file_identifier": entity.file_identifier,
            "title": entity.title,
            "abstract": entity.abstract,
            "topic_category": entity.topic_category,
            "keywords": entity.keywords,
            "lineage": entity.lineage,
            "supplemental_info": entity.supplemental_info,
            "source_format": entity.source_format,
        }

    def get_by_file_identifier(self, file_identifier: str) -> Optional[Dataset]:
        """
        Get dataset by file identifier.

        Args:
            file_identifier: Dataset file identifier

        Returns:
            Dataset or None
        """
        return self.get_by_field("file_identifier", file_identifier)

    def upsert_by_identifier(self, entity: Dataset) -> Dataset:
        """
        Insert or update dataset by file_identifier.

        Args:
            entity: Dataset entity

        Returns:
            Inserted or updated dataset
        """
        return self.upsert(entity, "file_identifier", entity.file_identifier)

    def search_by_keyword(self, keyword: str) -> List[Dataset]:
        """
        Search datasets by keyword in title or abstract.

        Args:
            keyword: Search keyword

        Returns:
            List of matching datasets
        """
        try:
            query = f"""
                SELECT * FROM {self.table_name}
                WHERE title LIKE ? OR abstract LIKE ?
                ORDER BY title
            """
            search_term = f"%{keyword}%"
            cursor = self.connection.execute(query, (search_term, search_term))
            rows = cursor.fetchall()

            return [self._map_row_to_entity(row) for row in rows]

        except sqlite3.Error as e:
            logger.error(f"Search failed: {e}")
            raise RepositoryError(f"Search failed: {e}") from e

    def get_all_with_metadata(self, limit: Optional[int] = None, offset: int = 0) -> List[Dict]:
        """
        Get all datasets with related metadata documents count.

        Args:
            limit: Maximum records
            offset: Records to skip

        Returns:
            List of datasets with metadata info
        """
        try:
            query = f"""
                SELECT 
                    d.*,
                    COUNT(DISTINCT m.id) as metadata_count,
                    COUNT(DISTINCT df.id) as data_files_count,
                    COUNT(DISTINCT sd.id) as supporting_docs_count
                FROM {self.table_name} d
                LEFT JOIN metadata_documents m ON d.id = m.dataset_id
                LEFT JOIN data_files df ON d.id = df.dataset_id
                LEFT JOIN supporting_documents sd ON d.id = sd.dataset_id
                GROUP BY d.id
                LIMIT ? OFFSET ?
            """
            cursor = self.connection.execute(query, (limit or -1, offset))
            rows = cursor.fetchall()

            results = []
            for row in rows:
                dataset = self._map_row_to_entity(row)
                results.append({
                    "dataset": dataset,
                    "metadata_count": row["metadata_count"],
                    "data_files_count": row["data_files_count"],
                    "supporting_docs_count": row["supporting_docs_count"],
                })

            return results

        except sqlite3.Error as e:
            logger.error(f"Get all with metadata failed: {e}")
            raise RepositoryError(f"Query failed: {e}") from e