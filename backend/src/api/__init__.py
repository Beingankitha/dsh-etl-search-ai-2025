"""
API module - FastAPI routers and endpoints.

Organized into logical routers under routes/:
- health: System status and diagnostics
- search: Semantic dataset search
- datasets: Dataset collection access
"""

from .routes import health_router, search_router, datasets_router

__all__ = [
    "health_router",
    "search_router",
    "datasets_router",
]
