# G2a-IMPLEMENTATION-REPORT

**Gate:** Phase 0C G2a — Minimum Offline Simulation Ledger  
**Authorization:** LIMITED GO (Chief Trading, 2026-11-03)  
**Status:** Delivered for independent review — **acceptance not automatic**  
**G2b / PAPER_ON / broker / live or paper API orders / schedules / paid APIs / new Bots / strategy promotion:** NOT authorized  
**Asia/Shanghai:** 2026-11-03

---

## Scope

Implement a deterministic, replayable, **DEMO/synthetic-only** paper simulation ledger that reuses accepted **G1-R4** schemas, validator, frozen hard limits, and Risk Gate **without weakening** any control. New work lives exclusively under `phase0c/g2a/`.

## Preservation

| Item | Status |
|------|--------|
| `phase0c/g1/` (accepted G1-R4) | **Byte-identical** to pre-G2a baseline (`g2a/out/g1_unchanged.json`) |
| `g1-FAILED-G1` … `g1-FAILED-G1-R3` | Untouched |
| Prior reports / HASHES | Untouched |
| `predictions/PRED-M1-001.md` | sha256 `2317319d9ec2b33d9ccd2b8316c6c39b2f78d2d25e7fa7ad45aeb0e9274f224e` (**unchanged**) |

Production `evaluate()` and `g1/frozen_id_registry.jsonl` were **not** used for simulation (would write into frozen g1). G1’s own suite was re-run from a **temporary lab layout copy** (50/50 OK); evidence in `g2a/out/g1_suite_from_temp_copy.json`.

---

## Design (minimal)

```
PRED+DEC (demo:true)
    → portfolio snapshot from ledger + synthetic marks
    → evaluate_for_tests(..., policy=FIXTURE_EVAL, allow_fixture_eval=True,
         registry=G2a IdRegistry)
    → GATE_RESULT ledger event
    → NO_TRADE → audit event, no fill / no position change
    → ACCEPT trade → deterministic FILL at pre-supplied synthetic price
    → append-only JSONL ledger (hash chain)
    → replay rebuilds identical tip state
```

### Modules

| Path | Role |
|------|------|
| `g2a/ledger.py` | Append-only JSONL; seq + `prev_event_sha256` chain; state: cash, whole-share positions, avg costs, realized/unrealized P&L, equity, peak, drawdown, day-start, stop latches, filled DEC map, outstanding pending |
| `g2a/fill_engine.py` | Builds `fill_v1` with `engineering_fixture: true` + `demo: true` |
| `g2a/prices.py` | Synthetic price book keyed by date/ticker; missing → fail closed |
| `g2a/simulator.py` | Orchestrates gate → fill/ledger; latch-enforced buy block |
| `g2a/replay.py` | Rebuild state from ledger bytes; tamper → `LedgerError` |
| `g2a/artifacts.py` | Demo PRED/DEC builders with content hashes |
| `g2a/schemas/` | `fill_v1`, `ledger_event_v1`, `ledger_state_v1` |
| `g2a/g2a_registry.jsonl` | G2a-owned registry file (sims use per-run paths in tests) |

### Gate reuse choice

G1 production `evaluate()` is `PAPER_OFF` / `READ_ONLY` and returns `LAB_MODE_BLOCKS_TRADE` for any trade, and binds the **fixed** `g1/frozen_id_registry.jsonl`.  

G2a therefore calls **`evaluate_for_tests(..., policy=g1/fixtures/policy_fixture_eval.json, allow_fixture_eval=True, registry=<G2a IdRegistry>)`**, which:

- Still enforces frozen numeric hard limits (20% / 2% / 10% / no short / no leverage / whole shares / all-symbol name cap including pending buys)
- Requires `demo: true` on PRED and DEC
- Does not write into g1’s registry
- Labels accepts as fixture/DEMO (`OK_TRADE_FIXTURE`)

**No g1 source was copied or weakened.** If this offline entry were insufficient, the authorized fallback was a G2a wrapper with equal-or-stronger checks — not needed.

### P&L method

**Average-cost:**

