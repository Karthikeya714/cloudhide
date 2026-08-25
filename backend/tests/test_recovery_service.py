from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from app.services.carrier_service import upload_and_analyze_carrier
from app.services.file_service import read_bytes, resolve_path, sha256_hex
from app.services.pipeline_service import hide_file
from app.services.recovery_service import RecoveryError, recover_transfer


def make_png_bytes(width=200, height=200, seed=0) -> bytes:
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8)
    buffer = BytesIO()
    Image.fromarray(arr, mode="RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def _upload_carriers(db_session, count: int):
    for seed in range(count):
        upload_and_analyze_carrier(db_session, f"carrier{seed}.png", make_png_bytes(seed=seed))


def test_full_hide_then_recover_matches_original_bytes(db_session):
    _upload_carriers(db_session, count=4)
    secret = b"CloudHide full pipeline test payload" * 15

    transfer = hide_file(db_session, "secret.bin", secret, fragment_count=4)
    recovered = recover_transfer(db_session, transfer.id)

    assert recovered.status == "recovered"
    assert recovered.recovered_storage_path is not None

    recovered_bytes = read_bytes(recovered.recovered_storage_path)
    assert recovered_bytes == secret
    assert sha256_hex(recovered_bytes) == sha256_hex(secret)


def test_recover_unknown_transfer_raises(db_session):
    with pytest.raises(RecoveryError):
        recover_transfer(db_session, "does-not-exist")


def test_recover_fails_on_missing_stego_image(db_session):
    _upload_carriers(db_session, count=3)
    transfer = hide_file(db_session, "secret.bin", b"missing fragment test" * 10, fragment_count=3)

    missing_stego = transfer.stego_images[0]
    resolve_path(missing_stego.storage_path).unlink()

    with pytest.raises(RecoveryError):
        recover_transfer(db_session, transfer.id)


def test_recover_fails_on_corrupted_stego_image(db_session):
    _upload_carriers(db_session, count=3)
    transfer = hide_file(db_session, "secret.bin", b"corrupted fragment test" * 10, fragment_count=3)

    target = transfer.stego_images[0]
    path = resolve_path(target.storage_path)
    image = Image.open(path)
    arr = np.array(image)
    flat = arr.reshape(-1)
    flat[500] ^= 0x01  # flip a bit inside the embedded payload region
    Image.fromarray(flat.reshape(arr.shape), mode="RGB").save(path, format="PNG")

    with pytest.raises(RecoveryError):
        recover_transfer(db_session, transfer.id)


def test_recover_fails_when_carrier_has_no_hidden_data(db_session):
    _upload_carriers(db_session, count=3)
    transfer = hide_file(db_session, "secret.bin", b"replaced carrier test" * 10, fragment_count=3)

    target = transfer.stego_images[0]
    path = resolve_path(target.storage_path)
    Image.fromarray(
        np.random.default_rng(99).integers(0, 256, size=(200, 200, 3), dtype=np.uint8), mode="RGB"
    ).save(path, format="PNG")

    with pytest.raises(RecoveryError):
        recover_transfer(db_session, transfer.id)
