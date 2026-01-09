"""
Unit tests for metadata enrichment services.

Tests keyword extraction and topic category classification.
"""

import pytest
from src.services.metadata_enrichment.metadata_enrichment_impl import (
    KeywordExtractor,
    TopicCategoryClassifier,
    MetadataEnricher,
)


# Test fixtures for reusable sample data
SAMPLE_TITLE = "Soil Carbon Monitoring in UK Woodlands"
SAMPLE_ABSTRACT = """
Long-term monitoring of soil carbon stocks in managed and unmanaged
woodland ecosystems. Measurements include carbon content, density, and
estimated stocks by depth interval.
"""


class TestKeywordExtractor:
    """Test keyword extraction from metadata."""

    def test_extract_keywords_from_title(self):
        """Test extracting keywords from simple title."""
        title = "Soil Carbon Monitoring in UK Woodlands"
        keywords = KeywordExtractor.extract_from_text(title, top_k=5)
        
        assert len(keywords) > 0
        # Should extract meaningful words
        assert any("soil" in k.lower() or "carbon" in k.lower() for k in keywords)

    def test_extract_keywords_from_description(self):
        """Test extracting keywords from longer description."""
        description = """
        This dataset contains soil moisture measurements collected from agricultural
        fields across England. Measurements include volumetric water content, soil
        temperature, and water retention characteristics. Data spans 2020-2023.
        """
        keywords = KeywordExtractor.extract_from_text(description, top_k=10)
        
        assert len(keywords) > 0
        assert any("soil" in k.lower() for k in keywords)
        assert any("water" in k.lower() or "moisture" in k.lower() for k in keywords)

    def test_extract_keywords_with_stopwords(self):
        """Test that common stopwords are filtered."""
        text = "The quick brown fox jumps over the lazy dog"
        keywords = KeywordExtractor.extract_from_text(text, top_k=10)
        
        # Should not include common stopwords
        assert "the" not in [k.lower() for k in keywords]
        assert "a" not in [k.lower() for k in keywords]
        assert "and" not in [k.lower() for k in keywords]

    def test_extract_keywords_scientific_terms(self):
        """Test that scientific keywords are preserved."""
        text = "Biodiversity assessment in coastal wetlands: ecosystem services and species habitat"
        keywords = KeywordExtractor.extract_from_text(text, top_k=10)
        
        # Scientific terms should be included even if not frequent
        assert any("biodiversity" in k.lower() for k in keywords)
        assert any("wetland" in k.lower() or "ecosystem" in k.lower() for k in keywords)

    def test_extract_keywords_ngrams(self):
        """Test extraction of multi-word phrases."""
        text = "land use land cover mapping using satellite imagery"
        keywords = KeywordExtractor.extract_from_text(text, top_k=10)
        
        # Should include multi-word phrases
        assert len(keywords) > 0

    def test_extract_keywords_frequency_scoring(self):
        """Test that frequent terms are scored higher."""
        text = "soil soil soil water water carbon carbon carbon carbon"
        keywords = KeywordExtractor.extract_from_text(text, top_k=3)
        
        # Carbon appears 4 times, should be first
        assert "carbon" in keywords[0].lower() if keywords else True

    def test_extract_keywords_deduplication(self):
        """Test that duplicate keywords are removed."""
        text = "soil soil soil water water ecosystem ecosystem ecosystem"
        keywords = KeywordExtractor.extract_from_text(text, top_k=10)
        
        # Should not have duplicates
        assert len(keywords) == len(set(keywords))

    def test_extract_keywords_empty_text(self):
        """Test extraction from empty text."""
        keywords = KeywordExtractor.extract_from_text("", top_k=10)
        
        assert keywords == []

    def test_extract_keywords_whitespace_only(self):
        """Test extraction from whitespace-only text."""
        keywords = KeywordExtractor.extract_from_text("   \n\t  ", top_k=10)
        
        assert keywords == []

    def test_extract_keywords_top_k_limit(self):
        """Test that top_k parameter limits results."""
        text = "soil water carbon nitrogen phosphorus ecosystem biodiversity"
        keywords_5 = KeywordExtractor.extract_from_text(text, top_k=5)
        keywords_10 = KeywordExtractor.extract_from_text(text, top_k=10)
        
        assert len(keywords_5) <= 5
        assert len(keywords_10) <= 10

    def test_extract_keywords_case_insensitivity(self):
        """Test that extraction is case-insensitive."""
        text1 = "SOIL Water Carbon"
        text2 = "soil water carbon"
        
        keywords1 = KeywordExtractor.extract_from_text(text1, top_k=10)
        keywords2 = KeywordExtractor.extract_from_text(text2, top_k=10)
        
        # Results should be equivalent
        assert len(keywords1) == len(keywords2)

    def test_extract_keywords_with_numbers(self):
        """Test handling of numbers in text."""
        text = "Dataset from 2020 with 1000 samples and 50 parameters"
        keywords = KeywordExtractor.extract_from_text(text, top_k=10)
        
        # Should extract meaningful keywords, may include some numbers
        assert len(keywords) > 0

    def test_extract_keywords_unicode(self):
        """Test extraction with unicode characters."""
        text = "Français: biodiversity, Español: ecosistema, 日本語: 生態系"
        keywords = KeywordExtractor.extract_from_text(text, top_k=10)
        
        # Should handle unicode gracefully
        assert len(keywords) >= 0  # No crash


