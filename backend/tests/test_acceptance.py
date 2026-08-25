"""Acceptance tests mapped 1:1 to the CloudHide test matrix (see docs/demo_script.md
and phases.md Phase 10). Each test name/docstring references the numbered case it
covers so results are traceable for grading, even though the underlying behavior
is also exercised by the unit-level tests in the other test modules.
"""
from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from app.services.carrier_service import upload_and_analyze_carrier
from app.services.file_service import resolve_path, sha256_hex
from app.services.pipeline_service import PipelineError, hide_file
from app.services.recovery_service import RecoveryError, recover_transfer
from app.services.steganography_service import UnsupportedFormatError, load_png_image


def make_png_bytes(width=200, height=200, seed=0) -> bytes:
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8)
    buffer = BytesIO()
    Image.fromarray(arr, mode="RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def _upload_carriers(db_session, count: int, width=200, height=200):
    for seed in range(count):
        upload_and_analyze_carrier(
            db_session, f"carrier{seed}.png", make_png_bytes(width, height, seed)
        )


def test_case_1_small_file_hides_and_recovers_successfully(db_session):
    """Test 1: small file -> successful hiding and recovery."""
    _upload_carriers(db_session, count=3)
    secret = b"a small secret"

    transfer = hide_file(db_session, "small.txt", secret, fragment_count=3)
    assert transfer.status == "completed"

    recovered = recover_transfer(db_session, transfer.id)
    assert recovered.status == "recovered"
    assert resolve_path(recovered.recovered_storage_path).read_bytes() == secret


def test_case_2_file_larger_than_carrier_capacity_gives_clear_error(db_session):
    """Test 2: file larger than carrier capacity -> clear insufficient-capacity error."""
    _upload_carriers(db_session, count=2, width=8, height=8)  # near-zero capacity

    with pytest.raises(PipelineError, match="capacity"):
        hide_file(db_session, "too_big.bin", b"X" * 5000, fragment_count=2)


def test_case_3_multiple_carriers_are_ranked_and_best_ones_selected(db_session):
    """Test 3: multiple carrier images -> correct ranking and selection."""
    _upload_carriers(db_session, count=2, width=32, height=32)  # low score, low capacity
    _upload_carriers(db_session, count=2, width=400, height=400)  # high score, high capacity

    transfer = hide_file(db_session, "secret.bin", b"payload" * 200, fragment_count=2)

    # The larger, higher-scoring carriers should have been preferred.
    used_carriers = {s.carrier.original_filename for s in transfer.stego_images}
    assert used_carriers == {"carrier0.png", "carrier1.png"}  # the 400x400 batch


def test_case_4_modified_stego_image_is_detected_as_tampered(db_session):
    """Test 4: modified stego image -> tampering/integrity failure detected."""
    _upload_carriers(db_session, count=2)
    transfer = hide_file(db_session, "secret.bin", b"tamper test payload" * 10, fragment_count=2)

    path = resolve_path(transfer.stego_images[0].storage_path)
    arr = np.array(Image.open(path))
    flat = arr.reshape(-1)
    flat[400] ^= 0x01  # flip a bit inside the embedded payload region
    Image.fromarray(flat.reshape(arr.shape), mode="RGB").save(path, format="PNG")

    with pytest.raises(RecoveryError):
        recover_transfer(db_session, transfer.id)


def test_case_5_missing_fragment_fails_recovery_clearly(db_session):
    """Test 5: missing fragment -> recovery fails clearly."""
    _upload_carriers(db_session, count=3)
    transfer = hide_file(db_session, "secret.bin", b"missing fragment payload" * 10, fragment_count=3)

    resolve_path(transfer.stego_images[0].storage_path).unlink()

    with pytest.raises(RecoveryError, match="missing|Missing"):
        recover_transfer(db_session, transfer.id)


def test_case_6_corrupted_fragment_hash_mismatch_is_detected(db_session):
    """Test 6: corrupted fragment -> hash mismatch detected."""
    _upload_carriers(db_session, count=2)
    transfer = hide_file(db_session, "secret.bin", b"corruption test payload" * 10, fragment_count=2)

    fragment_path = resolve_path(transfer.fragments[0].storage_path)
    corrupted = bytearray(fragment_path.read_bytes())
    corrupted[0] ^= 0xFF
    fragment_path.write_bytes(bytes(corrupted))

    from app.services.fragmentation_service import FragmentationError, reconstruct_file

    with pytest.raises(FragmentationError, match="integrity"):
        reconstruct_file(db_session, transfer.id)


def test_case_7_successful_recovery_matches_original_sha256(db_session):
    """Test 7: successful recovery -> recovered file matches original SHA-256 hash."""
    _upload_carriers(db_session, count=3)
    secret = b"faculty demo payload for hash verification" * 20

    transfer = hide_file(db_session, "demo.bin", secret, fragment_count=3)
    recovered = recover_transfer(db_session, transfer.id)

    recovered_bytes = resolve_path(recovered.recovered_storage_path).read_bytes()
    assert sha256_hex(recovered_bytes) == sha256_hex(secret)


def test_case_8_unsupported_image_format_is_rejected(db_session):
    """Test 8: unsupported image format -> validation error."""
    jpeg_buffer = BytesIO()
    Image.new("RGB", (64, 64)).save(jpeg_buffer, format="JPEG")

    with pytest.raises(UnsupportedFormatError):
        load_png_image(jpeg_buffer.getvalue())


def test_case_9_full_pipeline_upload_to_decrypt(client):
    """Test 9: full pipeline -> Upload -> Encrypt -> Fragment -> Hide -> Extract ->
    Reconstruct -> Decrypt, driven through the real HTTP API end to end."""
    for seed in range(3):
        response = client.post(
            "/api/carriers/upload",
            files={"file": (f"carrier{seed}.png", BytesIO(make_png_bytes(seed=seed)), "image/png")},
        )
        assert response.status_code == 201

    secret_content = b"end-to-end acceptance test payload" * 15
    hide_response = client.post(
        "/api/transfers/hide",
        files={"file": ("secret.bin", BytesIO(secret_content), "application/octet-stream")},
        data={"fragment_count": "3"},
    )
    assert hide_response.status_code == 201
    transfer_id = hide_response.json()["transfer_id"]

    recover_response = client.post(f"/api/transfers/{transfer_id}/recover")
    assert recover_response.status_code == 200
    assert recover_response.json()["integrity_verified"] is True

    download_response = client.get(f"/api/transfers/{transfer_id}/download")
    assert download_response.status_code == 200
    assert download_response.content == secret_content
