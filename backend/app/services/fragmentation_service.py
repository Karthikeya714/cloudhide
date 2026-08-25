"""Splits encrypted files into fragments and reconstructs them.

Kept deliberately simple (contiguous byte-range splitting) so a more advanced
strategy -- e.g. Shamir secret sharing with a reconstruction threshold -- can
be swapped in later without touching callers of fragment_file()/reconstruct_file().
"""
import logging

from sqlalchemy.orm import Session

from app.models.encrypted_file import EncryptedFile
from app.models.fragment import Fragment
from app.models.transfer import Transfer
from app.services.file_service import read_bytes, sha256_hex, write_bytes

logger = logging.getLogger(__name__)

MAX_FRAGMENTS = 64


class FragmentationError(Exception):
    pass


def _split_sizes(total_size: int, fragment_count: int) -> list[int]:
    base, remainder = divmod(total_size, fragment_count)
    sizes = [base + 1 if i < remainder else base for i in range(fragment_count)]
    return sizes


def fragment_file(
    db: Session,
    encrypted_file_id: str,
    fragment_count: int,
    transfer: Transfer | None = None,
) -> list[Fragment]:
    """Split an encrypted file (from Phase 1) into `fragment_count` fragments.

    If `transfer` is not provided, a new Transfer row is created to own the
    fragments (used when fragmentation is invoked standalone, e.g. via the
    /api/fragments/create endpoint). The full hiding pipeline (Phase 5) passes
    an already-created Transfer so it can track carriers and stego images
    against the same row.
    """
    if fragment_count < 1:
        raise ValueError("fragment_count must be at least 1")
    if fragment_count > MAX_FRAGMENTS:
        raise ValueError(f"fragment_count must not exceed {MAX_FRAGMENTS}")

    record = db.get(EncryptedFile, encrypted_file_id)
    if record is None:
        raise FragmentationError(f"No encrypted file with id {encrypted_file_id}")

    payload = read_bytes(record.storage_path)
    if fragment_count > len(payload):
        raise ValueError(
            f"fragment_count ({fragment_count}) cannot exceed encrypted file size ({len(payload)} bytes)"
        )

    if transfer is None:
        transfer = Transfer(
            encrypted_file_id=encrypted_file_id,
            original_filename=record.original_filename,
            fragment_count=fragment_count,
            status="fragmented",
        )
        db.add(transfer)
        db.flush()

    transfer_id = transfer.id
    sizes = _split_sizes(len(payload), fragment_count)

    fragments: list[Fragment] = []
    offset = 0
    for index, size in enumerate(sizes):
        chunk = payload[offset : offset + size]
        offset += size

        storage_path, _ = write_bytes("fragments", chunk, suffix=".frag")
        fragment = Fragment(
            transfer_id=transfer_id,
            encrypted_file_id=encrypted_file_id,
            fragment_index=index,
            total_fragments=fragment_count,
            size=len(chunk),
            sha256=sha256_hex(chunk),
            storage_path=storage_path,
        )
        db.add(fragment)
        fragments.append(fragment)

    db.commit()
    for fragment in fragments:
        db.refresh(fragment)

    logger.info(
        "Fragmented encrypted file %s into %d fragments under transfer %s",
        encrypted_file_id,
        fragment_count,
        transfer_id,
    )
    return fragments


def list_fragments(db: Session, transfer_id: str) -> list[Fragment]:
    return (
        db.query(Fragment)
        .filter(Fragment.transfer_id == transfer_id)
        .order_by(Fragment.fragment_index)
        .all()
    )


def reconstruct_file(db: Session, transfer_id: str) -> bytes:
    """Reassemble the original encrypted file from its fragments, verifying hashes."""
    fragments = list_fragments(db, transfer_id)
    if not fragments:
        raise FragmentationError(f"No fragments found for transfer {transfer_id}")

    expected_total = fragments[0].total_fragments
    if len(fragments) != expected_total:
        raise FragmentationError(
            f"Missing fragments for transfer {transfer_id}: expected {expected_total}, found {len(fragments)}"
        )

    expected_indices = list(range(expected_total))
    actual_indices = [f.fragment_index for f in fragments]
    if actual_indices != expected_indices:
        raise FragmentationError(
            f"Fragment indices for transfer {transfer_id} are not contiguous: {actual_indices}"
        )

    chunks: list[bytes] = []
    for fragment in fragments:
        chunk = read_bytes(fragment.storage_path)
        if sha256_hex(chunk) != fragment.sha256:
            raise FragmentationError(
                f"Fragment {fragment.fragment_index} of transfer {transfer_id} failed integrity check"
            )
        chunks.append(chunk)

    return b"".join(chunks)
