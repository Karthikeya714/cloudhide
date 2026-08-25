"""Cryptographic primitives: AES-256-GCM encryption and key management."""
import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import get_settings

AES_KEY_SIZE = 32  # 256-bit
GCM_NONCE_SIZE = 12  # 96-bit, recommended for AES-GCM


def generate_aes_key() -> bytes:
    """Generate a new random 256-bit AES key."""
    return AESGCM.generate_key(bit_length=256)


def generate_nonce() -> bytes:
    """Generate a new random 96-bit nonce for AES-GCM."""
    return os.urandom(GCM_NONCE_SIZE)


def aes_gcm_encrypt(plaintext: bytes, key: bytes, nonce: bytes | None = None) -> tuple[bytes, bytes]:
    """Encrypt plaintext with AES-256-GCM.

    Returns (ciphertext_with_tag, nonce). The returned ciphertext already
    includes the GCM authentication tag appended by the cryptography library.
    """
    if len(key) != AES_KEY_SIZE:
        raise ValueError(f"AES key must be {AES_KEY_SIZE} bytes, got {len(key)}")

    nonce = nonce or generate_nonce()
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return ciphertext, nonce


def aes_gcm_decrypt(ciphertext: bytes, key: bytes, nonce: bytes) -> bytes:
    """Decrypt ciphertext produced by aes_gcm_encrypt. Raises InvalidTag on tampering."""
    if len(key) != AES_KEY_SIZE:
        raise ValueError(f"AES key must be {AES_KEY_SIZE} bytes, got {len(key)}")

    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)


def _get_master_key() -> bytes:
    """Load the master key (used to wrap per-file keys) from settings.

    Falls back to a fixed development key with a loud warning if unset, so
    local development still works, but every deployment should set
    MASTER_KEY_BASE64 explicitly.
    """
    settings = get_settings()
    if settings.master_key_base64:
        key = base64.b64decode(settings.master_key_base64)
        if len(key) != AES_KEY_SIZE:
            raise ValueError("MASTER_KEY_BASE64 must decode to 32 bytes")
        return key

    import logging

    logging.getLogger(__name__).warning(
        "MASTER_KEY_BASE64 is not set; using an insecure development-only master key. "
        "Set MASTER_KEY_BASE64 in the environment before deploying."
    )
    return b"\x00" * AES_KEY_SIZE


def wrap_key(file_key: bytes) -> str:
    """Encrypt a per-file AES key with the master key for storage at rest.

    Returns a base64 string containing nonce + ciphertext, safe to store in
    the database (never expose it through API responses).
    """
    master_key = _get_master_key()
    ciphertext, nonce = aes_gcm_encrypt(file_key, master_key)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def unwrap_key(wrapped_key_b64: str) -> bytes:
    """Decrypt a per-file AES key that was wrapped with wrap_key()."""
    master_key = _get_master_key()
    raw = base64.b64decode(wrapped_key_b64)
    nonce, ciphertext = raw[:GCM_NONCE_SIZE], raw[GCM_NONCE_SIZE:]
    return aes_gcm_decrypt(ciphertext, master_key, nonce)
