"""Tests for SupportingDocumentRepository."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.infrastructure.database import Database
from src.models.database_models import Dataset, SupportingDocument
from src.repositories.dataset_repository import DatasetRepository
from src.repositories.supporting_document_repository import SupportingDocumentRepository
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
        file_identifier="test-support-001",
        title="Test Dataset",
    )
    return repo.insert(dataset)


def test_insert_and_retrieve_supporting_document(database, dataset):
    """Test inserting and retrieving a supporting document."""
    repo = SupportingDocumentRepository(database.connection)
    
    doc = SupportingDocument(
        dataset_id=dataset.id,
        document_url="https://example.com/doc.pdf",
        title="Example Document",
        file_extension=".pdf",
        text_content="Sample content"
    )
    
    inserted = repo.insert(doc)
    retrieved = repo.get_by_id(inserted.id)
    
    assert inserted.id is not None
    assert retrieved.document_url == "https://example.com/doc.pdf"
    assert retrieved.title == "Example Document"


def test_get_by_dataset(database, dataset):
    """Test retrieving all supporting documents for a dataset."""
    repo = SupportingDocumentRepository(database.connection)
    
    urls = [
        "https://example.com/doc1.pdf",
        "https://example.com/doc2.pdf",
        "https://example.com/doc3.docx"
    ]
    
    for url in urls:
        repo.insert(SupportingDocument(
            dataset_id=dataset.id,
            document_url=url
        ))
    
    results = repo.get_by_dataset(dataset.id)
    
    assert len(results) == 3
    assert all(d.dataset_id == dataset.id for d in results)


def test_get_with_text_content(database, dataset):
    """Test retrieving supporting documents with extracted text."""
    repo = SupportingDocumentRepository(database.connection)
    
    # Insert documents with and without text
    repo.insert(SupportingDocument(
        dataset_id=dataset.id,
        document_url="https://example.com/with-text.pdf",
        text_content="Extracted text"
    ))
    repo.insert(SupportingDocument(
        dataset_id=dataset.id,
        document_url="https://example.com/no-text.pdf"
    ))
    
    results = repo.get_with_text_content()
    ds_results = [d for d in results if d.dataset_id == dataset.id]
    
    assert len(ds_results) >= 1
    assert all(d.text_content for d in ds_results)


def test_dataset_isolation(database):
    """Test that documents from different datasets are isolated."""
    dataset_repo = DatasetRepository(database.connection)
    doc_repo = SupportingDocumentRepository(database.connection)
    
    ds1 = dataset_repo.insert(Dataset(file_identifier="ds1", title="DS1"))
    ds2 = dataset_repo.insert(Dataset(file_identifier="ds2", title="DS2"))
    
    doc_repo.insert(SupportingDocument(
        dataset_id=ds1.id,
        document_url="https://example.com/ds1-doc.pdf"
    ))
    doc_repo.insert(SupportingDocument(
        dataset_id=ds2.id,
        document_url="https://example.com/ds2-doc.pdf"
    ))
    
    ds1_docs = doc_repo.get_by_dataset(ds1.id)
    ds2_docs = doc_repo.get_by_dataset(ds2.id)
    
    assert len(ds1_docs) == 1
    assert len(ds2_docs) == 1


def test_invalid_dataset_reference(database):
    """Test error when referencing non-existent dataset."""
    repo = SupportingDocumentRepository(database.connection)
    
    doc = SupportingDocument(
        dataset_id=999,
        document_url="https://example.com/test.pdf"
    )
    
    with pytest.raises(RepositoryError):
        repo.insert(doc)


def test_supporting_document_with_minimal_fields(database, dataset):
    """Test creating supporting document with minimal fields."""
    repo = SupportingDocumentRepository(database.connection)
    
    doc = SupportingDocument(
        dataset_id=dataset.id,
        document_url="https://example.com/minimal.pdf"
    )
    
    result = repo.insert(doc)
    retrieved = repo.get_by_id(result.id)
    
    assert result.id is not None
    assert retrieved.document_url == "https://example.com/minimal.pdf"
    assert retrieved.title is None
    assert retrieved.text_content is None


def test_large_text_content(database, dataset):
    """Test storing large text content."""
    repo = SupportingDocumentRepository(database.connection)
    
    large_text = "x" * (2 * 1024 * 1024)  # 2MB
    
    doc = SupportingDocument(
        dataset_id=dataset.id,
        document_url="https://example.com/large.pdf",
        text_content=large_text
    )
    
    inserted = repo.insert(doc)
    retrieved = repo.get_by_id(inserted.id)
    
    assert len(retrieved.text_content) == len(large_text)
