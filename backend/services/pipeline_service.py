"""
Data Pipeline Service for StockPulse
Manages data extraction pipelines, scheduling, and monitoring
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import os
import uuid
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


class PipelineStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    SCHEDULED = "scheduled"


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PipelineJob:
    """Represents a data extraction job"""
    job_id: str
    pipeline_type: str
    symbols: List[str]
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_symbols: int = 0
    processed_symbols: int = 0
    successful_symbols: int = 0
    failed_symbols: int = 0
    errors: List[Dict] = field(default_factory=list)
    results: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "job_id": self.job_id,
            "pipeline_type": self.pipeline_type,
            "status": self.status.value,
            "symbols": self.symbols,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_symbols": self.total_symbols,
            "processed_symbols": self.processed_symbols,
            "successful_symbols": self.successful_symbols,
            "failed_symbols": self.failed_symbols,
            "progress_percent": round((self.processed_symbols / self.total_symbols * 100) if self.total_symbols > 0 else 0, 2),
            "errors": self.errors[-10:],  # Last 10 errors
            "duration_seconds": (
                (self.completed_at - self.started_at).total_seconds() 
                if self.completed_at and self.started_at else None
            )
        }


@dataclass
class PipelineMetrics:
    """Aggregated pipeline metrics"""
    total_jobs_run: int = 0
    successful_jobs: int = 0
    failed_jobs: int = 0
    total_symbols_processed: int = 0
    total_data_points_extracted: int = 0
    last_run_time: Optional[datetime] = None
    next_scheduled_run: Optional[datetime] = None
    avg_job_duration_seconds: float = 0
    uptime_since: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Data volume tracking
    expected_daily_symbols: int = 0
    received_daily_symbols: int = 0
    missing_symbols: List[str] = field(default_factory=list)
    delayed_symbols: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "total_jobs_run": self.total_jobs_run,
            "successful_jobs": self.successful_jobs,
            "failed_jobs": self.failed_jobs,
            "job_success_rate": round((self.successful_jobs / self.total_jobs_run * 100) if self.total_jobs_run > 0 else 0, 2),
            "total_symbols_processed": self.total_symbols_processed,
            "total_data_points_extracted": self.total_data_points_extracted,
            "last_run_time": self.last_run_time.isoformat() if self.last_run_time else None,
            "next_scheduled_run": self.next_scheduled_run.isoformat() if self.next_scheduled_run else None,
            "avg_job_duration_seconds": round(self.avg_job_duration_seconds, 2),
            "uptime_seconds": (datetime.now(timezone.utc) - self.uptime_since).total_seconds(),
            "expected_daily_symbols": self.expected_daily_symbols,
            "received_daily_symbols": self.received_daily_symbols,
            "data_completeness_percent": round(
                (self.received_daily_symbols / self.expected_daily_symbols * 100) 
                if self.expected_daily_symbols > 0 else 0, 2
            ),
            "missing_symbols_count": len(self.missing_symbols),
            "missing_symbols": self.missing_symbols[:20],  # First 20
            "delayed_symbols_count": len(self.delayed_symbols),
            "delayed_symbols": self.delayed_symbols[:20]  # First 20
        }


class DataPipelineService:
    """
    Central service for managing data extraction pipelines
    Handles scheduling, execution, and monitoring
    """
    
    # Default Indian stock symbols for extraction
    DEFAULT_SYMBOLS = [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
        "HINDUNILVR", "SBIN", "BHARTIARTL", "KOTAKBANK", "ITC",
        "LT", "AXISBANK", "BAJFINANCE", "ASIANPAINT", "MARUTI",
        "HCLTECH", "WIPRO", "ULTRACEMCO", "TITAN", "NESTLEIND",
        "SUNPHARMA", "BAJAJFINSV", "ONGC", "NTPC", "POWERGRID",
        "M&M", "TATASTEEL", "ADANIENT", "TECHM", "JSWSTEEL"
    ]
    
    def __init__(self, db=None, grow_extractor=None):
        """
        Initialize the data pipeline service
        
        Args:
            db: MongoDB database instance
            grow_extractor: GrowwAPIExtractor instance
        """
        self.db = db
        self.grow_extractor = grow_extractor
        
        # Pipeline state
        self.status = PipelineStatus.IDLE
        self.current_job: Optional[PipelineJob] = None
        
        # Job management
        self._jobs: Dict[str, PipelineJob] = {}
        self._job_history: List[Dict] = []
        
        # Metrics
        self.metrics = PipelineMetrics()
        self.metrics.expected_daily_symbols = len(self.DEFAULT_SYMBOLS)
        
        # Scheduler
        self._scheduler_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        # Extraction logs
        self._extraction_logs: List[Dict] = []
        
    async def initialize(self):
        """Initialize the pipeline service"""
        logger.info("Initializing Data Pipeline Service")
        
        if self.grow_extractor:
            await self.grow_extractor.initialize()
        
        # Load job history from database if available
        if self.db:
            try:
                history = await self.db.pipeline_jobs.find(
                    {}, {"_id": 0}
                ).sort("created_at", -1).limit(100).to_list(100)
                self._job_history = history
            except Exception as e:
                logger.warning(f"Could not load job history: {e}")
        
        logger.info("Data Pipeline Service initialized")
    
    async def start_scheduler(self, interval_minutes: int = 30):
        """Start the automatic extraction scheduler"""
        if self._scheduler_task and not self._scheduler_task.done():
            logger.warning("Scheduler already running")
            return
        
        self._is_running = True
        self._scheduler_task = asyncio.create_task(
            self._scheduler_loop(interval_minutes)
        )
        self.status = PipelineStatus.SCHEDULED
        self.metrics.next_scheduled_run = datetime.now(timezone.utc) + timedelta(minutes=interval_minutes)
        
        logger.info(f"Pipeline scheduler started with {interval_minutes} minute interval")
    
    async def stop_scheduler(self):
        """Stop the automatic extraction scheduler"""
        self._is_running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        self.status = PipelineStatus.IDLE
        self.metrics.next_scheduled_run = None
        logger.info("Pipeline scheduler stopped")
    
    async def _scheduler_loop(self, interval_minutes: int):
        """Internal scheduler loop"""
        while self._is_running:
            try:
                # Run extraction
                await self.run_extraction(self.DEFAULT_SYMBOLS)
                
                # Update next run time
                self.metrics.next_scheduled_run = datetime.now(timezone.utc) + timedelta(minutes=interval_minutes)
                
                # Wait for next interval
                await asyncio.sleep(interval_minutes * 60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                self._log_event("scheduler_error", {"error": str(e)})
                # Wait a bit before retrying
                await asyncio.sleep(60)
    
    async def run_extraction(
        self,
        symbols: Optional[List[str]] = None,
        extraction_type: str = "quotes"
    ) -> PipelineJob:
        """
        Run a data extraction job
        
        Args:
            symbols: List of stock symbols to extract (defaults to DEFAULT_SYMBOLS)
            extraction_type: Type of extraction ("quotes" or "historical")
            
        Returns:
            PipelineJob with extraction results
        """
        if symbols is None:
            symbols = self.DEFAULT_SYMBOLS
        
        # Create job
        job = PipelineJob(
            job_id=str(uuid.uuid4())[:12],
            pipeline_type=extraction_type,
            symbols=symbols,
            status=JobStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            total_symbols=len(symbols)
        )
        
        self._jobs[job.job_id] = job
        self.current_job = job
        self.status = PipelineStatus.RUNNING
        
        self._log_event("job_started", {
            "job_id": job.job_id,
            "type": extraction_type,
            "symbol_count": len(symbols)
        })
        
        try:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)
            
            if not self.grow_extractor:
                raise Exception("Groww extractor not initialized")
            
            # Run extraction based on type
            if extraction_type == "quotes":
                results = await self.grow_extractor.extract_bulk_quotes(symbols)
            else:
                # For historical data, we'd need more parameters
                results = await self.grow_extractor.extract_bulk_quotes(symbols)
            
            # Process results
            received_symbols = []
            for symbol, result in results.items():
                job.processed_symbols += 1
                
                if result.status.value == "success":
                    job.successful_symbols += 1
                    received_symbols.append(symbol)
                    job.results[symbol] = result.data
                else:
                    job.failed_symbols += 1
                    job.errors.append({
                        "symbol": symbol,
                        "error": result.error,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
            
            # Update metrics
            self.metrics.received_daily_symbols = len(received_symbols)
            self.metrics.missing_symbols = [s for s in symbols if s not in received_symbols]
            
            # Determine job status
            if job.successful_symbols == job.total_symbols:
                job.status = JobStatus.SUCCESS
            elif job.successful_symbols > 0:
                job.status = JobStatus.PARTIAL_SUCCESS
            else:
                job.status = JobStatus.FAILED
            
            job.completed_at = datetime.now(timezone.utc)
            
            # Update metrics
            self.metrics.total_jobs_run += 1
            if job.status in [JobStatus.SUCCESS, JobStatus.PARTIAL_SUCCESS]:
                self.metrics.successful_jobs += 1
            else:
                self.metrics.failed_jobs += 1
            
            self.metrics.total_symbols_processed += job.successful_symbols
            self.metrics.last_run_time = job.completed_at
            
            # Update average duration
            if job.started_at and job.completed_at:
                duration = (job.completed_at - job.started_at).total_seconds()
                total_duration = self.metrics.avg_job_duration_seconds * (self.metrics.total_jobs_run - 1)
                self.metrics.avg_job_duration_seconds = (total_duration + duration) / self.metrics.total_jobs_run
            
            self._log_event("job_completed", {
                "job_id": job.job_id,
                "status": job.status.value,
                "successful": job.successful_symbols,
                "failed": job.failed_symbols
            })
            
            # Store in database
            if self.db:
                try:
                    await self.db.pipeline_jobs.insert_one({**job.to_dict()})
                except Exception as e:
                    logger.warning(f"Could not store job in database: {e}")
            
            # Add to history
            self._job_history.insert(0, job.to_dict())
            if len(self._job_history) > 100:
                self._job_history = self._job_history[:100]
            
        except Exception as e:
            logger.error(f"Extraction job failed: {e}")
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now(timezone.utc)
            job.errors.append({
                "type": "job_error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            self.metrics.failed_jobs += 1
            self.metrics.total_jobs_run += 1
            
            self._log_event("job_failed", {
                "job_id": job.job_id,
                "error": str(e)
            })
        
        finally:
            self.current_job = None
            self.status = PipelineStatus.SCHEDULED if self._is_running else PipelineStatus.IDLE
        
        return job
    
    def _log_event(self, event_type: str, data: Dict):
        """Log a pipeline event"""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            **data
        }
        self._extraction_logs.append(log_entry)
        
        # Keep only last 1000 logs
        if len(self._extraction_logs) > 1000:
            self._extraction_logs = self._extraction_logs[-1000:]
        
        logger.info(f"Pipeline event: {event_type} - {data}")
    
    def get_status(self) -> Dict:
        """Get current pipeline status"""
        return {
            "status": self.status.value,
            "is_running": self._is_running,
            "current_job": self.current_job.to_dict() if self.current_job else None,
            "metrics": self.metrics.to_dict(),
            "extractor_metrics": self.grow_extractor.get_metrics() if self.grow_extractor else None,
            "default_symbols_count": len(self.DEFAULT_SYMBOLS),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get a specific job by ID"""
        job = self._jobs.get(job_id)
        return job.to_dict() if job else None
    
    def get_jobs(self, limit: int = 20) -> List[Dict]:
        """Get recent jobs"""
        jobs = list(self._jobs.values())
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return [j.to_dict() for j in jobs[:limit]]
    
    def get_job_history(self, limit: int = 50) -> List[Dict]:
        """Get job history"""
        return self._job_history[:limit]
    
    def get_logs(self, limit: int = 100, event_type: Optional[str] = None) -> List[Dict]:
        """Get extraction logs"""
        logs = self._extraction_logs
        if event_type:
            logs = [l for l in logs if l.get("event_type") == event_type]
        return logs[-limit:]
    
    def get_data_summary(self) -> Dict:
        """Get summary of extracted data"""
        # Aggregate data from recent successful jobs
        symbols_data = {}
        
        for job_dict in self._job_history[:10]:  # Last 10 jobs
            if job_dict.get("status") in ["success", "partial_success"]:
                results = job_dict.get("results", {})
                for symbol, data in results.items() if isinstance(results, dict) else []:
                    if symbol not in symbols_data:
                        symbols_data[symbol] = data
        
        return {
            "unique_symbols_extracted": len(symbols_data),
            "data_by_symbol": symbols_data,
            "last_extraction_time": self.metrics.last_run_time.isoformat() if self.metrics.last_run_time else None
        }


# Global service instance
_pipeline_service: Optional[DataPipelineService] = None


def get_pipeline_service() -> Optional[DataPipelineService]:
    """Get the global pipeline service instance"""
    return _pipeline_service


def init_pipeline_service(db=None, api_key: Optional[str] = None) -> DataPipelineService:
    """Initialize the global pipeline service"""
    global _pipeline_service
    
    from data_extraction.extractors.grow_extractor import GrowwAPIExtractor
    
    grow_extractor = None
    if api_key:
        grow_extractor = GrowwAPIExtractor(api_key=api_key, db=db)
    
    _pipeline_service = DataPipelineService(db=db, grow_extractor=grow_extractor)
    
    return _pipeline_service
