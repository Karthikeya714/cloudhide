"""Analyzes PNG carrier images and scores their suitability for LSB steganography.

The scoring heuristic is intentionally simple and documented so it can be
improved later (e.g. with learned distortion models) without touching
callers -- see analyze_carrier() as the single entry point.
"""
import logging
from dataclasses import dataclass, field

import numpy as np
from PIL import Image
from skimage.filters import sobel, threshold_otsu

from app.services.steganography_service import calculate_capacity

logger = logging.getLogger(__name__)

# A carrier offering this much usable payload capacity or more earns a full
# capacity score of 100; smaller carriers are scored proportionally.
REFERENCE_CAPACITY_BYTES = 500 * 1024  # 500 KB

# Local texture (block standard deviation) at or above this level is treated
# as "fully textured" for distortion-risk purposes.
TEXTURE_REFERENCE_STD = 64.0
BLOCK_SIZE = 8

# Weight applied to the distortion-risk penalty when combining sub-scores.
DISTORTION_PENALTY_WEIGHT = 0.3


@dataclass
class CarrierMetrics:
    width: int
    height: int
    pixel_count: int
    raw_capacity_bytes: int
    max_payload_bytes: int

    shannon_entropy: float  # bits per pixel, 0-8
    edge_density: float  # fraction of pixels classified as edges, 0-1
    distortion_risk: float  # 0-1, higher means embedding is more detectable

    capacity_score: float  # 0-100
    entropy_score: float  # 0-100
    edge_score: float  # 0-100
    distortion_score: float  # 0-100 (higher is worse)
    overall_score: float  # 0-100

    explanation: list[str] = field(default_factory=list)


def _shannon_entropy(gray: np.ndarray) -> float:
    histogram, _ = np.histogram(gray, bins=256, range=(0, 256))
    probabilities = histogram / histogram.sum()
    nonzero = probabilities[probabilities > 0]
    return float(-np.sum(nonzero * np.log2(nonzero)))


def _edge_density(gray: np.ndarray) -> float:
    normalized = gray.astype(np.float64) / 255.0
    edges = sobel(normalized)
    if edges.max() <= 0:
        return 0.0
    threshold = threshold_otsu(edges)
    return float((edges > threshold).mean())


def _distortion_risk(gray: np.ndarray) -> float:
    height, width = gray.shape
    cropped_h = height - height % BLOCK_SIZE
    cropped_w = width - width % BLOCK_SIZE

    if cropped_h < BLOCK_SIZE or cropped_w < BLOCK_SIZE:
        # Image too small to block; fall back to whole-image texture.
        block_stds = np.array([gray.std()])
    else:
        cropped = gray[:cropped_h, :cropped_w]
        blocks = (
            cropped.reshape(cropped_h // BLOCK_SIZE, BLOCK_SIZE, cropped_w // BLOCK_SIZE, BLOCK_SIZE)
            .swapaxes(1, 2)
            .reshape(-1, BLOCK_SIZE, BLOCK_SIZE)
        )
        block_stds = blocks.std(axis=(1, 2))

    mean_texture = float(block_stds.mean())
    normalized_texture = min(mean_texture / TEXTURE_REFERENCE_STD, 1.0)
    return 1.0 - normalized_texture


def analyze_carrier(image: Image.Image) -> CarrierMetrics:
    """Compute hiding capacity, entropy, edge density, distortion risk, and an
    overall 0-100 suitability score for a carrier image."""
    capacity = calculate_capacity(image)
    gray = np.array(image.convert("L"), dtype=np.uint8)

    entropy = _shannon_entropy(gray)
    edge_density = _edge_density(gray)
    distortion_risk = _distortion_risk(gray)

    capacity_score = min(100.0, 100.0 * capacity.raw_capacity_bytes / REFERENCE_CAPACITY_BYTES)
    entropy_score = min(100.0, (entropy / 8.0) * 100.0)
    edge_score = min(100.0, edge_density * 100.0)
    distortion_score = distortion_risk * 100.0

    overall_score = (capacity_score + entropy_score + edge_score) / 3.0
    overall_score -= DISTORTION_PENALTY_WEIGHT * distortion_score
    overall_score = max(0.0, min(100.0, overall_score))

    explanation = [
        f"Capacity: {capacity.max_payload_bytes} usable bytes at {capacity.width}x{capacity.height} "
        f"scores {capacity_score:.1f}/100 (reference: {REFERENCE_CAPACITY_BYTES} bytes for a full score).",
        f"Shannon entropy of {entropy:.2f} bits/pixel (max 8) scores {entropy_score:.1f}/100 -- "
        "higher entropy carriers hide LSB noise more effectively.",
        f"Edge density of {edge_density * 100:.1f}% of pixels scores {edge_score:.1f}/100 -- "
        "busy/textured regions mask embedding artifacts better than flat regions.",
        f"Distortion risk {distortion_score:.1f}/100 (from local texture analysis) is subtracted -- "
        "smooth/flat images make single-bit LSB changes more statistically detectable.",
        f"Overall suitability score: {overall_score:.1f}/100.",
    ]

    return CarrierMetrics(
        width=capacity.width,
        height=capacity.height,
        pixel_count=capacity.pixel_count,
        raw_capacity_bytes=capacity.raw_capacity_bytes,
        max_payload_bytes=capacity.max_payload_bytes,
        shannon_entropy=entropy,
        edge_density=edge_density,
        distortion_risk=distortion_risk,
        capacity_score=capacity_score,
        entropy_score=entropy_score,
        edge_score=edge_score,
        distortion_score=distortion_score,
        overall_score=overall_score,
        explanation=explanation,
    )
