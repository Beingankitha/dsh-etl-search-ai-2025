"""
Keyword and Topic Extraction Services

Automatically extracts keywords and infers topic categories from dataset
metadata (title, abstract, lineage) using NLP and semantic analysis.

This ensures all datasets have enriched metadata for better search results.
"""

import re
from typing import List, Optional
from collections import Counter
import logging

logger = logging.getLogger(__name__)


class KeywordExtractor:
    """Extract keywords from dataset metadata using multiple strategies."""
    
    # Common environmental/scientific keywords
    SCIENTIFIC_KEYWORDS = {
        'soil', 'water', 'carbon', 'nitrogen', 'biomass', 'ecosystem',
        'biodiversity', 'species', 'habitat', 'climate', 'temperature',
        'precipitation', 'vegetation', 'forest', 'wetland', 'grassland',
        'agriculture', 'pollution', 'contamination', 'monitoring', 'survey',
        'dataset', 'model', 'analysis', 'mapping', 'inventory', 'census',
        'abundance', 'diversity', 'richness', 'density', 'distribution',
        'spatial', 'temporal', 'trend', 'change', 'impact', 'restoration',
        'conservation', 'management', 'land use', 'land cover', 'uk',
        'great britain', 'england', 'scotland', 'wales', 'ireland'
    }
    
    @staticmethod
    def extract_from_text(text: str, top_k: int = 10) -> List[str]:
        """
        Extract keywords from text using multiple strategies.
        
        Strategy:
        1. Split text into words and filter for meaningful terms
        2. Keep scientific domain keywords
        3. Keep multi-word phrases (2-3 words)
        4. Score by frequency and length
        5. Return top K keywords
        
        Args:
            text: Input text (title, abstract, etc.)
            top_k: Number of keywords to extract
            
        Returns:
            List of extracted keywords
        """
        if not text:
            return []
        
        # Normalize text
        text_lower = text.lower()
        
        # Remove common words and special characters
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was',
            'been', 'be', 'have', 'has', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'can',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she',
            'it', 'we', 'they', 'what', 'which', 'who', 'when', 'where',
            'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more',
            'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only',
            'own', 'same', 'so', 'than', 'too', 'very', 'just', 'etc'
        }
        
        # Extract candidate terms
        candidates = []
        
        # Single word candidates (keep scientific keywords)
        words = re.findall(r'\b\w+\b', text_lower)
        for word in words:
            if len(word) > 3 and word not in stop_words:
                candidates.append(word)
            elif word in KeywordExtractor.SCIENTIFIC_KEYWORDS:
                candidates.append(word)
        
        # Multi-word phrases (2-3 word combinations)
        bigrams = re.findall(r'\b\w+\s+\w+\b', text_lower)
        for bigram in bigrams:
            words_in_bigram = bigram.split()
            if not any(w in stop_words for w in words_in_bigram):
                candidates.append(bigram)
        
        # Score by frequency
        counter = Counter(candidates)
        
        # Get top keywords, removing duplicates
        keywords = []
        seen = set()
        for keyword, count in counter.most_common(top_k * 2):
            # Normalize to lowercase
            keyword_normalized = keyword.lower()
            
            # Skip if already have similar keyword
            if keyword_normalized not in seen:
                keywords.append(keyword_normalized)
                seen.add(keyword_normalized)
                
                if len(keywords) >= top_k:
                    break
        
        return keywords[:top_k]
    
    @staticmethod
    def extract_from_dataset(
        title: Optional[str],
        abstract: Optional[str],
        lineage: Optional[str] = None,
        top_k: int = 8
    ) -> List[str]:
        """
        Extract keywords from dataset metadata fields.
        
        Combines keywords from title (high weight), abstract, and lineage.
        
        Args:
            title: Dataset title
            abstract: Dataset abstract
            lineage: Dataset lineage/methodology (optional)
            top_k: Number of keywords to return
            
        Returns:
            List of keywords
        """
        # Extract from each field with different weights
        keywords = []
        
        # Title is most important - extract all keywords
        if title:
            title_keywords = KeywordExtractor.extract_from_text(title, top_k=5)
            keywords.extend(title_keywords)
        
        # Abstract is important - extract top keywords
        if abstract:
            abstract_keywords = KeywordExtractor.extract_from_text(abstract, top_k=6)
            keywords.extend(abstract_keywords)
        
        # Lineage provides context - extract a few keywords
        if lineage:
            lineage_keywords = KeywordExtractor.extract_from_text(lineage, top_k=3)
            keywords.extend(lineage_keywords)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                unique_keywords.append(kw)
                seen.add(kw)
        
        return unique_keywords[:top_k]


