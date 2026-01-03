"""
DSH ETL Search AI - Main Package

This package provides a complete ETL (Extract-Transform-Load) pipeline for managing
and searching geospatial datasets through multiple data format parsers, document
extractors, and a vector search interface.

Core Modules:
    - services: ETL orchestration, parsers, extractors, and supporting document management
    - models: Data schemas and database models
    - repositories: Data access layer with unit of work pattern
    - infrastructure: HTTP client, database connections, logging
    - api: REST API routes and endpoints
    - config: Configuration management

Quick Start:
    from src.services import ETLService, ETLErrorHandler
    from src.models import Dataset, SearchRequest
    from src.infrastructure import Database
    
    # Initialize database
    db = Database("sqlite:///data/search.db")
    
    # Run ETL pipeline
    etl_service = ETLService(
        identifiers_file=Path("identifiers.txt"),
        unit_of_work=unit_of_work,
        batch_size=10
    )
    await etl_service.run_pipeline(verbose=True)
    
    # Search datasets
    request = SearchRequest(query="climate data")
    results = await search_service.search(request)

Key Features:
    - 3-phase ETL pipeline: EXTRACT → TRANSFORM → LOAD
    - Multi-format metadata parsing: ISO 19139, JSON, RDF, Schema.org
    - Document extraction: PDF, DOCX, TXT
    - Supporting document discovery and download
    - Adaptive batch processing with performance metrics
    - Comprehensive error handling with recovery strategies
    - Vector search with Chroma embeddings
    - Async/await for all I/O operations
    - Full audit trail and request tracking

Version: 0.1.0
"""

__version__ = "0.1.0"
__author__ = "RSE Manchester"

# Export main services for quick access
from .services import (
    # ETL Pipeline
    ETLService,
    ETLErrorHandler,
    RetryConfig,
    RetryStrategy,
    RecoverableError,
    NonRecoverableError,
    NetworkError,
    ParsingError,
    DatabaseError,
    ValidationError,
    AdaptiveBatchProcessor,
    ConcurrencyOptimizer,
    CachingBatchProcessor,
    PerformanceMetrics,
    # Parsers
    MetadataParser,
    MetadataParserError,
    ISO19139Parser,
    JSONMetadataParser,
    RDFParser,
    SchemaOrgParser,
    # Extractors
    CEHExtractor,
    CEHExtractorError,
    WebFolderTraverser,
    WebFolderTraverserError,
    ZipExtractor,
    ZipExtractorError,
    # Document Extraction
    DocumentExtractor,
    DocumentExtractorError,
    PDFExtractor,
    DOCXExtractor,
    TXTExtractor,
    UniversalDocumentExtractor,
    # Supporting Documents
    SupportingDocDiscoverer,
    SupportingDocURLs,
    SupportingDocDiscoveryError,
    SupportingDocDownloader,
    SupportingDocDownloaderError,
)

# Export main models
from .models import (
    Dataset,
    SearchRequest,
    SearchResult,
    ChatRequest,
    ChatMessage,
)

# Export database infrastructure
from .infrastructure import (
    Database,
    AsyncHTTPClient,
)

__all__ = [
    # Package info
    "__version__",
    "__author__",
    # ETL Services
    "ETLService",
    "ETLErrorHandler",
    "RetryConfig",
    "RetryStrategy",
    "RecoverableError",
    "NonRecoverableError",
    "NetworkError",
    "ParsingError",
    "DatabaseError",
    "ValidationError",
    "AdaptiveBatchProcessor",
    "ConcurrencyOptimizer",
    "CachingBatchProcessor",
    "PerformanceMetrics",
    # Parsers
    "MetadataParser",
    "MetadataParserError",
    "ISO19139Parser",
    "JSONMetadataParser",
    "RDFParser",
    "SchemaOrgParser",
    # Extractors
    "CEHExtractor",
    "CEHExtractorError",
    "WebFolderTraverser",
    "WebFolderTraverserError",
    "ZipExtractor",
    "ZipExtractorError",
    # Document Extraction
    "DocumentExtractor",
    "DocumentExtractorError",
    "PDFExtractor",
    "DOCXExtractor",
    "TXTExtractor",
    "UniversalDocumentExtractor",
    # Supporting Documents
    "SupportingDocDiscoverer",
    "SupportingDocURLs",
    "SupportingDocDiscoveryError",
    "SupportingDocDownloader",
    "SupportingDocDownloaderError",
    # Models
    "Dataset",
    "SearchRequest",
    "SearchResult",
    "ChatRequest",
    "ChatMessage",
    # Infrastructure
    "Database",
    "AsyncHTTPClient",
]
