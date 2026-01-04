"""
Indexing Service - Vector Indexing Pipeline

This module orchestrates the process of embedding all data and loading it
into the vector store. Handles both dataset metadata and supporting documents.

Architecture:
    - IndexingService: Orchestrates the indexing pipeline
    - IndexingProgress: Tracks progress and statistics
    - Batch processing for efficiency
    - Error recovery
    - Comprehensive logging and tracing

Features:
    - Full dataset indexing from database
    - Supporting document chunk indexing
    - Incremental updates (index single dataset)
    - Progress tracking with statistics
    - Error collection without stopping
    - Performance metrics
    - Observability with distributed tracing

Design Pattern:
    - Service Locator: Gets dependencies (database, embedding service, vector store)
    - Orchestrator: Coordinates multiple services
    - Batch Processor: Handles data in batches

Usage Example:
    from src.services.embeddings import IndexingService
    
    service = IndexingService()
    progress = service.index_all_datasets(supporting_docs=True)
    
    print(f"Indexed: {progress.total_indexed}/{progress.total_datasets}")
    if progress.errors:
        print(f"Errors: {len(progress.errors)}")
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime, timezone

from src.config import settings
from src.infrastructure import Database
from src.repositories import UnitOfWork
from src.services.embeddings import EmbeddingService, TextChunker, VectorStore
from src.services.document_extraction import UniversalDocumentExtractor
from src.logging_config import get_logger

logger = get_logger(__name__)

# Tracing is optional
try:
    from src.services.observability import get_tracer, with_span
    tracer = get_tracer(__name__)
except Exception:
    tracer = None
    def with_span(name):
        """No-op decorator."""
        def decorator(func):
            return func
        return decorator


@dataclass
class IndexingProgress:
    """
    Track indexing progress and statistics.
    
    Useful for reporting and monitoring long-running operations.
    """
    total_datasets: int = 0
    total_indexed: int = 0
    total_failed: int = 0
    total_docs: int = 0
    total_docs_indexed: int = 0
    total_docs_failed: int = 0
    errors: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Get duration in seconds if completed."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.total_indexed == 0:
            return 0.0
        return (self.total_indexed / self.total_datasets) * 100


class IndexingService:
    """
    Orchestrate embedding and vector indexing of all data.
    
    This service manages the process of:
    1. Reading datasets from database
    2. Generating embeddings for metadata
    3. Storing in vector database
    4. Processing supporting documents for RAG
    5. Tracking progress and errors
    """
    
    def __init__(
        self,
        database: Optional[Database] = None,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store: Optional[VectorStore] = None,
        extract_supporting_docs: bool = True
    ):
        """
        Initialize indexing service with dependencies.
        
        Args:
            database: Database instance. If None, creates new.
            embedding_service: EmbeddingService instance.
            vector_store: VectorStore instance.
            extract_supporting_docs: Whether to index supporting docs
        """
        # Initialize database if not provided
        self.database = database
        if not self.database:
            self.database = Database()
            if not self.database.connection:
                self.database.connect()
        
        # Initialize services if not provided
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store or VectorStore()
        self.extract_supporting_docs = extract_supporting_docs
        
        # Initialize utilities
        self.text_chunker = TextChunker()
        self.doc_extractor = UniversalDocumentExtractor() if extract_supporting_docs else None
        
        logger.info("IndexingService initialized")
    
    @with_span("index_all_datasets")
    def index_all_datasets(self, supporting_docs: bool = True) -> IndexingProgress:
        """
        Index all datasets from database into vector store.
        
        Pipeline:
        1. Load all datasets from SQLite
        2. Prepare text for embedding (title + abstract + keywords)
        3. Generate embeddings in batches
        4. Store in ChromaDB with metadata
        5. Optionally process supporting documents
        
        Args:
            supporting_docs: Whether to also index supporting documents
            
        Returns:
            IndexingProgress with statistics
        """
        progress = IndexingProgress()
        progress.started_at = datetime.now(timezone.utc)
        
        try:
            logger.info("Starting dataset indexing pipeline...")
            
            with UnitOfWork(self.database) as uow:
                # ===== Phase 1: Load Datasets =====
                datasets = uow.datasets.get_all()
                progress.total_datasets = len(datasets)
                
                logger.info(f"Found {progress.total_datasets} datasets to index")
                
                if progress.total_datasets == 0:
                    logger.warning("No datasets found to index")
                    progress.completed_at = datetime.now(timezone.utc)
                    return progress
                
                # ===== Phase 2: Prepare Embeddings =====
                logger.info("Preparing embeddings for datasets...")
                
                dataset_texts = []
                dataset_ids = []
                valid_datasets = []
                
                for dataset in datasets:
                    try:
                        # Combine title, abstract, keywords for semantic meaning
                        text_parts = [
                            dataset.title or "",
                            dataset.abstract or "",
                            " ".join(dataset.keywords) if dataset.keywords else ""
                        ]
                        combined_text = " ".join([t for t in text_parts if t])
                        
                        if combined_text.strip():
                            dataset_texts.append(combined_text)
                            dataset_ids.append(dataset.file_identifier)
                            valid_datasets.append(dataset)
                        else:
                            logger.warning(
                                f"Dataset {dataset.file_identifier} has no text content"
                            )
                            progress.errors.append(
                                f"Dataset {dataset.file_identifier}: No text content"
                            )
                    except Exception as e:
                        logger.warning(f"Error preparing text for {dataset.file_identifier}: {e}")
                        progress.errors.append(str(e))
                
                # ===== Phase 3: Generate Embeddings =====
                logger.info(f"Generating embeddings for {len(dataset_texts)} datasets...")
                
                embeddings = self.embedding_service.embed_texts(dataset_texts)
                
                # ===== Phase 4: Store in Vector Store =====
                logger.info(f"Storing {len(embeddings)} embeddings in vector store...")
                
                store_data = []
                for i, dataset in enumerate(valid_datasets):
                    metadata = {
                        "file_identifier": dataset.file_identifier,
                        "title": dataset.title or "",
                        "abstract": dataset.abstract or "",
                        "topic_category": str(dataset.topic_category) if dataset.topic_category else "",
                        "keywords": " ".join(dataset.keywords) if dataset.keywords else "",
                        "text_content": dataset_texts[i]
                    }
                    
                    store_data.append({
                        "file_identifier": dataset.file_identifier,
                        "embedding": embeddings[i],
                        "metadata": metadata
                    })
                
                # Batch add to vector store
                self.vector_store.add_datasets(store_data)
                progress.total_indexed = len(store_data)
                
                logger.info(
                    f"✓ Dataset indexing complete: {progress.total_indexed}/{progress.total_datasets}"
                )
            
            # ===== Phase 5: Index Supporting Documents (Optional) =====
            if self.extract_supporting_docs and supporting_docs:
                self._index_supporting_documents(progress)
            
            progress.completed_at = datetime.now(timezone.utc)
            return progress
            
        except Exception as e:
            logger.error(f"Critical error during dataset indexing: {e}")
            progress.errors.append(f"CRITICAL: {str(e)}")
            progress.completed_at = datetime.now(timezone.utc)
            raise
    
    @with_span("index_supporting_documents")
    def _index_supporting_documents(self, progress: IndexingProgress) -> None:
        """
        Index supporting documents from database.
        
        Process:
        1. Load supporting documents with extracted text
        2. Chunk text for RAG
        3. Generate embeddings for chunks
        4. Store in vector store with dataset linkage
        
        Args:
            progress: IndexingProgress to update
        """
        logger.info("Starting supporting documents indexing...")
        
        try:
            with UnitOfWork(self.database) as uow:
                # Load documents with extracted text
                docs = uow.supporting_documents.get_with_text_content()
                progress.total_docs = len(docs)
                
                if not docs:
                    logger.info("No supporting documents with text content found")
                    return
                
                logger.info(f"Found {progress.total_docs} documents with text content")
                
                # ===== Prepare Document Chunks =====
                doc_batch = []
                for doc in docs:
                    if not doc.text_content:
                        continue
                    
                    try:
                        # Chunk document text
                        chunks = self.text_chunker.chunk_text(doc.text_content)
                        
                        # Prepare metadata
                        metadata = {
                            "dataset_id": doc.dataset_id,
                            "document_url": doc.document_url,
                            "title": doc.title,
                            "file_extension": doc.file_extension or ""
                        }
                        
                        # Add each chunk to batch
                        for chunk_idx, chunk in enumerate(chunks):
                            doc_batch.append({
                                "doc_id": f"{doc.id}_chunk_{chunk_idx}",
                                "text": chunk,
                                "metadata": metadata
                            })
                        
                    except Exception as e:
                        logger.warning(f"Error processing document {doc.id}: {e}")
                        progress.errors.append(f"Doc {doc.id}: {e}")
                        progress.total_docs_failed += 1
                        continue
                
                if not doc_batch:
                    logger.warning("No document chunks to index")
                    return
                
                # ===== Generate Embeddings =====
                logger.info(f"Generating embeddings for {len(doc_batch)} document chunks...")
                chunk_texts = [d["text"] for d in doc_batch]
                embeddings = self.embedding_service.embed_texts(chunk_texts)
                
                # ===== Store in Vector Store =====
                for i, item in enumerate(doc_batch):
                    try:
                        self.vector_store.add_supporting_document(
                            doc_id=item["doc_id"],
                            embedding=embeddings[i],
                            metadata=item["metadata"],
                            text_chunk=item["text"]
                        )
                        progress.total_docs_indexed += 1
                    except Exception as e:
                        logger.warning(f"Error adding document chunk {item['doc_id']}: {e}")
                        progress.errors.append(str(e))
                
                logger.info(
                    f"✓ Supporting documents indexing complete: "
                    f"{progress.total_docs_indexed} chunks indexed"
                )
                
        except Exception as e:
            logger.error(f"Error during supporting documents indexing: {e}")
            progress.errors.append(str(e))
    
    @with_span("index_single_dataset")
    def index_single_dataset(self, file_identifier: str) -> bool:
        """
        Index single dataset (for incremental updates).
        
        Useful when a dataset is updated and needs re-indexing.
        
        Args:
            file_identifier: Dataset to index
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with UnitOfWork(self.database) as uow:
                dataset = uow.datasets.get_by_file_identifier(file_identifier)
                
                if not dataset:
                    logger.warning(f"Dataset not found: {file_identifier}")
                    return False
                
                # Prepare text
                text_parts = [
                    dataset.title or "",
                    dataset.abstract or "",
                    " ".join(dataset.keywords) if dataset.keywords else ""
                ]
                combined_text = " ".join([t for t in text_parts if t])
                
                # Generate embedding
                embedding = self.embedding_service.embed_text(combined_text)
                
                # Prepare metadata
                metadata = {
                    "file_identifier": dataset.file_identifier,
                    "title": dataset.title,
                    "abstract": dataset.abstract or "",
                    "text_content": combined_text
                }
                
                # Store in vector store (upserts if exists)
                self.vector_store.add_dataset(
                    file_identifier=file_identifier,
                    embedding=embedding,
                    metadata=metadata
                )
                
                logger.info(f"✓ Indexed dataset: {file_identifier}")
                return True
                
        except Exception as e:
            logger.error(f"Error indexing single dataset: {e}")
            return False


__all__ = [
    "IndexingService",
    "IndexingProgress",
]