class TopicCategoryClassifier:
    """Infer topic categories for datasets using keyword/text matching."""
    
    # Topic categories with associated keywords
    TOPIC_CATEGORIES = {
        'Climate': ['climate', 'temperature', 'precipitation', 'weather', 'atmospheric', 'greenhouse'],
        'Biodiversity': ['species', 'biodiversity', 'ecosystem', 'habitat', 'organisms', 'diversity', 'fauna', 'flora', 'earthworm'],
        'Soil': ['soil', 'carbon', 'nitrogen', 'organic matter', 'sediment', 'geology', 'topsoil'],
        'Water': ['water', 'hydrological', 'wetland', 'river', 'lake', 'groundwater', 'aquatic', 'hydrology'],
        'Land Use': ['land use', 'land cover', 'agriculture', 'forestry', 'urban', 'vegetation', 'habitat mapping'],
        'Pollution': ['pollution', 'contamination', 'heavy metals', 'pesticide', 'chemical', 'toxic', 'air quality'],
        'Monitoring': ['monitoring', 'survey', 'observation', 'measurement', 'sampling', 'assessment', 'inventory'],
        'Modeling': ['model', 'simulation', 'modeling', 'estimates', 'prediction', 'algorithm', 'analysis'],
        'Geospatial': ['spatial', 'mapping', 'gis', 'satellite', 'remote sensing', 'geographic', 'location'],
        'Environmental': ['environmental', 'ecology', 'ecosystem services', 'conservation', 'restoration', 'management'],
    }
    
    @staticmethod
    def classify(
        title: Optional[str],
        abstract: Optional[str],
        keywords: Optional[List[str]] = None,
        lineage: Optional[str] = None
    ) -> List[str]:
        """
        Classify dataset into topic categories.
        
        Matches text against category keywords and returns matching categories.
        
        Args:
            title: Dataset title
            abstract: Dataset abstract
            keywords: Extracted keywords (optional)
            lineage: Dataset lineage (optional)
            
        Returns:
            List of topic categories
        """
        # Combine all text
        full_text = " ".join(filter(None, [title, abstract, lineage])).lower()
        
        # If keywords provided, use them too
        if keywords:
            full_text += " " + " ".join(keywords)
        
        matched_categories = set()
        
        # Score each category based on keyword matches
        category_scores = {}
        
        for category, category_keywords in TopicCategoryClassifier.TOPIC_CATEGORIES.items():
            score = 0
            for keyword in category_keywords:
                if keyword in full_text:
                    score += full_text.count(keyword)
            category_scores[category] = score
        
        # Return categories with score > 0, sorted by score
        matched_categories = [
            cat for cat, score in sorted(
                category_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )
            if score > 0
        ]
        
        # Return top 3 categories
        return matched_categories[:3]


class MetadataEnricher:
    """Enriches dataset metadata with extracted keywords and topics."""
    
    def __init__(self):
        self.keyword_extractor = KeywordExtractor()
        self.topic_classifier = TopicCategoryClassifier()
    
    def enrich(
        self,
        title: Optional[str],
        abstract: Optional[str],
        keywords: Optional[List[str]] = None,
        topic_category: Optional[List[str]] = None,
        lineage: Optional[str] = None
    ) -> dict:
        """
        Enrich metadata with keywords and topics if missing.
        
        Args:
            title: Dataset title
            abstract: Dataset abstract
            keywords: Existing keywords (if any)
            topic_category: Existing topic categories (if any)
            lineage: Dataset lineage
            
        Returns:
            Dict with enriched metadata: {'keywords': [...], 'topic_category': [...]}
        """
        # Extract keywords if missing
        enriched_keywords = keywords if keywords and len(keywords) > 0 else None
        if not enriched_keywords:
            enriched_keywords = self.keyword_extractor.extract_from_dataset(
                title=title,
                abstract=abstract,
                lineage=lineage,
                top_k=8
            )
        
        # Classify topic if missing
        enriched_topics = topic_category if topic_category and len(topic_category) > 0 else None
        if not enriched_topics:
            enriched_topics = self.topic_classifier.classify(
                title=title,
                abstract=abstract,
                keywords=enriched_keywords,
                lineage=lineage
            )
        
        logger.info(
            f"Enriched metadata: keywords={len(enriched_keywords)}, "
            f"topics={len(enriched_topics)}"
        )
        
        return {
            'keywords': enriched_keywords,
            'topic_category': enriched_topics
        }


__all__ = [
    'KeywordExtractor',
    'TopicCategoryClassifier',
    'MetadataEnricher',
]
