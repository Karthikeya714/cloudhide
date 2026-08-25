# Architecture

## Overview

CloudHide is a monorepo with a FastAPI backend, a React/Vite frontend, and a
local (or MinIO) object store. The backend is organized as a pipeline of
independent, unit-testable services orchestrated by two top-level
coordinators: the hide pipeline and the recovery pipeline.

```
cloudhide/
├── backend/
│   └── app/
│       ├── api/            FastAPI routers (one module per resource)
│       ├── services/       Business logic, framework-agnostic
│       │   └── storage/    Pluggable storage backends
│       ├── models/         SQLAlchemy ORM models
│       ├── schemas/        Pydantic request/response models
│       ├── core/           Config, logging, crypto primitives
│       └── db/             Engine/session setup
├── frontend/
│   └── src/
│       ├── pages/          One component per route
│       ├── components/     Shared UI (Card, Dropzone, charts, ...)
│       ├── layouts/        App shell / navigation
│       ├── services/       API client (axios) + typed calls
│       └── types/          TypeScript interfaces mirroring backend schemas
└── storage/                 Local files: uploads, encrypted, fragments, carriers, stego, recovered
```

## Backend service layering

Each service has one responsibility and depends only on services below it in
this list — never the other way around, which is what keeps the pipeline
testable in isolation:

1. **`core/security.py`** — AES-256-GCM primitives, master-key wrapping.
2. **`services/file_service.py`** — storage-agnostic byte read/write/hash,
   delegating to whichever `StorageProvider` is configured.
3. **`services/storage/`** — `StorageProvider` interface with `Local` and
   `MinIO` implementations (Phase 7). Nothing above this layer knows which
   one is active.
4. **`services/encryption_service.py`** — AES-256-GCM encrypt/decrypt a whole
   file, tracked as an `EncryptedFile` row.
5. **`services/fragmentation_service.py`** — splits/reconstructs an encrypted
   file into byte-range fragments, tracked as `Fragment` rows under a
   `Transfer`.
6. **`services/steganography_service.py`** — pure LSB embed/extract on PIL
   images; no knowledge of the database or storage.
7. **`services/carrier_analysis_service.py`** — pure image scoring (entropy,
   edge density, distortion risk); no knowledge of the database.
8. **`services/carrier_service.py`** — persists carrier uploads + their
   computed metrics as `Carrier` rows.
9. **`services/image_quality_service.py`** — PSNR/SSIM between a carrier and
   its stego image.
10. **`services/pipeline_service.py`** — the hide orchestrator: encrypt →
    fragment → rank carriers → greedily assign carriers to fragments by
    capacity → embed → persist `StegoImage` rows.
11. **`services/recovery_service.py`** — the recovery orchestrator: locate
    stego images → extract → verify → reconstruct → decrypt → verify final
    hash → save.
12. **`services/analytics_service.py`** — read-only aggregation over stored
    `Transfer`/`StegoImage` rows for the dashboard and analytics page.

The steganography and carrier-analysis services never import anything from
`storage/` or touch the database directly — this is what Phase 7 depended on
to make storage genuinely swappable.

## Data flow: hiding a file

```
secret bytes
   │  encrypt_file()               AES-256-GCM, random key + nonce
   ▼
encrypted bytes (EncryptedFile row)
   │  fragment_file()              contiguous byte-range split
   ▼
N fragments (Fragment rows, owned by a new Transfer)
   │  rank_carriers() + select_carriers_for_fragments()
   ▼
N (fragment, carrier) pairs, largest fragments matched to carriers first
   │  embed_payload() per pair     header + SHA-256 checksum + LSB write
   ▼
N stego PNGs (StegoImage rows, with PSNR/SSIM/capacity_utilization)
   │
   ▼
Transfer.status = "completed", timing breakdown recorded
```

## Data flow: recovering a file

```
transfer_id
   │  load Transfer.stego_images
   ▼
extract_payload() per stego image  →  verify checksum against Fragment.sha256
   │  sort by fragment_index, verify none missing
   ▼
reconstructed encrypted bytes
   │  decrypt_payload()             verify encrypted_sha256, then original_sha256
   ▼
plaintext, written to storage/recovered, Transfer.status = "recovered"
```

## Frontend

A single-page React app (Vite + TypeScript + Tailwind v4) with five routed
pages sharing one `AppLayout`. All data is fetched from the backend at
runtime — no page uses hard-coded or mock data. `src/services/api.ts` is the
single point of contact with the backend; every page imports typed functions
from it rather than calling `fetch`/`axios` directly.
