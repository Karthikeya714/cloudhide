"""Fragment ORM model: a slice of an encrypted file, addressable within a transfer."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Fragment(Base):
    __tablename__ = "fragments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)

    transfer_id: Mapped[str] = mapped_column(String(36), ForeignKey("transfers.id"), index=True)
    encrypted_file_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("encrypted_files.id"), index=True
    )

    fragment_index: Mapped[int] = mapped_column(Integer)
    total_fragments: Mapped[int] = mapped_column(Integer)

    size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    storage_path: Mapped[str] = mapped_column(String(1024))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    transfer = relationship("Transfer", back_populates="fragments")
    stego_image = relationship("StegoImage", back_populates="fragment", uselist=False)
