"""
Metadata Parsers Module - Format-Specific Metadata Extraction

This module provides parsers for multiple metadata formats used in geospatial data catalogues.

Supported Formats:
    - ISO 19139 XML: International standard for geospatial metadata
    - JSON: Structured metadata in JSON format
    - RDF/Turtle: Semantic web format for linked data
    - Schema.org JSON-LD: Linked data for structured data markup

Classes:
    - MetadataParser: Abstract base class for all parsers
    - ISO19139Parser: Parses ISO 19139 XML metadata
    - JSONMetadataParser: Parses JSON metadata documents
    - RDFParser: Parses RDF/Turtle metadata
    - SchemaOrgParser: Parses Schema.org JSON-LD metadata
    - MetadataParserError: Exception for parser errors

Usage:
    from src.services.parsers import ISO19139Parser, JSONMetadataParser
    
    # Parse ISO 19139 XML
    xml_parser = ISO19139Parser()
    dataset = await xml_parser.parse(xml_content)
    
    # Parse JSON metadata
    json_parser = JSONMetadataParser()
    dataset = await json_parser.parse(json_content)
    
    # Use with fallback chain
    parsers = [xml_parser, json_parser, rdf_parser]
    for parser in parsers:
        try:
            dataset = await parser.parse(content)
            break
        except MetadataParserError:
            continue

Architecture:
    - Strategy Pattern: Each parser is a strategy for different formats
    - Async/Await: All parsers are async for non-blocking I/O
    - Exception Hierarchy: MetadataParserError for all parser errors
    - Type Safety: Uses Pydantic models for parsed results
"""

from .metadata_parser import MetadataParser, MetadataParserError
from .iso19139_parser import ISO19139Parser
from .json_parser import JSONMetadataParser
from .rdf_parser import RDFParser
from .schema_org_parser import SchemaOrgParser

__all__ = [
    # Base classes
    "MetadataParser",
    "MetadataParserError",
    # Concrete parsers
    "ISO19139Parser",
    "JSONMetadataParser",
    "RDFParser",
    "SchemaOrgParser",
]
