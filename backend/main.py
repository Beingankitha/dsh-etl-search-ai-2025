"""
FastAPI application entry point.

This is the main entry point for the FastAPI server serving the Dataset 
Search & Discovery API.

Usage:
    Development (with auto-reload):
        uv run uvicorn main:app --reload
        
    Production:
        uv run uvicorn main:app --host 0.0.0.0 --port 8000
        
    Direct Python execution:
        uv run python main.py
"""

import sys
from pathlib import Path

# Add backend directory to path for imports
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from src.api.app import app

if __name__ == "__main__":
    import uvicorn
    from src.config import get_settings
    
    settings = get_settings()
    
    # Use import string for app to enable reload functionality
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )