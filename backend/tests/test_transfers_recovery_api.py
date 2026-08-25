from io import BytesIO

import numpy as np
from PIL import Image


def make_png_bytes(width=200, height=200, seed=0) -> bytes:
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8)
    buffer = BytesIO()
    Image.fromarray(arr, mode="RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def _upload_carriers(client, count: int):
    for seed in range(count):
        response = client.post(
            "/api/carriers/upload",
            files={"file": (f"carrier{seed}.png", BytesIO(make_png_bytes(seed=seed)), "image/png")},
        )
        assert response.status_code == 201


def test_hide_then_recover_then_download_full_cycle(client):
    """The complete faculty-demo flow: hide -> recover -> download -> hash match."""
    _upload_carriers(client, count=3)

    secret_content = b"full cycle demo secret content" * 20
    hide_response = client.post(
        "/api/transfers/hide",
        files={"file": ("demo.bin", BytesIO(secret_content), "application/octet-stream")},
        data={"fragment_count": "3"},
    )
    assert hide_response.status_code == 201
    transfer_id = hide_response.json()["transfer_id"]

    recover_response = client.post(f"/api/transfers/{transfer_id}/recover")
    assert recover_response.status_code == 200
    recover_body = recover_response.json()
    assert recover_body["status"] == "recovered"
    assert recover_body["integrity_verified"] is True
    assert recover_body["recovered_size"] == len(secret_content)

    download_response = client.get(f"/api/transfers/{transfer_id}/download")
    assert download_response.status_code == 200
    assert download_response.content == secret_content
    assert "demo.bin" in download_response.headers["content-disposition"]


def test_download_before_recover_returns_conflict(client):
    _upload_carriers(client, count=2)
    hide_response = client.post(
        "/api/transfers/hide",
        files={"file": ("demo.bin", BytesIO(b"not yet recovered" * 5), "application/octet-stream")},
        data={"fragment_count": "2"},
    )
    transfer_id = hide_response.json()["transfer_id"]

    download_response = client.get(f"/api/transfers/{transfer_id}/download")
    assert download_response.status_code == 409


def test_recover_unknown_transfer_returns_404(client):
    response = client.post("/api/transfers/does-not-exist/recover")
    assert response.status_code == 404
