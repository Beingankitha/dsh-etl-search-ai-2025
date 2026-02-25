"""
Database migration system for production-safe schema evolution.

This module provides:
- Migration versioning system
- Rollback support
- Transaction safety
- Migration status tracking

Usage:
    from src.infrastructure.migrations import run_migrations
    
    # Automatically runs all pending migrations
    run_migrations()
"""

import sqlite3
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Base exception for migration errors."""
    pass


class Migration:
    """Represents a single database migration."""
    
    def __init__(self, version: str, description: str, up_sql: str, down_sql: str):
        """
        Args:
            version: Migration version (e.g., "001", "002")
            description: Human-readable description
            up_sql: SQL to apply migration
            down_sql: SQL to rollback migration
        """
        self.version = version
        self.description = description
        self.up_sql = up_sql
        self.down_sql = down_sql


# ============================================================================
# ALL MIGRATIONS - Add new migrations here
# ============================================================================

MIGRATIONS: List[Migration] = [
    Migration(
        version="001",
        description="Initial schema: datasets, metadata_documents, data_files, supporting_documents",
        up_sql="""
            -- Datasets table
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
            );

            -- Metadata documents table
            CREATE TABLE IF NOT EXISTS metadata_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id INTEGER NOT NULL,
                document_type TEXT NOT NULL,
                original_content BLOB NOT NULL,
                mime_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
            );

            -- Data files table
            CREATE TABLE IF NOT EXISTS data_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                file_path TEXT,
                file_size INTEGER,
                mime_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
            );

            -- Supporting documents table
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
                FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
                UNIQUE(dataset_id, document_url)
            );

            -- Create indexes for performance
            CREATE INDEX IF NOT EXISTS idx_file_identifier ON datasets(file_identifier);
            CREATE INDEX IF NOT EXISTS idx_dataset_id ON metadata_documents(dataset_id);
            CREATE INDEX IF NOT EXISTS idx_data_files_dataset_id ON data_files(dataset_id);
            CREATE INDEX IF NOT EXISTS idx_supporting_docs_dataset_id ON supporting_documents(dataset_id);
        """,
        down_sql="""
            DROP TABLE IF EXISTS supporting_documents;
            DROP TABLE IF EXISTS data_files;
            DROP TABLE IF EXISTS metadata_documents;
            DROP TABLE IF EXISTS datasets;
        """
    ),
    # TODO: Add future migrations here
    # Migration(
    #     version="002",
    #     description="Add search_index table for performance",
    #     up_sql="CREATE TABLE ...",
    #     down_sql="DROP TABLE ..."
    # ),
]


class MigrationManager:
    """Manages database migrations."""
    
    def __init__(self, connection: sqlite3.Connection):
        """
        Args:
            connection: SQLite database connection
        """
        self.connection = connection
        self._init_migration_table()
    
    def _init_migration_table(self) -> None:
        """Create migrations tracking table if not exists."""
        cursor = self.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT UNIQUE NOT NULL,
                description TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT CHECK(status IN ('applied', 'failed')) DEFAULT 'applied'
            )
        """)
        self.connection.commit()
    
    def get_applied_migrations(self) -> List[str]:
        """Get list of already-applied migrations."""
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT version FROM migrations WHERE status = 'applied' ORDER BY version"
        )
        return [row[0] for row in cursor.fetchall()]
    
    def get_pending_migrations(self) -> List[Migration]:
        """Get list of migrations that haven't been applied."""
        applied = set(self.get_applied_migrations())
        return [m for m in MIGRATIONS if m.version not in applied]
    
    def apply_migration(self, migration: Migration) -> bool:
        """
        Apply a single migration with transaction safety.
        
        Args:
            migration: Migration to apply
            
        Returns:
            True if successful, False otherwise
        """
        cursor = self.connection.cursor()
        try:
            logger.info(f"Applying migration {migration.version}: {migration.description}")
            
            # Execute migration in transaction
            cursor.executescript(migration.up_sql)
            
            # Record migration
            cursor.execute(
                "INSERT INTO migrations (version, description, status) VALUES (?, ?, 'applied')",
                (migration.version, migration.description)
            )
            
            self.connection.commit()
            logger.info(f"✓ Migration {migration.version} applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"✗ Migration {migration.version} failed: {e}")
            self.connection.rollback()
            
            # Record failure
            try:
                cursor.execute(
                    "INSERT OR REPLACE INTO migrations (version, description, status) VALUES (?, ?, 'failed')",
                    (migration.version, migration.description)
                )
                self.connection.commit()
            except:
                pass
            
            return False
    
    def rollback_migration(self, migration: Migration) -> bool:
        """
        Rollback a single migration.
        
        Args:
            migration: Migration to rollback
            
        Returns:
            True if successful, False otherwise
        """
        cursor = self.connection.cursor()
        try:
            logger.info(f"Rolling back migration {migration.version}: {migration.description}")
            
            # Execute rollback in transaction
            cursor.executescript(migration.down_sql)
            
            # Remove migration record
            cursor.execute("DELETE FROM migrations WHERE version = ?", (migration.version,))
            
            self.connection.commit()
            logger.info(f"✓ Migration {migration.version} rolled back successfully")
            return True
            
        except Exception as e:
            logger.error(f"✗ Rollback of migration {migration.version} failed: {e}")
            self.connection.rollback()
            return False
    
    def run_pending_migrations(self) -> Tuple[int, int]:
        """
        Run all pending migrations in order.
        
        Returns:
            Tuple of (successful, failed) migration counts
        """
        pending = self.get_pending_migrations()
        
        if not pending:
            logger.info("✓ No pending migrations")
            return 0, 0
        
        logger.info(f"Running {len(pending)} pending migrations...")
        
        successful = 0
        failed = 0
        
        for migration in pending:
            if self.apply_migration(migration):
                successful += 1
            else:
                failed += 1
                # Stop on first failure for safety
                logger.error("Stopping on migration failure")
                break
        
        if failed == 0:
            logger.info(f"✓ All {successful} migrations applied successfully")
        else:
            logger.error(f"✗ {failed} migration(s) failed")
        
        return successful, failed
    
    def status(self) -> None:
        """Print migration status."""
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()
        
        print("\n" + "=" * 60)
        print("MIGRATION STATUS")
        print("=" * 60)
        
        print(f"\nApplied Migrations ({len(applied)}):")
        if applied:
            for version in applied:
                migration = next((m for m in MIGRATIONS if m.version == version), None)
                desc = migration.description if migration else "Unknown"
                print(f"  ✓ {version}: {desc}")
        else:
            print("  None")
        
        print(f"\nPending Migrations ({len(pending)}):")
        if pending:
            for migration in pending:
                print(f"  ○ {migration.version}: {migration.description}")
        else:
            print("  None")
        
        print("\n" + "=" * 60)


def run_migrations(connection: sqlite3.Connection) -> Tuple[int, int]:
    """
    Run all pending migrations.
    
    Args:
        connection: SQLite database connection
        
    Returns:
        Tuple of (successful, failed) migration counts
        
    Raises:
        MigrationError: If any migration fails
    """
    manager = MigrationManager(connection)
    successful, failed = manager.run_pending_migrations()
    
    if failed > 0:
        raise MigrationError(f"{failed} migration(s) failed")
    
    return successful, failed


def show_migration_status(connection: sqlite3.Connection) -> None:
    """Show migration status."""
    manager = MigrationManager(connection)
    manager.status()
