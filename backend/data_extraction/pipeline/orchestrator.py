"""
Pipeline orchestrator for the data extraction system.

Coordinates the full extraction pipeline:
1. Raw data extraction from multiple sources
2. Data cleaning and normalization
3. Calculation of derived fields
4. Technical indicator computation
5. Validation against scoring rules
6. Quality assessment
7. Storage to MongoDB
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config.field_definitions import FIELD_BY_NAME, TOTAL_FIELDS
from ..extractors.base_extractor import BaseExtractor
from ..extractors.nse_bhavcopy import NSEBhavcopyExtractor
from ..extractors.yfinance_extractor import YFinanceExtractor
from ..models.extraction_models import (
    ExtractionRecord, ExtractionStatus, PipelineJob, StockDataRecord, QualityReport,
)
from ..processors.calculation_engine import CalculationEngine
from ..processors.technical_calculator import TechnicalCalculator
from ..processors.validation_engine import ValidationEngine
from ..processors.cleaner import DataCleaner
from ..quality.confidence_scorer import ConfidenceScorer

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Orchestrates the complete data extraction and processing pipeline.

    Usage:
        orchestrator = PipelineOrchestrator()
        await orchestrator.initialize()
        results = await orchestrator.run(["RELIANCE", "TCS", "INFY"])
        await orchestrator.close()
    """

    def __init__(self, db=None):
        """
        Initialize the orchestrator.

        Args:
            db: Optional MongoDB database instance for persistence
        """
        self.db = db

        # Processors
        self.calculation_engine = CalculationEngine()
        self.technical_calculator = TechnicalCalculator()
        self.validation_engine = ValidationEngine()
        self.cleaner = DataCleaner()
        self.confidence_scorer = ConfidenceScorer()

        # Extractors (initialized lazily)
        self._extractors: List[BaseExtractor] = []
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all extractors and establish connections."""
        if self._initialized:
            return

        # Create extractor instances
        self._extractors = [
            NSEBhavcopyExtractor(),
            YFinanceExtractor(),
        ]

        # Initialize each extractor
        for extractor in self._extractors:
            try:
                await extractor.initialize()
                logger.info(f"Initialized extractor: {extractor.get_source_name()}")
            except Exception as e:
                logger.error(f"Failed to initialize {extractor.get_source_name()}: {e}")

        self._initialized = True
        logger.info(f"Pipeline initialized with {len(self._extractors)} extractors")

    async def close(self) -> None:
        """Close all extractors and clean up resources."""
        for extractor in self._extractors:
            try:
                await extractor.close()
            except Exception as e:
                logger.error(f"Error closing {extractor.get_source_name()}: {e}")
        self._initialized = False

    async def run(
        self,
        symbols: List[str],
        sources: Optional[List[str]] = None,
    ) -> PipelineJob:
        """
        Run the full extraction pipeline for a list of symbols.

        Args:
            symbols: List of stock symbols to process
            sources: Optional list of source names to use (default: all)

        Returns:
            PipelineJob with results and status
        """
        if not self._initialized:
            await self.initialize()

        job = PipelineJob(
            job_id=str(uuid.uuid4()),
            symbols=symbols,
            sources=sources or [e.get_source_name() for e in self._extractors],
            status=ExtractionStatus.RUNNING,
            started_at=datetime.utcnow(),
            total_symbols=len(symbols),
        )

        records: Dict[str, StockDataRecord] = {}
        logger.info(f"Starting pipeline job {job.job_id} for {len(symbols)} symbols")

        for symbol in symbols:
            try:
                record = await self._process_symbol(symbol, sources)
                records[symbol] = record
                job.processed_symbols += 1
                logger.info(
                    f"[{job.processed_symbols}/{job.total_symbols}] "
                    f"{symbol}: {record.get_completeness():.1f}% complete"
                )
            except Exception as e:
                logger.error(f"Pipeline failed for {symbol}: {e}")
                job.failed_symbols += 1
                job.errors.append(f"{symbol}: {str(e)}")

        # Store results if DB available
        if self.db is not None:
            await self._store_results(records)

        job.completed_at = datetime.utcnow()
        job.status = (
            ExtractionStatus.SUCCESS if job.failed_symbols == 0
            else ExtractionStatus.PARTIAL if job.processed_symbols > 0
            else ExtractionStatus.FAILED
        )

        logger.info(
            f"Pipeline job {job.job_id} completed: "
            f"{job.processed_symbols} processed, {job.failed_symbols} failed"
        )

        return job

    async def _process_symbol(
        self,
        symbol: str,
        sources: Optional[List[str]] = None,
    ) -> StockDataRecord:
        """
        Run the full pipeline for a single symbol.

        Steps:
            1. Extract raw data from all sources
            2. Clean and normalize data
            3. Calculate derived fields
            4. Calculate technical indicators
            5. Run validation rules
            6. Score data quality/confidence
        """
        record = StockDataRecord(symbol=symbol, company_name="")

        # Step 1: Extract from all sources
        for extractor in self._extractors:
            if sources and extractor.get_source_name() not in sources:
                continue
            try:
                extraction = await extractor.extract(symbol, record)
                record.extraction_history.append(extraction)
                logger.debug(
                    f"{symbol} [{extractor.get_source_name()}]: "
                    f"{len(extraction.fields_extracted)} fields extracted"
                )
            except Exception as e:
                logger.warning(
                    f"{symbol} [{extractor.get_source_name()}] extraction error: {e}"
                )

        # Step 2: Clean and normalize
        cleaned_count = self.cleaner.clean_record(record)
        logger.debug(f"{symbol}: cleaned {cleaned_count} fields")

        # Step 3: Calculate derived fields
        calc_fields = self.calculation_engine.calculate_all(record)
        logger.debug(f"{symbol}: calculated {len(calc_fields)} derived fields")

        # Step 4: Calculate technical indicators
        tech_fields = self.technical_calculator.calculate_all(record)
        logger.debug(f"{symbol}: calculated {len(tech_fields)} technical indicators")

        # Step 5: Validate against scoring rules
        validation = self.validation_engine.validate_all(record)
        record.qualitative_metadata["validation_result"] = {
            "is_investable": validation["is_investable"],
            "deal_breakers_triggered": len(validation["triggered_deal_breakers"]),
            "risk_penalties_triggered": len(validation["triggered_risk_penalties"]),
            "quality_boosters_triggered": len(validation["triggered_quality_boosters"]),
            "net_adjustment": validation["net_adjustment"],
        }

        # Step 6: Score quality/confidence
        quality = self.confidence_scorer.score(record)
        record.qualitative_metadata["quality_report"] = {
            "completeness": quality.completeness_score,
            "freshness": quality.freshness_score,
            "source_agreement": quality.source_agreement_score,
            "overall_confidence": quality.overall_confidence,
            "missing_critical": quality.missing_critical_fields,
        }

        # Update company name if extracted
        if record.get_field("company_name"):
            record.company_name = record.get_field("company_name")

        return record

    async def run_single(self, symbol: str) -> StockDataRecord:
        """Convenience method to process a single symbol."""
        if not self._initialized:
            await self.initialize()
        return await self._process_symbol(symbol)

    async def _store_results(self, records: Dict[str, StockDataRecord]) -> None:
        """Store extraction results to MongoDB."""
        if self.db is None:
            return

        collection = self.db["stock_data"]
        for symbol, record in records.items():
            try:
                doc = record.to_dict()
                await collection.update_one(
                    {"symbol": symbol},
                    {"$set": doc},
                    upsert=True,
                )
            except Exception as e:
                logger.error(f"Error storing {symbol} to MongoDB: {e}")

    def get_extraction_summary(self, job: PipelineJob) -> Dict[str, Any]:
        """Generate a human-readable summary of a pipeline run."""
        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "total_symbols": job.total_symbols,
            "processed": job.processed_symbols,
            "failed": job.failed_symbols,
            "progress": f"{job.progress_pct:.1f}%",
            "duration_seconds": (
                (job.completed_at - job.started_at).total_seconds()
                if job.completed_at and job.started_at else None
            ),
            "sources_used": job.sources,
            "errors": job.errors[:10],  # Limit error output
        }