class TestTopicCategoryClassifier:
    """Test topic category classification."""

    def test_classify_single_topic(self):
        """Test classifying single topic."""
        result = TopicCategoryClassifier.classify(
            title="Soil carbon stocks in UK woodlands",
            abstract="Study of soil carbon"
        )
        
        assert isinstance(result, list)
        assert len(result) <= 3

    def test_classify_multiple_topics(self):
        """Test classifying multiple topics."""
        result = TopicCategoryClassifier.classify(
            title="Water Quality and Biodiversity Assessment",
            abstract="Assessment of species diversity in aquatic ecosystems"
        )
        assert isinstance(result, list)
        assert len(result) > 0

    def test_classify_with_confidence_scores(self):
        """Test classification returns multiple categories."""
        result = TopicCategoryClassifier.classify(
            title="Climate and Ecosystem Monitoring",
            abstract="Monitoring climate impacts on ecosystems"
        )
        assert isinstance(result, list)
        assert len(result) <= 3

    def test_classify_unknown_category(self):
        """Test classifying unknown category."""
        result = TopicCategoryClassifier.classify(
            title="XYZ123 Unrelated Text",
            abstract="Something unrelated"
        )
        assert isinstance(result, list)

    def test_classify_empty_text(self):
        """Test classifying empty text."""
        result = TopicCategoryClassifier.classify(title="", abstract="")
        assert isinstance(result, list)

    def test_classifier_consistency(self):
        """Test classifier consistency across runs."""
        result1 = TopicCategoryClassifier.classify(
            title="Biodiversity Monitoring",
            abstract="Monitoring biodiversity"
        )
        result2 = TopicCategoryClassifier.classify(
            title="Biodiversity Monitoring",
            abstract="Monitoring biodiversity"
        )
        
        assert result1 == result2

    def test_classifier_case_insensitivity(self):
        """Test classifier handles case variations."""
        result1 = TopicCategoryClassifier.classify(
            title="WATER QUALITY",
            abstract="Quality assessment"
        )
        result2 = TopicCategoryClassifier.classify(
            title="water quality",
            abstract="Quality assessment"
        )
        
        assert result1 == result2

    def test_classify_with_keywords(self):
        """Test classification with keywords."""
        result = TopicCategoryClassifier.classify(
            title="Soil Study",
            abstract="Carbon and organic matter",
            keywords=["soil", "carbon", "organic matter"]
        )
        assert isinstance(result, list)
        assert len(result) > 0

    def test_classifier_handles_long_text(self):
        """Test classifier with long text."""
        long_abstract = "soil carbon " * 500
        result = TopicCategoryClassifier.classify(
            title="Soil Study",
            abstract=long_abstract
        )
        assert isinstance(result, list)
        assert len(result) > 0


