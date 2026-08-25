"""Transfer ORM model: the top-level record tying together one hide/recover cycle."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Transfer(Base):
    __tablename__ = "transfers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)

    encrypted_file_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("encrypted_files.id"), nullable=True
    )
    original_filename: Mapped[str] = mapped_column(String(512))
    fragment_count: Mapped[int] = mapped_column(Integer)

    # pending -> fragmented -> completed -> recovered
    # (or failed / recovery_failed if either pipeline stage errors out)
    status: Mapped[str] = mapped_column(String(32), default="pending")

    # Hide-pipeline timing breakdown (Phase 8 analytics).
    encryption_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    fragmentation_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    embedding_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    processing_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)  # total hide time

    recovered_storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    # Recovery-pipeline timing breakdown.
    extraction_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    recovery_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)  # total recovery time

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    encrypted_file = relationship("EncryptedFile", back_populates="transfers")
    fragments = relationship(
        "Fragment", back_populates="transfer", order_by="Fragment.fragment_index"
    )
    stego_images = relationship("StegoImage", back_populates="transfer")
