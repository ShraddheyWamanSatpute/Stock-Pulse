"""
StockPulse Data Extraction System

Comprehensive data pipeline for collecting, processing, validating, and storing
all 160 data fields required by the StockPulse Indian Stock Analysis Platform.

Modules:
    config      - Field definitions, source configuration, validation rules
    models      - Data models for the extraction pipeline
    extractors  - Source-specific extraction modules
    processors  - Calculation engine, validation engine, data cleaning
    pipeline    - Orchestration, scheduling, dependency management
    quality     - Completeness tracking, freshness monitoring, confidence scoring
    storage     - MongoDB storage layer
"""

__version__ = "1.0.0"