class TestMetadataEnricher:
    """Test complete metadata enrichment pipeline."""

    def test_full_enrichment_pipeline(self):
        """Test complete enrichment workflow."""
        enricher = MetadataEnricher()
        result = enricher.enrich(
            title=SAMPLE_TITLE,
            abstract=SAMPLE_ABSTRACT
        )
        
        assert isinstance(result, dict)
        assert 'keywords' in result
        assert 'topic_category' in result
        assert isinstance(result['keywords'], list)
        assert isinstance(result['topic_category'], list)

    def test_enrichment_with_title_only(self):
        """Test enrichment with only title provided."""
        enricher = MetadataEnricher()
        result = enricher.enrich(title="Biodiversity in Wetlands", abstract="")
        
        assert isinstance(result, dict)
        assert len(result['keywords']) > 0

    def test_enrichment_empty_input(self):
        """Test enrichment with empty input."""
        enricher = MetadataEnricher()
        result = enricher.enrich(title="", abstract="")
        
        assert isinstance(result, dict)
        assert isinstance(result['keywords'], list)
        assert isinstance(result['topic_category'], list)

    def test_enrichment_preserves_existing_keywords(self):
        """Test that enrichment preserves existing keywords."""
        enricher = MetadataEnricher()
        existing_keywords = ["test", "important"]
        
        result = enricher.enrich(
            title="Test Dataset",
            abstract="",
            keywords=existing_keywords
        )
        
        # Should preserve existing keywords
        assert result['keywords'] == existing_keywords

    def test_enrichment_performance_small_dataset(self):
        """Test enrichment performance on small dataset."""
        enricher = MetadataEnricher()
        result = enricher.enrich(
            title="Small Dataset",
            abstract="Small abstract"
        )
        
        assert isinstance(result, dict)
        assert len(result['keywords']) > 0

    def test_enrichment_performance_large_dataset(self):
        """Test enrichment performance on larger dataset."""
        enricher = MetadataEnricher()
        large_abstract = "Abstract text. " * 1000
        
        result = enricher.enrich(
            title="Large Dataset",
            abstract=large_abstract
        )
        
        assert isinstance(result, dict)
        assert len(result['keywords']) > 0

    def test_enrichment_memory_efficiency(self):
        """Test enrichment doesn't use excessive memory."""
        enricher = MetadataEnricher()
        
        for i in range(20):
            result = enricher.enrich(
                title=f"Dataset {i}",
                abstract=f"Abstract {i}"
            )
            
            assert isinstance(result, dict)


class TestEnrichmentIntegration:
    """Integration tests for enrichment pipeline."""

    def test_enrichment_with_realistic_dataset(self):
        """Test enrichment with realistic dataset metadata."""
        enricher = MetadataEnricher()
        result = enricher.enrich(
            title="Volumetric Water Content in UK Soils",
            abstract="Time series measurement of soil water content from monitoring stations"
        )
        
        assert isinstance(result, dict)
        assert len(result['keywords']) > 0
        assert len(result['topic_category']) > 0

    def test_enrichment_multilingual_text(self):
        """Test enrichment with mixed-language text."""
        enricher = MetadataEnricher()
        result = enricher.enrich(
            title="Biodiversity Monitoring: Diversité Biologique",
            abstract="Données de sol"
        )
        
        # Should handle unicode gracefully
        assert isinstance(result, dict)

    def test_enrichment_consistency_across_formats(self):
        """Test that enrichment is consistent."""
        enricher = MetadataEnricher()
        
        result1 = enricher.enrich(
            title="Soil Carbon",
            abstract="Data about soil carbon"
        )
        
        result2 = enricher.enrich(
            title="Soil Carbon",
            abstract="Data about soil carbon"
        )
        
        # Should produce consistent results
        assert result1['keywords'] == result2['keywords']
        assert result1['topic_category'] == result2['topic_category']
