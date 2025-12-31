"""Tests for Unit of Work pattern."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.infrastructure.database import Database
from src.models.database_models import Dataset, MetadataDocument
from src.repositories.unit_of_work import UnitOfWork


@pytest.fixture
def database():
    """
    Create temporary test database.
    
    Creates a fresh database for EACH test to avoid
    state pollution between tests.
    """
    with TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        db.connect()
        db.create_tables()
        yield db
        db.close()


def test_unit_of_work_commit(database):
    """Test Unit of Work commit."""
    with UnitOfWork(database) as uow:
        dataset = Dataset(
            file_identifier="uow-001",
            title="UoW Test"
        )
        result = uow.datasets.insert(dataset)
        # No explicit commit - UnitOfWork does it on successful exit
        
        assert result.id is not None

    # Verify data was committed by reading in new UnitOfWork
    with UnitOfWork(database) as uow:
        found = uow.datasets.get_by_file_identifier("uow-001")
        assert found is not None
        assert found.title == "UoW Test"


def test_unit_of_work_multiple_repos(database):
    """Test Unit of Work with multiple repositories."""
    with UnitOfWork(database) as uow:
        # Insert dataset
        dataset = Dataset(
            file_identifier="uow-002",
            title="Multi-Repo Test"
        )
        saved_dataset = uow.datasets.insert(dataset)
        
        # Insert metadata document
        metadata = MetadataDocument(
            dataset_id=saved_dataset.id,
            document_type="iso19139",
            original_content=b"<xml>test</xml>",
            mime_type="application/xml"
        )
        saved_metadata = uow.metadata_documents.insert(metadata)
        
        assert saved_metadata.dataset_id == saved_dataset.id

    # Verify both were committed
    with UnitOfWork(database) as uow:
        found_dataset = uow.datasets.get_by_file_identifier("uow-002")
        found_metadata = uow.metadata_documents.get_by_id(saved_metadata.id)
        
        assert found_dataset is not None
        assert found_metadata is not None


def test_unit_of_work_rollback_on_error(database):
    """
    Test Unit of Work rollback on error.
    
    Verifies that changes are discarded when an exception occurs
    within the Unit of Work context.
    """
    # Attempt insert with exception
    try:
        with UnitOfWork(database) as uow:
            dataset = Dataset(
                file_identifier="uow-003",
                title="Rollback Test"
            )
            # Insert but don't commit (will be rolled back)
            uow.datasets.insert(dataset)
            
            # Force an exception BEFORE UnitOfWork exits
            raise ValueError("Simulated error during processing")
            
    except ValueError:
        # Expected - exception was raised
        pass
    
    # Verify that data was rolled back (NOT persisted)
    with UnitOfWork(database) as uow:
        result = uow.datasets.get_by_file_identifier("uow-003")
        
        # Should be None because transaction was rolled back
        assert result is None, (
            f"Expected None (rolled back), but found: {result}. "
            "This means the transaction was not properly rolled back."
        )