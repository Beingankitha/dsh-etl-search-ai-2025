"""
Architecture Module - System Design Documentation and Reference

This module contains high-level architectural documentation for the DSH ETL Search AI system.
It serves as a reference for understanding the system design, patterns, and rationale behind
implementation decisions.

Contents:
    - System architecture overview
    - Component interactions
    - Design patterns used
    - Data flow diagrams
    - Technology decisions
    - Scalability considerations
    - Future extensibility points

Purpose:
    This module is primarily documentation-focused and is useful for:
    - Onboarding new developers
    - Understanding the overall system design
    - Making informed decisions about future enhancements
    - Documenting architectural patterns and principles

Usage:
    See etl_architecture.py for detailed architecture documentation and diagrams.
    
    from src.services.architecture import (
        read_architecture_documentation,
        get_component_overview,
        describe_data_flow
    )
    
    # View architecture documentation
    docs = read_architecture_documentation()
    print(docs)
    
    # Understanding the three-phase pipeline:
    # 1. EXTRACT: Fetch data from external sources (CEH API, web, files)
    # 2. TRANSFORM: Parse and normalize data into domain models
    # 3. LOAD: Persist data to database with transaction management

Note:
    This module is documentation and reference material. For actual implementation,
    refer to the other service modules (etl, parsers, extractors, etc.)
"""

try:
    from .etl_architecture import (
        ARCHITECTURE_OVERVIEW,
        COMPONENT_DIAGRAM,
        DATA_FLOW_DIAGRAM,
        DESIGN_PATTERNS,
    )
    
    __all__ = [
        "ARCHITECTURE_OVERVIEW",
        "COMPONENT_DIAGRAM",
        "DATA_FLOW_DIAGRAM",
        "DESIGN_PATTERNS",
    ]
except ImportError:
    # If etl_architecture doesn't export these, provide empty exports
    __all__ = []
