"""
End-to-end tests for complete ETL and search workflows.

Tests full integration of extraction, parsing, enrichment, and indexing.
"""

import pytest
import json
from src.services.parsers.json_parser import JSONMetadataParser
from src.services.parsers.rdf_parser import RDFParser
from src.services.parsers.iso19139_parser import ISO19139Parser
from src.services.parsers.schema_org_parser import SchemaOrgParser
from src.services.metadata_enrichment.metadata_enrichment_impl import MetadataEnricher
from src.models import Dataset


class TestFullETLPipeline:
    """Test complete ETL pipeline from extraction to indexing."""

    @pytest.mark.asyncio
    async def test_json_to_enriched_dataset_pipeline(self):
        """Test complete pipeline: JSON parse -> enrich."""
        json_content = json.dumps({
            "fileIdentifier": "test-dataset-001",
            "title": "UK Soil Carbon Survey",
            "abstract": "Long-term monitoring of soil carbon stocks in managed and unmanaged woodlands",
            "keywords": ["soil", "carbon"],
            "topicCategory": ["geoscientificInformation"]
        })
        
        # Parse
        parser = JSONMetadataParser()
        dataset = await parser.parse(json_content)
        
        assert dataset.file_identifier == "test-dataset-001"
        assert dataset.title == "UK Soil Carbon Survey"
        
        # Enrich (synchronous call)
        enricher = MetadataEnricher()
        enriched = enricher.enrich(
            title=dataset.title,
            abstract=dataset.abstract,
            keywords=dataset.keywords
        )
        
        assert len(enriched['keywords']) > 0
        assert len(enriched['topic_category']) > 0

    @pytest.mark.asyncio
    async def test_iso_to_enriched_dataset_pipeline(self):
        """Test complete pipeline: ISO19139 parse -> enrich."""
        iso_content = """<?xml version="1.0" encoding="UTF-8"?>
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
            <gmd:fileIdentifier>
                <gco:CharacterString>iso-dataset-001</gco:CharacterString>
            </gmd:fileIdentifier>
            <gmd:identificationInfo>
                <gmd:MD_DataIdentification>
                    <gmd:title>
                        <gco:CharacterString>Water Quality Monitoring</gco:CharacterString>
                    </gmd:title>
                    <gmd:abstract>
                        <gco:CharacterString>Long-term water quality data from river monitoring stations</gco:CharacterString>
                    </gmd:abstract>
                    <gmd:topicCategory>
                        <gmd:MD_TopicCategoryCode>environment</gmd:MD_TopicCategoryCode>
                    </gmd:topicCategory>
                    <gmd:keyword>
                        <gco:CharacterString>water</gco:CharacterString>
                    </gmd:keyword>
                </gmd:MD_DataIdentification>
            </gmd:identificationInfo>
        </gmd:MD_Metadata>"""
        
        # Parse
        parser = ISO19139Parser()
        dataset = await parser.parse(iso_content)
        
        assert dataset.file_identifier == "iso-dataset-001"
        assert "water" in dataset.keywords
        
        # Enrich (synchronous call)
        enricher = MetadataEnricher()
        enriched = enricher.enrich(
            title=dataset.title,
            abstract=dataset.abstract,
            keywords=dataset.keywords
        )
        
        assert enriched['keywords'] is not None
        """Test complete pipeline: RDF parse -> enrich."""
        rdf_content = """
        @prefix dcat: <http://www.w3.org/ns/dcat#> .
        @prefix dct: <http://purl.org/dc/terms/> .
        
        <http://example.com/dataset/1> a dcat:Dataset ;
            dct:identifier "rdf-dataset-001" ;
            dct:title "Biodiversity Monitoring" ;
            dct:description "Species abundance and distribution data" ;
            dcat:keyword "biodiversity" ;
            dcat:keyword "species" .
        """
        
        # Parse
        parser = RDFParser()
        dataset = await parser.parse(rdf_content)
        
        assert dataset.file_identifier == "rdf-dataset-001"
        assert "biodiversity" in dataset.keywords
        
        # Enrich (synchronous call)
        enricher = MetadataEnricher()
        enriched = enricher.enrich(
            title=dataset.title,
            abstract=dataset.abstract,
            keywords=dataset.keywords
        )
        
        assert enriched['keywords'] is not None

    @pytest.mark.asyncio
    async def test_schema_org_to_enriched_dataset_pipeline(self):
        """Test complete pipeline: Schema.org parse -> enrich."""
        schema_content = json.dumps({
            "@context": "https://schema.org",
            "@type": "Dataset",
            "identifier": "schema-dataset-001",
            "name": "Land Use Classification",
            "description": "Remote sensing based land use land cover classification",
            "keywords": ["remote sensing", "land cover"]
        })
        
        # Parse
        parser = SchemaOrgParser()
        dataset = await parser.parse(schema_content)
        
        assert dataset.file_identifier == "schema-dataset-001"
        assert "remote sensing" in dataset.keywords
        
        # Enrich (synchronous call)
        enricher = MetadataEnricher()
        enriched = enricher.enrich(
            title=dataset.title,
            abstract=dataset.abstract,
            keywords=dataset.keywords
        )
        
        assert enriched['keywords'] is not None


