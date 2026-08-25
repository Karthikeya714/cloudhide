"""EncryptedFile ORM model: tracks a secret file after AES-256-GCM encryption."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EncryptedFile(Base):
    __tablename__ = "encrypted_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)

    original_filename: Mapped[str] = mapped_column(String(512))
    original_size: Mapped[int] = mapped_column(Integer)
    original_sha256: Mapped[str] = mapped_column(String(64))

    encrypted_size: Mapped[int] = mapped_column(Integer)
    encrypted_sha256: Mapped[str] = mapped_column(String(64))
    storage_path: Mapped[str] = mapped_column(String(1024))

    # AES-256 key that encrypted this file, itself encrypted ("wrapped") with
    # the server master key. Never exposed through API responses.
    wrapped_key: Mapped[str] = mapped_column(String(256))

    status: Mapped[str] = mapped_column(String(32), default="encrypted")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    transfers = relationship("Transfer", back_populates="encrypted_file")
