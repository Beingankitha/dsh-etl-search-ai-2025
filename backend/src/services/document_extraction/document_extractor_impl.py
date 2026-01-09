"""
Concrete document text extractor implementations for different formats.

Supports: PDF, DOCX, TXT, HTML, ZIP
"""

from pathlib import Path
from typing import Optional

from .document_extractor import DocumentExtractor, DocumentExtractorError
from .html_extractor import HTMLExtractor
from .zip_extractor import ZIPDocumentExtractor
from src.logging_config import get_logger

logger = get_logger(__name__)


class PlainTextExtractor(DocumentExtractor):
    """Extract text from plain text files."""
    
    SUPPORTED_MIMES = ["text/plain"]
    
    async def extract(self, file_path: str | Path) -> str:
        """Extract text from plain text file."""
        path = self._validate_file(file_path)
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            return self._sanitize_text(text)
        
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(path, 'r', encoding='latin-1') as f:
                    text = f.read()
                return self._sanitize_text(text)
            except Exception as e:
                raise DocumentExtractorError(f"Failed to read text file: {e}")
        
        except Exception as e:
            raise DocumentExtractorError(f"Failed to extract text: {e}")


class PDFExtractor(DocumentExtractor):
    """Extract text from PDF files."""
    
    SUPPORTED_MIMES = ["application/pdf"]
    
    async def extract(self, file_path: str | Path) -> str:
        """Extract text from PDF file."""
        path = self._validate_file(file_path)
        
        try:
            import PyPDF2
            
            text = []
            with open(path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    text.append(page.extract_text())
            
            full_text = "\n".join(text)
            return self._sanitize_text(full_text)
        
        except ImportError:
            raise DocumentExtractorError("PyPDF2 not installed. Install with: pip install PyPDF2")
        except Exception as e:
            raise DocumentExtractorError(f"Failed to extract text from PDF: {e}")


class DOCXExtractor(DocumentExtractor):
    """Extract text from DOCX files."""
    
    SUPPORTED_MIMES = ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    
    async def extract(self, file_path: str | Path) -> str:
        """Extract text from DOCX file."""
        path = self._validate_file(file_path)
        
        try:
            from docx import Document
            
            doc = Document(path)
            paragraphs = [para.text for para in doc.paragraphs]
            full_text = "\n".join(paragraphs)
            
            return self._sanitize_text(full_text)
        
        except ImportError:
            raise DocumentExtractorError("python-docx not installed. Install with: pip install python-docx")
        except Exception as e:
            raise DocumentExtractorError(f"Failed to extract text from DOCX: {e}")


class UniversalDocumentExtractor(DocumentExtractor):
    """
    Universal document extractor that auto-detects format and uses appropriate extractor.
    
    Falls back to TextExtractor if format not recognized.
    """
    
    SUPPORTED_MIMES = ["text/plain", "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/html", "application/xhtml+xml", "application/zip"]
    
    def __init__(self):
        """Initialize with format-specific extractors."""
        self.extractors = {
            '.txt': PlainTextExtractor(),
            '.pdf': PDFExtractor(),
            '.docx': DOCXExtractor(),
            '.html': HTMLExtractor(),
            '.htm': HTMLExtractor(),
            '.xhtml': HTMLExtractor(),
            '.zip': ZIPDocumentExtractor(),
            '.ZIP': ZIPDocumentExtractor(),
        }
    
    async def extract(self, file_path: str | Path) -> str:
        """Extract text from any supported document format."""
        path = self._validate_file(file_path)
        
        # Detect format from extension
        suffix = path.suffix.lower()
        
        if suffix in self.extractors:
            extractor = self.extractors[suffix]
            try:
                return await extractor.extract(path)
            except Exception as e:
                logger.warning(f"Failed to extract with {suffix} extractor, falling back to text: {e}")
        
        # Fallback: try to read as plain text
        logger.debug(f"No specific extractor for {suffix}, attempting plain text extraction")
        text_extractor = PlainTextExtractor()
        return await text_extractor.extract(path)