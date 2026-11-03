# trading-lab

AI Autonomous Trading Learning Lab — offline research code. DEMO / synthetic only. No broker, no orders.

Baseline imported 2026-11-03 from Chief Trading's lab copy, byte-for-byte. G2a-R1 changes are described in `phase0c/G2a-R1-REVIEW.md`:
- `phase0c/g1/` — G1-R4 Risk Gate + submit validator (ACCEPTED, FROZEN — never modify).
- `phase0c/g2a/` — G2a offline simulation ledger (FAIL / R1 CORRECTION AUTHORIZED; correction pending review).
- `predictions/PRED-M1-001.md` — frozen M1 evidence (sha256 2317319d…f224e), read-only, needed by tests.
- `phase0c/LAB-STATE.md` — authoritative lab state.
- `IMPORT-MANIFEST.sha256` — sha256 of every imported file.

Gate status: G2b, PAPER_ON, broker, orders, schedules, paid APIs NOT AUTHORIZED.

Run tests: `cd phase0c/g1 && python3 -m unittest discover -s tests` (49/50: `test_failed_archives_present` fails by design because failed archives `g1-FAILED-*` are intentionally not in this repo); `cd phase0c/g2a && python3 -m unittest discover -s tests` (28/28 including correction regressions).
