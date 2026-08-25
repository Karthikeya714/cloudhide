# Limitations

Documented honestly, per the project brief.

1. **Basic LSB steganography is not resistant to all steganalysis
   techniques.** CloudHide's `steganography_service.py` uses straightforward
   1-bit-per-channel LSB embedding. Statistical steganalysis methods (e.g.
   chi-square attacks, RS-analysis) can detect the *presence* of hidden data
   in an image, especially as payload size approaches a carrier's capacity,
   even though they cannot recover the *content* without the AES key. See
   [`threat_model.md`](threat_model.md).

2. **PNG is required because LSB embedding does not survive lossy
   compression.** JPEG (or any lossy re-encoding) would destroy the least
   significant bits the payload is hidden in. `load_png_image()` explicitly
   rejects any non-PNG format for this reason.

3. **Large secret files require large carrier capacity.** A carrier's usable
   capacity is roughly `width × height × 3 bits ÷ 8`, minus a 45-byte header.
   Hiding a large file either requires large/many carrier images or a higher
   fragment count; `select_carriers_for_fragments()` returns a clear
   `PipelineError` when available carriers can't cover the fragments, rather
   than silently truncating data.

4. **The prototype's storage providers do not guarantee availability.** The
   local filesystem provider has no redundancy, and the MinIO provider
   (Phase 7) assumes a single reachable MinIO instance with no replication
   configured. Production use would need a managed object store with its own
   durability guarantees.

5. **Encryption protects the hidden payload's confidentiality, not its
   detectability.** Even if an attacker successfully extracts the encrypted
   bytes from a stego image, AES-256-GCM makes recovering the plaintext
   infeasible without the key — but that same attacker can still statistically
   detect that *something* is hidden in the image, since the encrypted bytes
   still occupy LSB slots in a pattern distinguishable from an unmodified
   image at high payload ratios.

6. **Advanced threshold secret sharing (Shamir) is not implemented.**
   Fragmentation (Phase 2) is deliberately simple contiguous byte-range
   splitting — *all* fragments are required to reconstruct the file, there is
   no k-of-n threshold recovery. The fragmentation service was kept modular
   specifically so this could be added later (see
   [`future_improvements.md`](future_improvements.md)) without changing its
   callers.

7. **No authentication or authorization.** Every API endpoint is open to
   anyone who can reach the server; there is no concept of a user or an
   owner of a transfer. This was out of scope for the assigned phases.

8. **No automated steganalysis-resistance evaluation.** CloudHide computes
   PSNR/SSIM as *visual* quality metrics (Phase 8), which is not the same as
   measuring resistance to a steganalysis classifier. No such evaluation is
   implemented.

9. **Single-node, single-process assumptions.** The `@lru_cache`-based
   storage provider and settings singletons assume one running backend
   process; there's no distributed-lock handling for concurrent writers to
   the same carrier or transfer.