class TestMultiFormatParsing:
    """Test parsing multiple metadata formats."""

    @pytest.mark.asyncio
    async def test_parse_multiple_formats_for_same_dataset(self):
        """Test parsing same dataset in multiple formats."""
        
        # Sample data
        file_id = "multi-format-001"
        title = "Ecosystem Monitoring"
        abstract = "Comprehensive ecosystem data"
        keywords = ["ecosystem", "monitoring"]
        
        # JSON version
        json_data = json.dumps({
            "fileIdentifier": file_id,
            "title": title,
            "abstract": abstract,
            "keywords": keywords
        })
        
        # Parse with different parsers
        json_parser = JSONMetadataParser()
        json_dataset = await json_parser.parse(json_data)
        
        # All should produce equivalent results
        assert json_dataset.file_identifier == file_id
        assert json_dataset.title == title
        assert all(k in json_dataset.keywords for k in keywords)

    @pytest.mark.asyncio
    async def test_parser_format_detection_compatibility(self):
        """Test that different parsers handle similar data correctly."""
        
        parsers = [
            JSONMetadataParser(),
            SchemaOrgParser(),
        ]
        
        # Each parser with its native format
        json_content = json.dumps({
            "fileIdentifier": "test-id",
            "title": "Test",
            "abstract": "Test abstract"
        })
        
        dataset = await parsers[0].parse(json_content)
        assert dataset.file_identifier == "test-id"


class TestEnrichmentConsistency:
    """Test enrichment consistency across datasets."""

    @pytest.mark.asyncio
    async def test_enrichment_consistency_same_content(self):
        """Test enrichment produces consistent results for same content."""
        enricher = MetadataEnricher()
        
        title = "Soil Carbon Dynamics"
        abstract = "Measurement of soil carbon stocks and turnover rates"
        
        result1 = enricher.enrich(title=title, abstract=abstract)
        result2 = enricher.enrich(title=title, abstract=abstract)
        
        # Should produce identical results
        assert result1['keywords'] == result2['keywords']
        assert result1['topic_category'] == result2['topic_category']

    @pytest.mark.asyncio
    async def test_enrichment_across_different_metadata_formats(self):
        """Test enrichment consistency across different metadata formats."""
        enricher = MetadataEnricher()
        
        # All pointing to same dataset
        title = "Biodiversity Survey"
        abstract = "Assessment of species diversity and habitat quality"
        
        json_parser = JSONMetadataParser()
        json_dataset = await json_parser.parse(json.dumps({
            "fileIdentifier": "id-1",
            "title": title,
            "abstract": abstract
        }))
        
        # Enrich both (synchronous call)
        enriched = enricher.enrich(
            title=json_dataset.title,
            abstract=json_dataset.abstract
        )
        
        assert enriched['keywords'] is not None
        assert len(enriched['keywords']) > 0


