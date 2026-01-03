#!/usr/bin/env python3
"""
CLI Entry point for DSH ETL Search AI.

This script provides command-line interface for ETL operations, configuration, and management.

Usage:
    uv run python cli_main.py etl --help
    uv run python cli_main.py etl --limit 10 --verbose
    uv run python cli_main.py validate-config
    uv run python cli_main.py etl --dry-run
"""

import sys
from pathlib import Path

# Add backend directory to path for imports
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from src.cli import app

if __name__ == '__main__':
    app()