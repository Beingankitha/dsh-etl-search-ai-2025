"""
Unit of Work pattern for managing multiple repositories.

Provides transaction management across all repositories.
Implements explicit commit/rollback semantics for SQLite DEFERRED transactions.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

from src.config import get_settings
from src.infrastructure import Database, DatabaseError
from src.logging_config import get_logger
from .base_repository import BaseRepository
from .dataset_repository import DatasetRepository
from .metadata_document_repository import MetadataDocumentRepository
from .data_file_repository import DataFileRepository
from .supporting_document_repository import SupportingDocumentRepository

logger = get_logger(__name__)


class UnitOfWorkError(Exception):
    """Unit of Work specific error."""
    pass


class UnitOfWork:
    """
    Unit of Work pattern for transaction management.
    
    Manages multiple repositories and ensures transactional consistency.
    
    With SQLite DEFERRED isolation_level:
    - Transactions start on first write operation
    - Explicit commit() persists all changes
    - Explicit rollback() discards all changes
    - Context manager ensures automatic commit/rollback
    
    Example:
        with UnitOfWork(database) as uow:
            dataset = uow.datasets.insert(new_dataset)
            metadata = uow.metadata_documents.insert(new_metadata)
            # Auto-commits on successful exit
            
        # On exception, auto-rolls back
    """

    def __init__(self, database: Optional[Database] = None):
        """
        Initialize Unit of Work.

        Args:
            database: Database connection manager. 
                     If None, creates new instance using config.
                     
        Raises:
            UnitOfWorkError: If database initialization fails
        """
        if database is None:
            try:
                settings = get_settings()
                database = Database(settings.database_path)
                database.connect()
            except Exception as e:
                logger.error(f"Failed to initialize database: {e}")
                raise UnitOfWorkError(f"Database initialization failed: {e}") from e
        
        self.database = database
        self._connection: Optional[sqlite3.Connection] = None
        self._in_transaction = False
        
        # Repository instances
        self.datasets: Optional[DatasetRepository] = None
        self.metadata_documents: Optional[MetadataDocumentRepository] = None
        self.data_files: Optional[DataFileRepository] = None
        self.supporting_documents: Optional[SupportingDocumentRepository] = None

    def __enter__(self) -> UnitOfWork:
        """
        Enter context manager.
        
        Initializes all repositories with the database connection.
        SQLite DEFERRED transaction will start on first write.
        """
        try:
            self._connection = self.database.connection
            
            if not self._connection:
                raise UnitOfWorkError("Database connection not established")
            
            # Initialize all repositories with same connection
            # They will use this connection for all operations
            self.datasets = DatasetRepository(self._connection)
            self.metadata_documents = MetadataDocumentRepository(self._connection)
            self.data_files = DataFileRepository(self._connection)
            self.supporting_documents = SupportingDocumentRepository(self._connection)

            self._in_transaction = True
            logger.info("Unit of Work started (transaction will start on first write)")
            return self
            
        except Exception as e:
            logger.error(f"Failed to enter Unit of Work context: {e}")
            self._in_transaction = False
            raise UnitOfWorkError(f"Context enter failed: {e}") from e

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit context manager.
        
        Commits on success, rolls back on exception.
        
        Args:
            exc_type: Exception type (if any)
            exc_val: Exception value (if any)
            exc_tb: Exception traceback (if any)
        """
        try:
            if exc_type is not None:
                # Exception occurred - ROLLBACK
                self.rollback()
                logger.error(
                    f"Unit of Work rolled back due to {exc_type.__name__}: {exc_val}"
                )
            else:
                # Success - COMMIT
                self.commit()
                logger.info("Unit of Work committed successfully")
        except Exception as e:
            logger.error(f"Error during Unit of Work exit: {e}")
            raise UnitOfWorkError(f"Context exit failed: {e}") from e
        finally:
            self._in_transaction = False

    async def __aenter__(self) -> UnitOfWork:
        """Async context manager entry."""
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        return self.__exit__(exc_type, exc_val, exc_tb)

    def commit(self) -> None:
        """
        Commit transaction.
        
        Persists all changes made in this Unit of Work.
        Only works if connection is in a transaction.
        
        Raises:
            UnitOfWorkError: If commit fails
        """
        if not self._connection:
            logger.warning("Attempt to commit without active connection")
            return
            
        try:
            # Check if we're in a transaction (SQLite tracks this)
            # in_transaction is True if a transaction is active
            in_transaction = self._connection.in_transaction
            
            if in_transaction:
                self._connection.commit()
                logger.info("Transaction committed (all changes persisted)")
            # else: No active transaction (empty transaction), silently continue
                
        except sqlite3.Error as e:
            logger.error(f"Commit failed: {e}")
            raise UnitOfWorkError(f"Commit failed: {e}") from e

    def rollback(self) -> None:
        """
        Rollback transaction.
        
        Discards all changes made in this Unit of Work.
        Only works if connection is in a transaction.
        
        Raises:
            UnitOfWorkError: If rollback fails
        """
        if not self._connection:
            logger.warning("Attempt to rollback without active connection")
            return
            
        try:
            # Check if we're in a transaction
            in_transaction = self._connection.in_transaction
            
            if in_transaction:
                self._connection.rollback()
                logger.info("Transaction rolled back (all changes discarded)")
            # else: No active transaction (empty transaction), silently continue
                
        except sqlite3.Error as e:
            logger.error(f"Rollback failed: {e}")
            raise UnitOfWorkError(f"Rollback failed: {e}") from e

    def close(self) -> None:
        """Close the database connection."""
        if self.database:
            self.database.close()
            self._in_transaction = False
            logger.info("Unit of Work connection closed")