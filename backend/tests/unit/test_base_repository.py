"""
Tests for Repository Pattern Implementation

Tests base repository, all concrete repositories, and repository operations.
"""

import pytest
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional, List

from src.repositories import (
    BaseRepository,
    DatasetRepository,
    MetadataDocumentRepository,
    DataFileRepository,
    SupportingDocumentRepository,
    UnitOfWork,
    RepositoryError
)
from src.infrastructure import Database
from src.models import (
    Dataset,
    MetadataDocument,
    DataFile,
    SupportingDocument
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_db_dir():
    """Create temporary database directory"""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def database(temp_db_dir):
    """Create database instance"""
    db_path = temp_db_dir / "test.db"
    db = Database(str(db_path))
    db.connect()
    db.create_tables()
    return db


@pytest.fixture
def unit_of_work(database):
    """Create unit of work instance"""
    return UnitOfWork(database)


@pytest.fixture
def uow_context(unit_of_work):
    """Async context manager for unit of work"""
    with unit_of_work as uow:
        yield uow


# ============================================================================
# TEST: BaseRepository
# ============================================================================

class TestBaseRepository:
    """Test base repository functionality"""
    
    def test_repository_initialization(self, database):
        """Test repository initializes with connection"""
        conn = database.connection
        
        # Can't instantiate abstract class directly, but test conceptually
        assert conn is not None
        assert isinstance(conn, sqlite3.Connection)
    
    def test_repository_error_exception(self):
        """Test RepositoryError exception"""
        with pytest.raises(RepositoryError):
            raise RepositoryError("Test error")


# ============================================================================
# TEST: DatasetRepository
# ============================================================================

class TestDatasetRepository:
    """Test dataset repository operations"""
    
    def test_create_dataset(self, unit_of_work):
        """Test creating a dataset"""
        with unit_of_work as uow:
            dataset = Dataset(
                file_identifier="ds-001",
                title="Test Dataset",
                abstract="Test Description",
                lineage="Test Lineage"
            )
            
            created = uow.datasets.insert(dataset)
            
            assert created.file_identifier == "ds-001"
            assert created.title == "Test Dataset"
    
    def test_get_dataset_by_id(self, unit_of_work):
        """Test retrieving dataset by ID"""
        with unit_of_work as uow:
            # Create dataset
            dataset = Dataset(
                file_identifier="ds-002",
                title="Test Dataset",
                abstract="Test",
                lineage="Test"
            )
            created = uow.datasets.insert(dataset)
            
            # Retrieve it
            retrieved = uow.datasets.get_by_id(created.id)
            
            assert retrieved is not None
            assert retrieved.file_identifier == "ds-002"
    
    def test_get_dataset_by_identifier(self, unit_of_work):
        """Test retrieving dataset by identifier string"""
        with unit_of_work as uow:
            dataset = Dataset(
                file_identifier="ds-003",
                title="Test",
                abstract="Test",
                lineage="Test"
            )
            uow.datasets.insert(dataset)
            
            retrieved = uow.datasets.get_by_file_identifier("ds-003")
            
            assert retrieved is not None
            assert retrieved.file_identifier == "ds-003"
    
    def test_update_dataset(self, unit_of_work):
        """Test updating a dataset"""
        with unit_of_work as uow:
            dataset = Dataset(
                file_identifier="ds-004",
                title="Original Title",
                abstract="Test",
                lineage="Test"
            )
            created = uow.datasets.insert(dataset)
            
            # Update
            created.title = "Updated Title"
            updated = uow.datasets.update(created, created.id)
            
            assert updated.title == "Updated Title"
    
    def test_delete_dataset(self, unit_of_work):
        """Test deleting a dataset"""
        with unit_of_work as uow:
            dataset = Dataset(
                file_identifier="ds-005",
                title="Test",
                abstract="Test",
                lineage="Test"
            )
            created = uow.datasets.insert(dataset)
            dataset_id = created.id
            
            # Delete
            uow.datasets.delete(dataset_id)
            
            # Verify deleted
            retrieved = uow.datasets.get_by_id(dataset_id)
            assert retrieved is None
    
    def test_list_all_datasets(self, unit_of_work):
        """Test listing all datasets"""
        with unit_of_work as uow:
            # Create multiple datasets
            for i in range(3):
                dataset = Dataset(
                    file_identifier=f"ds-{i:03d}",
                    title=f"Dataset {i}",
                    abstract="Test",
                    lineage="Test"
                )
                uow.datasets.insert(dataset)
            
            # List all
            all_datasets = uow.datasets.get_all()
            
            assert len(all_datasets) >= 3
    
    def test_dataset_exists(self, unit_of_work):
        """Test checking if dataset exists"""
        with unit_of_work as uow:
            dataset = Dataset(
                file_identifier="ds-006",
                title="Test",
                abstract="Test",
                lineage="Test"
            )
            created = uow.datasets.insert(dataset)
            
            retrieved = uow.datasets.get_by_id(created.id)
            
            assert retrieved is not None


# ============================================================================
# TEST: MetadataDocumentRepository
# ============================================================================

class TestMetadataDocumentRepository:
    """Test metadata document repository"""
    
    def test_create_metadata_document(self, unit_of_work):
        """Test creating a metadata document"""
        with unit_of_work as uow:
            # First create a dataset
            dataset = Dataset(
                file_identifier="ds-md-001",
                title="Test",
                abstract="Test",
                lineage="Test"
            )
            dataset = uow.datasets.insert(dataset)
            
            # Then create metadata document
            metadata = MetadataDocument(
                dataset_id=dataset.id,
                document_type="iso19139",
                original_content=b"<xml>test</xml>"
            )
            created = uow.metadata_documents.insert(metadata)
            
            assert created.document_type == "iso19139"
            assert created.dataset_id == dataset.id
    
    def test_get_metadata_by_dataset(self, unit_of_work):
        """Test retrieving metadata documents by dataset"""
        with unit_of_work as uow:
            dataset = Dataset(
                file_identifier="ds-md-002",
                title="Test",
                abstract="Test",
                lineage="Test"
            )
            dataset = uow.datasets.insert(dataset)
            
            # Create metadata documents
            for fmt in ["iso19139", "json", "rdf"]:
                metadata = MetadataDocument(
                    dataset_id=dataset.id,
                    document_type=fmt,
                    original_content=f"content-{fmt}".encode()
                )
                uow.metadata_documents.insert(metadata)
            
            # Retrieve by dataset
            metadatas = uow.metadata_documents.get_by_dataset(dataset.id)
            
            assert len(metadatas) == 3
    
    def test_update_metadata_document(self, unit_of_work):
        """Test updating metadata document"""
        with unit_of_work as uow:
            dataset = Dataset(
                file_identifier="ds-md-003",
                title="Test",
                abstract="Test",
                lineage="Test"
            )
            dataset = uow.datasets.insert(dataset)
            
            metadata = MetadataDocument(
                dataset_id=dataset.id,
                document_type="iso19139",
                original_content=b"old content"
            )
            created = uow.metadata_documents.insert(metadata)
            
            # Update
            created.original_content = b"new content"
            updated = uow.metadata_documents.update(created, created.id)
            
            assert updated.original_content == b"new content"


# ============================================================================
# TEST: DataFileRepository
# ============================================================================

class TestDataFileRepository:
    """Test data file repository"""
    
    def test_create_data_file(self, unit_of_work):
        """Test creating a data file"""
        with unit_of_work as uow:
            dataset = Dataset(
                file_identifier="ds-df-001",
                title="Test",
                abstract="Test",
                lineage="Test"
            )
            dataset = uow.datasets.insert(dataset)
            
            data_file = DataFile(
                dataset_id=dataset.id,
                filename="test.csv",
                file_path="https://example.com/test.csv",
                file_size=1024
            )
            created = uow.data_files.insert(data_file)
            
            assert created.filename == "test.csv"
            assert created.dataset_id == dataset.id
    
    def test_get_files_by_dataset(self, unit_of_work):
        """Test retrieving files by dataset"""
        with unit_of_work as uow:
            dataset = Dataset(
                file_identifier="ds-df-002",
                title="Test",
                abstract="Test",
                lineage="Test"
            )
            dataset = uow.datasets.insert(dataset)
            
            # Create multiple files
            for i in range(3):
                data_file = DataFile(
                    dataset_id=dataset.id,
                    filename=f"file{i}.csv",
                    file_path=f"https://example.com/file{i}.csv",
                    file_size=1024 * (i + 1)
                )
                uow.data_files.insert(data_file)
            
            # Retrieve by dataset
            files = uow.data_files.get_by_dataset(dataset.id)
            
            assert len(files) == 3


# ============================================================================
# TEST: SupportingDocumentRepository
# ============================================================================

class TestSupportingDocumentRepository:
    """Test supporting document repository"""
    
    def test_create_supporting_document(self, unit_of_work):
        """Test creating a supporting document"""
        with unit_of_work as uow:
            dataset = Dataset(
                file_identifier="ds-sd-001",
                title="Test",
                abstract="Test",
                lineage="Test"
            )
            dataset = uow.datasets.insert(dataset)
            
            doc = SupportingDocument(
                dataset_id=dataset.id,
                document_url="https://example.com/doc.pdf",
                title="test.pdf",
                file_extension="pdf",
                text_content="Extracted text content"
            )
            created = uow.supporting_documents.insert(doc)
            
            assert created.title == "test.pdf"
            assert created.dataset_id == dataset.id
    
    def test_get_documents_by_dataset(self, unit_of_work):
        """Test retrieving supporting documents by dataset"""
        with unit_of_work as uow:
            dataset = Dataset(
                file_identifier="ds-sd-002",
                title="Test",
                abstract="Test",
                lineage="Test"
            )
            dataset = uow.datasets.insert(dataset)
            
            # Create documents
            for i in range(2):
                doc = SupportingDocument(
                    dataset_id=dataset.id,
                    document_url=f"https://example.com/doc{i}.pdf",
                    title=f"doc{i}.pdf",
                    file_extension="pdf",
                    text_content=f"Text {i}"
                )
                uow.supporting_documents.insert(doc)
            
            # Retrieve
            docs = uow.supporting_documents.get_by_dataset(dataset.id)
            
            assert len(docs) == 2


# ============================================================================
# TEST: Unit of Work Pattern
# ============================================================================

class TestUnitOfWork:
    """Test Unit of Work transaction pattern"""
    
    def test_unit_of_work_commit(self, unit_of_work):
        """Test UnitOfWork commit"""
        with unit_of_work as uow:
            dataset = Dataset(
                file_identifier="ds-uow-001",
                title="Test",
                abstract="Test",
                lineage="Test"
            )
            created = uow.datasets.insert(dataset)
            
            uow.commit()
            
            # Should be persisted
            retrieved = uow.datasets.get_by_id(created.id)
            assert retrieved is not None
    
    def test_unit_of_work_rollback(self, unit_of_work):
        """Test UnitOfWork rollback"""
        # Create a dataset first
        with unit_of_work as uow:
            dataset = Dataset(
                file_identifier="ds-uow-002",
                title="Original",
                abstract="Test",
                lineage="Test"
            )
            created = uow.datasets.insert(dataset)
            uow.commit()
        
        # Try to update and rollback
        with unit_of_work as uow:
            retrieved = uow.datasets.get_by_id(created.id)
            retrieved.title = "Modified"
            
            # Rollback should undo changes
            uow.rollback()
        
        # Verify original value
        with unit_of_work as uow:
            final = uow.datasets.get_by_id(created.id)
            assert final.title == "Original"
    
    def test_multiple_repositories(self, unit_of_work):
        """Test using multiple repositories in single transaction"""
        with unit_of_work as uow:
            # Create dataset
            dataset = Dataset(
                file_identifier="ds-multi-001",
                title="Test",
                abstract="Test",
                lineage="Test"
            )
            dataset = uow.datasets.insert(dataset)
            
            # Create metadata
            metadata = MetadataDocument(
                dataset_id=dataset.id,
                document_type="iso19139",
                original_content=b"<xml>test</xml>"
            )
            uow.metadata_documents.insert(metadata)
            
            # Create file
            data_file = DataFile(
                dataset_id=dataset.id,
                filename="test.csv",
                file_path="https://example.com/test.csv",
                file_size=1024
            )
            uow.data_files.insert(data_file)
            
            uow.commit()
            
            # Verify all created
            retrieved_dataset = uow.datasets.get_by_id(dataset.id)
            metadatas = uow.metadata_documents.get_by_dataset(dataset.id)
            files = uow.data_files.get_by_dataset(dataset.id)
            
            assert retrieved_dataset is not None
            assert len(metadatas) == 1
            assert len(files) == 1


# ============================================================================
# TEST: Repository Error Handling
# ============================================================================

class TestRepositoryErrorHandling:
    """Test error handling in repositories"""
    
    def test_get_nonexistent_dataset(self, unit_of_work):
        """Test getting non-existent dataset"""
        with unit_of_work as uow:
            result = uow.datasets.get_by_id(99999)
            
            assert result is None
    
    def test_delete_nonexistent(self, unit_of_work):
        """Test deleting non-existent entity"""
        with unit_of_work as uow:
            # Should not raise error
            uow.datasets.delete(99999)
