"""Tests for DatasetRepository."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.infrastructure.database import Database
from src.models.database_models import Dataset
from src.repositories.dataset_repository import DatasetRepository


@pytest.fixture
def database():
    """Create temporary test database."""
    with TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        db.connect()
        db.create_tables()
        yield db
        db.close()


def test_insert_dataset(database):
    """Test inserting a dataset."""
    repo = DatasetRepository(database.connection)
    
    dataset = Dataset(
        file_identifier="test-001",
        title="Test Dataset",
        abstract="A test dataset",
        topic_category="environment",
        keywords="test,data",
        source_format="iso"
    )
    
    result = repo.insert(dataset)
    
    assert result.id is not None
    assert result.file_identifier == "test-001"


def test_get_by_file_identifier(database):
    """Test retrieving dataset by file identifier."""
    repo = DatasetRepository(database.connection)
    
    dataset = Dataset(
        file_identifier="test-002",
        title="Test Dataset 2",
        abstract="Another test"
    )
    repo.insert(dataset)
    
    result = repo.get_by_file_identifier("test-002")
    
    assert result is not None
    assert result.title == "Test Dataset 2"


def test_upsert_inserts_new(database):
    """Test upsert inserts new dataset."""
    repo = DatasetRepository(database.connection)
    
    dataset = Dataset(
        file_identifier="test-003",
        title="Test Dataset 3"
    )
    
    result = repo.upsert_by_identifier(dataset)
    
    assert result.id is not None


def test_upsert_updates_existing(database):
    """Test upsert updates existing dataset."""
    repo = DatasetRepository(database.connection)
    
    dataset1 = Dataset(
        file_identifier="test-004",
        title="Original Title"
    )
    result1 = repo.insert(dataset1)
    
    dataset2 = Dataset(
        file_identifier="test-004",
        title="Updated Title"
    )
    result2 = repo.upsert_by_identifier(dataset2)
    
    assert result1.id == result2.id
    assert result2.title == "Updated Title"


def test_count_datasets(database):
    """Test counting datasets."""
    repo = DatasetRepository(database.connection)
    
    for i in range(3):
        repo.insert(Dataset(
            file_identifier=f"test-{i}",
            title=f"Dataset {i}"
        ))
    
    count = repo.count()
    assert count == 3


def test_search_by_keyword(database):
    """Test searching datasets by keyword."""
    repo = DatasetRepository(database.connection)
    
    repo.insert(Dataset(
        file_identifier="env-001",
        title="Environmental Survey",
        abstract="Environmental data"
    ))
    repo.insert(Dataset(
        file_identifier="soil-001",
        title="Soil Analysis",
        abstract="Agricultural data"
    ))
    
    results = repo.search_by_keyword("environmental")
    
    assert len(results) == 1
    assert results[0].file_identifier == "env-001"