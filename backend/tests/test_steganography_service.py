from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from app.services.steganography_service import (
    CorruptedDataError,
    InsufficientCapacityError,
    UnsupportedFormatError,
    calculate_capacity,
    embed_payload,
    extract_payload,
    image_to_png_bytes,
    load_png_image,
)


def make_png_bytes(width: int = 64, height: int = 64, seed: int = 0) -> bytes:
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8)
    image = Image.fromarray(arr, mode="RGB")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_load_png_image_accepts_valid_png():
    image = load_png_image(make_png_bytes())
    assert image.size == (64, 64)


def test_load_png_image_rejects_non_png():
    jpeg_buffer = BytesIO()
    Image.new("RGB", (32, 32), color=(10, 20, 30)).save(jpeg_buffer, format="JPEG")

    with pytest.raises(UnsupportedFormatError):
        load_png_image(jpeg_buffer.getvalue())


def test_load_png_image_rejects_garbage_bytes():
    with pytest.raises(UnsupportedFormatError):
        load_png_image(b"this is not an image")


def test_calculate_capacity_matches_expected_formula():
    image = load_png_image(make_png_bytes(width=10, height=10))
    capacity = calculate_capacity(image)

    assert capacity.width == 10
    assert capacity.height == 10
    assert capacity.pixel_count == 100
    assert capacity.raw_capacity_bytes == (100 * 3) // 8
    assert capacity.max_payload_bytes < capacity.raw_capacity_bytes


def test_embed_and_extract_roundtrip():
    image = load_png_image(make_png_bytes(width=128, height=128))
    payload = b"encrypted fragment bytes go here" * 20

    stego = embed_payload(image, payload, fragment_index=2)
    extracted = extract_payload(stego)

    assert extracted.fragment_index == 2
    assert extracted.payload == payload


def test_extraction_survives_png_save_and_reopen():
    image = load_png_image(make_png_bytes(width=128, height=128))
    payload = b"must survive a save/reopen cycle"

    stego = embed_payload(image, payload, fragment_index=7)
    png_bytes = image_to_png_bytes(stego)

    reopened = load_png_image(png_bytes)
    extracted = extract_payload(reopened)

    assert extracted.fragment_index == 7
    assert extracted.payload == payload


def test_embed_rejects_payload_exceeding_capacity():
    image = load_png_image(make_png_bytes(width=8, height=8))
    huge_payload = b"X" * 10_000

    with pytest.raises(InsufficientCapacityError):
        embed_payload(image, huge_payload, fragment_index=0)


def test_extract_rejects_image_with_no_hidden_data():
    image = load_png_image(make_png_bytes(width=64, height=64))
    with pytest.raises(CorruptedDataError):
        extract_payload(image)


def test_extract_detects_tampered_stego_image():
    from app.services.steganography_service import HEADER_SIZE

    image = load_png_image(make_png_bytes(width=64, height=64))
    payload = b"tamper-detection payload"
    stego = embed_payload(image, payload, fragment_index=1)

    arr = np.array(stego)
    flat = arr.reshape(-1)
    # Flip the LSB of a channel byte that carries a payload bit (just after
    # the header, which starts at bit/index HEADER_SIZE * 8).
    payload_start_index = HEADER_SIZE * 8
    flat[payload_start_index] ^= 0x01
    tampered = Image.fromarray(flat.reshape(arr.shape), mode="RGB")

    with pytest.raises(CorruptedDataError):
        extract_payload(tampered)


def test_embed_multiple_fragment_indices_are_preserved():
    image = load_png_image(make_png_bytes(width=64, height=64))

    for index in (0, 1, 255, 65535):
        stego = embed_payload(image, b"fragment payload", fragment_index=index)
        extracted = extract_payload(stego)
        assert extracted.fragment_index == index
