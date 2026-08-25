"""Application configuration loaded from environment variables / .env file."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "CloudHide"
    environment: str = "development"
    debug: bool = True

    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    database_url: str = "sqlite:///./cloudhide.db"

    storage_provider: str = "local"
    storage_root: str = "../storage"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "cloudhide"
    minio_secure: bool = False

    master_key_base64: str = ""

    default_fragment_count: int = 3

    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def storage_root_path(self) -> Path:
        path = Path(self.storage_root)
        if not path.is_absolute():
            path = (BACKEND_DIR / path).resolve()
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
