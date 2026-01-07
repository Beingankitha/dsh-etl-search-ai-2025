"""
API routes module - FastAPI routers for all endpoints.

Organized by domain:
- health: System status and diagnostics
- search: Semantic dataset search
- datasets: Dataset collection access
- chat: Conversational interface with RAG
"""

from .health import router as health_router
from .search import router as search_router
from .datasets import router as datasets_router
from .chat import router as chat_router

__all__ = [
    "health_router",
    "search_router",
    "datasets_router",
    "chat_router",
]