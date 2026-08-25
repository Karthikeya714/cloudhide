#!/usr/bin/env python
"""Final verification for CloudHide (Phase 10).

Starts the backend, waits for it to become healthy, runs the pytest suite,
then drives one real hide -> recover -> download cycle against the running
server and checks the recovered bytes match the original exactly.

Run with the backend's virtualenv interpreter, e.g. from the repo root:

    backend/venv/Scripts/python.exe scripts/verify.py      # Windows
    backend/venv/bin/python scripts/verify.py               # macOS/Linux

Exits 0 if every step passes, non-zero otherwise.
"""
import subprocess
import sys
import time
from pathlib import Path
from typing import IO

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
SAMPLES_DIR = REPO_ROOT / "samples"

HEALTH_URL = "http://127.0.0.1:8000/health"
BASE_URL = "http://127.0.0.1:8000"
STARTUP_TIMEOUT_S = 30
LOG_PATH = REPO_ROOT / "scripts" / "verify_backend.log"


def step(title: str) -> None:
    print(f"\n=== {title} ===")


def start_backend() -> tuple[subprocess.Popen, IO[str]]:
    step("Starting backend")
    # Redirect to a file rather than PIPE: an unread PIPE fills its OS buffer
    # after a few log lines and blocks the child process's writes, which
    # freezes uvicorn's event loop entirely (a classic subprocess deadlock).
    log_file = open(LOG_PATH, "w")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"],
        cwd=BACKEND_DIR,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    return process, log_file


def wait_for_health() -> bool:
    import httpx

    deadline = time.time() + STARTUP_TIMEOUT_S
    while time.time() < deadline:
        try:
            response = httpx.get(HEALTH_URL, timeout=2)
            if response.status_code == 200:
                print(f"Backend healthy: {response.json()}")
                return True
        except httpx.HTTPError:
            pass
        time.sleep(1)
    return False


def run_tests() -> bool:
    step("Running backend test suite")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=BACKEND_DIR,
    )
    return result.returncode == 0


def verify_full_pipeline() -> bool:
    step("Verifying complete hide -> recover -> download workflow")
    import httpx

    # Keep-alive connection reuse has proven flaky against uvicorn's default
    # event loop on Windows during this kind of rapid-fire scripted sequence;
    # disable pooling so every request opens a fresh connection.
    limits = httpx.Limits(max_keepalive_connections=0)
    with httpx.Client(base_url=BASE_URL, timeout=30, limits=limits) as client:
        carrier_files = sorted(SAMPLES_DIR.glob("sample_*.png"))[:2]
        if len(carrier_files) < 2:
            print(f"FAIL: expected sample carrier images in {SAMPLES_DIR}")
            return False

        for carrier_path in carrier_files:
            with open(carrier_path, "rb") as f:
                response = client.post(
                    "/api/carriers/upload",
                    files={"file": (carrier_path.name, f, "image/png")},
                )
            if response.status_code != 201:
                print(f"FAIL: carrier upload returned {response.status_code}: {response.text}")
                return False
        print(f"Uploaded {len(carrier_files)} carrier images.")

        secret_bytes = b"CloudHide final verification payload - " * 5
        response = client.post(
            "/api/transfers/hide",
            files={"file": ("verify_secret.bin", secret_bytes, "application/octet-stream")},
            data={"fragment_count": "2"},
        )
        if response.status_code != 201:
            print(f"FAIL: hide returned {response.status_code}: {response.text}")
            return False
        hide_body = response.json()
        transfer_id = hide_body["transfer_id"]
        print(f"Hide succeeded: transfer_id={transfer_id}, status={hide_body['status']}")

        response = client.post(f"/api/transfers/{transfer_id}/recover")
        if response.status_code != 200:
            print(f"FAIL: recover returned {response.status_code}: {response.text}")
            return False
        recover_body = response.json()
        if not recover_body["integrity_verified"]:
            print("FAIL: recovery reported integrity_verified=False")
            return False
        print(f"Recover succeeded: {recover_body}")

        response = client.get(f"/api/transfers/{transfer_id}/download")
        if response.status_code != 200:
            print(f"FAIL: download returned {response.status_code}: {response.text}")
            return False
        if response.content != secret_bytes:
            print("FAIL: downloaded bytes do not match the original secret")
            return False
        print("Downloaded file matches the original byte-for-byte.")

    return True


def main() -> int:
    process, log_file = start_backend()
    ok = False
    try:
        if not wait_for_health():
            print(f"FAIL: backend did not become healthy in time (see {LOG_PATH})")
            return 1

        if not run_tests():
            print("\nFAIL: test suite did not pass")
            return 1
        print("\nAll backend tests passed.")

        if not verify_full_pipeline():
            print(f"\nFAIL: end-to-end pipeline verification failed (see {LOG_PATH})")
            return 1

        print("\n=== CloudHide verification PASSED ===")
        ok = True
        return 0
    finally:
        step("Stopping backend")
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        log_file.close()
        if ok:
            # Best-effort cleanup; Windows can briefly hold the file handle
            # even after the child process exits, so a failure here is fine.
            try:
                LOG_PATH.unlink(missing_ok=True)
            except OSError:
                pass


if __name__ == "__main__":
    sys.exit(main())
