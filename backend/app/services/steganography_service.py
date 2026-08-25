"""PNG LSB steganography: embed and extract binary payloads inside images.

Payloads are embedded in the least significant bit of each R/G/B channel
byte, row-major, prefixed by a fixed-size header (magic bytes, version,
fragment index, payload length, SHA-256 checksum) so extraction can validate
that hidden data is present and intact before trusting it.
"""
import hashlib
import logging
import struct
from dataclasses import dataclass
from io import BytesIO

import numpy as np
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)

MAGIC = b"CHV1"
HEADER_FORMAT = ">4sBII32s"  # magic, version, fragment_index, payload_length, sha256
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
VERSION = 1

BITS_PER_BYTE = 8
CHANNELS_USED = 3  # R, G, B (alpha, if present, is left untouched)


class SteganographyError(Exception):
    pass


class UnsupportedFormatError(SteganographyError):
    pass


class InsufficientCapacityError(SteganographyError):
    pass


class CorruptedDataError(SteganographyError):
    pass


@dataclass
class CapacityInfo:
    width: int
    height: int
    pixel_count: int
    raw_capacity_bytes: int
    max_payload_bytes: int


@dataclass
class ExtractedPayload:
    fragment_index: int
    payload: bytes


def load_png_image(data: bytes) -> Image.Image:
    """Load and validate a PNG image from raw bytes."""
    try:
        image = Image.open(BytesIO(data))
        image.load()
    except UnidentifiedImageError as exc:
        raise UnsupportedFormatError("File is not a valid image") from exc

    if image.format != "PNG":
        raise UnsupportedFormatError(
            f"Unsupported image format '{image.format}'; only PNG carriers are supported"
        )
    return image


def calculate_capacity(image: Image.Image) -> CapacityInfo:
    """Compute how many bytes can be hidden in an image via 1-bit-per-channel LSB embedding."""
    width, height = image.size
    pixel_count = width * height
    raw_capacity_bits = pixel_count * CHANNELS_USED
    raw_capacity_bytes = raw_capacity_bits // BITS_PER_BYTE
    max_payload_bytes = max(raw_capacity_bytes - HEADER_SIZE, 0)

    return CapacityInfo(
        width=width,
        height=height,
        pixel_count=pixel_count,
        raw_capacity_bytes=raw_capacity_bytes,
        max_payload_bytes=max_payload_bytes,
    )


def _image_to_channel_array(image: Image.Image) -> np.ndarray:
    rgb = image.convert("RGB")
    return np.array(rgb, dtype=np.uint8)


def embed_payload(image: Image.Image, payload: bytes, fragment_index: int) -> Image.Image:
    """Embed `payload` into `image`, returning a new stego image (RGB, PNG-safe)."""
    capacity = calculate_capacity(image)
    if len(payload) > capacity.max_payload_bytes:
        raise InsufficientCapacityError(
            f"Payload of {len(payload)} bytes exceeds carrier capacity of "
            f"{capacity.max_payload_bytes} bytes for a {capacity.width}x{capacity.height} image"
        )
    if fragment_index < 0 or fragment_index > 0xFFFFFFFF:
        raise ValueError("fragment_index must fit in an unsigned 32-bit integer")

    checksum = hashlib.sha256(payload).digest()
    header = struct.pack(HEADER_FORMAT, MAGIC, VERSION, fragment_index, len(payload), checksum)
    blob = header + payload

    bits = np.unpackbits(np.frombuffer(blob, dtype=np.uint8))

    arr = _image_to_channel_array(image)
    flat = arr.reshape(-1)

    modified = flat.copy()
    modified[: len(bits)] = (modified[: len(bits)] & 0xFE) | bits

    stego_arr = modified.reshape(arr.shape)
    stego_image = Image.fromarray(stego_arr, mode="RGB")

    logger.info(
        "Embedded fragment %d (%d bytes) into %dx%d carrier",
        fragment_index,
        len(payload),
        capacity.width,
        capacity.height,
    )
    return stego_image


def extract_payload(image: Image.Image) -> ExtractedPayload:
    """Extract and verify a payload previously embedded by embed_payload()."""
    arr = _image_to_channel_array(image)
    flat = arr.reshape(-1)

    header_bit_count = HEADER_SIZE * BITS_PER_BYTE
    if flat.size < header_bit_count:
        raise CorruptedDataError("Image is too small to contain a valid CloudHide header")

    header_bits = flat[:header_bit_count] & 1
    header_bytes = np.packbits(header_bits).tobytes()

    try:
        magic, version, fragment_index, payload_length, checksum = struct.unpack(
            HEADER_FORMAT, header_bytes
        )
    except struct.error as exc:
        raise CorruptedDataError("Failed to parse steganography header") from exc

    if magic != MAGIC:
        raise CorruptedDataError("No valid CloudHide payload found in this image")
    if version != VERSION:
        raise CorruptedDataError(f"Unsupported CloudHide payload version {version}")

    payload_bit_count = payload_length * BITS_PER_BYTE
    if header_bit_count + payload_bit_count > flat.size:
        raise CorruptedDataError(
            "Declared payload length exceeds image capacity; image is corrupted or truncated"
        )

    payload_bits = flat[header_bit_count : header_bit_count + payload_bit_count] & 1
    payload = np.packbits(payload_bits).tobytes()

    if hashlib.sha256(payload).digest() != checksum:
        raise CorruptedDataError("Checksum mismatch: hidden data is corrupted")

    return ExtractedPayload(fragment_index=fragment_index, payload=payload)


def image_to_png_bytes(image: Image.Image) -> bytes:
    """Serialize an image to lossless PNG bytes."""
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
