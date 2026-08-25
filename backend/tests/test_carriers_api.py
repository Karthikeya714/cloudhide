from io import BytesIO

import numpy as np
from PIL import Image


def make_png_bytes(width=64, height=64, seed=0) -> bytes:
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8)
    buffer = BytesIO()
    Image.fromarray(arr, mode="RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def test_upload_carrier_returns_metrics(client):
    response = client.post(
        "/api/carriers/upload",
        files={"file": ("carrier.png", BytesIO(make_png_bytes()), "image/png")},
    )
    assert response.status_code == 201
    body = response.json()

    assert body["width"] == 64
    assert body["height"] == 64
    assert 0 <= body["overall_score"] <= 100
    assert isinstance(body["explanation"], list)
    assert len(body["explanation"]) > 0


def test_upload_carrier_rejects_non_png(client):
    jpeg_buffer = BytesIO()
    Image.new("RGB", (32, 32)).save(jpeg_buffer, format="JPEG")

    response = client.post(
        "/api/carriers/upload",
        files={"file": ("carrier.jpg", jpeg_buffer.getvalue(), "image/jpeg")},
    )
    assert response.status_code == 400


def test_analyze_and_rank_endpoints(client):
    for seed in range(3):
        response = client.post(
            "/api/carriers/upload",
            files={"file": (f"carrier{seed}.png", BytesIO(make_png_bytes(seed=seed)), "image/png")},
        )
        assert response.status_code == 201

    analyze_response = client.get("/api/carriers/analyze")
    assert analyze_response.status_code == 200
    assert len(analyze_response.json()) >= 3

    rank_response = client.get("/api/carriers/rank", params={"limit": 2})
    assert rank_response.status_code == 200
    body = rank_response.json()

    scores = [c["overall_score"] for c in body["carriers"]]
    assert scores == sorted(scores, reverse=True)
    assert len(body["recommended"]) == 2
    assert body["recommended"][0]["id"] == body["carriers"][0]["id"]


def test_analyze_unknown_carrier_id_returns_404(client):
    response = client.get("/api/carriers/analyze", params={"carrier_id": "does-not-exist"})
    assert response.status_code == 404
