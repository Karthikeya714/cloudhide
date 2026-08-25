"""Selects the configured StorageProvider from environment settings."""
from functools import lru_cache

from app.core.config import get_settings
from app.services.storage.base import StorageProvider
from app.services.storage.local_provider import LocalStorageProvider


@lru_cache
def get_storage_provider() -> StorageProvider:
    settings = get_settings()

    if settings.storage_provider == "minio":
        from app.services.storage.minio_provider import MinIOStorageProvider

        return MinIOStorageProvider(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            bucket=settings.minio_bucket,
            secure=settings.minio_secure,
        )

    if settings.storage_provider != "local":
        raise ValueError(f"Unsupported STORAGE_PROVIDER: {settings.storage_provider!r}")

    return LocalStorageProvider(settings.storage_root_path)
