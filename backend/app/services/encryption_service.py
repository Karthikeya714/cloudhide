"""Encrypts and decrypts secret files with AES-256-GCM, tracked in SQLite."""
import logging

from sqlalchemy.orm import Session

from app.core.security import (
    aes_gcm_decrypt,
    aes_gcm_encrypt,
    generate_aes_key,
    unwrap_key,
    wrap_key,
)
from app.models.encrypted_file import EncryptedFile
from app.services.file_service import (
    read_bytes,
    sha256_hex,
    validate_upload_size,
    write_bytes,
)

logger = logging.getLogger(__name__)

# Encrypted files on disk are stored as: 12-byte nonce || GCM ciphertext(+tag)
_NONCE_SIZE = 12


class DecryptionError(Exception):
    """Raised when a stored encrypted file fails to decrypt or verify."""


def encrypt_file(db: Session, original_filename: str, data: bytes) -> EncryptedFile:
    """Encrypt raw file bytes with a fresh AES-256-GCM key and persist metadata.

    The per-file key is wrapped with the server master key before storage;
    it is never returned to callers or exposed via the API.
    """
    validate_upload_size(data)

    original_sha256 = sha256_hex(data)

    file_key = generate_aes_key()
    ciphertext, nonce = aes_gcm_encrypt(data, file_key)
    payload = nonce + ciphertext

    storage_path, _ = write_bytes("encrypted", payload, suffix=".enc")

    record = EncryptedFile(
        original_filename=original_filename,
        original_size=len(data),
        original_sha256=original_sha256,
        encrypted_size=len(payload),
        encrypted_sha256=sha256_hex(payload),
        storage_path=storage_path,
        wrapped_key=wrap_key(file_key),
        status="encrypted",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info(
        "Encrypted file %s (%d bytes -> %d bytes) as %s",
        original_filename,
        len(data),
        len(payload),
        record.id,
    )
    return record


def decrypt_payload(record: EncryptedFile, payload: bytes) -> bytes:
    """Decrypt an in-memory encrypted payload against a known EncryptedFile record.

    Used both by decrypt_file() (payload read from local storage) and by the
    recovery pipeline (payload reconstructed from extracted fragments).
    """
    if sha256_hex(payload) != record.encrypted_sha256:
        raise DecryptionError("Encrypted file integrity check failed (hash mismatch)")

    nonce, ciphertext = payload[:_NONCE_SIZE], payload[_NONCE_SIZE:]
    file_key = unwrap_key(record.wrapped_key)

    try:
        plaintext = aes_gcm_decrypt(ciphertext, file_key, nonce)
    except Exception as exc:  # cryptography raises InvalidTag on tamper/wrong key
        raise DecryptionError(f"Decryption failed: {exc}") from exc

    if sha256_hex(plaintext) != record.original_sha256:
        raise DecryptionError("Decrypted file does not match original SHA-256 hash")

    return plaintext


def decrypt_file(db: Session, file_id: str) -> bytes:
    """Decrypt a previously encrypted file and verify its integrity end to end."""
    record = db.get(EncryptedFile, file_id)
    if record is None:
        raise DecryptionError(f"No encrypted file with id {file_id}")

    payload = read_bytes(record.storage_path)
    return decrypt_payload(record, payload)
