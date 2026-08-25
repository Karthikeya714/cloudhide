import pytest

from app.services.encryption_service import DecryptionError, decrypt_file, encrypt_file
from app.services.file_service import resolve_path, sha256_hex


def test_encrypt_file_persists_metadata_without_leaking_key(db_session):
    data = b"top secret course project payload" * 50
    record = encrypt_file(db_session, "secret.txt", data)

    assert record.id
    assert record.original_filename == "secret.txt"
    assert record.original_size == len(data)
    assert record.original_sha256 == sha256_hex(data)
    assert record.status == "encrypted"
    assert resolve_path(record.storage_path).exists()

    # The stored key must be wrapped (encrypted), never the raw key.
    assert record.wrapped_key
    assert record.wrapped_key != data


def test_encrypted_file_on_disk_differs_from_plaintext(db_session):
    data = b"identifiable plaintext marker CLOUDHIDE"
    record = encrypt_file(db_session, "note.txt", data)

    on_disk = resolve_path(record.storage_path).read_bytes()
    assert data not in on_disk


def test_encrypt_then_decrypt_roundtrip_matches_original(db_session):
    data = bytes(range(256)) * 10  # binary-safe content
    record = encrypt_file(db_session, "binary.dat", data)

    recovered = decrypt_file(db_session, record.id)
    assert recovered == data


def test_decrypt_rejects_tampered_encrypted_file(db_session):
    data = b"content that must remain intact"
    record = encrypt_file(db_session, "important.txt", data)

    path = resolve_path(record.storage_path)
    corrupted = bytearray(path.read_bytes())
    corrupted[-1] ^= 0xFF
    path.write_bytes(bytes(corrupted))

    with pytest.raises(DecryptionError):
        decrypt_file(db_session, record.id)


def test_decrypt_unknown_file_id_raises(db_session):
    with pytest.raises(DecryptionError):
        decrypt_file(db_session, "does-not-exist")


def test_encrypt_empty_file_rejected(db_session):
    with pytest.raises(ValueError):
        encrypt_file(db_session, "empty.txt", b"")
