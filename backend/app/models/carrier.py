"""Carrier ORM model: an uploaded PNG image plus its computed suitability metrics."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Carrier(Base):
    __tablename__ = "carriers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)

    original_filename: Mapped[str] = mapped_column(String(512))
    storage_path: Mapped[str] = mapped_column(String(1024))

    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    pixel_count: Mapped[int] = mapped_column(Integer)
    raw_capacity_bytes: Mapped[int] = mapped_column(Integer)
    max_payload_bytes: Mapped[int] = mapped_column(Integer)

    shannon_entropy: Mapped[float] = mapped_column(Float)
    edge_density: Mapped[float] = mapped_column(Float)
    distortion_risk: Mapped[float] = mapped_column(Float)

    capacity_score: Mapped[float] = mapped_column(Float)
    entropy_score: Mapped[float] = mapped_column(Float)
    edge_score: Mapped[float] = mapped_column(Float)
    distortion_score: Mapped[float] = mapped_column(Float)
    overall_score: Mapped[float] = mapped_column(Float)

    # JSON-encoded list[str] of human-readable reasons behind the score.
    explanation: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    stego_images = relationship("StegoImage", back_populates="carrier")
