from datetime import datetime

from pydantic import BaseModel


class AnalyticsSummaryResponse(BaseModel):
    total_transfers: int
    files_hidden: int
    successful_recoveries: int
    failed_hides: int
    failed_recoveries: int
    recovery_rate: float | None  # fraction 0-1, null if no recovery attempted yet

    avg_encryption_time_ms: float | None
    avg_fragmentation_time_ms: float | None
    avg_embedding_time_ms: float | None
    avg_extraction_time_ms: float | None
    avg_recovery_time_ms: float | None
    avg_processing_time_ms: float | None

    avg_psnr_db: float | None
    avg_ssim: float | None
    avg_capacity_utilization_percent: float | None


class RecentTransferResponse(BaseModel):
    id: str
    original_filename: str
    status: str
    fragment_count: int
    processing_time_ms: float | None
    recovery_time_ms: float | None
    avg_psnr_db: float | None
    avg_ssim: float | None
    created_at: datetime


class AnalyticsResponse(BaseModel):
    summary: AnalyticsSummaryResponse
    recent_transfers: list[RecentTransferResponse]
