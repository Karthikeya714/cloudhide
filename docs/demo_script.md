# Faculty Demonstration Script

Assumes the backend (`http://localhost:8000`) and frontend
(`http://localhost:5173`) are both running — see the root
[`README.md`](../README.md) for startup commands, or run
[`scripts/verify.py`](../scripts/verify.py) first to confirm both are healthy
and the full pipeline works before presenting.

Sample carrier images are provided in [`samples/`](../samples/) if you don't
want to source your own PNGs.

## Flow

1. Open the CloudHide dashboard at `http://localhost:5173/`. It shows Files
   Hidden, Successful Recoveries, Recovery Rate, Average PSNR, Average
   Processing Time, and Recent Transfers — all real numbers from the
   database (zero/empty on a fresh install).
2. Click **Hide File** in the nav bar.
3. Drag a secret file (any type — a text file works well for a legible demo)
   onto the "Secret File" dropzone.
4. Drag all three sample PNGs from `samples/` onto the "Carrier Images"
   dropzone. Point out each carrier's suitability score appearing as it
   finishes uploading and being analyzed.
5. Point out the **Recommended carriers** panel — it explains *why* each
   image was ranked where it was (capacity, entropy, edge density,
   distortion risk).
6. Set the **Number of fragments** field (3 is a good demo size — it matches
   the three sample carriers).
7. Click **Hide File**. Note the progress bar during upload, then the
   "Transfer Complete" card: status, fragment count, processing time, and a
   transfer ID link.
8. Click the transfer ID link to open **Transfer Details**. Show the
   pipeline timing breakdown (encryption/fragmentation/embedding times) and
   the per-fragment stego image table (which carrier, PSNR, SSIM, capacity
   used).
9. Click **Recover** on that same page. Point out the button becomes
   "Recover Again" and a **Download Recovered File** button appears.
10. Click **Download Recovered File** and open it — show it's byte-identical
    to the original secret file.
11. Navigate to **Recover File**. Show the transfer picker (a chip per
    recent transfer) as an alternative to typing a transfer ID.
12. Pick the transfer from the chip list and click **Recover** — point out
    "Integrity verified: Yes — SHA-256 hash matches original".
13. Navigate to **Analytics**. Walk through:
    - Summary cards (Files Hidden, Successful Recoveries, Recovery Rate,
      Average Processing Time).
    - The **Processing Time Breakdown** bar chart (encryption / fragmentation
      / embedding / extraction / recovery).
    - The **Security & Quality Metrics** cards: Average PSNR, Average SSIM,
      Carrier Capacity Utilization, Failed Operations.
    - The **Recent Transfers** table.
14. Back on the **Dashboard**, show the same summary now populated,
    confirming every page reads from the same live backend state.

## Optional: demonstrate failure handling

- Try **Hide File** with no carriers uploaded yet (fresh session) → clear
  "no suitable carriers" error, not a crash.
- On a completed transfer, manually delete or corrupt one of its stego PNGs
  in `storage/stego/` on disk, then click **Recover** → the UI surfaces the
  backend's clear tampering/missing-fragment error message instead of
  silently returning wrong data.

## Talking points for the security story

- Point to `docs/security.md`: every file is encrypted (AES-256-GCM) *before*
  fragmentation and hiding — the stego images never contain plaintext.
- Point to the SHA-256 checks at every stage (visible indirectly via the
  "Integrity verified" field and the tamper-detection demo above).
- Be upfront about limitations (`docs/limitations.md`): LSB steganography
  hides *content*, not the *fact* that something is hidden, and is not
  claimed to be steganalysis-proof.
