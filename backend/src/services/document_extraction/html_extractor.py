"""
HTML document text extractor.

Extracts meaningful text from HTML documents while removing scripts, styles,
and other non-content elements.
"""

from pathlib import Path
from typing import Optional

from .document_extractor import DocumentExtractor, DocumentExtractorError
from src.logging_config import get_logger

logger = get_logger(__name__)


class HTMLExtractor(DocumentExtractor):
    """Extract text from HTML files."""
    
    SUPPORTED_MIMES = ["text/html", "application/xhtml+xml"]
    
    async def extract(self, file_path: str | Path) -> str:
        """
        Extract text content from HTML file.
        
        Args:
            file_path: Path to HTML file
            
        Returns:
            Extracted text content with whitespace normalized
            
        Raises:
            DocumentExtractorError: If extraction fails
        """
        path = self._validate_file(file_path)
        
        try:
            # Try with BeautifulSoup if available (preferred)
            try:
                return await self._extract_with_beautifulsoup(path)
            except ImportError:
                logger.warning("BeautifulSoup not available, using fallback HTML parser")
                return await self._extract_with_html_parser(path)
        
        except Exception as e:
            raise DocumentExtractorError(f"Failed to extract text from HTML: {e}")
    
    async def _extract_with_beautifulsoup(self, path: Path) -> str:
        """Extract using BeautifulSoup (removes markup properly)."""
        from bs4 import BeautifulSoup
        
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()
        
        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, str) and '<!--' in str(text)):
            comment.extract()
        
        # Get text
        text = soup.get_text(separator='\n', strip=True)
        
        # Normalize whitespace
        lines = (line.strip() for line in text.split('\n'))
        lines = (line for line in lines if line)
        text = '\n'.join(lines)
        
        return self._sanitize_text(text)
    
    async def _extract_with_html_parser(self, path: Path) -> str:
        """Fallback extraction using built-in html.parser."""
        from html.parser import HTMLParser
        
        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text_parts = []
                self.skip_content = False
                self.skip_tags = {'script', 'style', 'meta', 'link', 'noscript'}
            
            def handle_starttag(self, tag, attrs):
                if tag in self.skip_tags:
                    self.skip_content = True
            
            def handle_endtag(self, tag):
                if tag in self.skip_tags:
                    self.skip_content = False
            
            def handle_data(self, data):
                if not self.skip_content:
                    # Clean up whitespace but preserve some structure
                    text = data.strip()
                    if text:
                        self.text_parts.append(text)
        
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()
        
        extractor = TextExtractor()
        try:
            extractor.feed(html_content)
        except Exception as e:
            logger.warning(f"HTML parsing error (continuing): {e}")
        
        # Join with newlines
        text = '\n'.join(extractor.text_parts)
        return self._sanitize_text(text)
