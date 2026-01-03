"""
Document Extraction Module - Text Extraction from Various Formats

This module provides utilities for extracting text content from various document formats.

Supported Formats:
    - PDF: Portable Document Format (.pdf)
    - DOCX: Microsoft Word 2007+ (.docx)
    - TXT: Plain text files (.txt)
    - RTF: Rich Text Format (.rtf)

Classes:
    - DocumentExtractor: Abstract base class for all extractors
    - PDFExtractor: Extracts text from PDF files
    - DOCXExtractor: Extracts text from DOCX files
    - TXTExtractor: Reads plain text files
    - UniversalDocumentExtractor: Factory that routes to appropriate extractor
    - DocumentExtractorError: Exception for extraction errors

Usage:
    from src.services.document_extraction import UniversalDocumentExtractor
    
    # Create factory instance
    extractor = UniversalDocumentExtractor()
    
    # Extract text (automatically detects format)
    text = await extractor.extract(Path("document.pdf"))
    
    # Or use specific extractor
    from src.services.document_extraction import PDFExtractor
    pdf_extractor = PDFExtractor()
    pdf_text = await pdf_extractor.extract(Path("report.pdf"))

Factory Pattern:
    - UniversalDocumentExtractor routes to specific extractors by file extension
    - Supports parallel extraction for multiple files
    - Graceful fallback if format not supported

Error Handling:
    - DocumentExtractorError for all extraction failures
    - Handles missing files, corrupted documents, encoding issues
"""

from .document_extractor import DocumentExtractor, DocumentExtractorError
from .pdf_extractor import PDFExtractor
from .docx_extractor import DOCXExtractor
from .txt_extractor import TXTExtractor
from .document_extractor_impl import UniversalDocumentExtractor

__all__ = [
    # Base classes
    "DocumentExtractor",
    "DocumentExtractorError",
    # Concrete extractors
    "PDFExtractor",
    "DOCXExtractor",
    "TXTExtractor",
    # Factory
    "UniversalDocumentExtractor",
]
