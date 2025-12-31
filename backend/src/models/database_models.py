"""
Database model classes for ORM mapping.

These classes represent table entities and are distinct from 
API request/response schemas in schemas.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List


@dataclass
class Dataset:
    """Dataset entity model."""
    file_identifier: str
    title: str
    abstract: Optional[str] = None
    topic_category: Optional[str] = None  # Stored as JSON string
    keywords: Optional[str] = None  # Stored as JSON string
    lineage: Optional[str] = None
    supplemental_info: Optional[str] = None
    source_format: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    id: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None values and id."""
        data = asdict(self)
        # Remove id and timestamps for insert operations
        data.pop("id", None)
        data.pop("created_at", None)
        data.pop("updated_at", None)
        return {k: v for k, v in data.items() if v is not None}


@dataclass
class MetadataDocument:
    """Metadata document entity model."""
    dataset_id: int
    document_type: str  # iso19139, json, schema_org, rdf
    original_content: bytes
    mime_type: Optional[str] = None
    created_at: Optional[str] = None
    id: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = asdict(self)
        data.pop("id", None)
        data.pop("created_at", None)
        return {k: v for k, v in data.items() if v is not None}


@dataclass
class DataFile:
    """Data file entity model."""
    dataset_id: int
    filename: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    created_at: Optional[str] = None
    id: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = asdict(self)
        data.pop("id", None)
        data.pop("created_at", None)
        return {k: v for k, v in data.items() if v is not None}


@dataclass
class SupportingDocument:
    """Supporting document entity model."""
    dataset_id: int
    document_url: str
    title: Optional[str] = None
    file_extension: Optional[str] = None
    downloaded_path: Optional[str] = None
    text_content: Optional[str] = None
    embedding_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    id: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = asdict(self)
        data.pop("id", None)
        data.pop("created_at", None)
        data.pop("updated_at", None)
        return {k: v for k, v in data.items() if v is not None}