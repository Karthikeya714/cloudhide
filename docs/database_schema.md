# Database Schema

SQLite for development (`backend/cloudhide.db`), via SQLAlchemy 2.0 models in
`backend/app/models/`. All primary keys are UUID strings.

## Tables

### `encrypted_files`
One row per secret file after AES-256-GCM encryption (Phase 1).

| Column | Type | Notes |
|---|---|---|
| `id` | str (PK) | |
| `original_filename` | str | |
| `original_size` | int | bytes, before encryption |
| `original_sha256` | str | integrity hash of the plaintext |
| `encrypted_size` | int | bytes, nonce + ciphertext + GCM tag |
| `encrypted_sha256` | str | integrity hash of the encrypted payload |
| `storage_path` | str | key into the active `StorageProvider` |
| `wrapped_key` | str | the AES-256 file key, itself AES-GCM-encrypted with the server master key. **Never returned by any API response.** |
| `status` | str | `encrypted` |
| `created_at` | datetime | |

### `transfers`
One row per hide/recover cycle (Phase 5+). The central record everything else hangs off.

| Column | Type | Notes |
|---|---|---|
| `id` | str (PK) | this is the "transfer ID" used throughout the API |
| `encrypted_file_id` | str (FK → `encrypted_files.id`) | |
| `original_filename` | str | denormalized for display |
| `fragment_count` | int | |
| `status` | str | `pending` → `fragmented` → `completed` → `recovered`, or `failed` / `recovery_failed` |
| `encryption_time_ms`, `fragmentation_time_ms`, `embedding_time_ms` | float, nullable | hide-pipeline timing breakdown |
| `processing_time_ms` | float, nullable | total hide time |
| `recovered_storage_path` | str, nullable | set once recovery succeeds |
| `extraction_time_ms`, `recovery_time_ms` | float, nullable | recovery-pipeline timing |
| `created_at` | datetime | |

### `fragments`
One row per encrypted-file fragment (Phase 2), owned by a transfer.

| Column | Type | Notes |
|---|---|---|
| `id` | str (PK) | |
| `transfer_id` | str (FK → `transfers.id`) | |
| `encrypted_file_id` | str (FK → `encrypted_files.id`) | |
| `fragment_index` | int | 0-based position within the transfer |
| `total_fragments` | int | |
| `size` | int | bytes |
| `sha256` | str | integrity hash of this fragment's bytes |
| `storage_path` | str | |
| `created_at` | datetime | |

### `carriers`
One row per uploaded PNG carrier image and its computed suitability metrics (Phase 4).

| Column | Type | Notes |
|---|---|---|
| `id` | str (PK) | |
| `original_filename`, `storage_path` | str | |
| `width`, `height`, `pixel_count` | int | |
| `raw_capacity_bytes`, `max_payload_bytes` | int | max_payload_bytes accounts for the steganography header overhead |
| `shannon_entropy` | float | bits/pixel, 0-8 |
| `edge_density` | float | 0-1 |
| `distortion_risk` | float | 0-1, higher = more detectable embedding |
| `capacity_score`, `entropy_score`, `edge_score`, `distortion_score`, `overall_score` | float | 0-100 each |
| `explanation` | text | JSON-encoded `list[str]` of human-readable scoring reasons |
| `created_at` | datetime | |

### `stego_images`
One row per (fragment, carrier) embedding (Phase 5), the join point of the whole system.

| Column | Type | Notes |
|---|---|---|
| `id` | str (PK) | |
| `transfer_id` | str (FK → `transfers.id`) | |
| `fragment_id` | str (FK → `fragments.id`, unique) | one stego image per fragment |
| `carrier_id` | str (FK → `carriers.id`) | |
| `storage_provider` | str | `local` or `minio` (Phase 7) |
| `storage_path` | str | |
| `psnr_db`, `ssim`, `capacity_utilization` | float, nullable | quality metrics computed at embed time (Phase 8) |
| `created_at` | datetime | |

## Relationships

```
EncryptedFile 1───* Transfer 1───* Fragment 1───1 StegoImage *───1 Carrier
```

- A `Transfer` belongs to one `EncryptedFile` and owns many `Fragment`s and `StegoImage`s.
- A `Fragment` belongs to exactly one `Transfer` and has at most one `StegoImage`.
- A `StegoImage` references exactly one `Fragment` and one `Carrier`; a `Carrier` can be reused across many `StegoImage`s (across different transfers).

## Notes

- SQLite foreign keys are declared but not enforced at the DB level by
  default (SQLAlchemy doesn't turn on `PRAGMA foreign_keys` here); integrity
  is maintained by the application layer, which always creates parent rows
  before children in a single transaction.
- No table stores a raw or unwrapped encryption key — only `wrapped_key`,
  which is itself ciphertext.