- Buy: `new_avg = (prev_qty×prev_avg + shares×price) / new_qty`; cash decreases by notional
- Sell: `realized = shares × (price − avg_cost)`; avg unchanged on partial sell; position removed at zero
- `unrealized_pnl = Σ qty × (mark − avg_cost)`
- `equity = cash + Σ qty × mark` (must hold at every recorded tip)

Zero-cost fills are allowed only as engineering fixtures; every fill is flagged `engineering_fixture` + `demo` and **must not** be treated as formal performance.

### Stop latch rules

- After MTM/fill, if daily loss ≥ 2% of `day_start_equity` → `daily_loss_stop_latched = True`
- If drawdown ≥ 10% of `peak_equity` → `drawdown_stop_latched = True`
- Risk-increasing `PAPER_BUY` blocked while either latch is set (`DRAWDOWN_STOP_LATCHED` checked first)
- `NEW_DAY` resets **only** the daily latch and sets `day_start_equity = equity`
- Drawdown latch **never auto-clears** in G2a
- `clear_stops` / `attempt_clear_stops` → always `STOP_CLEAR_FORBIDDEN` (no Bot API to clear)

### Idempotency

- If `decision_id` already in `filled_decision_ids` → `OK_IDEMPOTENT_REPLAY`, return existing fill id, **no second fill**
- Gate-level identical PRED+DEC replay still yields `OK_IDEMPOTENT_REPLAY` via G1 registry binding
- Same ID / different content → G1 `ID_HASH_CONFLICT` reject

### DEMO separation

All G2a artifacts are synthetic fixtures. Scenario evidence files carry `demo: true`. Not official forward research.

---

## Tests

- Suite: `phase0c/g2a/tests/test_g2a.py` (portable via `__file__`)
- Command: `cd phase0c/g2a && PYTHONDONTWRITEBYTECODE=1 python3 tests/test_g2a.py` (**ordinary python3, no `-S`**)
- Result: **16 tests, ok=true**

Covered:

1. Valid synthetic buy and sell (realized P&L)
2. NO_TRADE audit, no fill, no position change
3. Insufficient cash
4. Existing other-symbol exposure >20%
5. Pending other-symbol exposure >20%
6. Fractional holding + naked short rejection
7. Daily 2% loss stop (unrealized) + latch blocks buy
8. Peak 10% drawdown stop + NEW_DAY keeps DD latch
9. Unrealized P&L reconciliation
10. Duplicate fill prevention
11. Deterministic replay (rebuild == live; two runs identical ledger bytes)
12. Missing/corrupted/tampered/truncated/nonfinite fail-closed
13. Ledger ↔ Risk Gate portfolio consistency
14. Stop cannot be cleared
15. g1 tree unchanged + PRED hash
16. Two-pending 24% SPY and 19.2%+4.8% combo regressions

Evidence: `g2a/out/test_results.json`, `test_run_console.txt`, `replay_evidence.json` (equal=true), `reconciliation.json` (all_ok=true), `g1_unchanged.json`.

---

## Deliverables

| Artifact | Path |
|----------|------|
| Sources | `phase0c/g2a/` |
| Report | `phase0c/G2a-IMPLEMENTATION-REPORT.md` |
| Hashes | `phase0c/G2a-HASHES.sha256` (**does not list itself**) |
| ZIP | `phase0c/PHASE-0C-G2a-DELIVERABLE.zip` |
| ZIP sha256 | `phase0c/G2a-ZIP.sha256` |

---

## Limitations / open risks

1. Synchronous fill-by-default; outstanding pending is an engineering inject for gate projection tests, not a full live order lifecycle.
2. Synthetic prices only — no market data feed.
3. Average-cost inventory only (no lot-level HIFO/LIFO).
4. Drawdown latch permanent within a G2a ledger instance (by design); no founder unlock path.
5. G2b (broker/paper API, schedules, etc.) **not authorized**.

---

## Statement

Delivered for **independent review**. Acceptance is **not automatic**. **G2b is not authorized.** No broker connectivity, PAPER_ON, real/paper API orders, recurring automation, paid services, new Bots, strategy promotion, or M1 evidence modification was performed.
