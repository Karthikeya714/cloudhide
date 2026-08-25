# CloudHide

Secure encrypted file storage using adaptive image steganography.

CloudHide encrypts a secret file with AES-256-GCM, splits the ciphertext into
fragments, analyzes candidate PNG carrier images, and hides the fragments
inside the best-scoring carriers using LSB steganography. The reverse pipeline
extracts, verifies, reconstructs, and decrypts the original file.

## Project Status

All phases in [`../phases.md`](../phases.md) are implemented (Phase 0 through
Phase 10): project setup, encryption, fragmentation, steganography, adaptive
carrier selection, the full hide/recover pipelines, pluggable storage,
analytics, the complete frontend, and this final testing/documentation pass.

## Monorepo Layout

```
cloudhide/
├── backend/     FastAPI application (Python)
├── frontend/    React + Vite + TypeScript + Tailwind dashboard
├── storage/     Local storage for uploads, encrypted files, fragments, carriers, stego, recovered
├── samples/     Sample PNG carrier images for demoing without sourcing your own
├── scripts/     verify.py -- final end-to-end verification script
├── docs/        Architecture, security, threat model, API reference, demo script
└── docker-compose.yml
```

## Backend

Requirements: Python 3.12+

```bash
cd backend
python -m venv venv
./venv/Scripts/activate       # Windows
# source venv/bin/activate    # macOS/Linux
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

The API is served at `http://localhost:8000`. Interactive docs at
`http://localhost:8000/docs`. Health check at `http://localhost:8000/health`.
Static endpoint reference: [`docs/api.md`](docs/api.md).

Run tests:

```bash
cd backend
pytest
```

87 tests cover unit-level behavior of every service plus full end-to-end
integration tests, including the 9 acceptance scenarios in
`backend/tests/test_acceptance.py` mapped directly to the course's required
test matrix.

## Frontend

Requirements: Node 20+

```bash
cd frontend
npm install
npm run dev
```

The dashboard is served at `http://localhost:5173` and proxies `/api` and
`/health` requests to the backend during development (see `vite.config.ts`).

## Final Verification

Run the whole thing end to end -- starts the backend, runs the full pytest
suite, then drives a real hide → recover → download cycle against the live
server and checks the recovered bytes match exactly:

```bash
backend/venv/Scripts/python.exe scripts/verify.py      # Windows
# backend/venv/bin/python scripts/verify.py              # macOS/Linux
```

## Docker Compose

```bash
docker compose up --build
```

Starts the backend, frontend, and a local MinIO instance for object storage.

## Configuration

Backend configuration lives in `backend/.env` (see `backend/.env.example` for
all available options: database URL, storage provider, MinIO credentials,
CORS origins, and the master key used to protect per-file encryption keys).
Never commit a real `.env` file or encryption keys.

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — service layering and data flow
- [`docs/database_schema.md`](docs/database_schema.md) — tables and relationships
- [`docs/security.md`](docs/security.md) — encryption, key management, integrity checks
- [`docs/threat_model.md`](docs/threat_model.md) — what is and isn't defended against
- [`docs/limitations.md`](docs/limitations.md) — honest limitations of LSB steganography and this prototype
- [`docs/future_improvements.md`](docs/future_improvements.md) — optional next steps
- [`docs/api.md`](docs/api.md) — endpoint reference
- [`docs/demo_script.md`](docs/demo_script.md) — step-by-step faculty demonstration flow
