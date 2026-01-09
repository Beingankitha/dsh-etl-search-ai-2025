import asyncio
import logging
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

# Import from implementation files (internal to etl module)
from .etl_error_handler import ETLErrorHandler, RetryConfig, RetryStrategy
from .etl_optimizer import (
    AdaptiveBatchProcessor,
    ConcurrencyOptimizer,
    CachingBatchProcessor,
)
from src.infrastructure.metadata_cache import MetadataCache, CachedMetadataFetcher
from src.services.extractors import DatasetFileExtractor

# Import observability module
from src.services.observability import (
    get_tracer,
    trace_async_method,
    with_span,
    set_span_attributes,
    add_span_event,
    get_current_span,
)

# Import from other service modules via their public APIs
from src.services.extractors import CEHExtractor
from src.services.parsers import (
    ISO19139Parser,
    JSONMetadataParser,
    RDFParser,
    SchemaOrgParser,
)
from src.services.supporting_documents import (
    SupportingDocDiscoverer,
    SupportingDocDownloader,
)
from src.services.document_extraction import (
    DocumentExtractor,
    UniversalDocumentExtractor,
)
from src.repositories import UnitOfWork
from src.models import (
    DatasetEntity,
    MetadataDocument,
    DataFile,
    SupportingDocument
)
from src.config import settings
from src.logging_config import get_logger
from rich.console import Console
from rich.text import Text

logger = get_logger(__name__)
tracer = get_tracer(__name__)
console = Console()


