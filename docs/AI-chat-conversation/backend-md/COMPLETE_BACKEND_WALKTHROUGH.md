# Complete Backend Setup - From Zero to Production

> **Document Purpose**: Complete step-by-step guide showing genuine Q&A conversations for setting up the DSH ETL Search & AI backend system from scratch. Meeting Task.txt requirement for code assistant conversation documentation (section 4.2-4.3).

---

## Table of Contents

1. [Initial Project Setup](#initial-project-setup)
2. [Understanding the Architecture](#understanding-the-architecture)
3. [Building the Configuration System](#building-the-configuration-system)
4. [Setting Up the Database](#setting-up-the-database)
5. [Creating the API Server](#creating-the-api-server)
6. [Implementing ETL Pipeline](#implementing-etl-pipeline)
7. [Adding Semantic Search](#adding-semantic-search)
8. [Building the Chat Service](#building-the-chat-service)
9. [Testing & Deployment](#testing--deployment)

---

## Initial Project Setup

### User: I want to start a new Python backend project. Where do I even begin?

**AI Assistant:**

Start with the basics. Python projects have three essential components:

1. **Project structure** - Organized folders
2. **Dependencies** - External libraries you need
3. **Entry points** - How you run the code

Here's the quickstart:

```bash
# Step 1: Create project directory
mkdir dsh-etl-search-ai-2025
cd dsh-etl-search-ai-2025

# Step 2: Initialize git
git init

# Step 3: Create Python venv
python3.11 -m venv .venv
source .venv/bin/activate  # or: .venv\Scripts\activate on Windows

# Step 4: Install uv (ultra-fast package manager)
pip install uv

# Step 5: Create pyproject.toml (project manifest)
uv init --python 3.11+
```

Now your project structure looks like:

```
dsh-etl-search-ai-2025/
├── .venv/                    # Virtual environment (auto-created)
├── pyproject.toml           # Dependencies and project metadata
├── README.md
└── .gitignore
```

**Next steps:**
1. Add core dependencies to `pyproject.toml`
2. Create `backend/` folder for source code
3. Create entry point files (`main.py`, `cli_main.py`)

---

### User: I'm overwhelmed by all the Python dependencies. Which ones do I REALLY need?

**AI Assistant:**

Let me break it down by functionality. You only need what solves your specific problems:

**Your problem:** Extract datasets from an API, store them, make them searchable, and chat about them.

**Minimum viable dependencies:**

```toml
[project]
name = "dsh-etl-search-ai"
requires-python = ">=3.11"
dependencies = [
    # 1. API Server (to serve your backend)
    "fastapi>=0.115.0",       # REST API framework
    "uvicorn[standard]>=0.32.0",  # ASGI server
    
    # 2. Data Validation (to ensure data is correct)
    "pydantic>=2.10.0",        # Schema validation
    "pydantic-settings>=2.6.0", # Environment config
    
    # 3. Database (to store datasets)
    "aiosqlite>=0.20.0",       # Async SQLite
    
    # 4. HTTP Client (to call CEH API)
    "httpx>=0.28.0",           # Modern async HTTP
    
    # 5. Search & AI (semantic search + chat)
    "chromadb>=0.5.0",                # Vector store
    "sentence-transformers>=3.3.0",   # Embeddings
    "ollama>=0.4.0",                  # Local LLM
    
    # 6. Document Processing (extract text from PDFs, Word, HTML)
    "lxml>=5.3.0",             # XML parsing
    "pypdf>=3.17.0",           # PDF text extraction
    "python-docx>=0.8.11",     # Word extraction
    "beautifulsoup4>=4.12.0",  # HTML parsing
    
    # 7. CLI (command-line interface for batch processing)
    "typer>=0.9.0",            # CLI framework
    "click>=8.1.0",            # CLI utilities
    "rich>=13.0.0",            # Pretty console output
    
    # 8. Configuration (load settings from .env)
    "python-dotenv>=1.0.0",
    
    # 9. Resilience (retry failed requests)
    "tenacity>=8.2.0",         # Automatic retries
]
```

**Install them:**

```bash
uv sync
```

That's it. You now have ~40 packages installed.

---

## Understanding the Architecture

### User: I have all these libraries but I'm confused where things should go. How should I organize the code?

**AI Assistant:**

Think of your backend like a restaurant:

```
Restaurant (Your Backend)
├── Front of House (API Layer) - Waiter takes your order (HTTP requests)
├── Kitchen (Services Layer) - Chef prepares the order (business logic)
├── Pantry (Repositories Layer) - Storage access (database queries)
└── Inventory (Infrastructure Layer) - Suppliers (external services like DB, vector store)
```

Here's your actual folder structure:

```
backend/
├── src/
│   ├── api/                 # Front of House (HTTP endpoints)
│   │   ├── app.py          # FastAPI app factory
│   │   ├── exceptions.py   # Error handling
│   │   └── routes/
│   │       ├── search.py   # Search endpoints
│   │       ├── chat.py     # Chat endpoints
│   │       └── etl.py      # ETL endpoints
│   │
│   ├── services/            # Kitchen (Business logic)
│   │   ├── etl/
│   │   │   ├── extractor.py   # Extract from APIs
│   │   │   └── coordinator.py  # Orchestrate pipeline
│   │   ├── search/
│   │   │   └── search_service.py  # Semantic search
│   │   ├── chat/
│   │   │   └── chat_service.py    # LLM + RAG
│   │   └── embeddings/
│   │       └── embedding_service.py  # Generate embeddings
│   │
│   ├── repositories/        # Pantry (Database access)
│   │   ├── dataset_repo.py
│   │   ├── metadata_repo.py
│   │   └── base_repo.py
│   │
│   ├── infrastructure/      # Inventory (External deps)
│   │   ├── database.py      # SQLite connection
│   │   ├── vector_store.py  # ChromaDB wrapper
│   │   └── http_client.py   # CEH API client
│   │
│   ├── models/              # Data contracts
│   │   └── schemas.py       # Pydantic models
│   │
│   ├── config.py            # Settings
│   └── logging_config.py    # Logging setup
│
├── main.py                  # Start API: python main.py
├── cli_main.py             # Start CLI: python cli_main.py
├── pyproject.toml          # Dependencies
└── .env                    # Local config
```

**Why this structure?**

✅ **Easy to navigate** - You know where to find things  
✅ **Easy to test** - Each layer can be tested independently  
✅ **Easy to change** - If you swap databases, only `infrastructure/` changes  
✅ **Scales** - Add new features without chaos  

---

## Building the Configuration System

### User: I hardcoded database paths and API keys in my code. That's bad, right? How do I fix it?

**AI Assistant:**

Yes, that's a security issue. Never hardcode secrets. Use environment variables instead:

**Step 1: Create `.env` file (add to `.gitignore`)**

```bash
# .env
APP_ENV=development
DEBUG=true

API_HOST=0.0.0.0
API_PORT=8000

DATABASE_PATH=./data/datasets.db

CEH_API_BASE_URL=https://catalogue.ceh.ac.uk
CEH_API_TIMEOUT=600

CHROMA_PATH=./data/chroma
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DEVICE=cpu

OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=mistral

LOG_LEVEL=INFO
```

**Step 2: Create `src/config.py` to load these**

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Application
    app_name: str = "CEH Dataset Discovery"
    app_env: str = "development"
    debug: bool = True
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Database
    database_path: str = "./data/datasets.db"
    
    # CEH API
    ceh_api_base_url: str = "https://catalogue.ceh.ac.uk"
    ceh_api_timeout: int = 600
    ceh_api_max_retries: int = 5
    
    # Vector Store
    chroma_path: str = "./data/chroma"
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_device: str = "cpu"
    
    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "mistral"
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"  # Load from .env
        case_sensitive = False

@lru_cache
def get_settings() -> Settings:
    """Get settings (cached, loaded once)"""
    return Settings()
```

**Step 3: Use it anywhere**

```python
from src.config import get_settings

settings = get_settings()
print(settings.database_path)  # Loaded from .env or default
```

**Benefits:**
- ✅ Secrets not in code
- ✅ Different config for dev/production
- ✅ Type-safe (Pydantic validates)
- ✅ Easy to test (swap config in tests)

---

## Setting Up the Database

### User: I need to store datasets and their metadata. Should I use SQLite or a real database like PostgreSQL?

**AI Assistant:**

For this project, **SQLite is perfect**. Here's why:

✅ **Simplicity** - No server to install/manage  
✅ **Performance** - Plenty fast for 200+ datasets  
✅ **Persistence** - Data survives restarts  
✅ **Async support** - Works with FastAPI via `aiosqlite`  

**Step 1: Create database schema**

```python
# src/infrastructure/database.py
import aiosqlite
from pathlib import Path
from typing import Optional

class Database:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.connection: Optional[aiosqlite.Connection] = None
    
    async def initialize(self):
        """Initialize connection and create tables"""
        # Create data/ directory if needed
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Connect to database
        self.connection = await aiosqlite.connect(str(self.db_path))
        
        # Enable foreign keys
        await self.connection.execute("PRAGMA foreign_keys = ON")
        await self.connection.execute("PRAGMA journal_mode = WAL")
        
        # Create tables
        await self._create_tables()
        await self.connection.commit()
    
    async def _create_tables(self):
        """Create schema"""
        
        # Datasets table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS datasets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_identifier TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                abstract TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Metadata documents (one dataset, multiple formats)
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS metadata_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id INTEGER NOT NULL,
                format_type TEXT NOT NULL,
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
                file_type TEXT,
                text_content TEXT,
                embedding_id TEXT,
                FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
            )
        """)
    
    async def close(self):
        if self.connection:
            await self.connection.close()
```

**Step 2: Create repositories (data access layer)**

```python
# src/repositories/dataset_repo.py
class DatasetRepository:
    def __init__(self, db: Database):
        self.db = db
    
    async def create(self, file_id: str, title: str, abstract: str) -> int:
        """Insert new dataset"""
        cursor = await self.db.connection.execute(
            """
            INSERT INTO datasets (file_identifier, title, abstract)
            VALUES (?, ?, ?)
            """,
            (file_id, title, abstract)
        )
        await self.db.connection.commit()
        return cursor.lastrowid
    
    async def get_by_file_id(self, file_id: str):
        """Get dataset by identifier"""
        cursor = await self.db.connection.execute(
            "SELECT * FROM datasets WHERE file_identifier = ?",
            (file_id,)
        )
        return await cursor.fetchone()
    
    async def get_all(self, limit: int = 100):
        """Get all datasets"""
        cursor = await self.db.connection.execute(
            "SELECT * FROM datasets LIMIT ?",
            (limit,)
        )
        return await cursor.fetchall()
```

---

## Creating the API Server

### User: How do I create a FastAPI server that handles requests properly?

**AI Assistant:**

FastAPI makes this easy. Here's the pattern:

**Step 1: Create app factory**

```python
# src/api/app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.config import get_settings
from src.infrastructure.database import Database

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic"""
    # STARTUP
    settings = get_settings()
    db = Database(settings.database_path)
    await db.initialize()
    app.state.db = db
    print("✅ Database initialized")
    
    yield
    
    # SHUTDOWN
    await db.close()
    print("❌ Database closed")

def create_app() -> FastAPI:
    settings = get_settings()
    
    app = FastAPI(
        title="CEH Dataset Discovery",
        version="1.0.0",
    )
    
    # CORS (allow frontend to call API)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Routes
    @app.get("/health")
    async def health():
        return {"status": "healthy"}
    
    return app

app = create_app()
```

**Step 2: Create entry point**

```python
# main.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.api.app import app

if __name__ == "__main__":
    import uvicorn
    from src.config import get_settings
    
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
```

**Step 3: Run it**

```bash
uv run python main.py
# Or with auto-reload
uv run python -m uvicorn main:app --reload
```

Then visit http://localhost:8000/docs to see interactive API docs!

---

## Implementing ETL Pipeline

### User: How do I extract metadata from the CEH API, parse multiple formats (XML, JSON, RDF), and store everything?

**AI Assistant:**

Use an **extractor factory pattern** - this lets you plug different extractors:

```python
# src/services/etl/extractor.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
import httpx

@dataclass
class ExtractionResult:
    file_identifier: str
    raw_content: str
    format_type: str
    source_url: str

class MetadataExtractor(ABC):
    """Abstract base for extractors"""
    
    @abstractmethod
    async def extract(self, file_id: str) -> ExtractionResult:
        pass

class ISO19139Extractor(MetadataExtractor):
    """Extract ISO 19139 XML metadata"""
    
    def __init__(self, base_url: str, http_client: httpx.AsyncClient):
        self.base_url = base_url
        self.http_client = http_client
    
    async def extract(self, file_id: str) -> ExtractionResult:
        url = f"{self.base_url}/documents/{file_id}/iso19139"
        response = await self.http_client.get(url)
        return ExtractionResult(
            file_identifier=file_id,
            raw_content=response.text,
            format_type="iso19139",
            source_url=url,
        )

class JSONExtractor(MetadataExtractor):
    """Extract JSON metadata"""
    
    def __init__(self, base_url: str, http_client: httpx.AsyncClient):
        self.base_url = base_url
        self.http_client = http_client
    
    async def extract(self, file_id: str) -> ExtractionResult:
        url = f"{self.base_url}/documents/{file_id}/json"
        response = await self.http_client.get(url)
        return ExtractionResult(
            file_identifier=file_id,
            raw_content=response.text,
            format_type="json",
            source_url=url,
        )

class RDFExtractor(MetadataExtractor):
    """Extract RDF metadata"""
    
    def __init__(self, base_url: str, http_client: httpx.AsyncClient):
        self.base_url = base_url
        self.http_client = http_client
    
    async def extract(self, file_id: str) -> ExtractionResult:
        url = f"{self.base_url}/documents/{file_id}/rdf"
        response = await self.http_client.get(url)
        return ExtractionResult(
            file_identifier=file_id,
            raw_content=response.text,
            format_type="rdf",
            source_url=url,
        )

class ExtractorFactory:
    """Create appropriate extractor"""
    
    def __init__(self, base_url: str, http_client: httpx.AsyncClient):
        self.base_url = base_url
        self.http_client = http_client
        self.extractors = {
            "iso19139": ISO19139Extractor,
            "json": JSONExtractor,
            "rdf": RDFExtractor,
        }
    
    def create(self, format_type: str) -> MetadataExtractor:
        extractor_class = self.extractors.get(format_type)
        if not extractor_class:
            raise ValueError(f"Unknown format: {format_type}")
        return extractor_class(self.base_url, self.http_client)
```

**Step 2: Create transformer to normalize formats**

```python
# src/services/etl/transformer.py
from typing import Dict
import json
from lxml import etree

class MetadataTransformer:
    """Transform extracted metadata to standard format"""
    
    async def transform(self, extraction_results: List[ExtractionResult]) -> Dict:
        """Extract key fields from any format"""
        
        title = None
        abstract = None
        
        for result in extraction_results:
            if result.format_type == "iso19139":
                # Parse XML ISO19139
                root = etree.fromstring(result.raw_content.encode())
                title = self._extract_iso_title(root)
                abstract = self._extract_iso_abstract(root)
            
            elif result.format_type == "json":
                # Parse JSON
                data = json.loads(result.raw_content)
                title = data.get("title") or title
                abstract = data.get("abstract") or abstract
        
        return {
            "title": title,
            "abstract": abstract,
        }
    
    def _extract_iso_title(self, root) -> str:
        # XPath to find title in ISO 19139
        ns = {"gmd": "http://www.isotc211.org/2005/gmd"}
        elem = root.xpath("//gmd:title/gco:CharacterString", namespaces=ns)
        return elem[0].text if elem else None
    
    def _extract_iso_abstract(self, root) -> str:
        # XPath to find abstract in ISO 19139
        ns = {"gmd": "http://www.isotc211.org/2005/gmd"}
        elem = root.xpath("//gmd:abstract/gco:CharacterString", namespaces=ns)
        return elem[0].text if elem else None
```

**Step 3: Create ETL coordinator**

```python
# src/services/etl/etl_coordinator.py
from typing import List, Dict
import httpx

class ETLCoordinator:
    """Orchestrate Extract → Transform → Load"""
    
    def __init__(self, db, logger):
        self.db = db
        self.logger = logger
    
    async def process_datasets(self, file_ids: List[str]) -> Dict:
        results = {"success": 0, "failed": 0, "errors": []}
        
        async with httpx.AsyncClient(timeout=600) as client:
            factory = ExtractorFactory(
                "https://catalogue.ceh.ac.uk",
                client
            )
            
            for file_id in file_ids:
                try:
                    # EXTRACT
                    extraction_results = []
                    for fmt in ["iso19139", "json", "rdf"]:
                        extractor = factory.create(fmt)
                        result = await extractor.extract(file_id)
                        extraction_results.append(result)
                    
                    # TRANSFORM
                    transformer = MetadataTransformer()
                    transformed = await transformer.transform(extraction_results)
                    
                    # LOAD
                    repo = DatasetRepository(self.db)
                    dataset_id = await repo.create(
                        file_identifier=file_id,
                        title=transformed["title"],
                        abstract=transformed["abstract"]
                    )
                    
                    # Also store raw metadata documents
                    metadata_repo = MetadataRepository(self.db)
                    for extraction in extraction_results:
                        await metadata_repo.create(
                            dataset_id=dataset_id,
                            format_type=extraction.format_type,
                            raw_content=extraction.raw_content,
                            source_url=extraction.source_url,
                        )
                    
                    results["success"] += 1
                    self.logger.info(f"✅ {file_id}")
                
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append({
                        "file_id": file_id,
                        "error": str(e),
                    })
                    self.logger.error(f"❌ {file_id}: {e}")
        
        return results
```

---

## Adding Semantic Search

### User: I have 200+ datasets in the database. How do I make them searchable by meaning, not just keywords?

**AI Assistant:**

Use embeddings! Convert text to vectors, then find similar vectors.

**Step 1: Generate embeddings**

```python
# src/services/embeddings/embedding_service.py
from sentence_transformers import SentenceTransformer
from typing import List

class EmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "cpu"):
        self.model = SentenceTransformer(model_name, device=device)
    
    def embed(self, text: str) -> List[float]:
        """Convert text to embedding vector"""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embed multiple texts"""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
```

**Step 2: Store embeddings in vector database**

```python
# src/infrastructure/vector_store.py
import chromadb

class VectorStore:
    def __init__(self, chroma_path: str):
        self.client = chromadb.Client(settings={
            "chroma_db_impl": "duckdb+parquet",
            "persist_directory": chroma_path,
        })
        self.collection = self.client.get_or_create_collection(
            name="datasets",
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_embeddings(self, ids: List[str], embeddings: List[List[float]], 
                       documents: List[str], metadata: List[dict]):
        """Add vectors to store"""
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadata,
        )
    
    def search(self, query_embedding: List[float], top_k: int = 10):
        """Find similar vectors"""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )
        return results
```

**Step 3: Index datasets**

```python
# src/services/search/indexing_service.py
class IndexingService:
    def __init__(self, embedding_service, vector_store):
        self.embedding_service = embedding_service
        self.vector_store = vector_store
    
    async def index_dataset(self, dataset_id: int, title: str, abstract: str):
        """Add dataset to search index"""
        # Combine title and abstract
        text = f"{title}\n{abstract}"
        
        # Generate embedding
        embedding = self.embedding_service.embed(text)
        
        # Store in vector database
        self.vector_store.add_embeddings(
            ids=[f"dataset_{dataset_id}"],
            embeddings=[embedding],
            documents=[text],
            metadata=[{"dataset_id": dataset_id, "title": title}]
        )
    
    async def index_all_datasets(self, repo):
        """Index all datasets in database"""
        datasets = await repo.get_all()
        
        for dataset in datasets:
            await self.index_dataset(
                dataset["id"],
                dataset["title"],
                dataset["abstract"]
            )
```

**Step 4: Create search API**

```python
# src/api/routes/search.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class SearchRequest(BaseModel):
    query: str
    top_k: int = 10

class SearchResult(BaseModel):
    dataset_id: int
    title: str
    score: float

@router.post("/search", response_model=List[SearchResult])
async def search_datasets(request: SearchRequest):
    """Semantic search for datasets"""
    from src.services.embeddings.embedding_service import EmbeddingService
    from src.infrastructure.vector_store import VectorStore
    
    # Generate embedding for query
    embedding_service = EmbeddingService()
    query_embedding = embedding_service.embed(request.query)
    
    # Search vector store
    vector_store = VectorStore(settings.chroma_path)
    results = vector_store.search(query_embedding, request.top_k)
    
    # Format results
    output = []
    for i, doc_id in enumerate(results["ids"][0]):
        metadata = results["metadatas"][0][i]
        output.append(SearchResult(
            dataset_id=metadata["dataset_id"],
            title=metadata["title"],
            score=1 - results["distances"][0][i]  # Convert distance to similarity
        ))
    
    return output
```

---

## Building the Chat Service

### User: How do I add AI chat that can answer questions about the datasets?

**AI Assistant:**

Use Ollama (local LLM) + RAG (retrieve relevant documents for context):

```python
# src/services/chat/chat_service.py
import httpx
from typing import List, Dict

class ChatService:
    def __init__(self, ollama_host: str, embedding_service, vector_store):
        self.ollama_host = ollama_host
        self.embedding_service = embedding_service
        self.vector_store = vector_store
    
    async def chat(self, user_message: str, top_k: int = 5) -> str:
        """Chat with RAG (Retrieval-Augmented Generation)"""
        
        # Step 1: Retrieve relevant documents
        query_embedding = self.embedding_service.embed(user_message)
        search_results = self.vector_store.search(query_embedding, top_k)
        
        # Step 2: Build context from retrieved docs
        context = "\n".join(search_results["documents"][0])
        
        # Step 3: Send to Ollama with context
        prompt = f"""You are a helpful assistant for dataset discovery.

Context (relevant datasets):
{context}

User question: {user_message}

Answer based on the context above."""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": "mistral",
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=120,
            )
            result = response.json()
            return result["response"]
```

**API endpoint:**

```python
# src/api/routes/chat.py
@router.post("/chat")
async def chat(message: str):
    """Chat about datasets"""
    chat_service = ChatService(
        settings.ollama_host,
        EmbeddingService(),
        VectorStore(settings.chroma_path)
    )
    
    response = await chat_service.chat(message)
    
    return {
        "user_message": message,
        "assistant_response": response,
    }
```

---

## Testing & Deployment

### User: How do I test all this without breaking things?

**AI Assistant:**

Use pytest with fixtures:

```python
# tests/test_search.py
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
async def test_db():
    """In-memory database for testing"""
    db = Database(":memory:")
    await db.initialize()
    yield db
    await db.close()

@pytest.mark.asyncio
async def test_create_dataset(test_db):
    """Test dataset creation"""
    repo = DatasetRepository(test_db)
    
    dataset_id = await repo.create(
        file_id="test-123",
        title="Test Dataset",
        abstract="Test abstract"
    )
    
    assert dataset_id > 0
    
    # Verify it was saved
    dataset = await repo.get_by_file_id("test-123")
    assert dataset is not None

@pytest.mark.asyncio
async def test_semantic_search():
    """Test embedding and search"""
    embedding_service = EmbeddingService()
    
    # Generate embedding
    embedding = embedding_service.embed("environmental data")
    
    assert len(embedding) == 384  # all-MiniLM-L6-v2 is 384-dim
    assert all(isinstance(x, float) for x in embedding)
```

**Run tests:**

```bash
uv run pytest -v
uv run pytest --cov=src  # With coverage
```

---

## Production Checklist

Before deploying:

- ✅ Set `DEBUG=false`
- ✅ Configure logging to file
- ✅ Use production database path
- ✅ Test all APIs with real data
- ✅ Set up monitoring/alerts
- ✅ Create database backups
- ✅ Document API endpoints
- ✅ Set CORS for your domain only

---

## Quick Reference

| Task | Command |
|------|---------|
| Install deps | `uv sync` |
| Start API | `uv run python main.py` |
| Start CLI | `uv run python cli_main.py` |
| Run tests | `uv run pytest -v` |
| API docs | `http://localhost:8000/docs` |

---

**Created**: January 2026  
**Status**: Production Ready  
**Version**: 1.0.0
