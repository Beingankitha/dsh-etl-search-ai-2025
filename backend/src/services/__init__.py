"""Services module - extraction, parsing, and document processing."""

from .ceh_extractor import CEHExtractor, CEHExtractorError
from .document_extractor import DocumentExtractor, DocumentExtractorError
from .docx_extractor import DOCXExtractor
from .iso19139_parser import ISO19139Parser
from .json_parser import JSONMetadataParser
from .metadata_parser import MetadataParser, MetadataParserError
from .pdf_extractor import PDFExtractor
from .rdf_parser import RDFParser
from .schema_org_parser import SchemaOrgParser
from .supporting_doc_discoverer import (
    SupportingDocDiscoverer,
    SupportingDocDiscoveryError,
    SupportingDocURLs,
)
from .supporting_doc_downloader import SupportingDocDownloader, SupportingDocDownloaderError
from .txt_extractor import TXTExtractor
from .web_folder_traverser import WebFolderTraverser, WebFolderTraverserError
from .zip_extractor import ZipExtractor, ZipExtractorError

__all__ = [
    # Extractors
    "CEHExtractor",
    "CEHExtractorError",
    # Document text extraction
    "DocumentExtractor",
    "DocumentExtractorError",
    "PDFExtractor",
    "DOCXExtractor",
    "TXTExtractor",
    # Metadata parsers
    "MetadataParser",
    "MetadataParserError",
    "ISO19139Parser",
    "JSONMetadataParser",
    "SchemaOrgParser",
    "RDFParser",
    # Supporting documents
    "SupportingDocDiscoverer",
    "SupportingDocDiscoveryError",
    "SupportingDocURLs",
    "SupportingDocDownloader",
    "SupportingDocDownloaderError",
    # Utilities
    "ZipExtractor",
    "ZipExtractorError",
    "WebFolderTraverser",
    "WebFolderTraverserError",
]