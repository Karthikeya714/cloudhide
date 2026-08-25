import io


def _encrypt_via_api(client, content: bytes) -> str:
    response = client.post(
        "/api/files/encrypt",
        files={"file": ("payload.bin", io.BytesIO(content), "application/octet-stream")},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_create_and_list_fragments(client):
    encrypted_file_id = _encrypt_via_api(client, b"E" * 800)

    create_response = client.post(
        "/api/fragments/create",
        json={"encrypted_file_id": encrypted_file_id, "fragment_count": 4},
    )
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["fragment_count"] == 4
    assert len(body["fragments"]) == 4

    transfer_id = body["transfer_id"]
    list_response = client.get(f"/api/fragments/{transfer_id}")
    assert list_response.status_code == 200
    fragments = list_response.json()
    assert [f["fragment_index"] for f in fragments] == [0, 1, 2, 3]


def test_create_fragments_unknown_file_returns_404(client):
    response = client.post(
        "/api/fragments/create",
        json={"encrypted_file_id": "does-not-exist", "fragment_count": 3},
    )
    assert response.status_code == 404


def test_get_fragments_unknown_transfer_returns_404(client):
    response = client.get("/api/fragments/does-not-exist")
    assert response.status_code == 404
