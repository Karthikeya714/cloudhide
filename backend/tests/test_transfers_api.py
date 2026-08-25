from io import BytesIO

import numpy as np
from PIL import Image


def make_png_bytes(width=200, height=200, seed=0) -> bytes:
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8)
    buffer = BytesIO()
    Image.fromarray(arr, mode="RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def _upload_carriers(client, count: int, width=200, height=200, seed_offset=0):
    ids = []
    for seed in range(seed_offset, seed_offset + count):
        response = client.post(
            "/api/carriers/upload",
            files={"file": (f"carrier{seed}.png", BytesIO(make_png_bytes(width, height, seed)), "image/png")},
        )
        assert response.status_code == 201
        ids.append(response.json()["id"])
    return ids


def test_full_pipeline_end_to_end(client):
    """Upload carriers -> hide a secret file -> list/get the resulting transfer."""
    _upload_carriers(client, count=3)

    secret_content = b"end-to-end faculty demo secret" * 10
    hide_response = client.post(
        "/api/transfers/hide",
        files={"file": ("secret.txt", BytesIO(secret_content), "text/plain")},
        data={"fragment_count": "3"},
    )
    assert hide_response.status_code == 201
    body = hide_response.json()

    assert body["fragment_count"] == 3
    assert body["status"] == "completed"
    assert len(body["stego_images"]) == 3
    assert len(body["selected_carrier_ids"]) == 3
    assert body["processing_time_ms"] > 0

    transfer_id = body["transfer_id"]

    list_response = client.get("/api/transfers")
    assert list_response.status_code == 200
    assert any(t["id"] == transfer_id for t in list_response.json())

    get_response = client.get(f"/api/transfers/{transfer_id}")
    assert get_response.status_code == 200
    detail = get_response.json()
    assert detail["id"] == transfer_id
    assert detail["status"] == "completed"
    assert detail["recovered"] is False
    assert len(detail["fragments"]) == 3
    assert len(detail["stego_images"]) == 3
    for stego in detail["stego_images"]:
        assert stego["psnr_db"] > 0
        assert 0 <= stego["ssim"] <= 1
        assert stego["carrier_filename"]
    assert detail["encryption_time_ms"] > 0
    assert detail["embedding_time_ms"] > 0


def test_hide_with_explicit_carrier_ids_only_uses_those_carriers(client):
    # A larger, unrelated pool that must be ignored when carrier_ids scopes the hide.
    _upload_carriers(client, count=4, width=400, height=400, seed_offset=100)
    session_ids = _upload_carriers(client, count=2, width=100, height=100, seed_offset=200)

    response = client.post(
        "/api/transfers/hide",
        files={"file": ("secret.txt", BytesIO(b"scoped api test payload"), "text/plain")},
        data={"fragment_count": "2", "carrier_ids": ",".join(session_ids)},
    )
    assert response.status_code == 201
    body = response.json()
    assert set(body["selected_carrier_ids"]) == set(session_ids)


def test_hide_with_unknown_carrier_id_returns_clear_error(client):
    _upload_carriers(client, count=1)
    response = client.post(
        "/api/transfers/hide",
        files={"file": ("secret.txt", BytesIO(b"payload"), "text/plain")},
        data={"fragment_count": "1", "carrier_ids": "does-not-exist"},
    )
    assert response.status_code == 409
    assert "Unknown carrier" in response.json()["detail"]


def test_hide_fails_gracefully_with_no_carriers(client):
    response = client.post(
        "/api/transfers/hide",
        files={"file": ("secret.txt", BytesIO(b"no carriers uploaded"), "text/plain")},
        data={"fragment_count": "2"},
    )
    assert response.status_code == 409


def test_get_unknown_transfer_returns_404(client):
    response = client.get("/api/transfers/does-not-exist")
    assert response.status_code == 404
