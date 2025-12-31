"""Tests for database initialization and connection."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.infrastructure.database import Database, DatabaseError


def test_database_creates_file():
    """Test that database file is created."""
    with TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        db.connect()
        
        assert db_path.exists()
        db.close()


def test_database_create_tables():
    """Test that schema is created correctly."""
    with TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        db.connect()
        db.create_tables()
        
        cursor = db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        
        assert "datasets" in tables
        assert "metadata_documents" in tables
        assert "data_files" in tables
        assert "supporting_documents" in tables
        
        db.close()


def test_database_context_manager():
    """Test database context manager."""
    with TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        
        with db as conn:
            assert conn is not None
            assert conn == db.connection


def test_database_foreign_keys_enabled():
    """Test that foreign key constraints are enabled."""
    with TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        db.connect()
        
        cursor = db.connection.execute("PRAGMA foreign_keys")
        enabled = cursor.fetchone()[0]
        
        assert enabled == 1  # Enabled
        db.close()