from io import BytesIO

import numpy as np
from PIL import Image


def make_png_bytes(width=200, height=200, seed=0) -> bytes:
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8)
    buffer = BytesIO()
    Image.fromarray(arr, mode="RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def test_analytics_endpoint_reflects_real_pipeline_run(client):
    for seed in range(2):
        response = client.post(
            "/api/carriers/upload",
            files={"file": (f"carrier{seed}.png", BytesIO(make_png_bytes(seed=seed)), "image/png")},
        )
        assert response.status_code == 201

    hide_response = client.post(
        "/api/transfers/hide",
        files={"file": ("secret.bin", BytesIO(b"analytics api test" * 15), "application/octet-stream")},
        data={"fragment_count": "2"},
    )
    assert hide_response.status_code == 201
    transfer_id = hide_response.json()["transfer_id"]

    recover_response = client.post(f"/api/transfers/{transfer_id}/recover")
    assert recover_response.status_code == 200

    analytics_response = client.get("/api/analytics")
    assert analytics_response.status_code == 200
    body = analytics_response.json()

    summary = body["summary"]
    assert summary["total_transfers"] == 1
    assert summary["files_hidden"] == 1
    assert summary["successful_recoveries"] == 1
    assert summary["recovery_rate"] == 1.0
    assert summary["avg_psnr_db"] > 0
    assert 0 <= summary["avg_ssim"] <= 1
    assert summary["avg_encryption_time_ms"] > 0

    assert len(body["recent_transfers"]) == 1
    assert body["recent_transfers"][0]["id"] == transfer_id


def test_analytics_endpoint_with_no_data(client):
    response = client.get("/api/analytics")
    assert response.status_code == 200
    body = response.json()

    assert body["summary"]["total_transfers"] == 0
    assert body["summary"]["avg_psnr_db"] is None
    assert body["recent_transfers"] == []
