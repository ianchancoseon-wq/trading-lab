G2a accepted altered PRED/DEC content under filled IDs, cleared daily-loss halts
on NEW_DAY, and persisted registry bindings separately from fills. This correction
validates replay bundles before shortcuts, preserves both halt latches, and
commits bindings, gates and ledger effects atomically with recoverable retries.
Recovery verifies snapshots and derives IDs from committed events.

Stacked on `import/g1r4-g2a` (PR #1), which remains unmerged. Draft for independent
review only; neither PR may merge without explicit Founder approval. LAB-STATE
records G2a FAIL / R1 CORRECTION AUTHORIZED. G1-R4 remains ACCEPTED and frozen.

Validation: 28/28 G2a tests, including real process-death boundaries, concurrent
retries, failed writes, changed-content rejection, halt persistence and
byte-identical restart replay. Frozen G1 tests in a temporary copy: 49/50 passed;
the documented missing-historical-archives test fails. Original defects reproduced
against the imported commit. No frozen G1 or M1 bytes changed.

Integrity/review evidence: `phase0c/G2a-R1-REVIEW.md`,
`phase0c/G2a-R1-HASHES.sha256`, `phase0c/g2a/r1_evidence/`.
Run `python3 phase0c/g2a/verify_integrity.py` to verify import/frozen/R1 hashes.

Limitations: POSIX local filesystem and full-ledger rewrite per commit; old
accepted ledgers lacking durable bindings fail closed for review; physical power
loss not tested; pending acceptance has no later execution API. Offline synthetic
fixtures only. No broker connections, API orders, PAPER_ON, automation or G2b.
