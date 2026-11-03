# G1-R4-IMPLEMENTATION-REPORT

**Prior:** G1-R3 FAIL (independent audit — other-symbol name-cap bypass)  
**This build:** G1-R4 Focused Correction (all-symbol 20% hard cap)  
**Status:** Delivered for independent re-audit — **acceptance not automatic**  
**G2 / PAPER_ON / broker / schedules / paid APIs / new Bots:** NOT authorized  
**Asia/Shanghai:** 2026-11-03

---

## Preservation

| Item | Path |
|------|------|
| Failed G1 | `phase0c/g1-FAILED-G1/` |
| Failed G1-R1 | `phase0c/g1-FAILED-G1-R1/` |
| Failed G1-R2 | `phase0c/g1-FAILED-G1-R2/` |
| Failed G1-R3 | `phase0c/g1-FAILED-G1-R3/` |
| Prior reports/hashes | G1 through G1-R3 retained under `phase0c/` |
| PRED-M1-001 audit copy | `phase0c/audit-evidence/PRED-M1-001.md` |
| PRED sha256 | `2317319d9ec2b33d9ccd2b8316c6c39b2f78d2d25e7fa7ad45aeb0e9274f224e` (**unchanged**) |

---

## Defect

Risk Gate enforced `MAX_SIZE_PCT_PER_NAME` (20%) only for the **decision ticker**. Existing or pending exposures above 20% in **other** symbols incorrectly yielded ACCEPT for a new risk-increasing PAPER_BUY.

Reproduced (all must REJECT after R4):

1. Existing SPY 30% + proposed QQQ 10%
2. Pending SPY 30% + proposed QQQ 10%
3. Two pending SPY buys totaling 24% + proposed QQQ 10%
4. Existing SPY 19.2% + pending SPY 4.8% + proposed QQQ 10%

---

## Correction (minimal)

In `_evaluate_core` (`risk_gate.py`):

1. Build complete projected portfolio = holdings + outstanding ACCEPT/PENDING PAPER_BUY adds only (**unfilled pending sells still not credited** — R3 preserved).
2. Compute per-symbol projected name % for **every** ticker; if any `> 20%` and intent is `PAPER_BUY`, REJECT with `NAME_EXPOSURE_CAP:<TICKER>`.
3. After applying the proposed trade, check post-trade name % for **every** symbol; REJECT with `POST_TRADE_NAME_EXPOSURE_CAP:<TICKER>` (legacy unscoped `POST_TRADE_NAME_EXPOSURE_CAP` retained for decision ticker diagnostics).
4. No architecture redesign. R3 fixes preserved (finite_numbers rename, alias rejection, 1e999, fixed registry, pending consistency, F4/F6, etc.).

### New / reinforced reason codes

- `NAME_EXPOSURE_CAP:<SYM>` — pre-trade projected portfolio already over per-name hard cap (blocks risk-increasing PAPER_BUY)
- `POST_TRADE_NAME_EXPOSURE_CAP:<SYM>` — post-trade any symbol over 20%

---

## Tests

- Suite: `phase0c/g1/tests/test_g1.py` (portable via `__file__`)
- Command: `cd phase0c/g1 && python3 tests/test_g1.py` (**ordinary python3, no `-S`**)
- Log: `phase0c/g1/out/test_run_console.txt`, `out/test_results.json`
- Result: **50 tests, ok=true** (46 prior + 4 new all-symbol name-cap regressions)
- Archives assertion now includes `g1-FAILED-G1-R3`

---

## Deliverables

| Artifact | Path |
|----------|------|
| Sources | `phase0c/g1/` |
| Report | `phase0c/G1-R4-IMPLEMENTATION-REPORT.md` |
| Hashes | `phase0c/G1-R4-HASHES.sha256` (does **not** list itself) |
| ZIP | `phase0c/PHASE-0C-G1-R4-DELIVERABLE.zip` |
| ZIP sha256 | `phase0c/G1-R4-ZIP.sha256` (sibling only; not inside HASHES) |

---

## Limitations

1. Append-only lab-wide MANIFEST service still deferred.
2. EVENT calendar join still field-level.
3. No G2 ledger / broker / schedules.
4. DEMO fixtures excluded from formal forward scores.
5. No predictive-improvement claims.
6. PAPER_SELL of an over-cap name that reduces that name to ≤20% with no other violator remains allowed from the name-cap path; other over-cap symbols still fail closed via post-trade per-symbol checks.

---

## Request

Independent G1-R4 re-audit against the four reproduced cases and the full suite. **G1-R4 completion does not imply automatic acceptance. G2 remains NOT AUTHORIZED.**

---

## Integrity (computed at package time)

| Item | sha256 |
|------|--------|
| `g1/risk_gate.py` | `b5f86e381021da20673e309282371a63d0c7b52f1ffce6b6e2fb75c3a58585f6` |
| `PHASE-0C-G1-R4-DELIVERABLE.zip` | see sibling `G1-R4-ZIP.sha256` (not embedded in HASHES) |

Per-file source + report hashes: `G1-R4-HASHES.sha256` (does **not** include its own hash).
