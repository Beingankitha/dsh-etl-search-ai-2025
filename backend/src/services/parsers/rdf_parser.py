"""
RDF (Turtle) metadata parser for CEH datasets.

Parses semantic web metadata in RDF Turtle format using DCAT vocabulary.
"""

from __future__ import annotations

import logging
from typing import Optional

from rdflib import Graph, Namespace, RDF, RDFS

from src.logging_config import get_logger
from src.models import Dataset
from .metadata_parser import MetadataParser, MetadataParserError

logger = get_logger(__name__)


class RDFParser(MetadataParser):
    """
    Parses RDF/Turtle metadata documents.

    Uses DCAT (Data Catalog Vocabulary) ontology to extract dataset metadata:
    - dcat:Dataset as primary entity
    - dct:identifier, dct:title, dct:description
    - dcat:keyword, dct:subject (topics)
    - dct:provenance (lineage)
    """

    # RDF Namespaces
    DCAT = Namespace("http://www.w3.org/ns/dcat#")
    DCT = Namespace("http://purl.org/dc/terms/")
    FOAF = Namespace("http://xmlns.com/foaf/0.1/")

    async def parse(self, content: str) -> Dataset:
        """
        Parse RDF Turtle into Dataset.

        Args:
            content: Turtle RDF string

        Returns:
            Parsed Dataset

        Raises:
            MetadataParserError: If parsing fails
        """
        try:
            logger.info("Parsing RDF/Turtle metadata")
            graph = Graph()
            graph.parse(data=content, format="turtle")
            return self._extract_dataset(graph)
        except Exception as e:
            logger.error(f"Failed to parse RDF/Turtle: {e}")
            raise MetadataParserError(f"RDF parse error: {e}") from e

    def _extract_dataset(self, graph: Graph) -> Dataset:
        """
        Extract Dataset from RDF graph.

        Args:
            graph: RDF graph

        Returns:
            Dataset object
        """
        # Find Dataset subject (typically first dcat:Dataset)
        dataset_subject = None
        for subject in graph.subjects(predicate=RDF.type, object=self.DCAT.Dataset):
            dataset_subject = subject
            break

        if not dataset_subject:
            raise MetadataParserError("No dcat:Dataset found in RDF graph")

        file_identifier = self._extract_identifier(graph, dataset_subject)
        title = self._extract_title(graph, dataset_subject)
        abstract = self._extract_description(graph, dataset_subject)
        topic_category = self._extract_subjects(graph, dataset_subject)
        keywords = self._extract_keywords(graph, dataset_subject)
        lineage = self._extract_provenance(graph, dataset_subject)
        supplemental_info = self._extract_supplemental(graph, dataset_subject)

        return Dataset(
            file_identifier=file_identifier or "unknown",
            title=title or "Unknown Title",
            abstract=abstract or "",
            topic_category=topic_category,
            keywords=keywords,
            lineage=lineage,
            supplemental_info=supplemental_info,
        )

    def _extract_identifier(self, graph: Graph, subject) -> Optional[str]:
        """Extract identifier from RDF dataset."""
        # Try dct:identifier
        for obj in graph.objects(subject=subject, predicate=self.DCT.identifier):
            return self._sanitize_string(str(obj))
        return None

    def _extract_title(self, graph: Graph, subject) -> Optional[str]:
        """Extract title from RDF dataset."""
        for obj in graph.objects(subject=subject, predicate=self.DCT.title):
            return self._sanitize_string(str(obj))
        return None

    def _extract_description(self, graph: Graph, subject) -> Optional[str]:
        """Extract description from RDF dataset."""
        for obj in graph.objects(subject=subject, predicate=self.DCT.description):
            return self._sanitize_string(str(obj))
        return None

    def _extract_subjects(self, graph: Graph, subject) -> list[str]:
        """Extract subject/topics from RDF dataset."""
        subjects = []
        for obj in graph.objects(subject=subject, predicate=self.DCT.subject):
            sanitized = self._sanitize_string(str(obj))
            if sanitized:
                subjects.append(sanitized)
        return subjects

    def _extract_keywords(self, graph: Graph, subject) -> list[str]:
        """Extract keywords from RDF dataset."""
        keywords = []
        for obj in graph.objects(subject=subject, predicate=self.DCAT.keyword):
            sanitized = self._sanitize_string(str(obj))
            if sanitized:
                keywords.append(sanitized)
        return keywords

    def _extract_provenance(self, graph: Graph, subject) -> Optional[str]:
        """Extract provenance/lineage from RDF dataset."""
        # Try dct:provenance and dct:creator
        provenance_parts = []

        for obj in graph.objects(subject=subject, predicate=self.DCT.provenance):
            sanitized = self._sanitize_string(str(obj))
            if sanitized:
                provenance_parts.append(sanitized)

        for creator in graph.objects(subject=subject, predicate=self.DCT.creator):
            creator_name = None
            # Try FOAF.name for creator
            for name_obj in graph.objects(subject=creator, predicate=self.FOAF.name):
                creator_name = self._sanitize_string(str(name_obj))
                break
            if creator_name:
                provenance_parts.append(f"Creator: {creator_name}")

        return "; ".join(provenance_parts) if provenance_parts else None

    def _extract_supplemental(self, graph: Graph, subject) -> Optional[str]:
        """Extract supplemental information from RDF dataset."""
        # Try dct:coverage, dcat:distribution URLs
        supp_parts = []

        for coverage in graph.objects(subject=subject, predicate=self.DCT.coverage):
            sanitized = self._sanitize_string(str(coverage))
            if sanitized:
                supp_parts.append(f"Coverage: {sanitized}")

        return "; ".join(supp_parts) if supp_parts else None