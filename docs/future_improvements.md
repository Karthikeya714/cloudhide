# Future Improvements

Optional extensions beyond the current phases, roughly in order of how
directly they build on existing seams in the codebase:

1. **Shamir Secret Sharing for threshold-based recovery.**
   `fragmentation_service.py` was deliberately kept to a narrow interface
   (`fragment_file()` / `reconstruct_file()`) specifically so a k-of-n
   threshold scheme could replace the simple byte-range splitter without
   touching the hide/recovery pipelines that call it.

2. **Machine learning carrier selection.** `carrier_analysis_service.py`'s
   scoring formula (`analyze_carrier()`) is an explicit, documented heuristic
   combining capacity/entropy/edge-density/distortion sub-scores. It could be
   replaced by a learned model (e.g. trained on steganalysis detectability
   labels) behind the same `CarrierMetrics` return type.

3. **Multi-cloud distribution.** The `StorageProvider` interface (Phase 7)
   already abstracts local vs. MinIO; adding an `S3StorageProvider` or a
   provider that shards stego images across multiple backends is a natural
   extension of that same interface.

4. **Advanced frequency-domain steganography** (DCT/DWT-based embedding)
   as an alternative or complement to spatial-domain LSB, offering better
   steganalysis resistance at some capacity cost.

5. **JPEG-robust embedding**, so carriers aren't restricted to PNG.

6. **User authentication and authorization**, scoping transfers to accounts
   and adding access control to the API.

7. **A key management service** (e.g. HashiCorp Vault, AWS KMS) to replace
   the current single-master-key-in-an-env-var model with rotation, audit
   logging, and per-tenant keys.

8. **Digital watermarking** as a complementary technique to steganography —
   for provenance/ownership marking rather than secret hiding.

9. **Steganalysis resistance evaluation** — an automated test harness that
   runs standard steganalysis detectors (chi-square, RS-analysis, or a
   trained CNN detector) against generated stego images and reports
   detection rates, to give the entropy/edge/distortion scoring a real
   ground-truth signal to optimize against.

10. **Automated cloud reliability scoring** for the storage layer — health
    checks and latency/availability metrics per configured `StorageProvider`,
    surfaced in the analytics dashboard alongside the existing pipeline
    timing metrics.
