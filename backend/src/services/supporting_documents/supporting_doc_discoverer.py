"""
Supporting document URL discovery from metadata documents.

Extracts supporting document URLs from:
- ISO 19139 XML (gmd:onlineResource/gmd:linkage)
- JSON metadata (supportingDocuments array)
- Schema.org JSON-LD (url, distribution)
- RDF (dcat:distribution, foaf:page)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional, List
from urllib.parse import urljoin, urlparse

from lxml import etree
from rdflib import Graph, Namespace, RDF

from src.logging_config import get_logger

logger = get_logger(__name__)


class SupportingDocDiscoveryError(Exception):
    """Base exception for document discovery errors."""
    pass


class SupportingDocURLs:
    """Container for discovered supporting document URLs."""

    def __init__(self):
        self.supporting_docs: list[str] = []  # General supporting docs
        self.download_urls: list[str] = []  # ZIP files for download
        self.fileaccess_urls: list[str] = []  # Web folder access URLs
        self.metadata_urls: list[str] = []  # Links to metadata documents

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "supporting_docs": self.supporting_docs,
            "download_urls": self.download_urls,
            "fileaccess_urls": self.fileaccess_urls,
            "metadata_urls": self.metadata_urls,
        }


class SupportingDocDiscoverer:
    """
    Discovers supporting document URLs from various metadata formats.

    Strategy pattern: different discoverers for each format, unified interface.
    """

    ISO_NAMESPACES = {
        "gmd": "http://www.isotc211.org/2005/gmd",
        "gco": "http://www.isotc211.org/2005/gco",
    }

    DCAT = Namespace("http://www.w3.org/ns/dcat#")
    DCT = Namespace("http://purl.org/dc/terms/")
    FOAF = Namespace("http://xmlns.com/foaf/0.1/")

    def __init__(self):
        """Initialize discoverer."""
        self.urls = SupportingDocURLs()

    async def discover_from_iso_xml(self, xml_content: str) -> SupportingDocURLs:
        """
        Discover URLs from ISO 19139 XML.

        Args:
            xml_content: XML string

        Returns:
            SupportingDocURLs with discovered URLs
        """
        try:
            self.urls = SupportingDocURLs()
            root = etree.fromstring(xml_content.encode("utf-8"))

            # FIXED: Extract all linkage URLs - use gmd:URL not gco:URL
            # ISO 19139 XML structure: gmd:linkage/gmd:URL contains the URL text
            xpath = ".//gmd:linkage/gmd:URL/text()"
            urls = root.xpath(xpath, namespaces=self.ISO_NAMESPACES)

            for url in urls:
                self._classify_and_add_url(url)

            logger.info(f"Discovered {len(urls)} URLs from ISO XML")
            return self.urls

        except Exception as e:
            logger.error(f"Failed to discover URLs from ISO XML: {e}")
            raise SupportingDocDiscoveryError(f"ISO XML discovery failed: {e}") from e

    async def discover_from_json(self, json_content: str) -> SupportingDocURLs:
        """
        Discover URLs from JSON metadata.

        Args:
            json_content: JSON string

        Returns:
            SupportingDocURLs with discovered URLs
        """
        try:
            self.urls = SupportingDocURLs()
            data = json.loads(json_content)

            # Look for common patterns
            patterns = [
                ("supportingDocuments", list),
                ("resources", list),
                ("downloads", list),
                ("links", list),
                ("distribution", list),
            ]

            for key, expected_type in patterns:
                if key in data and isinstance(data[key], expected_type):
                    items = data[key]
                    for item in items:
                        if isinstance(item, dict):
                            # Try to extract URL
                            url = item.get("url") or item.get("href") or item.get("link")
                            if url:
                                self._classify_and_add_url(url)
                        elif isinstance(item, str):
                            self._classify_and_add_url(item)

            logger.info(f"Discovered {len(self.urls.supporting_docs)} URLs from JSON")
            return self.urls

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            raise SupportingDocDiscoveryError(f"Invalid JSON: {e}") from e
        except Exception as e:
            logger.error(f"Failed to discover URLs from JSON: {e}")
            raise SupportingDocDiscoveryError(f"JSON discovery failed: {e}") from e

    async def discover_from_rdf(self, turtle_content: str) -> SupportingDocURLs:
        """
        Discover URLs from RDF Turtle.

        Args:
            turtle_content: Turtle RDF string

        Returns:
            SupportingDocURLs with discovered URLs
        """
        try:
            self.urls = SupportingDocURLs()
            graph = Graph()
            graph.parse(data=turtle_content, format="turtle")

            # Extract dcat:distribution URLs
            for subject in graph.subjects():
                for dist in graph.objects(subject=subject, predicate=self.DCAT.distribution):
                    url_obj = list(
                        graph.objects(subject=dist, predicate=self.DCAT.accessURL)
                    ) or list(graph.objects(subject=dist, predicate=self.DCAT.downloadURL))

                    for url in url_obj:
                        self._classify_and_add_url(str(url))

                # Extract foaf:page URLs
                for page in graph.objects(subject=subject, predicate=self.FOAF.page):
                    self._classify_and_add_url(str(page))

            logger.info(f"Discovered {len(self.urls.supporting_docs)} URLs from RDF")
            return self.urls

        except Exception as e:
            logger.error(f"Failed to discover URLs from RDF: {e}")
            raise SupportingDocDiscoveryError(f"RDF discovery failed: {e}") from e

    def _classify_and_add_url(self, url: str) -> None:
        """
        Classify URL by type and add to appropriate list.

        Args:
            url: URL to classify
        """
        if not url or not isinstance(url, str):
            return

        url = url.strip()
        if not url.startswith(("http://", "https://", "ftp://")):
            return

        # Check if it's a download (zip, tar, gz, etc.)
        if re.search(r"\.(zip|tar|tar\.gz|tgz|7z|rar)$", url, re.IGNORECASE):
            self.urls.download_urls.append(url)
            return

        # Check if it's a web folder/directory access
        # Only classify as fileaccess if explicitly marked or is a known directory pattern
        # Do NOT classify website homepages (like eidc.ac.uk/) as fileaccess
        if "fileaccess" in url.lower() or "/directory/" in url.lower():
            self.urls.fileaccess_urls.append(url)
            return

        # Check if it's metadata document
        if re.search(r"\.(xml|json|rdf|ttl|n3)$", url, re.IGNORECASE):
            self.urls.metadata_urls.append(url)
            return

        # FIXED: Exclude HTML pages and other web content
        # These should NOT be stored as supporting documents
        if re.search(r"\.(html|htm|asp|aspx|php|jsp|cgi|py|js|css)$", url, re.IGNORECASE):
            logger.debug(f"Skipping web page: {url}")
            return
        
        # Exclude common web domain URLs without file extensions
        # (e.g., orcid.org, eidc.ac.uk, etc.) - these are landing pages
        parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        if not path or path == '':
            logger.debug(f"Skipping domain/landing page: {url}")
            return

        # Only add if it looks like a real document with extension
        # or is a known document URL pattern
        if Path(path).suffix or 'document' in url.lower() or 'file' in url.lower():
            # Default: supporting document
            self.urls.supporting_docs.append(url)
        else:
            logger.debug(f"Skipping non-document URL: {url}")

    async def discover(
        self, 
        identifier: str,
        json_content: Optional[str] = None,
        xml_content: Optional[str] = None,
        rdf_content: Optional[str] = None
    ) -> List[str]:
        """
        Discover supporting document URLs from available metadata formats.
        
        Tries formats in priority order:
        1. JSON (most reliable)
        2. XML (ISO 19139)
        3. RDF (Turtle)
        
        Args:
            identifier: Dataset identifier (for logging)
            json_content: JSON metadata content
            xml_content: ISO 19139 XML metadata content
            rdf_content: RDF Turtle metadata content
            
        Returns:
            List of discovered document URLs (all types combined)
        """
        logger.debug(f"[{identifier}] Discovering supporting documents")
        
        all_urls = SupportingDocURLs()
        
        # Try JSON first (most likely to have structured links)
        if json_content:
            try:
                json_urls = await self.discover_from_json(json_content)
                logger.debug(f"[{identifier}] JSON: Found {len(json_urls.supporting_docs)} supporting docs")
                
                # Combine URLs from JSON
                all_urls.supporting_docs.extend(json_urls.supporting_docs)
                all_urls.download_urls.extend(json_urls.download_urls)
                all_urls.fileaccess_urls.extend(json_urls.fileaccess_urls)
                all_urls.metadata_urls.extend(json_urls.metadata_urls)
                
            except Exception as e:
                logger.warning(f"[{identifier}] JSON discovery failed: {e}")
        
        # Try XML if JSON didn't find anything
        if xml_content and not all_urls.supporting_docs:
            try:
                xml_urls = await self.discover_from_iso_xml(xml_content)
                logger.debug(f"[{identifier}] XML: Found {len(xml_urls.supporting_docs)} supporting docs")
                
                # Combine URLs from XML
                all_urls.supporting_docs.extend(xml_urls.supporting_docs)
                all_urls.download_urls.extend(xml_urls.download_urls)
                all_urls.fileaccess_urls.extend(xml_urls.fileaccess_urls)
                all_urls.metadata_urls.extend(xml_urls.metadata_urls)
                
            except Exception as e:
                logger.warning(f"[{identifier}] XML discovery failed: {e}")
        
        # Try RDF as fallback
        if rdf_content and not all_urls.supporting_docs:
            try:
                rdf_urls = await self.discover_from_rdf(rdf_content)
                logger.debug(f"[{identifier}] RDF: Found {len(rdf_urls.supporting_docs)} supporting docs")
                
                # Combine URLs from RDF
                all_urls.supporting_docs.extend(rdf_urls.supporting_docs)
                all_urls.download_urls.extend(rdf_urls.download_urls)
                all_urls.fileaccess_urls.extend(rdf_urls.fileaccess_urls)
                all_urls.metadata_urls.extend(rdf_urls.metadata_urls)
                
            except Exception as e:
                logger.warning(f"[{identifier}] RDF discovery failed: {e}")
        
        # Combine all URL types into single list
        all_discovered_urls = (
            all_urls.supporting_docs +
            all_urls.download_urls +
            all_urls.fileaccess_urls +
            all_urls.metadata_urls
        )
        
        logger.info(f"[{identifier}] Discovered {len(all_discovered_urls)} total URLs")
        
        return all_discovered_urls