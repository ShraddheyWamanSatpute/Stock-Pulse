"""
Pydantic models for Data Pipeline API
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class PipelineStatusEnum(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    SCHEDULED = "scheduled"


class JobStatusEnum(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExtractionTypeEnum(str, Enum):
    QUOTES = "quotes"
    HISTORICAL = "historical"
    FUNDAMENTALS = "fundamentals"


class PipelineMetricsResponse(BaseModel):
    """Pipeline metrics response model"""
    total_jobs_run: int = 0
    successful_jobs: int = 0
    failed_jobs: int = 0
    job_success_rate: float = 0.0
    total_symbols_processed: int = 0
    total_data_points_extracted: int = 0
    last_run_time: Optional[str] = None
    next_scheduled_run: Optional[str] = None
    avg_job_duration_seconds: float = 0.0
    uptime_seconds: float = 0.0
    expected_daily_symbols: int = 0
    received_daily_symbols: int = 0
    data_completeness_percent: float = 0.0
    missing_symbols_count: int = 0
    missing_symbols: List[str] = []
    delayed_symbols_count: int = 0
    delayed_symbols: List[str] = []


class APIMetricsResponse(BaseModel):
    """API call metrics response model"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    retry_count: int = 0
    rate_limit_hits: int = 0
    avg_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    success_rate: float = 0.0
    last_request_time: Optional[str] = None
    recent_errors: List[Dict[str, Any]] = []


class PipelineStatusResponse(BaseModel):
    """Pipeline status response model"""
    status: PipelineStatusEnum
    is_running: bool
    current_job: Optional[Dict[str, Any]] = None
    metrics: PipelineMetricsResponse
    extractor_metrics: Optional[APIMetricsResponse] = None
    default_symbols_count: int
    timestamp: str


class JobResponse(BaseModel):
    """Pipeline job response model"""
    job_id: str
    pipeline_type: str
    status: JobStatusEnum
    symbols: List[str]
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_symbols: int = 0
    processed_symbols: int = 0
    successful_symbols: int = 0
    failed_symbols: int = 0
    progress_percent: float = 0.0
    errors: List[Dict[str, Any]] = []
    duration_seconds: Optional[float] = None


class RunExtractionRequest(BaseModel):
    """Request model for running extraction"""
    symbols: Optional[List[str]] = Field(
        None,
        description="List of stock symbols to extract. If not provided, uses default symbols.",
        example=["RELIANCE", "TCS", "INFY"]
    )
    extraction_type: ExtractionTypeEnum = Field(
        ExtractionTypeEnum.QUOTES,
        description="Type of data extraction to perform"
    )


class RunExtractionResponse(BaseModel):
    """Response model for extraction run"""
    message: str
    job: JobResponse


class StartSchedulerRequest(BaseModel):
    """Request model for starting scheduler"""
    interval_minutes: int = Field(
        30,
        ge=5,
        le=1440,
        description="Interval between extractions in minutes (5-1440)"
    )


class LogEntry(BaseModel):
    """Pipeline log entry model"""
    timestamp: str
    event_type: str
    job_id: Optional[str] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class LogsResponse(BaseModel):
    """Response model for logs endpoint"""
    logs: List[Dict[str, Any]]
    total_count: int


class DataSummaryResponse(BaseModel):
    """Response model for data summary"""
    unique_symbols_extracted: int
    data_by_symbol: Dict[str, Any]
    last_extraction_time: Optional[str] = None


class APITestRequest(BaseModel):
    """Request model for API test"""
    symbol: str = Field(
        "RELIANCE",
        description="Stock symbol to test with"
    )


class APITestResponse(BaseModel):
    """Response model for API test"""
    success: bool
    message: str
    latency_ms: Optional[float] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
