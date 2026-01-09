## Table of Contents

1. [Project Structure & Architecture](#project-structure--architecture)
2. [Environment & Dependencies Setup](#environment--dependencies-setup)
3. [Configuration Management](#configuration-management)
4. [ETL Pipeline Implementation](#etl-pipeline-implementation)
5. [Database & ORM Setup](#database--orm-setup)
6. [Vector Store & Embeddings](#vector-store--embeddings)
7. [FastAPI Application Setup](#fastapi-application-setup)
8. [API Routes & Error Handling](#api-routes--error-handling)
9. [Distributed Tracing & Observability](#distributed-tracing--observability)
10. [Testing Strategy](#testing-strategy)

---

## Project Structure & Architecture

### Q: How should I organize a Python backend that handles ETL, API serving, embeddings, and chat functionality?

**A:** For a complex system like this, you want clear separation of concerns. Here's the recommended structure:

```
backend/
├── src/
│   ├── __init__.py
│   ├── api/                          # API layer
│   │   ├── app.py                    # FastAPI app factory
│   │   ├── exceptions.py             # Custom exceptions
│   │   ├── middleware/               # Cross-cutting concerns
│   │   │   ├── logging.py
│   │   │   └── error_handler.py
│   │   └── routes/                   # Domain-specific routers
│   │       ├── search.py
│   │       ├── datasets.py
│   │       ├── chat.py
│   │       └── health.py
│   ├── services/                     # Business logic layer
│   │   ├── etl/                      # Extract-Transform-Load
│   │   │   ├── coordinator.py
│   │   │   └── metadata_extractor.py
│   │   ├── search/                   # Semantic search
│   │   │   └── search_service.py
│   │   ├── chat/                     # Chat with RAG
│   │   │   └── chat_service.py
│   │   ├── embeddings/               # Vector generation
│   │   │   └── embedding_service.py
│   │   └── observability/            # Tracing & logging
│   │       └── tracing_config.py
│   ├── repositories/                 # Data access layer
│   │   ├── base_repository.py
│   │   ├── dataset_repository.py
│   │   └── metadata_repository.py
│   ├── models/                       # Data models
│   │   ├── schemas.py                # Pydantic request/response schemas
│   │   └── entities.py               # Domain entities
│   ├── infrastructure/               # Infrastructure & external services
│   │   ├── database.py
│   │   ├── vector_store.py
│   │   └── http_client.py
│   ├── config.py                     # Settings & configuration
│   └── logging_config.py             # Logging setup
├── main.py                           # Entry point
├── cli_main.py                       # CLI entry point
├── pyproject.toml                    # Dependencies
└── tests/                            # Test suite
    ├── unit/
    ├── integration/
    └── e2e/
```

**Why this structure?**

- **Separation of Concerns**: Each layer (API, services, repositories) has a single responsibility
- **Testability**: Repositories and services can be mocked independently
- **Scalability**: Easy to add new routes, services, or extractors
- **Maintainability**: Clear dependencies flow downward (API → Services → Repositories)
- **Observability**: Centralized logging and tracing configuration

---

## Environment & Dependencies Setup

### Q: What's the best way to manage Python dependencies and set up the development environment?

**A:** Use `pyproject.toml` with modern Python packaging standards. Here's what you need:

```toml
[project]
name = "dsh-etl-search-ai"
version = "0.1.0"
description = "CEH Dataset Discovery System with Semantic Search and AI Chat"
requires-python = ">=3.11"
dependencies = [
    # Web Framework
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    
    # Data Validation
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
    
    # HTTP & Networking
    "httpx>=0.28.0",        # Async HTTP client
    
    # Vector Store & Embeddings
    "chromadb>=0.5.0",
    "sentence-transformers>=3.3.0",
    "numpy>=1.24.0",
    
    # LLM & Chat
    "ollama>=0.4.0",
    
    # CLI
    "typer>=0.9.0",
    "click>=8.1.0",
    
    # Configuration
    "python-dotenv>=1.0.0",
    
    # Parsing & Document Processing
    "lxml>=5.3.0",           # XML parsing
    "xmltodict>=0.13.0",     # XML to dict conversion
    "requests>=2.31.0",      # HTTP requests (for CEH API)
    "rdflib>=6.3.0",         # RDF/RDF-S parsing
    "pypdf>=3.17.0",         # PDF text extraction
    "python-docx>=0.8.11",   # Word document extraction
    "beautifulsoup4>=4.12.0",# HTML parsing
    
    # Async & Concurrency
    "aiosqlite>=0.20.0",
    "aiohttp>=3.8.0",
    "tenacity>=8.2.0",       # Retry logic
    
    # CLI Output
    "rich>=13.0.0",
    
    # Observability
    "opentelemetry-api>=1.21.0",
    "opentelemetry-sdk>=1.21.0",
    "opentelemetry-exporter-otlp>=0.42b0",
    "opentelemetry-exporter-prometheus>=0.42b0",
]

[dependency-groups]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.8.0",
]
```

**Installation:**

```bash
# Using uv (fastest)
uv sync

# Or using pip
pip install -e ".[dev]"
```

### Q: How do I handle environment variables without hardcoding credentials or configuration?

**A:** Create a `.env` file for local development:

```bash
# .env (add to .gitignore)

# Application
APP_ENV=development
DEBUG=true

# API
API_HOST=0.0.0.0
API_PORT=8000

# Database
DATABASE_PATH=./data/datasets.db

# CEH API
CEH_API_BASE_URL=https://catalogue.ceh.ac.uk
CEH_API_TIMEOUT=600
CEH_API_MAX_RETRIES=5

# Vector Store
CHROMA_PATH=./data/chroma
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DEVICE=cpu

# Ollama LLM
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=mistral

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/dsh_etl_search_ai.log
```

Then load it in your app using Pydantic Settings (see Configuration Management section below).

---

## Configuration Management

### Q: How should I structure configuration so it's secure, testable, and works across development/staging/production?

**A:** Use Pydantic Settings with environment variable override capability:

```python
"""
Application configuration using Pydantic Settings.
Loads values from environment variables and .env file.
"""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore unknown environment variables
    )

    # Application
    app_name: str = "CEH Dataset Discovery"
    app_env: str = "development"
    debug: bool = True

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Database Configuration
    database_path: str = "./data/datasets.db"
    database_echo: bool = False  # Set True for SQL query logging

    # CEH API Configuration
    ceh_api_base_url: str = "https://catalogue.ceh.ac.uk"
    ceh_api_timeout: int = 600  # 10 minutes for large downloads
    ceh_api_max_retries: int = 5
    ceh_api_retry_delay: int = 2

    # Vector Store & Embeddings
    chroma_path: str = "./data/chroma"
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_batch_size: int = 32
    embedding_device: str = "cpu"  # Use 'cuda' for NVIDIA GPU
    text_chunk_size: int = 1000
    text_chunk_overlap: int = 200

    # Ollama LLM
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "mistral"
    ollama_timeout: int = 120

    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"

    # Field Validators
    @field_validator("metadata_formats", mode="before")
    @classmethod
    def parse_metadata_formats(cls, v):
        """Allow comma-separated string or list."""
        if isinstance(v, str):
            return [fmt.strip() for fmt in v.split(",")]
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance (loaded once per process)."""
    return Settings()
```

**Usage in your app:**

```python
from src.config import get_settings

settings = get_settings()

# Access config anywhere in your app
print(settings.app_name)
print(settings.database_path)
```

**Why this approach?**

- ✅ Single source of truth for configuration
- ✅ Type-safe with Pydantic validation
- ✅ Environment variables override defaults
- ✅ Cached singleton pattern (loaded once)
- ✅ Easy to test with different configs
- ✅ Secrets never in code (use env vars)

---

## ETL Pipeline Implementation

### Q: How should I structure an ETL pipeline that extracts metadata from multiple sources (API, XML, JSON, RDF) and transforms it into a consistent format?

**A:** Use an abstract extractor pattern with factory. This allows plugging different extractors for different sources:

```python
"""
ETL Coordinator - orchestrates the extraction, transformation, and loading of datasets.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class ExtractionResult:
    """Result from extraction operation."""
    file_identifier: str
    raw_content: str
    format_type: str  # 'iso19139', 'json', 'schema_org', 'rdf'
    source_url: str


class MetadataExtractor(ABC):
    """Abstract base class for metadata extraction."""

    @abstractmethod
    async def extract(self, file_identifier: str) -> ExtractionResult:
        """Extract metadata for a given file identifier."""
        pass


class ISO19139Extractor(MetadataExtractor):
    """Extract ISO 19139 XML metadata."""

    async def extract(self, file_identifier: str) -> ExtractionResult:
        # Call CEH API to fetch ISO 19139 XML
        url = f"{self.base_url}/documents/{file_identifier}/iso19139"
        response = await self.http_client.get(url)
        
        return ExtractionResult(
            file_identifier=file_identifier,
            raw_content=response.text,
            format_type="iso19139",
            source_url=url,
        )


class JSONExtractor(MetadataExtractor):
    """Extract JSON metadata."""

    async def extract(self, file_identifier: str) -> ExtractionResult:
        url = f"{self.base_url}/documents/{file_identifier}/json"
        response = await self.http_client.get(url)
        
        return ExtractionResult(
            file_identifier=file_identifier,
            raw_content=response.text,
            format_type="json",
            source_url=url,
        )


class RDFExtractor(MetadataExtractor):
    """Extract RDF metadata."""

    async def extract(self, file_identifier: str) -> ExtractionResult:
        url = f"{self.base_url}/documents/{file_identifier}/rdf"
        response = await self.http_client.get(url)
        
        return ExtractionResult(
            file_identifier=file_identifier,
            raw_content=response.text,
            format_type="rdf",
            source_url=url,
        )


class ExtractorFactory:
    """Factory for creating appropriate extractors."""

    def __init__(self, base_url: str, http_client):
        self.base_url = base_url
        self.http_client = http_client

    def create_extractor(self, format_type: str) -> MetadataExtractor:
        """Create extractor based on format type."""
        extractors = {
            "iso19139": ISO19139Extractor,
            "json": JSONExtractor,
            "rdf": RDFExtractor,
        }
        
        extractor_class = extractors.get(format_type)
        if not extractor_class:
            raise ValueError(f"Unknown format: {format_type}")
        
        return extractor_class(self.base_url, self.http_client)


class ETLCoordinator:
    """Orchestrates the ETL pipeline."""

    def __init__(self, extractor_factory, transformer, loader, logger):
        self.extractor_factory = extractor_factory
        self.transformer = transformer
        self.loader = loader
        self.logger = logger

    async def process_datasets(self, file_identifiers: List[str]) -> Dict[str, Any]:
        """Process multiple datasets through ETL pipeline."""
        results = {
            "success": 0,
            "failed": 0,
            "errors": [],
        }

        for file_id in file_identifiers:
            try:
                # EXTRACT: Get raw metadata
                extraction_results = []
                for format_type in ["iso19139", "json", "rdf"]:
                    extractor = self.extractor_factory.create_extractor(format_type)
                    result = await extractor.extract(file_id)
                    extraction_results.append(result)

                # TRANSFORM: Parse and normalize metadata
                transformed_data = await self.transformer.transform(extraction_results)

                # LOAD: Store in database
                await self.loader.load(transformed_data)

                results["success"] += 1
                self.logger.info(f"Successfully processed dataset: {file_id}")

            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "file_id": file_id,
                    "error": str(e),
                })
                self.logger.error(f"Failed to process dataset {file_id}: {e}")

        return results
```

**Why this design?**

- ✅ **Single Responsibility**: Each extractor handles one format
- ✅ **Open/Closed Principle**: Easy to add new extractors without modifying existing code
- ✅ **Factory Pattern**: Centralized creation of extractors
- ✅ **Type Safety**: Clear contracts with abstract base class
- ✅ **Testability**: Easy to mock individual extractors

---

## Database & ORM Setup

### Q: How should I structure SQLite database access for datasets with relationships (Dataset → Metadata → DataFiles → SupportingDocs)?

**A:** Use the Repository pattern with async SQLite:

```python
"""
SQLite database initialization and connection pooling.
"""

import aiosqlite
from pathlib import Path
from typing import Optional


class Database:
    """Database connection manager."""

    def __init__(self, database_path: str):
        self.database_path = Path(database_path)
        self.connection: Optional[aiosqlite.Connection] = None

    async def initialize(self):
        """Initialize database and create tables."""
        # Create database directory if it doesn't exist
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        # Connect and enable foreign keys
        self.connection = await aiosqlite.connect(str(self.database_path))
        await self.connection.execute("PRAGMA foreign_keys = ON")
        await self.connection.execute("PRAGMA journal_mode = WAL")

        # Create tables
        await self._create_tables()
        await self.connection.commit()

    async def _create_tables(self):
        """Create database schema."""
        
        # Datasets table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS datasets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_identifier TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                abstract TEXT,
                cedc_link TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Metadata documents (one dataset can have multiple formats)
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS metadata_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id INTEGER NOT NULL,
                format_type TEXT NOT NULL,  -- 'iso19139', 'json', 'rdf', 'schema_org'
                raw_content TEXT NOT NULL,
                source_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
            )
        """)

        # Data files
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS data_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                file_url TEXT,
                file_size INTEGER,
                mime_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
            )
        """)

        # Supporting documents (PDFs, Word docs, etc.)
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS supporting_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT,
                file_type TEXT,  -- 'pdf', 'docx', 'html'
                text_content TEXT,
                embedding_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
            )
        """)

    async def close(self):
        """Close database connection."""
        if self.connection:
            await self.connection.close()

    async def get_connection(self) -> aiosqlite.Connection:
        """Get active database connection."""
        if not self.connection:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self.connection


# Repository pattern for data access
class DatasetRepository:
    """Data access for datasets."""

    def __init__(self, db: Database):
        self.db = db

    async def create(self, file_identifier: str, title: str, abstract: str) -> int:
        """Create a new dataset."""
        conn = await self.db.get_connection()
        
        cursor = await conn.execute(
            """
            INSERT INTO datasets (file_identifier, title, abstract)
            VALUES (?, ?, ?)
            """,
            (file_identifier, title, abstract),
        )
        await conn.commit()
        return cursor.lastrowid

    async def get_by_file_id(self, file_identifier: str):
        """Retrieve dataset by file identifier."""
        conn = await self.db.get_connection()
        
        cursor = await conn.execute(
            "SELECT * FROM datasets WHERE file_identifier = ?",
            (file_identifier,),
        )
        return await cursor.fetchone()

    async def get_all(self, limit: int = 100, offset: int = 0):
        """Retrieve all datasets with pagination."""
        conn = await self.db.get_connection()
        
        cursor = await conn.execute(
            "SELECT * FROM datasets LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return await cursor.fetchall()


class MetadataRepository:
    """Data access for metadata documents."""

    def __init__(self, db: Database):
        self.db = db

    async def create(
        self,
        dataset_id: int,
        format_type: str,
        raw_content: str,
        source_url: str,
    ) -> int:
        """Store metadata document."""
        conn = await self.db.get_connection()
        
        cursor = await conn.execute(
            """
            INSERT INTO metadata_documents 
            (dataset_id, format_type, raw_content, source_url)
            VALUES (?, ?, ?, ?)
            """,
            (dataset_id, format_type, raw_content, source_url),
        )
        await conn.commit()
        return cursor.lastrowid

    async def get_by_dataset(self, dataset_id: int, format_type: Optional[str] = None):
        """Get metadata documents for a dataset."""
        conn = await self.db.get_connection()
        
        if format_type:
            cursor = await conn.execute(
                """
                SELECT * FROM metadata_documents 
                WHERE dataset_id = ? AND format_type = ?
                """,
                (dataset_id, format_type),
            )
        else:
            cursor = await conn.execute(
                "SELECT * FROM metadata_documents WHERE dataset_id = ?",
                (dataset_id,),
            )
        
        return await cursor.fetchall()
```

---

## Vector Store & Embeddings

### Q: How do I integrate ChromaDB and sentence-transformers for semantic search across datasets?

**A:** Create an embedding service that generates and stores embeddings:

```python
"""
Embedding service for generating vector embeddings.
"""

from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List
import numpy as np


class EmbeddingService:
    """Generate and manage embeddings."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "cpu"):
        """Initialize embedding model."""
        self.model = SentenceTransformer(model_name, device=device)
        self.model_dim = self.model.get_sentence_embedding_dimension()

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()


class ChromaVectorStore:
    """ChromaDB vector store wrapper."""

    def __init__(self, chroma_path: str):
        """Initialize ChromaDB connection."""
        settings = ChromaSettings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=chroma_path,
            anonymized_telemetry=False,
        )
        
        self.client = chromadb.Client(settings)
        self.collection = None

    def get_collection(self, name: str = "datasets"):
        """Get or create a collection."""
        if not self.collection:
            self.collection = self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
        return self.collection

    async def add_embeddings(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadata: List[dict],
    ):
        """Add embeddings to the vector store."""
        collection = self.get_collection()
        
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadata,
        )

    async def search(self, query_embedding: List[float], top_k: int = 10):
        """Search for similar embeddings."""
        collection = self.get_collection()
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )
        
        return results


class SemanticIndexingService:
    """Service to index datasets semantically."""

    def __init__(self, embedding_service: EmbeddingService, vector_store: ChromaVectorStore):
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    async def index_dataset(
        self,
        dataset_id: int,
        title: str,
        abstract: str,
        supporting_docs: List[dict],
    ):
        """Index a dataset with its title, abstract, and supporting docs."""
        
        # Combine text for embedding
        text_parts = [title, abstract]
        text_to_embed = " ".join(filter(None, text_parts))

        # Generate embedding
        embedding = self.embedding_service.embed_text(text_to_embed)

        # Store in vector database
        await self.vector_store.add_embeddings(
            ids=[f"dataset_{dataset_id}"],
            embeddings=[embedding],
            documents=[text_to_embed],
            metadata=[{
                "dataset_id": dataset_id,
                "title": title,
                "type": "dataset",
            }],
        )

        # Index supporting documents separately
        for doc in supporting_docs:
            doc_embedding = self.embedding_service.embed_text(doc["text_content"])
            await self.vector_store.add_embeddings(
                ids=[f"doc_{doc['id']}"],
                embeddings=[doc_embedding],
                documents=[doc["text_content"][:500]],  # Store first 500 chars
                metadata=[{
                    "dataset_id": dataset_id,
                    "document_id": doc["id"],
                    "file_name": doc["file_name"],
                    "type": "supporting_document",
                }],
            )

    async def search_datasets(self, query: str, top_k: int = 10):
        """Semantic search across datasets."""
        # Generate embedding for query
        query_embedding = self.embedding_service.embed_text(query)

        # Search vector store
        results = await self.vector_store.search(query_embedding, top_k)

        return results
```

---

## FastAPI Application Setup

### Q: How should I structure a FastAPI app with proper middleware, error handling, and dependency injection?

**A:** Create an app factory with layered middleware and dependency injection:

```python
"""
FastAPI application factory and configuration.
"""

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from typing import Optional

from src.config import get_settings
from src.logging_config import get_logger
from src.api.middleware.logging import RequestLoggingMiddleware
from src.api.exceptions import APIException, ErrorResponse
from src.infrastructure.database import Database
from src.api.routes import health_router, search_router, chat_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage app lifecycle: startup and shutdown.
    """
    logger.info("Starting DSH ETL Search AI application")
    
    # Startup: Initialize database
    settings = get_settings()
    database = Database(settings.database_path)
    await database.initialize()
    app.state.database = database
    
    yield
    
    # Shutdown: Close database
    logger.info("Shutting down application")
    await app.state.database.close()


def create_app(settings: Optional[object] = None) -> FastAPI:
    """
    Create and configure FastAPI application.
    """
    if settings is None:
        settings = get_settings()

    # Create app with lifespan management
    app = FastAPI(
        title=settings.app_name,
        description="Semantic search and discovery for environmental datasets",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ========================================================================
    # CORS Middleware (for frontend development)
    # ========================================================================
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ========================================================================
    # Request Logging Middleware
    # ========================================================================
    app.add_middleware(RequestLoggingMiddleware)

    # ========================================================================
    # Exception Handler
    # ========================================================================
    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        """Handle custom API exceptions."""
        logger.error(
            f"API Error: {exc.error_code} - {exc.message}",
            extra={"status_code": exc.status_code}
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error_code=exc.error_code,
                message=exc.message,
                request_id=request.headers.get("X-Request-ID"),
            ).model_dump(),
        )

    # ========================================================================
    # Dependency Injection
    # ========================================================================
    def get_database() -> Database:
        """Get database instance from app state."""
        return app.state.database

    # Store get_database in app for use in routers
    app.dependency_overrides = {
        "get_database": get_database,
    }

    # ========================================================================
    # Routes
    # ========================================================================
    app.include_router(health_router, prefix="/api/v1", tags=["health"])
    app.include_router(search_router, prefix="/api/v1/search", tags=["search"])
    app.include_router(chat_router, prefix="/api/v1/chat", tags=["chat"])

    return app


# Create app instance
app = create_app()
```

---

## API Routes & Error Handling

### Q: How should I structure API routes with proper error handling and validation?

**A:** Use Pydantic schemas and custom exceptions:

```python
"""
Search API routes with semantic search capability.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional

from src.repositories.dataset_repository import DatasetRepository
from src.services.search.search_service import SemanticSearchService
from src.infrastructure.database import Database

router = APIRouter()


# ============================================================================
# Request/Response Schemas (Pydantic)
# ============================================================================

class SearchRequest(BaseModel):
    """Semantic search request."""
    query: str = Field(..., min_length=3, description="Search query")
    top_k: int = Field(10, ge=1, le=100, description="Number of results")


class SearchResult(BaseModel):
    """Single search result."""
    dataset_id: int
    title: str
    abstract: Optional[str]
    relevance_score: float
    url: Optional[str]


class SearchResponse(BaseModel):
    """Search API response."""
    query: str
    results: List[SearchResult]
    total_results: int


class ErrorResponse(BaseModel):
    """Error response schema."""
    error_code: str
    message: str
    request_id: Optional[str] = None


# ============================================================================
# Custom Exceptions
# ============================================================================

class APIException(Exception):
    """Base class for API exceptions."""
    
    def __init__(self, error_code: str, message: str, status_code: int = 400):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code


class SearchQueryError(APIException):
    """Invalid search query."""
    
    def __init__(self, message: str):
        super().__init__("INVALID_SEARCH_QUERY", message, 400)


class DatabaseError(APIException):
    """Database operation failed."""
    
    def __init__(self, message: str):
        super().__init__("DATABASE_ERROR", message, 500)


# ============================================================================
# Routes
# ============================================================================

@router.post("/semantic", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    db: Database = Depends(lambda: None),  # Get from app context
):
    """
    Perform semantic search across datasets.
    
    Returns datasets ranked by semantic similarity to query.
    """
    try:
        if not request.query or len(request.query.strip()) == 0:
            raise SearchQueryError("Search query cannot be empty")

        # Initialize services
        dataset_repo = DatasetRepository(db)
        search_service = SemanticSearchService()

        # Perform search
        results = await search_service.search(
            query=request.query,
            top_k=request.top_k,
        )

        # Map to response schema
        search_results = [
            SearchResult(
                dataset_id=r["dataset_id"],
                title=r["title"],
                abstract=r.get("abstract"),
                relevance_score=r["score"],
                url=r.get("url"),
            )
            for r in results
        ]

        return SearchResponse(
            query=request.query,
            results=search_results,
            total_results=len(search_results),
        )

    except SearchQueryError as e:
        raise APIException(e.error_code, e.message, e.status_code)
    except Exception as e:
        raise APIException("SEARCH_FAILED", f"Search failed: {str(e)}", 500)


@router.get("/datasets", response_model=List[SearchResult])
async def list_datasets(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """List all datasets with pagination."""
    try:
        # Implementation here
        pass
    except Exception as e:
        raise APIException("LIST_FAILED", str(e), 500)
```

---

## Distributed Tracing & Observability

### Q: How should I add observability with OpenTelemetry, structured logging, and correlation IDs?

**A:** Implement tracing middleware and structured logging:

```python
"""
Structured logging configuration.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Optional


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request context if available
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def get_logger(name: str) -> logging.Logger:
    """Get configured logger instance."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(JSONFormatter())
        logger.addHandler(console_handler)
        
        # File handler
        file_handler = logging.FileHandler("logs/app.log")
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

    logger.setLevel(logging.INFO)
    return logger


# ============================================================================
# Request Logging Middleware
# ============================================================================

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
import uuid


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with correlation ID."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate correlation ID
        correlation_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id

        # Add to response headers
        response = await call_next(request)
        response.headers["X-Request-ID"] = correlation_id

        # Log request
        logger = get_logger(__name__)
        logger.info(
            f"{request.method} {request.url.path}",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
            }
        )

        return response


# ============================================================================
# OpenTelemetry Tracing
# ============================================================================

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter


def initialize_tracing(service_name: str = "dsh-etl-search-ai"):
    """Initialize OpenTelemetry tracing."""
    
    # Create tracer provider
    tracer_provider = TracerProvider()
    
    try:
        # Export to OTLP (e.g., Jaeger)
        otlp_exporter = OTLPSpanExporter(
            endpoint="localhost:4317",
            insecure=True,
        )
        tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    except Exception as e:
        logger = get_logger(__name__)
        logger.warning(f"Could not initialize OTLP exporter: {e}")

    trace.set_tracer_provider(tracer_provider)


def get_tracer(name: str) -> trace.Tracer:
    """Get tracer for instrumentation."""
    return trace.get_tracer(name)
```

---

## Testing Strategy

### Q: How should I structure tests for a complex backend with async operations, ETL processes, and external API calls?

**A:** Use pytest with proper fixtures and mocking:

```python
"""
Test fixtures and utilities.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

import aiosqlite
from src.infrastructure.database import Database
from src.repositories.dataset_repository import DatasetRepository


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
async def test_database():
    """Create in-memory test database."""
    db = Database(":memory:")
    await db.initialize()
    yield db
    await db.close()


@pytest.fixture
async def dataset_repository(test_database):
    """Create dataset repository with test database."""
    return DatasetRepository(test_database)


@pytest.fixture
def mock_http_client():
    """Mock HTTP client for external API calls."""
    return AsyncMock()


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service."""
    service = AsyncMock()
    service.embed_text.return_value = [0.1, 0.2, 0.3]  # Mock embedding
    return service


# ============================================================================
# Unit Tests
# ============================================================================

@pytest.mark.asyncio
async def test_dataset_repository_create(dataset_repository):
    """Test creating a dataset in repository."""
    dataset_id = await dataset_repository.create(
        file_identifier="test-123",
        title="Test Dataset",
        abstract="Test abstract",
    )
    
    assert dataset_id > 0


@pytest.mark.asyncio
async def test_dataset_repository_get_by_id(dataset_repository):
    """Test retrieving dataset by ID."""
    # Create dataset
    dataset_id = await dataset_repository.create(
        file_identifier="test-456",
        title="Another Dataset",
        abstract="Another abstract",
    )
    
    # Retrieve
    dataset = await dataset_repository.get_by_file_id("test-456")
    assert dataset is not None


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_etl_pipeline_end_to_end(
    test_database,
    mock_http_client,
    mock_embedding_service,
):
    """Test full ETL pipeline."""
    # Setup
    from src.services.etl.etl_coordinator import ETLCoordinator
    
    coordinator = ETLCoordinator(
        extractor_factory=MagicMock(),
        transformer=MagicMock(),
        loader=MagicMock(),
        logger=MagicMock(),
    )
    
    # Mock responses
    coordinator.extractor_factory.create_extractor.return_value.extract = AsyncMock(
        return_value={
            "file_identifier": "test-789",
            "raw_content": "<xml></xml>",
            "format_type": "iso19139",
        }
    )
    
    # Execute
    results = await coordinator.process_datasets(["test-789"])
    
    # Assert
    assert results["success"] >= 0


# ============================================================================
# API Tests
# ============================================================================

@pytest.mark.asyncio
async def test_search_api_endpoint(client):
    """Test semantic search API endpoint."""
    response = await client.post(
        "/api/v1/search/semantic",
        json={
            "query": "environmental datasets",
            "top_k": 10,
        },
    )
    
    assert response.status_code == 200
    assert "results" in response.json()
```

---

## Summary & Best Practices

Here are the key takeaways for building a production-ready Python backend:

### Architecture
- ✅ **Layered Architecture**: API → Services → Repositories → Database
- ✅ **Dependency Injection**: Services injected, not created
- ✅ **Factory Pattern**: For pluggable implementations
- ✅ **Abstract Base Classes**: Clear contracts for implementations

### Configuration
- ✅ **Environment Variables**: Use `.env` for local dev
- ✅ **Pydantic Settings**: Type-safe configuration
- ✅ **Feature Flags**: Easy to toggle features
- ✅ **Logging Configuration**: Centralized setup

### Data Layer
- ✅ **Repository Pattern**: Abstraction over database
- ✅ **Async Operations**: Use `aiosqlite` for non-blocking I/O
- ✅ **Connection Pooling**: Efficient resource use
- ✅ **Transactions**: Ensure data consistency

### Observability
- ✅ **Structured Logging**: JSON logs for easy parsing
- ✅ **Correlation IDs**: Track requests across systems
- ✅ **Distributed Tracing**: Use OpenTelemetry
- ✅ **Error Handling**: Comprehensive exception handling

### Testing
- ✅ **Unit Tests**: Test individual components in isolation
- ✅ **Integration Tests**: Test component interactions
- ✅ **E2E Tests**: Test full workflows
- ✅ **Fixtures**: Reusable test setup

### API Development
- ✅ **Pydantic Schemas**: Validation and documentation
- ✅ **OpenAPI**: Auto-generated API documentation
- ✅ **Error Responses**: Consistent error format
- ✅ **CORS**: Configure for frontend development

---

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [SQLite with Python](https://docs.python.org/3/library/sqlite3.html)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [Pytest Documentation](https://docs.pytest.org/)
