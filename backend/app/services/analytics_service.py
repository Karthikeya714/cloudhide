"""Aggregates real timing, quality, and success metrics from stored transfers.

All numbers here are computed from the database at request time -- nothing
is hard-coded or simulated, per the Phase 8 requirement to use real data.
"""
from dataclasses import dataclass, field
from statistics import fmean

from sqlalchemy.orm import Session

from app.models.stego_image import StegoImage
from app.models.transfer import Transfer

HIDE_SUCCESS_STATUSES = ("completed", "recovered")
RECOVERY_ATTEMPTED_STATUSES = ("recovered", "recovery_failed")


@dataclass
class AnalyticsSummary:
    total_transfers: int
    files_hidden: int
    successful_recoveries: int
    failed_hides: int
    failed_recoveries: int
    recovery_rate: float | None  # 0-1

    avg_encryption_time_ms: float | None
    avg_fragmentation_time_ms: float | None
    avg_embedding_time_ms: float | None
    avg_extraction_time_ms: float | None
    avg_recovery_time_ms: float | None
    avg_processing_time_ms: float | None

    avg_psnr_db: float | None
    avg_ssim: float | None
    avg_capacity_utilization_percent: float | None


@dataclass
class TransferSummary:
    id: str
    original_filename: str
    status: str
    fragment_count: int
    processing_time_ms: float | None
    recovery_time_ms: float | None
    avg_psnr_db: float | None
    avg_ssim: float | None
    created_at: object  # datetime, kept loose to avoid importing here


@dataclass
class AnalyticsResponseData:
    summary: AnalyticsSummary
    recent_transfers: list[TransferSummary] = field(default_factory=list)


def _avg(values: list[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    return fmean(clean) if clean else None


def get_analytics(db: Session, recent_limit: int = 20) -> AnalyticsResponseData:
    transfers = db.query(Transfer).all()
    total_transfers = len(transfers)

    files_hidden = sum(1 for t in transfers if t.status in HIDE_SUCCESS_STATUSES)
    successful_recoveries = sum(1 for t in transfers if t.status == "recovered")
    failed_hides = sum(1 for t in transfers if t.status == "failed")
    failed_recoveries = sum(1 for t in transfers if t.status == "recovery_failed")

    recovery_attempts = successful_recoveries + failed_recoveries
    recovery_rate = (successful_recoveries / recovery_attempts) if recovery_attempts else None

    avg_encryption_time_ms = _avg([t.encryption_time_ms for t in transfers])
    avg_fragmentation_time_ms = _avg([t.fragmentation_time_ms for t in transfers])
    avg_embedding_time_ms = _avg([t.embedding_time_ms for t in transfers])
    avg_extraction_time_ms = _avg([t.extraction_time_ms for t in transfers])
    avg_recovery_time_ms = _avg([t.recovery_time_ms for t in transfers])
    avg_processing_time_ms = _avg([t.processing_time_ms for t in transfers])

    stego_images = db.query(StegoImage).all()
    finite_psnr = [s.psnr_db for s in stego_images if s.psnr_db is not None and s.psnr_db != float("inf")]
    avg_psnr_db = fmean(finite_psnr) if finite_psnr else None
    avg_ssim = _avg([s.ssim for s in stego_images])
    capacity_values = [
        s.capacity_utilization * 100
        for s in stego_images
        if s.capacity_utilization is not None
    ]
    avg_capacity_utilization_percent = fmean(capacity_values) if capacity_values else None

    summary = AnalyticsSummary(
        total_transfers=total_transfers,
        files_hidden=files_hidden,
        successful_recoveries=successful_recoveries,
        failed_hides=failed_hides,
        failed_recoveries=failed_recoveries,
        recovery_rate=recovery_rate,
        avg_encryption_time_ms=avg_encryption_time_ms,
        avg_fragmentation_time_ms=avg_fragmentation_time_ms,
        avg_embedding_time_ms=avg_embedding_time_ms,
        avg_extraction_time_ms=avg_extraction_time_ms,
        avg_recovery_time_ms=avg_recovery_time_ms,
        avg_processing_time_ms=avg_processing_time_ms,
        avg_psnr_db=avg_psnr_db,
        avg_ssim=avg_ssim,
        avg_capacity_utilization_percent=avg_capacity_utilization_percent,
    )

    recent = (
        db.query(Transfer).order_by(Transfer.created_at.desc()).limit(recent_limit).all()
    )
    recent_summaries = [
        TransferSummary(
            id=t.id,
            original_filename=t.original_filename,
            status=t.status,
            fragment_count=t.fragment_count,
            processing_time_ms=t.processing_time_ms,
            recovery_time_ms=t.recovery_time_ms,
            avg_psnr_db=_avg([s.psnr_db for s in t.stego_images if s.psnr_db != float("inf")]),
            avg_ssim=_avg([s.ssim for s in t.stego_images]),
            created_at=t.created_at,
        )
        for t in recent
    ]

    return AnalyticsResponseData(summary=summary, recent_transfers=recent_summaries)
