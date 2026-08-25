"""Recovers the original secret file from a transfer's stego images.

transfer_id -> locate stego images -> extract fragments -> verify checksums
-> sort by fragment index -> reconstruct encrypted file -> decrypt -> verify
final hash -> save recovered file.
"""
import logging
import time

from sqlalchemy.orm import Session

from app.models.transfer import Transfer
from app.services.encryption_service import DecryptionError, decrypt_payload
from app.services.file_service import read_bytes, sha256_hex, write_bytes
from app.services.steganography_service import (
    CorruptedDataError,
    SteganographyError,
    extract_payload,
    load_png_image,
)

logger = logging.getLogger(__name__)


class RecoveryError(Exception):
    """Raised when a transfer cannot be recovered (missing/corrupted data, decryption failure)."""


def _run_recovery(db: Session, transfer: Transfer, start: float) -> Transfer:
    transfer_id = transfer.id
    stego_images = transfer.stego_images
    if not stego_images:
        raise RecoveryError(f"No stego images found for transfer {transfer_id}")
    if len(stego_images) != transfer.fragment_count:
        raise RecoveryError(
            f"Missing stego images for transfer {transfer_id}: "
            f"expected {transfer.fragment_count}, found {len(stego_images)}"
        )

    extraction_start = time.perf_counter()
    extracted_chunks: dict[int, bytes] = {}
    for stego in stego_images:
        try:
            stego_bytes = read_bytes(stego.storage_path)
        except FileNotFoundError as exc:
            raise RecoveryError(f"Stego image missing from storage: {stego.storage_path}") from exc

        try:
            image = load_png_image(stego_bytes)
            extracted = extract_payload(image)
        except (CorruptedDataError, SteganographyError) as exc:
            raise RecoveryError(f"Corrupted stego image for transfer {transfer_id}: {exc}") from exc

        fragment = stego.fragment
        if sha256_hex(extracted.payload) != fragment.sha256:
            raise RecoveryError(
                f"Fragment {extracted.fragment_index} checksum mismatch after extraction "
                f"(hidden data may have been tampered with)"
            )

        extracted_chunks[extracted.fragment_index] = extracted.payload
    transfer.extraction_time_ms = (time.perf_counter() - extraction_start) * 1000

    expected_indices = set(range(transfer.fragment_count))
    found_indices = set(extracted_chunks.keys())
    if found_indices != expected_indices:
        missing = sorted(expected_indices - found_indices)
        raise RecoveryError(f"Missing fragments for transfer {transfer_id}: {missing}")

    reconstructed_encrypted = b"".join(
        extracted_chunks[i] for i in range(transfer.fragment_count)
    )

    encrypted_record = transfer.encrypted_file
    if encrypted_record is None:
        raise RecoveryError(f"Transfer {transfer_id} has no associated encrypted file")

    try:
        plaintext = decrypt_payload(encrypted_record, reconstructed_encrypted)
    except DecryptionError as exc:
        raise RecoveryError(f"Decryption failed for transfer {transfer_id}: {exc}") from exc

    recovered_path, _ = write_bytes("recovered", plaintext, suffix=".bin")

    transfer.recovered_storage_path = recovered_path
    transfer.recovery_time_ms = (time.perf_counter() - start) * 1000
    transfer.status = "recovered"
    db.commit()
    db.refresh(transfer)

    logger.info(
        "Recovered transfer %s (%d bytes) in %.1f ms",
        transfer.id,
        len(plaintext),
        transfer.recovery_time_ms,
    )
    return transfer


def recover_transfer(db: Session, transfer_id: str) -> Transfer:
    """Run the complete recovery pipeline and return the updated Transfer.

    On success, transfer.recovered_storage_path points at the plaintext file
    in local storage and transfer.status is "recovered". On failure, the
    transfer's status is set to "recovery_failed" (for analytics visibility)
    and the original RecoveryError is re-raised.
    """
    start = time.perf_counter()

    transfer = db.get(Transfer, transfer_id)
    if transfer is None:
        raise RecoveryError(f"No transfer with id {transfer_id}")

    if transfer.status not in ("completed", "recovered", "recovery_failed"):
        # Hiding itself never finished for this transfer (e.g. it's still
        # "fragmented" or already "failed") -- there is nothing to recover,
        # and overwriting that status with "recovery_failed" would hide the
        # real problem (a failed hide) behind a misleading recovery error.
        raise RecoveryError(
            f"Transfer {transfer_id} has status '{transfer.status}'; "
            "hiding never completed successfully, so there is nothing to recover"
        )

    try:
        return _run_recovery(db, transfer, start)
    except RecoveryError:
        db.rollback()
        failed_transfer = db.get(Transfer, transfer_id)
        if failed_transfer is not None:
            failed_transfer.status = "recovery_failed"
            db.commit()
        raise
