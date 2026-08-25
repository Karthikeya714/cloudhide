# Security Design

## Encryption

- **Algorithm:** AES-256-GCM (authenticated encryption), via Python's
  `cryptography` library (`cryptography.hazmat.primitives.ciphers.aead.AESGCM`).
- **Key generation:** a fresh random 256-bit key is generated per file with
  `AESGCM.generate_key()`, backed by the OS CSPRNG.
- **Nonce:** a fresh random 96-bit nonce is generated per encryption with
  `os.urandom(12)` — the size recommended for AES-GCM. Nonces are never reused
  across encryptions.
- **On-disk format:** encrypted files are stored as `nonce (12 bytes) ||
  ciphertext || GCM tag (16 bytes)`, so the nonce always travels with the
  ciphertext it belongs to.
- **Tamper detection:** GCM's authentication tag means any modification to
  the ciphertext (including a re-ordered or truncated file) causes decryption
  to raise `InvalidTag` rather than silently returning corrupted plaintext.
  CloudHide surfaces this as `DecryptionError` / `RecoveryError`.

## Key management

- Every file gets its own AES-256 key ("file key"). The file key is never
  written to disk or the database in the clear.
- Before storage, the file key is itself encrypted ("wrapped") with a single
  **master key** (`wrap_key()` / `unwrap_key()` in `core/security.py`), also
  using AES-256-GCM. The wrapped key (nonce + ciphertext) is stored as
  `EncryptedFile.wrapped_key`.
- The master key is read from the `MASTER_KEY_BASE64` environment variable
  (32 random bytes, base64-encoded). **Every deployment must set this
  explicitly** — `core/security.py` falls back to an insecure all-zero
  development key and logs a loud warning if it's unset, so local dev still
  works but nothing resembling production security is silently assumed.
- No API response ever includes `wrapped_key`, a file key, or the master key.
  This is enforced structurally: the Pydantic response schemas
  (`schemas/file.py`, etc.) simply don't declare those fields, so FastAPI
  cannot serialize them even by accident.

## Integrity verification

SHA-256 hashes are checked at every hand-off in both pipelines:

1. **Hide:** original file hash recorded at encryption time.
2. **Fragment:** each fragment's hash recorded at split time.
3. **Embed:** each stego image's LSB payload includes its own SHA-256
   checksum in the steganography header (see below), independent of the
   database.
4. **Recover — extract:** each extracted fragment's hash is checked against
   its steganography-header checksum (`extract_payload`) *and* against the
   `Fragment.sha256` recorded in the database, so tampering with either the
   stego image or the fragment metadata is caught.
5. **Recover — reconstruct:** the reassembled encrypted file's hash is
   checked against `EncryptedFile.encrypted_sha256` before decryption is
   even attempted.
6. **Recover — decrypt:** the decrypted plaintext's hash is checked against
   `EncryptedFile.original_sha256` as the final end-to-end integrity gate.

## Steganography payload structure

Every embedded payload is prefixed with a fixed 45-byte header (see
`services/steganography_service.py`):

```
magic (4 bytes, "CHV1") | version (1 byte) | fragment_index (4 bytes)
| payload_length (4 bytes) | SHA-256 checksum (32 bytes) | payload...
```

`extract_payload()` validates the magic bytes and version before trusting
anything else in the header, then validates the checksum before returning
the payload — an image with no CloudHide data, a corrupted header, or a
tampered payload all fail cleanly with a `CorruptedDataError`.

## Secrets and configuration

- All security-sensitive values (`MASTER_KEY_BASE64`, MinIO credentials) are
  read from environment variables (`backend/.env`, never committed — see
  `.gitignore`) via `pydantic-settings`.
- `backend/.env.example` documents every variable without real values.

## What this design does *not* claim

See [`limitations.md`](limitations.md) and [`threat_model.md`](threat_model.md)
for an honest accounting of what CloudHide's security model does not cover.
