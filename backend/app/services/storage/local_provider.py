"""Local filesystem storage provider (the default for development)."""
from pathlib import Path

from app.services.storage.base import StorageProvider


class LocalStorageProvider(StorageProvider):
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        return self.root / key

    def upload_file(self, key: str, data: bytes) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    def download_file(self, key: str) -> bytes:
        path = self._resolve(key)
        if not path.exists():
            raise FileNotFoundError(f"No such storage file: {key}")
        return path.read_bytes()

    def delete_file(self, key: str) -> None:
        self._resolve(key).unlink(missing_ok=True)

    def file_exists(self, key: str) -> bool:
        return self._resolve(key).exists()
