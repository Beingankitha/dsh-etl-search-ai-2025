"""Tests for DataFileRepository."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.infrastructure.database import Database
from src.models.database_models import Dataset, DataFile
from src.repositories.dataset_repository import DatasetRepository
from src.repositories.data_file_repository import DataFileRepository
from src.repositories.base_repository import RepositoryError


@pytest.fixture
def database():
    """Create temporary test database."""
    with TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        db.connect()
        db.create_tables()
        yield db
        db.close()


@pytest.fixture
def dataset(database):
    """Create a test dataset."""
    repo = DatasetRepository(database.connection)
    dataset = Dataset(
        file_identifier="test-dataset-001",
        title="Test Dataset",
    )
    return repo.insert(dataset)


def test_insert_and_retrieve_data_file(database, dataset):
    """Test inserting and retrieving a data file."""
    repo = DataFileRepository(database.connection)
    
    file = DataFile(
        dataset_id=dataset.id,
        filename="data.csv",
        file_path="/data/test.csv",
        file_size=1024,
        mime_type="text/csv"
    )
    
    inserted = repo.insert(file)
    retrieved = repo.get_by_id(inserted.id)
    
    assert inserted.id is not None
    assert retrieved.filename == "data.csv"
    assert retrieved.dataset_id == dataset.id


def test_get_by_dataset(database, dataset):
    """Test retrieving all data files for a dataset."""
    repo = DataFileRepository(database.connection)
    
    # Insert multiple files
    for filename in ["data.csv", "map.shp", "image.tif"]:
        repo.insert(DataFile(
            dataset_id=dataset.id,
            filename=filename
        ))
    
    results = repo.get_by_dataset(dataset.id)
    
    assert len(results) == 3
    assert all(f.dataset_id == dataset.id for f in results)


def test_count_by_dataset(database, dataset):
    """Test counting data files for a dataset."""
    repo = DataFileRepository(database.connection)
    
    for i in range(5):
        repo.insert(DataFile(
            dataset_id=dataset.id,
            filename=f"file_{i}.csv"
        ))
    
    count = repo.count_by_dataset(dataset.id)
    assert count == 5


def test_count_by_dataset_empty(database, dataset):
    """Test counting when no files exist."""
    repo = DataFileRepository(database.connection)
    count = repo.count_by_dataset(dataset.id)
    assert count == 0


def test_dataset_isolation(database):
    """Test that files from different datasets are isolated."""
    dataset_repo = DatasetRepository(database.connection)
    file_repo = DataFileRepository(database.connection)
    
    # Create two datasets
    ds1 = dataset_repo.insert(Dataset(file_identifier="ds1", title="DS1"))
    ds2 = dataset_repo.insert(Dataset(file_identifier="ds2", title="DS2"))
    
    # Add files
    file_repo.insert(DataFile(dataset_id=ds1.id, filename="file1.csv"))
    file_repo.insert(DataFile(dataset_id=ds2.id, filename="file2.csv"))
    
    ds1_files = file_repo.get_by_dataset(ds1.id)
    ds2_files = file_repo.get_by_dataset(ds2.id)
    
    assert len(ds1_files) == 1
    assert len(ds2_files) == 1
    assert ds1_files[0].filename == "file1.csv"
    assert ds2_files[0].filename == "file2.csv"


def test_invalid_dataset_reference(database):
    """Test error when referencing non-existent dataset."""
    repo = DataFileRepository(database.connection)
    
    file = DataFile(dataset_id=999, filename="test.csv")
    
    with pytest.raises(RepositoryError):
        repo.insert(file)


def test_files_ordered_by_filename(database, dataset):
    """Test that files are returned ordered by filename."""
    repo = DataFileRepository(database.connection)
    
    filenames = ["zebra.csv", "apple.csv", "monkey.csv"]
    for fname in filenames:
        repo.insert(DataFile(dataset_id=dataset.id, filename=fname))
    
    results = repo.get_by_dataset(dataset.id)
    result_names = [f.filename for f in results]
    
    assert result_names == sorted(filenames)
