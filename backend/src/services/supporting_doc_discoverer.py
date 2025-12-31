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
from typing import Optional
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

            # Extract all onlineResource links
            xpath = ".//gmd:onlineResource/gmd:linkage/gco:URL/text()"
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
        if "fileaccess" in url.lower() or "/directory/" in url.lower() or url.endswith("/"):
            self.urls.fileaccess_urls.append(url)
            return

        # Check if it's metadata document
        if re.search(r"\.(xml|json|rdf|ttl|n3)$", url, re.IGNORECASE):
            self.urls.metadata_urls.append(url)
            return

        # Default: supporting document
        self.urls.supporting_docs.append(url)