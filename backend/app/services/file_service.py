"""Storage-agnostic file helpers: safe reads/writes and integrity hashing.

Reads and writes go through the configured StorageProvider (see
app.services.storage), so callers never need to know whether data lives on
the local filesystem or in MinIO/S3.
"""
import hashlib
import logging
import uuid
from pathlib import Path

from app.core.config import get_settings
from app.services.storage import get_storage_provider

logger = logging.getLogger(__name__)

# Reject absurdly large uploads before they reach memory/disk.
MAX_UPLOAD_SIZE_BYTES = 200 * 1024 * 1024  # 200 MB


class FileTooLargeError(Exception):
    pass


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_upload_size(data: bytes) -> None:
    if len(data) == 0:
        raise ValueError("Uploaded file is empty")
    if len(data) > MAX_UPLOAD_SIZE_BYTES:
        raise FileTooLargeError(
            f"File size {len(data)} bytes exceeds the {MAX_UPLOAD_SIZE_BYTES} byte limit"
        )


def write_bytes(subdir: str, data: bytes, suffix: str = "") -> tuple[str, str]:
    """Store bytes under a new uniquely-named key inside a storage "subdir".

    Returns (storage_key, provider_location). storage_key is what should be
    persisted in the database (e.g. "encrypted/<uuid>.enc"); it is the value
    later passed to read_bytes()/resolve_path(), regardless of provider.
    """
    key = f"{subdir}/{uuid.uuid4().hex}{suffix}"
    provider = get_storage_provider()
    location = provider.upload_file(key, data)
    logger.info("Wrote %d bytes to %s (%s)", len(data), key, location)
    return key, location


def read_bytes(storage_key: str) -> bytes:
    provider = get_storage_provider()
    return provider.download_file(storage_key)


def delete_bytes(storage_key: str) -> None:
    provider = get_storage_provider()
    provider.delete_file(storage_key)


def file_exists(storage_key: str) -> bool:
    provider = get_storage_provider()
    return provider.file_exists(storage_key)


def resolve_path(storage_key: str) -> Path:
    """Resolve a storage key to a local filesystem path.

    Only meaningful when the active storage provider is local; used by tests
    and local-only tooling that need to inspect files directly on disk.
    """
    settings = get_settings()
    return settings.storage_root_path / storage_key
