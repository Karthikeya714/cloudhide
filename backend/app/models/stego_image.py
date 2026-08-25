"""StegoImage ORM model: a carrier image with one embedded fragment."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StegoImage(Base):
    __tablename__ = "stego_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)

    transfer_id: Mapped[str] = mapped_column(String(36), ForeignKey("transfers.id"), index=True)
    fragment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("fragments.id"), unique=True, index=True
    )
    carrier_id: Mapped[str] = mapped_column(String(36), ForeignKey("carriers.id"), index=True)

    # "local" or "minio" (Phase 7); the object key/path within that provider.
    storage_provider: Mapped[str] = mapped_column(String(32), default="local")
    storage_path: Mapped[str] = mapped_column(String(1024))

    # Quality/evaluation metrics (Phase 8 analytics), computed at embed time by
    # comparing the stego image against its original carrier image.
    psnr_db: Mapped[float | None] = mapped_column(Float, nullable=True)
    ssim: Mapped[float | None] = mapped_column(Float, nullable=True)
    capacity_utilization: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-1

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    transfer = relationship("Transfer", back_populates="stego_images")
    fragment = relationship("Fragment", back_populates="stego_image")
    carrier = relationship("Carrier", back_populates="stego_images")
