"""Services module - extraction, parsing, and document processing.

Organized into logical submodules:
- etl: Pipeline orchestration and error handling
- parsers: Metadata format parsers (ISO19139, JSON, RDF, Schema.org)
- extractors: Data extraction (CEH API, web folders, ZIP files)
- document_extraction: Text extraction (PDF, DOCX, TXT)
- supporting_documents: URL discovery and file downloading
- architecture: System design documentation
"""

# ETL Module (Orchestration)
from .etl import (
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
)

# Parsers Module
from .parsers import (
    MetadataParser,
    MetadataParserError,
    ISO19139Parser,
    JSONMetadataParser,
    RDFParser,
    SchemaOrgParser,
)

# Extractors Module
from .extractors import (
    CEHExtractor,
    CEHExtractorError,
    WebFolderTraverser,
    WebFolderTraverserError,
    ZipExtractor,
    ZipExtractorError,
)

# Document Extraction Module
from .document_extraction import (
    DocumentExtractor,
    DocumentExtractorError,
    PDFExtractor,
    DOCXExtractor,
    TXTExtractor,
    UniversalDocumentExtractor,
)

# Supporting Documents Module
from .supporting_documents import (
    SupportingDocDiscoverer,
    SupportingDocURLs,
    SupportingDocDiscoveryError,
    SupportingDocDownloader,
    SupportingDocDownloaderError,
)

__all__ = [
    # ETL Module
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
    # Parsers Module
    "MetadataParser",
    "MetadataParserError",
    "ISO19139Parser",
    "JSONMetadataParser",
    "RDFParser",
    "SchemaOrgParser",
    # Extractors Module
    "CEHExtractor",
    "CEHExtractorError",
    "WebFolderTraverser",
    "WebFolderTraverserError",
    "ZipExtractor",
    "ZipExtractorError",
    # Document Extraction Module
    "DocumentExtractor",
    "DocumentExtractorError",
    "PDFExtractor",
    "DOCXExtractor",
    "TXTExtractor",
    "UniversalDocumentExtractor",
    # Supporting Documents Module
    "SupportingDocDiscoverer",
    "SupportingDocURLs",
    "SupportingDocDiscoveryError",
    "SupportingDocDownloader",
    "SupportingDocDownloaderError",
]