"""Storage provider interface.

Every other CloudHide service (encryption, fragmentation, carrier analysis,
the hiding/recovery pipelines) reads and writes bytes through this interface
via app.services.file_service, never a concrete provider directly. This is
what lets the storage backend be swapped (local filesystem <-> MinIO <-> S3)
without touching pipeline or steganography code.
"""
from abc import ABC, abstractmethod


class StorageProvider(ABC):
    @abstractmethod
    def upload_file(self, key: str, data: bytes) -> str:
        """Store `data` under `key`. Returns a provider-specific location string."""

    @abstractmethod
    def download_file(self, key: str) -> bytes:
        """Retrieve the bytes stored under `key`. Raises FileNotFoundError if absent."""

    @abstractmethod
    def delete_file(self, key: str) -> None:
        """Remove the object stored under `key`, if present."""

    @abstractmethod
    def file_exists(self, key: str) -> bool:
        """Return True if an object exists under `key`."""
