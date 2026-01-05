"""
SQLite database connection manager and schema initialization.

Uses context manager pattern for safe connection handling.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from src.config import get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)


class DatabaseError(Exception):
    """Base exception for database errors."""
    pass


class Database:
    """
    SQLite database connection manager.
    
    Features:
    - Explicit transaction control (isolation_level='DEFERRED')
    - Context manager support
    - Automatic schema initialization
    - Foreign key enforcement
    
    Note: Uses isolation_level='DEFERRED' for proper transaction semantics.
    """

    def __init__(self, db_path: Optional[str | Path] = None):
        """
        Initialize database.

        Args:
            db_path: Path to SQLite database file. 
                    If None, uses DATABASE_PATH from settings.
        """
        if db_path is None:
            settings = get_settings()
            db_path = settings.database_path
        
        self.db_path = Path(db_path)
        self.connection: Optional[sqlite3.Connection] = None

    def __enter__(self) -> sqlite3.Connection:
        """Enter context manager."""
        self.connect()
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        self.close()

    async def __aenter__(self) -> sqlite3.Connection:
        """Async context manager entry."""
        self.connect()
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        self.close()

    def connect(self) -> None:
        """
        Establish database connection.
        
        Uses isolation_level='DEFERRED' for proper transaction semantics:
        - READ: No transaction started
        - WRITE: Transaction starts on first write
        - EXPLICIT COMMIT: Required to persist changes
        """
        try:
            # Create parent directories if needed
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Use isolation_level='DEFERRED' for proper transaction control
            # This prevents autocommit and requires explicit commit()
            # Use check_same_thread=False for async/multi-threaded environments
            # (Uvicorn uses multiple worker threads per request)
            self.connection = sqlite3.connect(
                str(self.db_path),
                isolation_level='DEFERRED',  # ← CRITICAL for rollback support
                timeout=30.0,
                check_same_thread=False  # ← CRITICAL for async environments
            )
            self.connection.row_factory = sqlite3.Row
            
            # Enable foreign key constraints
            # Use execute() to avoid implicit transaction
            self.connection.execute("PRAGMA foreign_keys = ON")
            
            # Optional: Enable query logging
            settings = get_settings()
            if settings.database_echo:
                self.connection.set_trace(print)
            logger.info(f"Connected to database: {self.db_path} (isolation_level=DEFERRED)")
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise DatabaseError(f"Connection failed: {e}") from e

    def close(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

    def create_tables(self) -> None:
        """Create all database tables."""
        if not self.connection:
            self.connect()

        try:
            cursor = self.connection.cursor()

            # Datasets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS datasets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_identifier TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    abstract TEXT,
                    topic_category TEXT,
                    keywords TEXT,
                    lineage TEXT,
                    supplemental_info TEXT,
                    source_format TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Metadata documents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metadata_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dataset_id INTEGER NOT NULL,
                    document_type TEXT NOT NULL,
                    original_content BLOB NOT NULL,
                    mime_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
                )
            """)

            # Data files table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS data_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dataset_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    file_path TEXT,
                    file_size INTEGER,
                    mime_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
                )
            """)

            # Supporting documents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS supporting_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dataset_id INTEGER NOT NULL,
                    document_url TEXT NOT NULL,
                    title TEXT,
                    file_extension TEXT,
                    downloaded_path TEXT,
                    text_content TEXT,
                    embedding_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
                )
            """)

            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_identifier 
                ON datasets(file_identifier)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_dataset_id 
                ON metadata_documents(dataset_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_data_files_dataset_id 
                ON data_files(dataset_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_supporting_docs_dataset_id 
                ON supporting_documents(dataset_id)
            """)

            self.connection.commit()
            logger.info("Database tables created successfully")

        except sqlite3.Error as e:
            logger.error(f"Failed to create tables: {e}")
            self.connection.rollback()
            raise DatabaseError(f"Schema creation failed: {e}") from e

    def execute(self, query: str, params: tuple = None) -> sqlite3.Cursor:
        """
        Execute a query.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Cursor object
        """
        if not self.connection:
            raise DatabaseError("Database not connected")

        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor
        except sqlite3.Error as e:
            logger.error(f"Query execution failed: {e}")
            raise DatabaseError(f"Query failed: {e}") from e

    def commit(self) -> None:
        """Commit transaction."""
        if self.connection:
            self.connection.commit()

    def rollback(self) -> None:
        """Rollback transaction."""
        if self.connection:
            self.connection.rollback()