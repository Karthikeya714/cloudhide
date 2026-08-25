import io


def test_encrypt_endpoint_returns_metadata_without_key(client):
    file_content = b"faculty demo secret content"
    response = client.post(
        "/api/files/encrypt",
        files={"file": ("demo.txt", io.BytesIO(file_content), "text/plain")},
    )

    assert response.status_code == 201
    body = response.json()

    assert body["original_filename"] == "demo.txt"
    assert body["original_size"] == len(file_content)
    assert body["encrypted_size"] > body["original_size"]
    assert body["status"] == "encrypted"
    assert "id" in body

    # The response must never expose the encryption key or nonce.
    serialized = str(body)
    assert "wrapped_key" not in serialized
    assert "key" not in body


def test_encrypt_endpoint_rejects_empty_file(client):
    response = client.post(
        "/api/files/encrypt",
        files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
    )
    assert response.status_code == 400
