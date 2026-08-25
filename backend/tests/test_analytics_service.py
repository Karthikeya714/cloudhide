from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from app.services.analytics_service import get_analytics
from app.services.carrier_service import upload_and_analyze_carrier
from app.services.pipeline_service import PipelineError, hide_file
from app.services.recovery_service import RecoveryError, recover_transfer
from app.services.file_service import resolve_path


def make_png_bytes(width=200, height=200, seed=0) -> bytes:
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8)
    buffer = BytesIO()
    Image.fromarray(arr, mode="RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def _upload_carriers(db_session, count: int, seed_offset: int = 0):
    for i in range(count):
        upload_and_analyze_carrier(
            db_session, f"carrier{seed_offset + i}.png", make_png_bytes(seed=seed_offset + i)
        )


def test_analytics_reflect_completed_hide_pipeline(db_session):
    _upload_carriers(db_session, count=3)
    hide_file(db_session, "secret.bin", b"analytics payload" * 20, fragment_count=3)

    data = get_analytics(db_session)

    assert data.summary.total_transfers == 1
    assert data.summary.files_hidden == 1
    assert data.summary.successful_recoveries == 0
    assert data.summary.avg_encryption_time_ms is not None
    assert data.summary.avg_fragmentation_time_ms is not None
    assert data.summary.avg_embedding_time_ms is not None
    assert data.summary.avg_processing_time_ms is not None
    assert data.summary.avg_psnr_db is not None and data.summary.avg_psnr_db > 0
    assert data.summary.avg_ssim is not None and 0 <= data.summary.avg_ssim <= 1
    assert data.summary.avg_capacity_utilization_percent is not None


def test_analytics_reflect_successful_recovery(db_session):
    _upload_carriers(db_session, count=2)
    transfer = hide_file(db_session, "secret.bin", b"recovery analytics test" * 10, fragment_count=2)
    recover_transfer(db_session, transfer.id)

    data = get_analytics(db_session)

    assert data.summary.successful_recoveries == 1
    assert data.summary.recovery_rate == 1.0
    assert data.summary.avg_recovery_time_ms is not None
    assert data.summary.avg_extraction_time_ms is not None


def test_analytics_count_failed_hide_and_failed_recovery(db_session):
    # Failed hide: no carriers uploaded at all.
    with pytest.raises(PipelineError):
        hide_file(db_session, "secret.bin", b"will fail" * 5, fragment_count=2)

    # Successful hide, then a failed recovery (corrupt a stego image).
    _upload_carriers(db_session, count=2)
    transfer = hide_file(db_session, "secret2.bin", b"will recover fail" * 10, fragment_count=2)
    stego = transfer.stego_images[0]
    resolve_path(stego.storage_path).unlink()

    with pytest.raises(RecoveryError):
        recover_transfer(db_session, transfer.id)

    data = get_analytics(db_session)

    assert data.summary.failed_hides == 1
    assert data.summary.failed_recoveries == 1
    assert data.summary.recovery_rate == 0.0
    # 1 failed-hide transfer + 1 completed-then-recovery-failed transfer.
    assert data.summary.total_transfers == 2


def test_analytics_recent_transfers_ordered_most_recent_first(db_session):
    _upload_carriers(db_session, count=2)
    first = hide_file(db_session, "first.bin", b"first payload" * 5, fragment_count=2)
    second = hide_file(db_session, "second.bin", b"second payload" * 5, fragment_count=2)

    data = get_analytics(db_session, recent_limit=10)

    ids = [t.id for t in data.recent_transfers]
    assert ids.index(second.id) < ids.index(first.id)


def test_analytics_with_no_data_returns_nulls_not_errors(db_session):
    data = get_analytics(db_session)

    assert data.summary.total_transfers == 0
    assert data.summary.avg_psnr_db is None
    assert data.summary.recovery_rate is None
    assert data.recent_transfers == []
