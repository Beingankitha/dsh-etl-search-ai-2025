"""
Abstract base repository class using repository pattern.

Provides generic CRUD operations for all entity types.
"""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List, Dict, Any

from src.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class RepositoryError(Exception):
    """Base exception for repository operations."""
    pass


class BaseRepository(ABC, Generic[T]):
    """
    Abstract base repository for generic CRUD operations.
    
    Generic type T represents the entity type (Dataset, MetadataDocument, etc).
    Subclasses must implement abstract methods for database mapping.
    
    CRITICAL: Repositories do NOT auto-commit. Use UnitOfWork for transaction management.
    """

    def __init__(self, connection: sqlite3.Connection):
        """
        Initialize repository.

        Args:
            connection: SQLite connection object (from UnitOfWork)
        """
        self.connection = connection

    @property
    @abstractmethod
    def table_name(self) -> str:
        """Return the database table name."""
        pass

    @abstractmethod
    def _map_row_to_entity(self, row: sqlite3.Row) -> T:
        """
        Map database row to entity object.

        Args:
            row: Database row

        Returns:
            Entity object
        """
        pass

    @abstractmethod
    def _map_entity_to_dict(self, entity: T) -> Dict[str, Any]:
        """
        Map entity object to dictionary for insertion.

        Args:
            entity: Entity object

        Returns:
            Dictionary of fields
        """
        pass

    def insert(self, entity: T) -> T:
        """
        Insert new entity (does NOT commit).

        Args:
            entity: Entity to insert

        Returns:
            Entity with ID assigned

        Raises:
            RepositoryError: If insertion fails
        """
        try:
            data = self._map_entity_to_dict(entity)
            columns = ", ".join(data.keys())
            placeholders = ", ".join("?" * len(data))
            query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"

            cursor = self.connection.execute(query, tuple(data.values()))
            # NOTE: NO COMMIT HERE - UnitOfWork handles commit/rollback
            
            logger.debug(f"Inserted {self.table_name}: {cursor.lastrowid}")
            # Refetch to get auto-generated ID
            return self.get_by_id(cursor.lastrowid)

        except sqlite3.Error as e:
            logger.error(f"Insert failed: {e}")
            raise RepositoryError(f"Insert failed: {e}") from e

    def update(self, entity: T, entity_id: int) -> T:
        """
        Update existing entity (does NOT commit).

        Args:
            entity: Updated entity
            entity_id: Entity ID to update

        Returns:
            Updated entity

        Raises:
            RepositoryError: If update fails
        """
        try:
            data = self._map_entity_to_dict(entity)
            # Remove id from update
            data.pop("id", None)
            
            set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
            query = f"UPDATE {self.table_name} SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"

            self.connection.execute(query, tuple(list(data.values()) + [entity_id]))
            # NOTE: NO COMMIT HERE - UnitOfWork handles commit/rollback
            
            logger.debug(f"Updated {self.table_name} id={entity_id}")
            return self.get_by_id(entity_id)

        except sqlite3.Error as e:
            logger.error(f"Update failed: {e}")
            raise RepositoryError(f"Update failed: {e}") from e

    def upsert(self, entity: T, unique_field: str, unique_value: Any) -> T:
        """
        Insert or update entity based on unique field (does NOT commit).

        Args:
            entity: Entity to insert/update
            unique_field: Field name for uniqueness check
            unique_value: Value to check

        Returns:
            Inserted or updated entity

        Raises:
            RepositoryError: If operation fails
        """
        try:
            # Check if exists
            existing = self.get_by_field(unique_field, unique_value)

            if existing:
                return self.update(entity, existing.id)
            else:
                return self.insert(entity)

        except RepositoryError:
            raise
        except Exception as e:
            logger.error(f"Upsert failed: {e}")
            raise RepositoryError(f"Upsert failed: {e}") from e

    def get_by_id(self, entity_id: int) -> Optional[T]:
        """
        Get entity by ID (read-only, no commit needed).

        Args:
            entity_id: Entity ID

        Returns:
            Entity or None if not found
        """
        try:
            query = f"SELECT * FROM {self.table_name} WHERE id = ?"
            cursor = self.connection.execute(query, (entity_id,))
            row = cursor.fetchone()

            return self._map_row_to_entity(row) if row else None

        except sqlite3.Error as e:
            logger.error(f"Get by ID failed: {e}")
            raise RepositoryError(f"Query failed: {e}") from e

    def get_by_field(self, field_name: str, field_value: Any) -> Optional[T]:
        """
        Get single entity by field value (read-only, no commit needed).

        Args:
            field_name: Field name
            field_value: Field value

        Returns:
            Entity or None if not found
        """
        try:
            query = f"SELECT * FROM {self.table_name} WHERE {field_name} = ? LIMIT 1"
            cursor = self.connection.execute(query, (field_value,))
            row = cursor.fetchone()

            return self._map_row_to_entity(row) if row else None

        except sqlite3.Error as e:
            logger.error(f"Get by field failed: {e}")
            raise RepositoryError(f"Query failed: {e}") from e

    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """
        Get all entities with pagination (read-only, no commit needed).

        Args:
            limit: Maximum records to return
            offset: Number of records to skip

        Returns:
            List of entities
        """
        try:
            query = f"SELECT * FROM {self.table_name} LIMIT ? OFFSET ?"
            cursor = self.connection.execute(query, (limit or -1, offset))
            rows = cursor.fetchall()

            return [self._map_row_to_entity(row) for row in rows]

        except sqlite3.Error as e:
            logger.error(f"Get all failed: {e}")
            raise RepositoryError(f"Query failed: {e}") from e

    def get_paginated(self, limit: int = 10, offset: int = 0) -> List[T]:
        """
        Get paginated entities (convenience alias for get_all).

        Args:
            limit: Maximum records per page
            offset: Starting record offset

        Returns:
            List of entities for current page
        """
        return self.get_all(limit=limit, offset=offset)

    def count(self) -> int:
        """
        Get total entity count (read-only, no commit needed).

        Returns:
            Total count
        """
        try:
            query = f"SELECT COUNT(*) as cnt FROM {self.table_name}"
            cursor = self.connection.execute(query)
            row = cursor.fetchone()

            return row["cnt"] if row else 0

        except sqlite3.Error as e:
            logger.error(f"Count failed: {e}")
            raise RepositoryError(f"Query failed: {e}") from e

    def delete(self, entity_id: int) -> bool:
        """
        Delete entity by ID (does NOT commit).

        Args:
            entity_id: Entity ID

        Returns:
            True if deleted, False if not found

        Raises:
            RepositoryError: If deletion fails
        """
        try:
            query = f"DELETE FROM {self.table_name} WHERE id = ?"
            cursor = self.connection.execute(query, (entity_id,))
            # NOTE: NO COMMIT HERE - UnitOfWork handles commit/rollback
            
            deleted = cursor.rowcount > 0
            logger.debug(f"Deleted {self.table_name} id={entity_id}: {deleted}")
            return deleted

        except sqlite3.Error as e:
            logger.error(f"Delete failed: {e}")
            raise RepositoryError(f"Delete failed: {e}") from e

    def delete_by_field(self, field_name: str, field_value: Any) -> int:
        """
        Delete entities by field value (does NOT commit).

        Args:
            field_name: Field name
            field_value: Field value

        Returns:
            Number of rows deleted
        """
        try:
            query = f"DELETE FROM {self.table_name} WHERE {field_name} = ?"
            cursor = self.connection.execute(query, (field_value,))
            # NOTE: NO COMMIT HERE - UnitOfWork handles commit/rollback
            
            logger.debug(f"Deleted {cursor.rowcount} rows from {self.table_name}")
            return cursor.rowcount

        except sqlite3.Error as e:
            logger.error(f"Delete failed: {e}")
            raise RepositoryError(f"Delete failed: {e}") from e