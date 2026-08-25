from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from app.services.carrier_service import upload_and_analyze_carrier
from app.services.fragmentation_service import reconstruct_file
from app.services.pipeline_service import PipelineError, hide_file
from app.services.steganography_service import extract_payload, load_png_image
from app.services.file_service import read_bytes


def make_png_bytes(width=200, height=200, seed=0) -> bytes:
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8)
    buffer = BytesIO()
    Image.fromarray(arr, mode="RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def _upload_carriers(db_session, count: int, width=200, height=200):
    for seed in range(count):
        upload_and_analyze_carrier(db_session, f"carrier{seed}.png", make_png_bytes(width, height, seed))


def test_hide_file_creates_completed_transfer_with_stego_images(db_session):
    _upload_carriers(db_session, count=3)

    secret = b"CloudHide course project secret payload" * 5
    transfer = hide_file(db_session, "secret.txt", secret, fragment_count=3)

    assert transfer.status == "completed"
    assert transfer.fragment_count == 3
    assert len(transfer.fragments) == 3
    assert len(transfer.stego_images) == 3
    assert transfer.processing_time_ms is not None
    assert transfer.processing_time_ms > 0

    # Every fragment must have exactly one stego image using a distinct carrier.
    carrier_ids = {s.carrier_id for s in transfer.stego_images}
    assert len(carrier_ids) == 3


def test_hide_file_fails_with_insufficient_carriers(db_session):
    _upload_carriers(db_session, count=1)

    with pytest.raises(PipelineError):
        hide_file(db_session, "secret.txt", b"some secret data", fragment_count=3)


def test_hide_file_fails_when_carriers_too_small(db_session):
    # 4x4 PNGs have almost no capacity.
    _upload_carriers(db_session, count=2, width=4, height=4)

    with pytest.raises(PipelineError):
        hide_file(db_session, "secret.txt", b"X" * 5000, fragment_count=2)


def test_stego_images_can_be_extracted_and_reconstructed_to_original(db_session):
    _upload_carriers(db_session, count=4)

    secret = bytes(range(256)) * 8
    transfer = hide_file(db_session, "binary.dat", secret, fragment_count=4)

    # Extract each fragment straight back out of its stego image.
    for stego in transfer.stego_images:
        stego_bytes = read_bytes(stego.storage_path)
        stego_image = load_png_image(stego_bytes)
        extracted = extract_payload(stego_image)

        matching_fragment = next(f for f in transfer.fragments if f.id == stego.fragment_id)
        assert extracted.fragment_index == matching_fragment.fragment_index
        assert extracted.payload == read_bytes(matching_fragment.storage_path)

    reconstructed_encrypted = reconstruct_file(db_session, transfer.id)
    original_encrypted_bytes = read_bytes(transfer.encrypted_file.storage_path)
    assert reconstructed_encrypted == original_encrypted_bytes
