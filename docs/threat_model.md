# Threat Model

This is an academic course project. This document states, honestly, what
CloudHide defends against and what it does not — see also
[`limitations.md`](limitations.md).

## Assets

1. The **secret file's contents**.
2. The **fact that a secret file exists / was transferred** (the hidden
   nature of the transfer itself).
3. The **AES-256 file keys** and the **server master key**.

## In scope: what CloudHide defends against

| Threat | Defense |
|---|---|
| An attacker obtains a stego image and tries to read the hidden data without the master key | AES-256-GCM: without the file key, the extracted bytes are ciphertext, computationally infeasible to decrypt |
| An attacker modifies a stego image (adds noise, re-saves, crops) hoping to corrupt undetected | GCM authentication tag + per-fragment SHA-256 + steganography-header checksum all independently detect tampering; recovery fails loudly rather than returning corrupted data |
| An attacker swaps in a different (unrelated) PNG as a "stego image" | `extract_payload()` rejects it: no valid magic bytes/header found |
| An attacker with API access tries to read the encryption key via a response | No response schema includes the wrapped key or master key; verified by tests (`test_files_api.py`) |
| A fragment is lost or duplicated | Recovery checks fragment count and index contiguity before attempting reconstruction |

## Explicitly out of scope

| Threat | Why it's not covered | Mitigation path |
|---|---|---|
| **Steganalysis** — a statistical attacker who suspects a specific image is a stego carrier and tries to detect that fact (not decrypt it) | Plain LSB embedding is well-known to be detectable by chi-square/RS-analysis and similar techniques for large payloads relative to image size. Encryption hides *content*, not *presence*. | Documented in limitations; see "Optional future improvements" for adaptive/frequency-domain embedding |
| **Compromise of the server / master key** | If `MASTER_KEY_BASE64` or the SQLite database is stolen together, every wrapped file key can be unwrapped | Standard key-management practice (KMS/HSM, key rotation) is out of scope for this prototype |
| **Network-level interception** | No TLS is configured by this project (dev servers only) | Deploy behind HTTPS/TLS termination in any real deployment |
| **Authentication / authorization** | Every API endpoint is open; there is no user model | Listed under future improvements — out of scope for the current phases |
| **Denial of service** | No rate limiting; a large `fragment_count` or many concurrent uploads could exhaust resources | `MAX_UPLOAD_SIZE_BYTES` and `MAX_FRAGMENTS` provide basic bounds only |
| **Malicious carrier images (decompression bombs, crafted PNGs)** | Pillow's decoder is trusted as-is; no additional sandboxing | Out of scope for a course prototype |
| **Side-channel timing attacks on decryption** | The `cryptography` library's AES-GCM implementation is used as-is; no additional constant-time hardening was added at the application layer | Out of scope |

## Summary

CloudHide's real security property is: **if an attacker obtains a stego
image without the server's master key, they cannot recover the secret
file's contents, and any tampering with a stego image or its fragment
metadata is detected before corrupted data is trusted.** It does **not**
claim that the existence of hidden data is undetectable to a determined
steganalyst, and it does not implement authentication, transport security,
or key-management infrastructure — those are standard requirements for any
production deployment, but are outside this course project's scope.