class ETLService:
    """
    Orchestrates ETL pipeline for dataset extraction, transformation, and loading.
    
    Three-phase pipeline:
    1. EXTRACT: Fetch dataset identifiers and metadata documents from CEH
    2. TRANSFORM: Parse metadata into Dataset models and related entities
    3. LOAD: Upsert datasets into database
    """
    
    def __init__(
        self,
        identifiers_file: Path,
        unit_of_work: UnitOfWork,
        batch_size: int = 10,
        max_concurrent_downloads: int = 5,
        dry_run: bool = False,
        enable_supporting_docs: bool = True,
        enable_data_files: bool = True,
        enable_adaptive_batching: bool = True,
        enable_error_recovery: bool = True,
        verbose: bool = False
    ):
        """
        Initialize ETL Service with support for error recovery and optimization.
        
        Args:
            identifiers_file: Path to file with dataset identifiers (one per line)
            unit_of_work: UnitOfWork instance for database transactions
            batch_size: Number of datasets to process per batch
            max_concurrent_downloads: Max concurrent HTTP requests
            dry_run: If True, validate without committing to database
            enable_supporting_docs: Whether to process supporting documents
            enable_data_files: Whether to extract and load dataset data files
            enable_adaptive_batching: Whether to use adaptive batch sizing
            enable_error_recovery: Whether to use error recovery mechanisms
            verbose: Whether to enable verbose output to console
        """
        self.identifiers_file = identifiers_file
        self.unit_of_work = unit_of_work
        self.batch_size = batch_size
        self.max_concurrent_downloads = max_concurrent_downloads
        self.dry_run = dry_run
        self.enable_supporting_docs = enable_supporting_docs
        self.enable_data_files = enable_data_files
        self.verbose = verbose
        
        # Initialize metadata caching system
        cache_dir = Path("./data/metadata_cache")
        self.metadata_cache = MetadataCache(
            cache_dir=cache_dir,
            enable_caching=True,
            cache_expiration_days=30
        )
        
        # Initialize services
        self.ceh_extractor = CEHExtractor(max_concurrent=max_concurrent_downloads)
        
        # Wrap CEH extractor with caching
        self.cached_fetcher = CachedMetadataFetcher(
            cache=self.metadata_cache,
            ceh_extractor=self.ceh_extractor
        )
        self.iso_parser = ISO19139Parser()
        self.json_parser = JSONMetadataParser()
        self.rdf_parser = RDFParser()
        self.schema_org_parser = SchemaOrgParser()
        # Initialize supporting document processing components
        if self.enable_supporting_docs:
            self.doc_discoverer = SupportingDocDiscoverer()
            from src.infrastructure.http_client import AsyncHTTPClient
            self.http_client = AsyncHTTPClient(max_concurrent=max_concurrent_downloads)
            # Convert cache_dir string to Path object
            cache_dir_path = Path(settings.supporting_docs_cache_dir)
            self.doc_downloader = SupportingDocDownloader(
                http_client=self.http_client,
                cache_dir=cache_dir_path  # Pass Path object, not string
            )
            self.text_extractor = UniversalDocumentExtractor()
        
        # Initialize data file extraction
        if self.enable_data_files:
            from src.services.extractors import DatasetFileExtractor
            from src.infrastructure.http_client import AsyncHTTPClient
            # Create or reuse HTTP client
            if not self.enable_supporting_docs:
                self.http_client = AsyncHTTPClient(max_concurrent=max_concurrent_downloads)
            self.dataset_file_extractor = DatasetFileExtractor(
                http_client=self.http_client,
                file_repository=None,  # Will be set per-call with active unit of work
                max_concurrent=max_concurrent_downloads
            )
            self.unit_of_work_ref = unit_of_work  # Store reference for later use
        
        # Error handling and recovery
        self.error_handler = ETLErrorHandler(
            retry_config=RetryConfig(
                max_retries=3,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF
            )
        ) if enable_error_recovery else None
        
        # Optimization
        self.batch_processor = AdaptiveBatchProcessor(
            initial_batch_size=batch_size,
            enable_adaptive=enable_adaptive_batching
        ) if enable_adaptive_batching else None
        
        self.concurrency_optimizer = ConcurrencyOptimizer(
            initial_concurrency=max_concurrent_downloads
        )
        
        self.cache_processor = CachingBatchProcessor(enable_tracking=True)
        
        # Pipeline tracking
        self.report: Dict[str, Any] = {
            'total_identifiers': 0,
            'successful': 0,
            'failed': 0,
            'metadata_extracted': 0,
            'supporting_docs_found': 0,
            'supporting_docs_downloaded': 0,
            'text_extracted': 0,
            'data_files_extracted': 0,
            'data_files_stored': 0,
            'errors': [],
            'duration': 0.0,
            'cache_stats': {},
            'metadata_cache_stats': {},
            'error_recovery_stats': {}
        }
    
    def _print_with_identifier(self, identifier: str, message: str, style: str = "green"):
        """
        Print a message with identifier prefix, avoiding Rich markup interpretation of brackets.
        
        Args:
            identifier: Dataset identifier
            message: Message to print (can include Rich markup)
            style: Style to apply to the message
        """
        text = Text(f"[{identifier}] ", style=None)
        text.append(message, style=style)
        console.print(text)
    
    @trace_async_method(attributes={"module": "etl", "phase": "pipeline"})
    async def run_pipeline(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute complete ETL pipeline with error handling and optimization.
        """
        start_time = time.time()
        span = get_current_span()
        
        # Set span attributes for root trace
        span.set_attribute("batch_size", self.batch_size)
        span.set_attribute("max_concurrent", self.max_concurrent_downloads)
        span.set_attribute("dry_run", self.dry_run)
        span.set_attribute("enable_supporting_docs", self.enable_supporting_docs)
        span.set_attribute("enable_data_files", self.enable_data_files)
        
        try:
            # Initialize HTTP client if needed for supporting docs or data files
            if (self.enable_supporting_docs or self.enable_data_files) and hasattr(self, 'http_client'):
                async with self.http_client:
                    return await self._run_pipeline_internal(limit, start_time)
            else:
                return await self._run_pipeline_internal(limit, start_time)
                
        except Exception as e:
            logger.exception("ETL pipeline failed")
            self.report['duration'] = time.time() - start_time
            raise
        
        finally:
            # ✅ Cleanup resources
            logger.debug("Cleaning up resources...")
            
            try:
                if hasattr(self, 'ceh_extractor') and self.ceh_extractor:
                    await self.ceh_extractor.close()
                    logger.debug("✓ CEH extractor closed")
            except Exception as e:
                logger.warning(f"Error closing CEH extractor: {e}")
            
            try:
                if self.enable_supporting_docs and hasattr(self, 'http_client') and self.http_client:
                    await self.http_client.close()
                    logger.debug("✓ HTTP client closed")
            except Exception as e:
                logger.warning(f"Error closing HTTP client: {e}")
            
            try:
                if self.enable_supporting_docs and hasattr(self, 'doc_downloader'):
                    if hasattr(self.doc_downloader, 'close'):
                        await self.doc_downloader.close()
                        logger.debug("✓ Document downloader closed")
            except Exception as e:
                logger.warning(f"Error closing document downloader: {e}")
            
            logger.debug("✓ Cleanup complete")

    async def _run_pipeline_internal(self, limit: Optional[int], start_time: float) -> Dict[str, Any]:
        """
        Internal pipeline execution with initialized resources.
        """
        # Phase 1: Read identifiers
        identifiers = self._read_identifiers(limit)
        self.report['total_identifiers'] = len(identifiers)
        
        logger.info(f"Loaded {len(identifiers)} dataset identifiers from {self.identifiers_file}")
        
        # Phase 2: Extract metadata for all identifiers
        metadata_docs = await self._extract_phase(identifiers)
        logger.info(f"Extracted metadata for {len(metadata_docs)} datasets")
        
        # Phase 3: Transform and load
        await self._transform_and_load_phase(metadata_docs)
        
        # Add optimization stats to report
        if self.cache_processor:
            self.report['cache_stats'] = self.cache_processor.get_cache_stats()
        
        # Add metadata cache stats
        self.report['metadata_cache_stats'] = self.metadata_cache.get_stats()
        
        if self.error_handler:
            self.report['error_recovery_stats'] = self.error_handler.get_error_report()
        
        self.report['duration'] = time.time() - start_time
        return self.report
    
    def _read_identifiers(self, limit: Optional[int] = None) -> List[str]:
        """
        Read dataset identifiers from file.
        
        Args:
            limit: Maximum number of identifiers to read
            
        Returns:
            List of dataset identifiers
        """
        identifiers = []
        
        try:
            with open(self.identifiers_file, 'r') as f:
                for line in f:
                    identifier = line.strip()
                    if identifier and not identifier.startswith('#'):  # Skip empty lines and comments
                        identifiers.append(identifier)
                        if limit and len(identifiers) >= limit:
                            break
            
            logger.info(f"Read {len(identifiers)} identifiers from {self.identifiers_file}")
            return identifiers
            
        except Exception as e:
            logger.error(f"Failed to read identifiers file: {e}")
            raise
    
    @trace_async_method(attributes={"phase": "extract"})
    async def _extract_phase(self, identifiers: List[str]) -> Dict[str, Dict[str, str]]:
        """
        EXTRACT PHASE: Fetch metadata documents in all 4 formats from CEH.
        
        Args:
            identifiers: List of dataset identifiers
            
        Returns:
            Dictionary mapping identifier → {format: content}
        """
        span = get_current_span()
        span.set_attribute("identifiers_count", len(identifiers))
        
        logger.info(f"Starting EXTRACT phase for {len(identifiers)} datasets")
        
        metadata_docs = {}
        successful = 0
        
        # Process in batches
        for i in range(0, len(identifiers), self.batch_size):
            batch = identifiers[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(identifiers) + self.batch_size - 1) // self.batch_size
            
            batch_span_attrs = {
                "batch_number": batch_num,
                "batch_size": len(batch),
                "total_batches": total_batches
            }
            add_span_event(span, "batch_started", batch_span_attrs)
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} datasets)")
            
            # Fetch metadata for batch concurrently
            batch_results = await asyncio.gather(
                *[self._fetch_metadata_for_identifier(identifier) for identifier in batch],
                return_exceptions=True
            )
            
            for identifier, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    # self._record_error(identifier, f"Extract phase failed: {str(result)}")
                    self._record_error(
                        identifier=identifier,
                        operation="extract_phase",
                        message=f"Extract phase failed: {str(result)}",
                        error_type=type(result).__name__ if isinstance(result, Exception) else "Unknown"
                    )
                    logger.error(f"Failed to extract metadata for {identifier}: {result}")
                else:
                    metadata_docs[identifier] = result
                    successful += 1        
            
        self.report['metadata_extracted'] = successful
        logger.info(f"EXTRACT phase complete: {self.report['metadata_extracted']}/{len(identifiers)} successful")
        return metadata_docs
    
    # async def _fetch_metadata_for_identifier(self, identifier: str) -> Dict[str, str]:
    #     """
    #     Fetch metadata in all 4 formats for a single identifier.
        
    #     Args:
    #         identifier: Dataset identifier
            
    #     Returns:
    #         Dictionary with keys: 'xml', 'json', 'rdf', 'schema_org'
    #     """
    #     try:
    #         # Fetch all formats concurrently
    #         xml_content, json_content, rdf_content, schema_org_content = await asyncio.gather(
    #             self.ceh_extractor.fetch_dataset_xml(identifier),
    #             self.ceh_extractor.fetch_dataset_json(identifier),
    #             self.ceh_extractor.fetch_dataset_rdf(identifier),
    #             self.ceh_extractor.fetch_dataset_schema_org(identifier),
    #             return_exceptions=True
    #         )
            
    #         return {
    #             'identifier': identifier,
    #             'xml': xml_content if not isinstance(xml_content, Exception) else None,
    #             'json': json_content if not isinstance(json_content, Exception) else None,
    #             'rdf': rdf_content if not isinstance(rdf_content, Exception) else None,
    #             'schema_org': schema_org_content if not isinstance(schema_org_content, Exception) else None
    #         }
            
    #     except Exception as e:
    #         logger.error(f"Failed to fetch metadata for {identifier}: {e}")
    #         raise
    
    async def _fetch_metadata_for_identifier(self, identifier: str) -> Dict[str, str]:
        """
        Fetch metadata in all 4 formats for a single identifier with caching.
        
        Uses CachedMetadataFetcher to automatically cache and retrieve metadata,
        avoiding repeated downloads of the same dataset formats.
        """
        try:
            logger.debug(f"[{identifier}] Fetching all metadata formats (with caching)")
            
            # Reset cache status tracking for this identifier
            self.cached_fetcher.clear_fetch_cache_status()
            
            # Fetch all formats concurrently using CACHED fetcher
            xml_content, json_content, rdf_content, schema_org_content = await asyncio.gather(
                self.cached_fetcher.fetch_xml(identifier),
                self.cached_fetcher.fetch_json(identifier),
                self.cached_fetcher.fetch_rdf(identifier),
                self.cached_fetcher.fetch_schema_org(identifier),
                return_exceptions=True
            )
            
            # Note: We don't log individual format success here - we only log
            # the format that's actually used during the TRANSFORM phase (in _parse_metadata_with_fallback)
            # This avoids showing "success for all formats" when only one is actually used
            
            # Capture cache status for later use (before it gets overwritten by next fetch)
            cache_status_snapshot = dict(self.cached_fetcher.fetch_cache_status)
            
            return {
                'identifier': identifier,
                'xml': xml_content if not isinstance(xml_content, Exception) else None,
                'json': json_content if not isinstance(json_content, Exception) else None,
                'rdf': rdf_content if not isinstance(rdf_content, Exception) else None,
                'schema_org': schema_org_content if not isinstance(schema_org_content, Exception) else None,
                '_cache_status': cache_status_snapshot  # Store cache status for this identifier
            }
            
        except Exception as e:
            logger.error(f"[{identifier}] Failed to fetch metadata: {e}")
            raise

    async def _transform_and_load_phase(self, metadata_docs: Dict[str, Dict[str, str]]):
        """
        TRANSFORM & LOAD PHASES: Parse metadata and upsert to database.
        
        Args:
            metadata_docs: Dictionary mapping identifier → {format: content}
        """
        logger.info(f"Starting TRANSFORM & LOAD phases for {len(metadata_docs)} datasets")
        
        identifiers = list(metadata_docs.keys())
        
        # Process in batches
        for i in range(0, len(identifiers), self.batch_size):
            batch = identifiers[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(identifiers) + self.batch_size - 1) // self.batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} datasets)")
            
            # Process each dataset in batch
            for identifier in batch:
                try:
                    await self._process_single_dataset(identifier, metadata_docs[identifier])
                    self.report['successful'] += 1
                    logger.info(f"[{identifier}] ✓ Successfully processed")
                    
                except Exception as e:
                    self.report['failed'] += 1
                    logger.error(f"[{identifier}] Transform & Load failed: {e}")
                    self._record_error(identifier, "transform_load", str(e), "etl_error")
                    continue
        
        logger.info(f"TRANSFORM & LOAD complete: {self.report['successful']} successful, {self.report['failed']} failed")
    
    async def _process_single_dataset(self, identifier: str, metadata_docs: Dict[str, str]):
        """
        Process a single dataset: parse metadata and load to database.
        
        Args:
            identifier: Dataset identifier
            metadata_docs: Dictionary with 'xml', 'json', 'rdf', 'schema_org' content and '_cache_status'
        """
        try:
            logger.debug(f"Processing dataset {identifier}")
            
            # Parse metadata with fallback strategy
            dataset_model = await self._parse_metadata_with_fallback(identifier, metadata_docs)
            
            if not dataset_model:
                raise ValueError(f"Could not parse metadata in any format for {identifier}")
            
            # Get source format from the parsed dataset
            source_format = getattr(dataset_model, 'source_format', 'unknown')
            
            # Get cache status for the format that was used (from metadata_docs snapshot)
            cache_status_snapshot = metadata_docs.get('_cache_status', {})
            cache_status = cache_status_snapshot.get(source_format, 'unknown')
            cache_text = "(cached)" if cache_status == 'cached' else "(cache miss)"
            
            # Verbose output: Show fetch status with format and cache info
            if self.verbose:
                # Format the format name for display
                if source_format == 'schema_org':
                    format_display = 'Schema.org'
                else:
                    format_display = source_format.upper()
                
                # Show fetch status with cache info
                self._print_with_identifier(identifier, f"✓ {format_display} fetch SUCCESS {cache_text}")
                self._print_with_identifier(identifier, f"✓ Parsed: \"{dataset_model.title}\"")
            
            # Load to database
            await self._load_dataset_to_database(identifier, dataset_model, metadata_docs)
            
            # Track supporting docs
            num_supporting_docs = 0
            # Process supporting documents
            if self.enable_supporting_docs:
                num_supporting_docs = await self._process_supporting_documents(identifier, metadata_docs)
            
            # Track data files
            num_data_files = 0
            # Process data files
            if self.enable_data_files:
                num_data_files = await self._process_data_files(identifier, metadata_docs)

            logger.info(f"[{identifier}] ✓ Dataset processed successfully")
            if self.verbose:
                # Print blank line between datasets for readability
                console.print()
            # self.report['successful'] += 1 #(handled in _transform_and_load_phase)

        except Exception as e:
            logger.error(f"[{identifier}] Failed to process dataset: {e}")
            if self.verbose:
                self._print_with_identifier(identifier, f"✗ Processing failed: {e}", style="red")
            # Don't record error here - let _transform_and_load_phase handle it
            raise

    async def _process_supporting_documents(self, identifier: str, metadata_docs: Dict[str, str]):
        """
        Discover, download, and extract text from supporting documents.
        
        Args:
            identifier: Dataset identifier
            metadata_docs: Metadata documents dictionary with 'xml', 'json', 'rdf', 'schema_org'
            
        Returns:
            Number of supporting documents processed
        """
        try:
            # ✅ FIXED: Call unified discover() method with available formats
            doc_urls = await self.doc_discoverer.discover(
                identifier=identifier,
                json_content=metadata_docs.get('json'),
                xml_content=metadata_docs.get('xml'),
                rdf_content=metadata_docs.get('rdf')
            )
            
            if not doc_urls:
                logger.debug(f"[{identifier}] No supporting documents found")
                return 0
            
            # FIXED: Deduplicate URLs before downloading
            unique_doc_urls = list(dict.fromkeys(doc_urls))  # Preserves order while removing duplicates
            
            num_docs = len(unique_doc_urls)
            self.report['supporting_docs_found'] += num_docs
            logger.info(f"[{identifier}] Found {num_docs} supporting documents")
            if self.verbose:
                self._print_with_identifier(identifier, f"✓ Found {num_docs} supporting docs")
            
            # Download documents
            try:
                downloaded_items = await self.doc_downloader.download_batch(unique_doc_urls)
                
                if not downloaded_items:
                    logger.debug(f"[{identifier}] No documents were downloaded")
                    return 0
                
                num_downloaded = len(downloaded_items)
                self.report['supporting_docs_downloaded'] += num_downloaded
                logger.info(f"[{identifier}] Downloaded {num_downloaded} documents")
                if self.verbose:
                    self._print_with_identifier(identifier, f"✓ Downloaded {num_downloaded} docs")
                
                # Extract text from each document
                text_count = 0
                
                # FIXED: Use single transaction for all supporting docs in this dataset
                async with self.unit_of_work:
                    dataset = self.unit_of_work.datasets.get_by_file_identifier(identifier)
                    if not dataset:
                        logger.warning(f"[{identifier}] Dataset not found for supporting docs")
                        return 0
                    
                    for url, doc_path in downloaded_items:
                        try:
                            # ✅ FIXED: Use correct method name 'extract' not 'extract_text'
                            text_content = await self.text_extractor.extract(Path(doc_path))
                            
                            if text_content and not self.dry_run:
                                # Store supporting document with correct foreign key
                                supporting_doc = SupportingDocument(
                                    dataset_id=dataset.id,
                                    document_url=url,
                                    title=Path(doc_path).name,
                                    file_extension=Path(doc_path).suffix,
                                    downloaded_path=str(doc_path),
                                    text_content=text_content,
                                    created_at=datetime.now(timezone.utc).isoformat()
                                )
                                self.unit_of_work.supporting_documents.insert(supporting_doc)
                                logger.debug(f"[{identifier}] Stored supporting document: {Path(doc_path).name}")
                            
                            text_count += 1
                            self.report['text_extracted'] += 1
                            
                        except Exception as e:
                            logger.warning(f"[{identifier}] Failed to extract text from {doc_path}: {e}")
                            continue
                    
                    # FIXED: Single commit for all documents
                    self.unit_of_work.commit()
                
                if self.verbose and text_count > 0:
                    self._print_with_identifier(identifier, f"✓ Extracted text from {text_count} docs")
                
                return text_count
            
            except Exception as e:
                logger.warning(f"[{identifier}] Failed to download supporting documents: {e}")
                return 0
        
        except Exception as e:
            logger.debug(f"[{identifier}] Supporting document processing failed (non-fatal): {e}")
            # Don't fail the entire pipeline if supporting docs fail
            return 0
    
    async def _process_data_files(self, identifier: str, metadata_docs: Dict[str, str]):
        """
        Discover, download, extract, and load dataset data files.
        
        Args:
            identifier: Dataset identifier
            metadata_docs: Metadata documents dictionary with 'xml', 'json', 'rdf', 'schema_org'
            
        Returns:
            Number of data files stored
        """
        try:
            # Get dataset ID and set up repository with active unit of work
            async with self.unit_of_work:
                dataset = self.unit_of_work.datasets.get_by_file_identifier(identifier)
                if not dataset:
                    logger.warning(f"[{identifier}] Dataset not found, skipping data files")
                    return 0
                dataset_id = dataset.id
                
                # Set the file repository on the extractor to use the active connection
                self.dataset_file_extractor.file_repository = self.unit_of_work.data_files
            
            # Extract and load data files (outside context, but repository already set)
            stats = await self.dataset_file_extractor.extract_and_load(
                identifier=identifier,
                dataset_id=dataset_id,
                metadata_docs=metadata_docs,
                dry_run=self.dry_run
            )
            
            # Update report
            files_found = stats.get('files_extracted', 0)
            files_stored = stats.get('files_stored', 0)
            
            self.report['data_files_extracted'] += files_found
            self.report['data_files_stored'] += files_stored
            
            if self.verbose and files_found > 0:
                self._print_with_identifier(identifier, f"✓ Found {files_found} data files")
            
            if self.verbose and files_stored > 0:
                self._print_with_identifier(identifier, f"✓ Stored {files_stored} files")
            
            if files_stored > 0:
                logger.info(f"[{identifier}] Extracted and stored {files_stored} data files")
            
            return files_stored
        
        except Exception as e:
            logger.debug(f"[{identifier}] Data file processing failed (non-fatal): {e}")
            # Don't fail the entire pipeline if data files fail
            return 0
    
    async def _parse_metadata_with_fallback(
        self,
        identifier: str,
        metadata_docs: Dict[str, str]
    ) -> Optional[DatasetEntity]:
        """
        Parse metadata with intelligent fallback across formats.
        
        Tries formats in order: XML → JSON → RDF → Schema.org
        
        Priority:
        1. XML (ISO 19139)
        2. JSON
        3. RDF
        4. Schema.org

        Args:
            identifier: Dataset identifier
            metadata_docs: Dictionary with format keys and content values
            
        Returns:
            Parsed Dataset model or None if all formats fail
        """
        parsers = [
            ('xml', self.iso_parser.parse),
            ('json', self.json_parser.parse),
            ('rdf', self.rdf_parser.parse),
            ('schema_org', self.schema_org_parser.parse),
        ]
        
        for format_name, parser_func in parsers:
            content = metadata_docs.get(format_name)
            
            if not content:
                continue
            
            try:
                logger.debug(f"[{identifier}] Attempting to parse {format_name}")
                dataset = await parser_func(content)
                dataset.file_identifier = identifier
                dataset.source_format = format_name  # ✅ Track which format was used
                logger.info(f"[{identifier}] Successfully parsed {format_name}")
                return dataset
                
            except Exception as e:
                logger.warning(f"[{identifier}] Failed to parse {format_name}: {e}")
                continue
        
        logger.error(f"[{identifier}] Failed to parse metadata in any format")
        return None
    
    async def _load_dataset_to_database(
        self,
        identifier: str,
        dataset: DatasetEntity,
        metadata_docs: Dict[str, str]
    ):
        """
        Load dataset and metadata documents to database.
        
        Args:
            identifier: Dataset identifier
            dataset: Parsed Dataset model
            metadata_docs: Dictionary with format keys and content values
        """
        if self.dry_run:
            logger.debug(f"[{identifier}] Dry-run mode: skipping database write")
            return
        
        async with self.unit_of_work:
            # Upsert dataset and get the database record with ID
            upserted_dataset = self.unit_of_work.datasets.upsert_by_identifier(dataset)
            logger.debug(f"[{identifier}] Dataset upserted with ID: {upserted_dataset.id}")
            
            # Store metadata documents (use database ID, not file identifier)
            for format_name, content in metadata_docs.items():
                if format_name.startswith('_') or format_name == 'identifier' or not content:
                    continue
                
                try:
                    # Check if metadata document already exists for this dataset and format
                    existing_metadata = self.unit_of_work.metadata_documents.get_by_dataset_and_type(
                        upserted_dataset.id, format_name
                    )
                    
                    metadata_doc = MetadataDocument(
                        dataset_id=upserted_dataset.id,
                        document_type=format_name,
                        original_content=content.encode('utf-8') if isinstance(content, str) else content,
                        mime_type=self._get_mime_type(format_name),
                        created_at=datetime.now(timezone.utc).isoformat()
                    )
                    
                    # Insert or update
                    if existing_metadata:
                        # Update existing metadata document
                        self.unit_of_work.metadata_documents.update(metadata_doc, existing_metadata.id)
                        logger.debug(f"[{identifier}] Updated {format_name} metadata document (ID: {existing_metadata.id})")
                    else:
                        # Insert new metadata document
                        self.unit_of_work.metadata_documents.insert(metadata_doc)
                        logger.debug(f"[{identifier}] Inserted new {format_name} metadata document")
                    
                except Exception as e:
                    logger.warning(f"[{identifier}] Failed to store {format_name} metadata: {e}")
            
            self.unit_of_work.commit()
            logger.info(f"[{identifier}] Dataset and metadata committed to database")

    def _get_mime_type(self, format_name: str) -> str:
        """Get MIME type for format."""
        mime_types = {
            'xml': 'application/xml',
            'json': 'application/json',
            'rdf': 'application/rdf+xml',
            'schema_org': 'application/ld+json',
        }
        return mime_types.get(format_name, 'text/plain')

    def _record_error(
        self,
        identifier: str,
        operation: str,
        message: str,
        error_type: str
    ):
        """
        Record error in report.
        
        Args:
            identifier: Dataset identifier
            operation: Operation that failed
            message: Error message
            error_type: Type of error
        """
        self.report['errors'].append({
            'identifier': identifier,
            'operation': operation,
            'message': message,
            'error_type': error_type,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        logger.debug(f"[{identifier}] Error recorded: {operation} - {message}")