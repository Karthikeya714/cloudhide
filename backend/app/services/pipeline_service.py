"""Orchestrates the full CloudHide hiding pipeline:

secret file -> encrypt -> fragment -> analyze/rank carriers -> select carriers
-> check capacity -> embed fragments -> generate stego images -> persist.
"""
import logging
import time

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.carrier import Carrier
from app.models.fragment import Fragment
from app.models.stego_image import StegoImage
from app.models.transfer import Transfer
from app.services.carrier_service import rank_carriers
from app.services.encryption_service import encrypt_file
from app.services.file_service import read_bytes, write_bytes
from app.services.fragmentation_service import fragment_file
from app.services.image_quality_service import compute_quality_metrics
from app.services.steganography_service import (
    embed_payload,
    image_to_png_bytes,
    load_png_image,
)

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Raised when the hiding pipeline cannot complete (e.g. no suitable carriers)."""


def _select_carrier_for_fragment(
    fragment: Fragment, available_carriers: list[Carrier]
) -> tuple[Carrier, int]:
    """Pick the best-ranked available carrier with enough capacity for this fragment.

    `available_carriers` is assumed sorted best-to-worst by overall_score.
    Returns the chosen carrier and its index in `available_carriers` so the
    caller can remove it from the pool.
    """
    for index, carrier in enumerate(available_carriers):
        if carrier.max_payload_bytes >= fragment.size:
            return carrier, index

    raise PipelineError(
        f"No available carrier has sufficient capacity for fragment {fragment.fragment_index} "
        f"({fragment.size} bytes). Upload larger or more carrier images."
    )


def select_carriers_for_fragments(db: Session, fragments: list[Fragment]) -> list[Carrier]:
    """Greedily assign one carrier per fragment, preferring higher-scoring carriers."""
    ranked = rank_carriers(db)
    if len(ranked) < len(fragments):
        raise PipelineError(
            f"Need {len(fragments)} carrier images but only {len(ranked)} are available. "
            "Upload more carrier images before hiding."
        )

    pool = list(ranked)
    # Assign largest fragments first so they get first pick of capacity.
    carrier_by_fragment_id: dict[str, Carrier] = {}
    for fragment in sorted(fragments, key=lambda f: f.size, reverse=True):
        carrier, index = _select_carrier_for_fragment(fragment, pool)
        carrier_by_fragment_id[fragment.id] = carrier
        pool.pop(index)

    # Return in the original fragment order for predictable embedding.
    return [carrier_by_fragment_id[f.id] for f in fragments]


def hide_file(
    db: Session,
    original_filename: str,
    secret_data: bytes,
    fragment_count: int,
) -> Transfer:
    """Run the complete hide pipeline and return the populated Transfer."""
    start = time.perf_counter()

    encrypt_start = time.perf_counter()
    encrypted_file = encrypt_file(db, original_filename, secret_data)
    encryption_time_ms = (time.perf_counter() - encrypt_start) * 1000

    transfer = Transfer(
        encrypted_file_id=encrypted_file.id,
        original_filename=original_filename,
        fragment_count=fragment_count,
        status="pending",
        encryption_time_ms=encryption_time_ms,
    )
    db.add(transfer)
    db.flush()

    try:
        frag_start = time.perf_counter()
        fragments = fragment_file(db, encrypted_file.id, fragment_count, transfer=transfer)
        transfer.fragmentation_time_ms = (time.perf_counter() - frag_start) * 1000
        transfer.status = "fragmented"

        carriers = select_carriers_for_fragments(db, fragments)

        embed_start = time.perf_counter()
        for fragment, carrier in zip(fragments, carriers):
            fragment_bytes = read_bytes(fragment.storage_path)
            carrier_bytes = read_bytes(carrier.storage_path)
            carrier_image = load_png_image(carrier_bytes)

            stego_image_obj = embed_payload(carrier_image, fragment_bytes, fragment.fragment_index)
            stego_png_bytes = image_to_png_bytes(stego_image_obj)

            psnr_db, ssim = compute_quality_metrics(carrier_image, stego_image_obj)
            capacity_utilization = (
                fragment.size / carrier.max_payload_bytes if carrier.max_payload_bytes else None
            )

            storage_path, _ = write_bytes("stego", stego_png_bytes, suffix=".png")

            stego_record = StegoImage(
                transfer_id=transfer.id,
                fragment_id=fragment.id,
                carrier_id=carrier.id,
                storage_provider=get_settings().storage_provider,
                storage_path=storage_path,
                psnr_db=psnr_db,
                ssim=ssim,
                capacity_utilization=capacity_utilization,
            )
            db.add(stego_record)
        transfer.embedding_time_ms = (time.perf_counter() - embed_start) * 1000

        transfer.status = "completed"
        transfer.processing_time_ms = (time.perf_counter() - start) * 1000
        db.commit()
        db.refresh(transfer)

        logger.info(
            "Completed hide pipeline for transfer %s: %d fragments in %.1f ms",
            transfer.id,
            fragment_count,
            transfer.processing_time_ms,
        )
        return transfer

    except Exception:
        db.rollback()
        # Re-fetch (or re-create) the transfer row as failed for visibility.
        failed_transfer = db.get(Transfer, transfer.id)
        if failed_transfer is not None:
            failed_transfer.status = "failed"
            db.commit()
        logger.exception("Hide pipeline failed for transfer %s", transfer.id)
        raise
