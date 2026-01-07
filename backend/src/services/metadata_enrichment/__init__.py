"""
Metadata Enrichment Service - Keywords and Topics Extraction

This service automatically extracts keywords and infers topic categories from dataset
metadata (title, abstract, lineage) using NLP and semantic analysis.

Classes:
    - KeywordExtractor: Extracts keywords from metadata text
    - TopicCategoryClassifier: Classifies datasets into topic categories
    - MetadataEnricher: Main enrichment orchestrator

Features:
    - Keyword extraction using frequency analysis and domain-specific terms
    - Topic classification using keyword matching
    - Multi-field enrichment (title, abstract, lineage)
    - Automatic deduplication and ranking

Usage:
    from src.services.metadata_enrichment import MetadataEnricher
    
    enricher = MetadataEnricher()
    enriched = enricher.enrich(
        title="Climate Data Analysis",
        abstract="A dataset analyzing temperature trends...",
        lineage="Data collected from weather stations"
    )
    # Returns: {'keywords': [...], 'topic_category': [...]}
"""

from .metadata_enrichment_impl import (
    KeywordExtractor,
    TopicCategoryClassifier,
    MetadataEnricher,
)

__all__ = [
    'KeywordExtractor',
    'TopicCategoryClassifier',
    'MetadataEnricher',
]