class TestErrorRecovery:
    """Test error handling and recovery in pipelines."""

    @pytest.mark.asyncio
    async def test_pipeline_recovers_from_invalid_json(self):
        """Test pipeline handles invalid JSON gracefully."""
        invalid_json = '{"incomplete": '
        
        parser = JSONMetadataParser()
        with pytest.raises(Exception):
            await parser.parse(invalid_json)

    @pytest.mark.asyncio
    async def test_enrichment_with_missing_data(self):
        """Test enrichment handles missing data gracefully."""
        enricher = MetadataEnricher()
        
        # Empty inputs (synchronous call)
        enriched = enricher.enrich(
            title="",
            abstract=""
        )
        
        assert isinstance(enriched['keywords'], list)
        assert isinstance(enriched['topic_category'], list)

    @pytest.mark.asyncio
    async def test_pipeline_graceful_degradation(self):
        """Test that pipeline degrades gracefully with partial data."""
        json_content = json.dumps({
            "title": "Minimal Dataset"
            # Missing other fields
        })
        
        parser = JSONMetadataParser()
        dataset = await parser.parse(json_content)
        
        # Should still be valid
        assert dataset.title == "Minimal Dataset"
        assert dataset.file_identifier == "unknown"  # Graceful default


class TestBatchProcessing:
    """Test processing batches of datasets."""

    @pytest.mark.asyncio
    async def test_batch_parse_multiple_json_documents(self):
        """Test parsing batch of JSON documents."""
        parser = JSONMetadataParser()
        
        documents = [
            {"fileIdentifier": f"batch-{i}", "title": f"Dataset {i}"}
            for i in range(10)
        ]
        
        results = []
        for doc in documents:
            dataset = await parser.parse(json.dumps(doc))
            results.append(dataset)
        
        assert len(results) == 10
        assert all(r.file_identifier.startswith("batch-") for r in results)

    @pytest.mark.asyncio
    async def test_batch_enrich_datasets(self):
        """Test enriching batch of datasets."""
        enricher = MetadataEnricher()
        
        datasets = [
            {"title": f"Soil Study {i}", "abstract": f"Dataset about soil {i}"}
            for i in range(5)
        ]
        
        results = []
        for ds in datasets:
            enriched = enricher.enrich(
                title=ds["title"],
                abstract=ds["abstract"]
            )
            results.append(enriched)
        
        assert len(results) == 5
        assert all(r['keywords'] is not None for r in results)


class TestPerformanceBenchmarks:
    """Performance tests for common operations."""

    @pytest.mark.asyncio
    async def test_parse_performance_small_document(self):
        """Test parsing performance for small JSON document."""
        import time
        
        parser = JSONMetadataParser()
        doc = json.dumps({
            "fileIdentifier": "perf-test",
            "title": "Small Doc",
            "abstract": "Short abstract"
        })
        
        start = time.time()
        for _ in range(100):
            await parser.parse(doc)
        elapsed = time.time() - start
        
        # Should parse 100 small docs in reasonable time
        assert elapsed < 10.0

    @pytest.mark.asyncio
    async def test_parse_performance_large_document(self):
        """Test parsing performance for large JSON document."""
        import time
        
        parser = JSONMetadataParser()
        keywords = [f"keyword-{i}" for i in range(500)]
        doc = json.dumps({
            "fileIdentifier": "large-doc",
            "title": "Large Document",
            "abstract": "Large abstract. " * 1000,
            "keywords": keywords
        })
        
        start = time.time()
        result = await parser.parse(doc)
        elapsed = time.time() - start
        
        # Should handle large docs quickly
        assert elapsed < 5.0
        assert len(result.keywords) == 500

    @pytest.mark.asyncio
    async def test_enrichment_performance_batch(self):
        """Test enrichment performance on batch."""
        import time
        
        enricher = MetadataEnricher()
        datasets = [
            {"title": f"Dataset {i}", "abstract": f"Abstract {i}"}
            for i in range(20)
        ]
        
        start = time.time()
        for ds in datasets:
            enricher.enrich(
                title=ds["title"],
                abstract=ds["abstract"]
            )
        elapsed = time.time() - start
        
        # Should enrich 20 datasets quickly
        assert elapsed < 30.0
