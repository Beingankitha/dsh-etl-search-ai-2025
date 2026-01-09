## Quick Navigation

- **[Environment Setup](#environment-setup)** - Dependencies, Python config
- **[Architecture Questions](#architecture-questions)** - Project structure, design patterns
- **[Backend Implementation](#backend-implementation)** - FastAPI, services, repos
- **[Data Layer](#data-layer)** - SQLite, async operations
- **[Search & Embeddings](#search--embeddings)** - Vector stores, semantic search
- **[CLI & ETL](#cli--etl)** - Batch processing, data extraction
- **[Observability](#observability)** - Logging, tracing, monitoring

---

## Environment Setup

### Question: How do I set up Python 3.11+ with uv package manager?

**Answer:**

First, install uv (ultra-fast Python package installer):

```bash
# On macOS
brew install uv

# On Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

Then create your project:

```bash
# Initialize project with uv
uv init --python 3.11+
cd dsh-etl-search-ai-2025

# Create venv
uv venv

# Activate venv
source .venv/bin/activate  # macOS/Linux
# or on Windows: .venv\Scripts\activate

# Install dependencies from pyproject.toml
uv sync
uv sync --extra dev  # Include dev dependencies
```

Check what's installed:

```bash
uv pip list
```

---

### Question: What Python packages do I actually need for ETL, semantic search, and API?

**Answer:**

Here's the minimal production setup broken down by use case:

```toml
[project]
name = "dsh-etl-search-ai"
requires-python = ">=3.11"

dependencies = [
    # API Server
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",

    # Data Validation
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",

    # HTTP Client (for CEH API calls)
    "httpx>=0.28.0",
    "requests>=2.31.0",

    # Database
    "aiosqlite>=0.20.0",  # Async SQLite

    # Vector Store & ML
    "chromadb>=0.5.0",
    "sentence-transformers>=3.3.0",
    "numpy>=1.24.0",

    # LLM Integration
    "ollama>=0.4.0",

    # CLI
    "typer>=0.9.0",
    "click>=8.1.0",
    "rich>=13.0.0",

    # Document Processing
    "lxml>=5.3.0",         # XML parsing
    "xmltodict>=0.13.0",   # XML → dict
    "rdflib>=6.3.0",       # RDF parsing
    "pypdf>=3.17.0",       # PDF text extraction
    "python-docx>=0.8.11", # Word document extraction
    "beautifulsoup4>=4.12.0",  # HTML parsing

    # Resilience
    "tenacity>=8.2.0",  # Retry logic

    # Configuration
    "python-dotenv>=1.0.0",

    # Observability
    "opentelemetry-api>=1.21.0",
    "opentelemetry-sdk>=1.21.0",
]

[dependency-groups]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.8.0",
]
```

---

### Question: How do I set up environment variables so I don't hardcode secrets?

**Answer:**

Create a `.env` file in your project root (add to `.gitignore`):

```bash
# .env - Development configuration
APP_ENV=development
DEBUG=true

# API
API_HOST=0.0.0.0
API_PORT=8000

# Database
DATABASE_PATH=./data/datasets.db

# CEH Catalogue API
CEH_API_BASE_URL=https://catalogue.ceh.ac.uk
CEH_API_TIMEOUT=600
CEH_API_MAX_RETRIES=5

# Vector Store
CHROMA_PATH=./data/chroma
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DEVICE=cpu  # Use 'cuda' for NVIDIA GPU

# Ollama LLM
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=mistral

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/dsh_etl_search_ai.log
```

Then load it in Python:

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    app_env: str = "development"
    database_path: str = "./data/datasets.db"
    chroma_path: str = "./data/chroma"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache
def get_settings() -> Settings:
    return Settings()

# Use it
settings = get_settings()
print(settings.database_path)
```

---

## Architecture Questions

### Question: My backend needs to handle ETL, API serving, embeddings, and chat. How do I structure this to avoid spaghetti code?

**Answer:**

Use **Layered Architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────┐
│          API Layer (FastAPI)            │  Routes & HTTP handlers
├─────────────────────────────────────────┤
│        Services Layer (Business Logic)  │  ETL, Search, Chat coordination
├─────────────────────────────────────────┤
│     Repository Layer (Data Access)      │  Database queries
├─────────────────────────────────────────┤
│    Infrastructure Layer (External deps) │  DB, Vector Store, HTTP client
└─────────────────────────────────────────┘
```

**Concrete structure:**

```python
# services/etl/etl_service.py - Business logic
class ETLCoordinator:
    def __init__(self, extractor, transformer, loader):
        self.extractor = extractor
        self.transformer = transformer
        self.loader = loader
    
    async def process_dataset(self, file_id: str):
        # Extract metadata
        raw = await self.extractor.extract(file_id)
        # Transform to standard format
        transformed = await self.transformer.transform(raw)
        # Load into DB
        await self.loader.load(transformed)


# repositories/dataset_repo.py - Data access
class DatasetRepository:
    def __init__(self, db: Database):
        self.db = db
    
    async def create(self, title: str, abstract: str) -> int:
        # SQL operations here
        pass


# api/routes/etl.py - HTTP endpoints
@router.post("/etl/process")
async def start_etl(request: ETLRequest, repo: DatasetRepository = Depends()):
    coordinator = ETLCoordinator(...)
    result = await coordinator.process_dataset(request.file_id)
    return {"status": "success", "id": result}
```

**Benefits:**
- ✅ Easy to test (mock services/repos independently)
- ✅ Easy to swap implementations (different DB, vector store)
- ✅ Clear data flow (top-to-bottom)
- ✅ SOLID principles (Single Responsibility, Dependency Inversion)

---

### Question: Should I use ORM (SQLAlchemy) or raw SQL queries?

**Answer:**

For this project, **raw async SQL with aiosqlite is better** because:

1. **Simplicity**: You're using SQLite, not complex relationships
2. **Performance**: Raw SQL is faster for simple queries
3. **Learning**: Easier to understand what's happening
4. **Async**: aiosqlite plays well with FastAPI

Here's the pattern:

```python
# infrastructure/database.py
import aiosqlite

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = None
    
    async def initialize(self):
        self.connection = await aiosqlite.connect(self.db_path)
        await self.connection.execute("PRAGMA foreign_keys = ON")
        await self._create_tables()
    
    async def _create_tables(self):
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS datasets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_identifier TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                abstract TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await self.connection.commit()

# repositories/dataset_repo.py
class DatasetRepository:
    def __init__(self, db: Database):
        self.db = db
    
    async def create(self, file_id: str, title: str, abstract: str):
        cursor = await self.db.connection.execute(
            """
            INSERT INTO datasets (file_identifier, title, abstract)
            VALUES (?, ?, ?)
            """,
            (file_id, title, abstract)
        )
        await self.db.connection.commit()
        return cursor.lastrowid
    
    async def get_by_id(self, file_id: str):
        cursor = await self.db.connection.execute(
            "SELECT * FROM datasets WHERE file_identifier = ?",
            (file_id,)
        )
        return await cursor.fetchone()
```

---

## Backend Implementation

### Question: How do I structure a FastAPI app that's production-ready from day one?

**Answer:**

Use an **app factory pattern** with proper lifecycle management:

```python
# src/api/app.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.config import get_settings
from src.infrastructure.database import Database
from src.api.routes import search_router, chat_router, etl_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage app startup and shutdown.
    This runs once when the app starts and once when it shuts down.
    """
    # STARTUP
    settings = get_settings()
    db = Database(settings.database_path)
    await db.initialize()
    app.state.db = db
    print("✅ Database initialized")
    
    yield
    
    # SHUTDOWN
    await app.state.db.close()
    print("❌ Database closed")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        description="Semantic search for environmental datasets",
        version="1.0.0",
        docs_url="/docs",
    )
    
    # CORS middleware (for frontend)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Routes
    app.include_router(search_router, prefix="/api/v1/search")
    app.include_router(chat_router, prefix="/api/v1/chat")
    app.include_router(etl_router, prefix="/api/v1/etl")
    
    # Health check
    @app.get("/health")
    async def health():
        return {"status": "healthy"}
    
    return app


app = create_app()

# main.py
if __name__ == "__main__":
    import uvicorn
    from src.config import get_settings
    
    settings = get_settings()
    uvicorn.run(
        "src.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
```

**Start the server:**

```bash
# Development (with auto-reload)
uv run python -m uvicorn src.api.app:app --reload --port 8000

# Production
uv run python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --workers 4
```

---

### Question: How do I handle errors properly so users get meaningful messages, not stack traces?

**Answer:**

Create custom exceptions and a global error handler:

```python
# api/exceptions.py
class APIException(Exception):
    """Base API exception."""
    def __init__(self, error_code: str, message: str, status_code: int = 400):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code


class DatasetNotFoundError(APIException):
    def __init__(self, file_id: str):
        super().__init__(
            "DATASET_NOT_FOUND",
            f"Dataset {file_id} not found",
            404
        )


class SearchQueryError(APIException):
    def __init__(self, reason: str):
        super().__init__(
            "INVALID_SEARCH_QUERY",
            f"Invalid search query: {reason}",
            400
        )


class EmbeddingError(APIException):
    def __init__(self, reason: str):
        super().__init__(
            "EMBEDDING_FAILED",
            f"Embedding generation failed: {reason}",
            500
        )


# api/app.py - Add exception handler
from fastapi.responses import JSONResponse

@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
            }
        }
    )


# Usage in routes
@app.get("/datasets/{file_id}")
async def get_dataset(file_id: str, repo = Depends()):
    dataset = await repo.get_by_file_id(file_id)
    if not dataset:
        raise DatasetNotFoundError(file_id)
    return dataset
```

---

## Data Layer

### Question: How do I design a SQLite schema for datasets with their metadata, data files, and supporting documents?

**Answer:**

Here's an Entity-Relationship design:

```
Dataset (1) ──────── (Many) Metadata Documents (store all 4 formats: ISO19139, JSON, RDF, Schema.org)
  │
  ├── (Many) Data Files (actual CSV, NetCDF, etc.)
  │
  └── (Many) Supporting Documents (PDFs, Word docs, HTML files)
```

**SQL Schema:**

```sql
-- Main dataset table
CREATE TABLE datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_identifier TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    abstract TEXT,
    cedc_link TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Metadata in multiple formats
CREATE TABLE metadata_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id INTEGER NOT NULL,
    format_type TEXT NOT NULL,  -- 'iso19139', 'json', 'rdf', 'schema_org'
    raw_content TEXT NOT NULL,  -- Store entire XML/JSON/RDF document
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);

-- Data files (CSVs, NetCDF, etc.)
CREATE TABLE data_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    file_url TEXT,
    file_size INTEGER,
    mime_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);

-- Supporting documents (PDFs, Word, HTML)
CREATE TABLE supporting_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    file_path TEXT,
    file_type TEXT,  -- 'pdf', 'docx', 'html'
    text_content TEXT,  -- Extracted text for embedding
    embedding_id TEXT,  -- Link to vector store
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);

-- Indexes for common queries
CREATE INDEX idx_datasets_file_id ON datasets(file_identifier);
CREATE INDEX idx_metadata_dataset ON metadata_documents(dataset_id, format_type);
CREATE INDEX idx_data_files_dataset ON data_files(dataset_id);
CREATE INDEX idx_support_docs_dataset ON supporting_documents(dataset_id);
```

---

### Question: How do I make database operations async without blocking the API?

**Answer:**

Use async context managers and aiosqlite:

```python
# infrastructure/database.py
import aiosqlite
from pathlib import Path
from contextlib import asynccontextmanager


class Database:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.connection: Optional[aiosqlite.Connection] = None
    
    async def initialize(self):
        """Initialize connection and create tables."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.connection = await aiosqlite.connect(str(self.db_path))
        await self.connection.execute("PRAGMA foreign_keys = ON")
        await self.connection.execute("PRAGMA journal_mode = WAL")
        
        await self._create_tables()
        await self.connection.commit()
    
    async def _create_tables(self):
        """Create all tables (see SQL schema above)."""
        await self.connection.execute("""...""")
    
    async def close(self):
        """Close connection."""
        if self.connection:
            await self.connection.close()
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for transactions."""
        try:
            yield self.connection
            await self.connection.commit()
        except Exception:
            await self.connection.rollback()
            raise


# repositories/dataset_repo.py
class DatasetRepository:
    def __init__(self, db: Database):
        self.db = db
    
    async def create_with_metadata(self, dataset: dict, metadata: dict):
        """Create dataset with metadata in a transaction."""
        async with self.db.transaction() as conn:
            # Insert dataset
            cursor = await conn.execute(
                """
                INSERT INTO datasets (file_identifier, title, abstract)
                VALUES (?, ?, ?)
                """,
                (dataset["file_id"], dataset["title"], dataset["abstract"])
            )
            dataset_id = cursor.lastrowid
            
            # Insert metadata in all formats
            for format_type, content in metadata.items():
                await conn.execute(
                    """
                    INSERT INTO metadata_documents 
                    (dataset_id, format_type, raw_content)
                    VALUES (?, ?, ?)
                    """,
                    (dataset_id, format_type, content)
                )
            
            return dataset_id


# Usage in API
@app.post("/datasets")
async def create_dataset(req: DatasetCreateRequest):
    repo = DatasetRepository(app.state.db)
    dataset_id = await repo.create_with_metadata(
        req.dataset,
        req.metadata
    )
    return {"id": dataset_id}
```

---

## Search & Embeddings

### Question: How do I add semantic search using embeddings and vector store?

**Answer:**

Use sentence-transformers for embeddings and ChromaDB for vector storage:

```python
# services/embeddings/embedding_service.py
from sentence_transformers import SentenceTransformer
from typing import List


class EmbeddingService:
    """Generate text embeddings."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "cpu"):
        self.model = SentenceTransformer(model_name, device=device)
        self.dimension = self.model.get_sentence_embedding_dimension()
    
    def embed(self, text: str) -> List[float]:
        """Embed a single text."""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts."""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()


# infrastructure/vector_store.py
import chromadb
from chromadb.config import Settings as ChromaSettings


class VectorStore:
    """ChromaDB wrapper for semantic search."""
    
    def __init__(self, chroma_path: str):
        settings = ChromaSettings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=chroma_path,
            anonymized_telemetry=False,
        )
        self.client = chromadb.Client(settings)
        self.collection = None
    
    def get_collection(self, name: str = "datasets") -> chromadb.Collection:
        if not self.collection:
            self.collection = self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
        return self.collection
    
    async def add(self, ids: List[str], embeddings: List[List[float]], 
                  documents: List[str], metadata: List[dict]):
        """Add embeddings to vector store."""
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


# services/search/search_service.py
class SearchService:
    """Semantic search across datasets."""
    
    def __init__(self, embedding_service: EmbeddingService, 
                 vector_store: VectorStore):
        self.embedding_service = embedding_service
        self.vector_store = vector_store
    
    async def index_dataset(self, dataset_id: int, title: str, abstract: str):
        """Add dataset to search index."""
        text = f"{title}\n{abstract}"
        embedding = self.embedding_service.embed(text)
        
        await self.vector_store.add(
            ids=[f"dataset_{dataset_id}"],
            embeddings=[embedding],
            documents=[text],
            metadata=[{"dataset_id": dataset_id, "type": "dataset"}]
        )
    
    async def search(self, query: str, top_k: int = 10) -> List[dict]:
        """Search for datasets."""
        # Generate embedding for query
        query_embedding = self.embedding_service.embed(query)
        
        # Search vector store
        results = await self.vector_store.search(query_embedding, top_k)
        
        # Format results
        output = []
        for i, doc_id in enumerate(results["ids"][0]):
            output.append({
                "id": doc_id,
                "score": results["distances"][0][i],
                "metadata": results["metadatas"][0][i],
            })
        
        return output
```

**API endpoint:**

```python
# api/routes/search.py
from fastapi import APIRouter

router = APIRouter()

@router.post("/search")
async def search_datasets(query: str, top_k: int = 10):
    """Semantic search for datasets."""
    search_service = SearchService(
        embedding_service=EmbeddingService(),
        vector_store=VectorStore(settings.chroma_path)
    )
    
    results = await search_service.search(query, top_k)
    
    return {
        "query": query,
        "results": results,
        "count": len(results)
    }
```

---

## CLI & ETL

### Question: How do I create a CLI for batch ETL processing?

**Answer:**

Use Typer for a modern CLI:

```python
# cli_main.py
import typer
from typing import Optional
from pathlib import Path

from src.services.etl.etl_coordinator import ETLCoordinator
from src.config import get_settings

app = typer.Typer(
    name="dsh-etl",
    help="Extract and index datasets from CEH catalogue"
)


@app.command()
def process_datasets(
    input_file: Path = typer.Option(
        ...,
        help="File with dataset identifiers (one per line)"
    ),
    limit: Optional[int] = typer.Option(
        None,
        help="Process only first N datasets"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose/-q",
        help="Verbose logging"
    ),
):
    """
    Extract and index datasets from CEH catalogue.
    
    Example:
        python cli_main.py process-datasets --input-file identifiers.txt --limit 50
    """
    import asyncio
    
    settings = get_settings()
    
    # Read identifiers
    with open(input_file) as f:
        identifiers = [line.strip() for line in f if line.strip()]
    
    if limit:
        identifiers = identifiers[:limit]
    
    print(f"📚 Processing {len(identifiers)} datasets...")
    
    # Run ETL
    coordinator = ETLCoordinator(settings)
    results = asyncio.run(coordinator.process_all(identifiers))
    
    print(f"✅ Success: {results['success']}")
    print(f"❌ Failed: {results['failed']}")


@app.command()
def index_embeddings(
    limit: Optional[int] = typer.Option(None, help="Index first N datasets")
):
    """Generate embeddings for existing datasets."""
    print("🔄 Generating embeddings...")
    # Implementation


@app.command()
def health_check():
    """Check system health."""
    import asyncio
    from src.infrastructure.database import Database
    
    settings = get_settings()
    
    async def check():
        # Check database
        db = Database(settings.database_path)
        await db.initialize()
        await db.close()
        print("✅ Database: OK")
        
        # Check Ollama
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{settings.ollama_host}/api/tags")
                resp.raise_for_status()
            print("✅ Ollama: OK")
        except Exception as e:
            print(f"❌ Ollama: {e}")
    
    asyncio.run(check())


if __name__ == "__main__":
    app()
```

**Run CLI:**

```bash
# Show help
uv run python cli_main.py --help

# Process datasets
uv run python cli_main.py process-datasets --input-file metadata-file-identifiers.txt --limit 50

# Check health
uv run python cli_main.py health-check
```

---

## Observability

### Question: How do I add structured logging and distributed tracing?

**Answer:**

```python
# logging_config.py
import logging
import json
from datetime import datetime


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
        
        # Add extra fields
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def setup_logging(log_level: str = "INFO", log_file: str = "./logs/app.log"):
    """Configure structured logging."""
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """Get logger instance."""
    return logging.getLogger(name)


# Usage
from src.logging_config import get_logger

logger = get_logger(__name__)
logger.info("Application started")
```

---

## Production Checklist

Before deploying to production:

- ✅ Set `DEBUG=false` in environment
- ✅ Use strong database backups
- ✅ Enable CORS only for your frontend domain
- ✅ Configure logging to file (not just console)
- ✅ Use connection pooling for database
- ✅ Set up monitoring (health checks, error alerts)
- ✅ Test error scenarios (network timeouts, database failures)
- ✅ Use HTTPS in production
- ✅ Validate all user input with Pydantic
- ✅ Keep dependencies updated

---

## Common Issues & Solutions

### Issue: "Database is locked"

**Solution:** Use WAL mode and connection pooling:

```python
await connection.execute("PRAGMA journal_mode = WAL")
```

### Issue: Embeddings too slow

**Solution:** Use batch processing and smaller model:

```python
# Use smaller model
EmbeddingService(model_name="all-MiniLM-L6-v2")  # Fast

# Or batch embed
embeddings = service.embed_batch(list_of_1000_texts)
```

### Issue: OOM (out of memory) with large documents

**Solution:** Process in chunks:

```python
def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200):
    """Split text into overlapping chunks."""
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunks.append(text[i:i + chunk_size])
    return chunks
```

---
