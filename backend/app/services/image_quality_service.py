"""Image quality metrics for evaluating stego images against their carriers."""
import numpy as np
from PIL import Image
from skimage.metrics import peak_signal_noise_ratio, structural_similarity


def compute_quality_metrics(original: Image.Image, stego: Image.Image) -> tuple[float, float]:
    """Compute PSNR (dB) and SSIM between an original carrier and its stego image.

    Both images are compared as RGB arrays of identical dimensions (embedding
    never changes image size). Returns (psnr_db, ssim).
    """
    original_arr = np.array(original.convert("RGB"), dtype=np.uint8)
    stego_arr = np.array(stego.convert("RGB"), dtype=np.uint8)

    if original_arr.shape != stego_arr.shape:
        raise ValueError(
            f"Cannot compare images of different dimensions: {original_arr.shape} vs {stego_arr.shape}"
        )

    if np.array_equal(original_arr, stego_arr):
        # Identical images: PSNR is mathematically infinite, SSIM is exactly 1.
        return float("inf"), 1.0

    psnr = float(peak_signal_noise_ratio(original_arr, stego_arr, data_range=255))
    ssim = float(structural_similarity(original_arr, stego_arr, channel_axis=2, data_range=255))
    return psnr, ssim
