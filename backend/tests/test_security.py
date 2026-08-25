import pytest
from cryptography.exceptions import InvalidTag

from app.core.security import (
    aes_gcm_decrypt,
    aes_gcm_encrypt,
    generate_aes_key,
    generate_nonce,
    unwrap_key,
    wrap_key,
)
from app.services.file_service import sha256_hex


def test_generate_aes_key_is_256_bit():
    key = generate_aes_key()
    assert len(key) == 32


def test_generate_nonce_is_96_bit_and_random():
    n1 = generate_nonce()
    n2 = generate_nonce()
    assert len(n1) == 12
    assert n1 != n2


def test_encrypt_decrypt_roundtrip():
    key = generate_aes_key()
    plaintext = b"the quick brown fox jumps over the lazy dog"

    ciphertext, nonce = aes_gcm_encrypt(plaintext, key)
    assert ciphertext != plaintext

    decrypted = aes_gcm_decrypt(ciphertext, key, nonce)
    assert decrypted == plaintext


def test_decrypt_with_wrong_key_fails():
    key = generate_aes_key()
    wrong_key = generate_aes_key()
    ciphertext, nonce = aes_gcm_encrypt(b"secret data", key)

    with pytest.raises(InvalidTag):
        aes_gcm_decrypt(ciphertext, wrong_key, nonce)


def test_decrypt_tampered_ciphertext_fails():
    key = generate_aes_key()
    ciphertext, nonce = aes_gcm_encrypt(b"secret data", key)
    tampered = bytes([ciphertext[0] ^ 0xFF]) + ciphertext[1:]

    with pytest.raises(InvalidTag):
        aes_gcm_decrypt(tampered, key, nonce)


def test_wrap_unwrap_key_roundtrip():
    key = generate_aes_key()
    wrapped = wrap_key(key)
    assert isinstance(wrapped, str)

    unwrapped = unwrap_key(wrapped)
    assert unwrapped == key


def test_sha256_hex_is_deterministic_and_correct_length():
    data = b"hello cloudhide"
    digest = sha256_hex(data)
    assert len(digest) == 64
    assert digest == sha256_hex(data)
    assert digest != sha256_hex(b"different data")
