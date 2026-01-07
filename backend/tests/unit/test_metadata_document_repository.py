"""Tests for MetadataDocumentRepository."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.infrastructure.database import Database
from src.models.database_models import Dataset, MetadataDocument
from src.repositories.dataset_repository import DatasetRepository
from src.repositories.metadata_document_repository import MetadataDocumentRepository
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
        file_identifier="test-metadata-001",
        title="Test Dataset",
    )
    return repo.insert(dataset)


def test_insert_and_retrieve_metadata_document(database, dataset):
    """Test inserting and retrieving a metadata document."""
    repo = MetadataDocumentRepository(database.connection)
    
    doc = MetadataDocument(
        dataset_id=dataset.id,
        document_type="iso19139",
        original_content=b"<metadata>test</metadata>",
        mime_type="application/xml"
    )
    
    inserted = repo.insert(doc)
    retrieved = repo.get_by_id(inserted.id)
    
    assert inserted.id is not None
    assert retrieved.document_type == "iso19139"
    assert retrieved.original_content == b"<metadata>test</metadata>"


def test_get_by_dataset(database, dataset):
    """Test retrieving all metadata documents for a dataset."""
    repo = MetadataDocumentRepository(database.connection)
    
    for doc_type in ["iso19139", "json", "schema_org"]:
        repo.insert(MetadataDocument(
            dataset_id=dataset.id,
            document_type=doc_type,
            original_content=f"<{doc_type}>content</{doc_type}>".encode()
        ))
    
    results = repo.get_by_dataset(dataset.id)
    
    assert len(results) == 3
    assert all(d.dataset_id == dataset.id for d in results)


def test_get_by_type(database, dataset):
    """Test retrieving metadata documents by type."""
    repo = MetadataDocumentRepository(database.connection)
    
    # Insert documents with different types
    repo.insert(MetadataDocument(
        dataset_id=dataset.id,
        document_type="iso19139",
        original_content=b"iso1"
    ))
    repo.insert(MetadataDocument(
        dataset_id=dataset.id,
        document_type="iso19139",
        original_content=b"iso2"
    ))
    repo.insert(MetadataDocument(
        dataset_id=dataset.id,
        document_type="json",
        original_content=b"json1"
    ))
    
    iso_docs = repo.get_by_type("iso19139")
    json_docs = repo.get_by_type("json")
    
    assert len(iso_docs) >= 2
    assert len(json_docs) >= 1


def test_dataset_isolation(database):
    """Test that documents from different datasets are isolated."""
    dataset_repo = DatasetRepository(database.connection)
    doc_repo = MetadataDocumentRepository(database.connection)
    
    ds1 = dataset_repo.insert(Dataset(file_identifier="ds1", title="DS1"))
    ds2 = dataset_repo.insert(Dataset(file_identifier="ds2", title="DS2"))
    
    doc_repo.insert(MetadataDocument(
        dataset_id=ds1.id,
        document_type="json",
        original_content=b'{"ds": 1}'
    ))
    doc_repo.insert(MetadataDocument(
        dataset_id=ds2.id,
        document_type="json",
        original_content=b'{"ds": 2}'
    ))
    
    ds1_docs = doc_repo.get_by_dataset(ds1.id)
    ds2_docs = doc_repo.get_by_dataset(ds2.id)
    
    assert len(ds1_docs) == 1
    assert len(ds2_docs) == 1


def test_invalid_dataset_reference(database):
    """Test error when referencing non-existent dataset."""
    repo = MetadataDocumentRepository(database.connection)
    
    doc = MetadataDocument(
        dataset_id=999,
        document_type="json",
        original_content=b"content"
    )
    
    with pytest.raises(RepositoryError):
        repo.insert(doc)


def test_large_metadata_content(database, dataset):
    """Test storing large metadata content."""
    repo = MetadataDocumentRepository(database.connection)
    
    large_content = b"x" * (1024 * 1024)  # 1MB
    
    doc = MetadataDocument(
        dataset_id=dataset.id,
        document_type="json",
        original_content=large_content
    )
    
    inserted = repo.insert(doc)
    retrieved = repo.get_by_id(inserted.id)
    
    assert len(retrieved.original_content) == len(large_content)
