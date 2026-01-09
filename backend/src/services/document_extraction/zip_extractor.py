"""
ZIP document extractor for supporting documents.

Extracts text content from ZIP archives by:
1. Extracting all documents from ZIP in-memory
2. Extracting text from each document
3. Combining text content into single result
"""

import zipfile
from io import BytesIO
from pathlib import Path

import html2text

from .document_extractor import DocumentExtractor, DocumentExtractorError
from .pdf_extractor import PDFExtractor
from src.logging_config import get_logger

logger = get_logger(__name__)


class ZIPDocumentExtractor(DocumentExtractor):
    """Extract text from ZIP archive files containing documents."""
    
    SUPPORTED_MIMES = ["application/zip", "application/x-zip-compressed"]
    
    def __init__(self):
        """Initialize with format-specific extractors."""
        self.pdf_extractor = PDFExtractor()
    
    async def extract(self, file_path: str | Path) -> str:
        """
        Extract text from all documents in ZIP archive.
        
        Args:
            file_path: Path to ZIP file
            
        Returns:
            Combined text from all documents in ZIP
            
        Raises:
            DocumentExtractorError: If extraction fails
        """
        path = self._validate_file(file_path)
        
        try:
            all_text = []
            
            with zipfile.ZipFile(path, 'r') as zip_file:
                # Check ZIP integrity
                bad_file = zip_file.testzip()
                if bad_file:
                    logger.warning(f"ZIP file has corrupted file: {bad_file}")
                    # Continue anyway, extract what we can
                
                # Extract and process each file in ZIP
                for file_info in zip_file.filelist:
                    # Skip directories
                    if file_info.is_dir():
                        continue
                    
                    file_path_in_zip = file_info.filename
                    
                    # Skip non-document files
                    if not self._should_process(file_path_in_zip):
                        continue
                    
                    try:
                        # Read file from ZIP
                        content = zip_file.read(file_path_in_zip)
                        
                        # Extract text based on file type
                        text = await self._extract_from_content(
                            content=content,
                            filename=file_path_in_zip
                        )
                        
                        if text:
                            all_text.append(f"--- {file_path_in_zip} ---\n{text}")
                            logger.debug(f"Extracted text from {file_path_in_zip}")
                    
                    except Exception as e:
                        logger.warning(f"Failed to extract {file_path_in_zip} from ZIP: {e}")
                        # Continue with next file
                        continue
            
            if not all_text:
                logger.warning(f"No text extracted from ZIP: {path}")
                return ""
            
            # Combine all extracted text
            combined_text = "\n\n".join(all_text)
            return self._sanitize_text(combined_text)
        
        except zipfile.BadZipFile as e:
            raise DocumentExtractorError(f"Invalid ZIP file: {e}")
        except Exception as e:
            raise DocumentExtractorError(f"Failed to extract text from ZIP: {e}")
    
    async def _extract_from_content(self, content: bytes, filename: str) -> str:
        """
        Extract text from file content based on file type.
        
        Args:
            content: File content as bytes
            filename: Filename to determine type
            
        Returns:
            Extracted text, or empty string if unsupported
        """
        suffix = Path(filename).suffix.lower()
        
        try:
            if suffix == '.pdf':
                # Extract PDF from memory
                import PyPDF2
                pdf_io = BytesIO(content)
                reader = PyPDF2.PdfReader(pdf_io)
                
                pages = []
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    pages.append(page.extract_text())
                
                return "\n".join(pages) if pages else ""
            
            elif suffix in ['.html', '.htm']:
                # HTML files - convert to markdown
                try:
                    html_content = content.decode('utf-8')
                except UnicodeDecodeError:
                    html_content = content.decode('latin-1')
                
                h = html2text.HTML2Text()
                h.ignore_links = False
                h.ignore_images = False
                h.body_width = 0  # Don't wrap text
                
                try:
                    text = h.handle(html_content)
                    return text.strip() if text else ""
                except Exception as e:
                    logger.warning(f"Failed to parse HTML content from {filename}: {e}")
                    # Fallback to plain text extraction
                    return html_content
            
            elif suffix in ['.txt', '.md', '.log']:
                # Plain text files
                try:
                    return content.decode('utf-8')
                except UnicodeDecodeError:
                    return content.decode('latin-1')
            
            elif suffix in ['.json', '.xml', '.csv']:
                # Structured text files
                try:
                    return content.decode('utf-8')
                except UnicodeDecodeError:
                    return content.decode('latin-1')
            
            else:
                logger.debug(f"Unsupported file type in ZIP: {suffix}")
                return ""
        
        except Exception as e:
            logger.warning(f"Failed to extract {filename}: {e}")
            return ""
    
    @staticmethod
    def _should_process(filename: str) -> bool:
        """
        Check if file should be processed.
        
        Args:
            filename: Filename from ZIP
            
        Returns:
            True if file should be processed
        """
        # Skip common non-document files
        skip_patterns = [
            '__pycache__', '.pyc', '.pyo', '.so',
            '.gitignore', '.gitkeep', '.DS_Store',
            'Thumbs.db', '.project',
            '.egg-info',
        ]
        
        for pattern in skip_patterns:
            if pattern in filename.lower():
                return False
        
        # Only process known document types
        allowed_extensions = [
            '.pdf', '.txt', '.md', '.json', '.xml', '.csv',
            '.log', '.yaml', '.yml', '.html', '.htm'
        ]
        
        suffix = Path(filename).suffix.lower()
        return suffix in allowed_extensions
