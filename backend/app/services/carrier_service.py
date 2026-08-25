"""DB-aware orchestration around carrier analysis: upload, persist, list, rank."""
import json
import logging

from sqlalchemy.orm import Session

from app.models.carrier import Carrier
from app.services.carrier_analysis_service import analyze_carrier
from app.services.file_service import write_bytes
from app.services.steganography_service import load_png_image

logger = logging.getLogger(__name__)

DEFAULT_RECOMMENDATION_COUNT = 3


def upload_and_analyze_carrier(db: Session, original_filename: str, data: bytes) -> Carrier:
    """Validate a PNG carrier, compute its suitability metrics, and persist both."""
    image = load_png_image(data)
    metrics = analyze_carrier(image)

    storage_path, _ = write_bytes("carriers", data, suffix=".png")

    carrier = Carrier(
        original_filename=original_filename,
        storage_path=storage_path,
        width=metrics.width,
        height=metrics.height,
        pixel_count=metrics.pixel_count,
        raw_capacity_bytes=metrics.raw_capacity_bytes,
        max_payload_bytes=metrics.max_payload_bytes,
        shannon_entropy=metrics.shannon_entropy,
        edge_density=metrics.edge_density,
        distortion_risk=metrics.distortion_risk,
        capacity_score=metrics.capacity_score,
        entropy_score=metrics.entropy_score,
        edge_score=metrics.edge_score,
        distortion_score=metrics.distortion_score,
        overall_score=metrics.overall_score,
        explanation=json.dumps(metrics.explanation),
    )
    db.add(carrier)
    db.commit()
    db.refresh(carrier)

    logger.info(
        "Analyzed carrier %s (%s): score=%.1f capacity=%d bytes",
        carrier.id,
        original_filename,
        carrier.overall_score,
        carrier.max_payload_bytes,
    )
    return carrier


def list_carriers(db: Session) -> list[Carrier]:
    return db.query(Carrier).order_by(Carrier.created_at.desc()).all()


def get_carrier(db: Session, carrier_id: str) -> Carrier | None:
    return db.get(Carrier, carrier_id)


def rank_carriers(db: Session) -> list[Carrier]:
    """All carriers sorted best-to-worst by overall suitability score."""
    return db.query(Carrier).order_by(Carrier.overall_score.desc()).all()


def recommend_carriers(db: Session, count: int = DEFAULT_RECOMMENDATION_COUNT) -> list[Carrier]:
    """Top-N carriers by overall suitability score."""
    return rank_carriers(db)[:count]


def explanation_list(carrier: Carrier) -> list[str]:
    return json.loads(carrier.explanation)
