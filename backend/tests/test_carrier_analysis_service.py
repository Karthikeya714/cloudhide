from io import BytesIO

import numpy as np
from PIL import Image

from app.services.carrier_analysis_service import analyze_carrier


def flat_png(width: int = 64, height: int = 64, value: int = 128) -> Image.Image:
    arr = np.full((height, width, 3), value, dtype=np.uint8)
    return Image.fromarray(arr, mode="RGB")


def noisy_png(width: int = 64, height: int = 64, seed: int = 1) -> Image.Image:
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8)
    return Image.fromarray(arr, mode="RGB")


def test_analyze_carrier_returns_all_metric_fields():
    metrics = analyze_carrier(noisy_png())

    assert metrics.width == 64
    assert metrics.height == 64
    assert metrics.pixel_count == 64 * 64
    assert metrics.raw_capacity_bytes > 0
    assert 0 <= metrics.shannon_entropy <= 8
    assert 0 <= metrics.edge_density <= 1
    assert 0 <= metrics.distortion_risk <= 1
    assert 0 <= metrics.overall_score <= 100
    assert len(metrics.explanation) >= 1


def test_flat_image_has_zero_entropy_and_high_distortion_risk():
    metrics = analyze_carrier(flat_png())

    assert metrics.shannon_entropy == 0.0
    assert metrics.distortion_risk == 1.0


def test_noisy_image_scores_higher_than_flat_image():
    flat_metrics = analyze_carrier(flat_png())
    noisy_metrics = analyze_carrier(noisy_png())

    assert noisy_metrics.overall_score > flat_metrics.overall_score
    assert noisy_metrics.shannon_entropy > flat_metrics.shannon_entropy


def test_larger_image_has_higher_capacity_score():
    small_metrics = analyze_carrier(noisy_png(width=16, height=16, seed=2))
    large_metrics = analyze_carrier(noisy_png(width=256, height=256, seed=2))

    assert large_metrics.raw_capacity_bytes > small_metrics.raw_capacity_bytes
    assert large_metrics.capacity_score >= small_metrics.capacity_score
