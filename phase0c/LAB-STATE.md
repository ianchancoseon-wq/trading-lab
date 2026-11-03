# LAB-STATE — AI Autonomous Trading Learning Lab (authoritative handoff)

**Updated:** 2026-11-03 15:35 (Asia/Shanghai)
**Rule:** If chat history conflicts with this file, THIS FILE wins. Update it at every gate change.

## Current gate
- **G1-R4: ACCEPTED** (independent offline engineering acceptance, 2026-11-03). Frozen — do not modify `phase0c/g1/`.
- **G2a: LIMITED GO** (2026-11-03) — minimum offline simulation ledger in `phase0c/g2a/`, synthetic fixtures only. **Delivered 2026-11-03, awaiting independent review** (16/16 tests, replay equal, g1 unchanged).
- **G2b: NOT AUTHORIZED.** Also not authorized: PAPER_ON, broker connections, real/paper orders, recurring automation/schedules, paid APIs, new Bots.

## Gate history
| Gate | Result |
|------|--------|
| M1 SPY PRED freeze | frozen |
| M1.1 / M2 / M2.1 | done; M2.1 conditionally accepted -> Phase 0C design |
| G0 | conditional -> v1.1 five fixes |
| G1 | LIMITED GO -> FAIL |
| G1-R1 | FAIL (pending hide, aliases, frozen identity) |
| G1-R2 | FAIL (-S only, qqq/QQQ, 1e999, registry path, manifest self-hash) |
| G1-R3 | FAIL (20% cap only checked on decision ticker) |
| G1-R4 | ACCEPTED 2026-11-03 (50/50 tests) |
| G2a | delivered 2026-11-03 (16/16), pending independent review |

## Immutable evidence (never modify)
- `predictions/PRED-M1-001.md` sha256 `2317319d9ec2b33d9ccd2b8316c6c39b2f78d2d25e7fa7ad45aeb0e9274f224e`
- Copy: `phase0c/audit-evidence/PRED-M1-001.md`
- Failed builds kept: `phase0c/g1-FAILED-G1`, `-G1-R1`, `-G1-R2`, `-G1-R3`
- All prior reports / HASHES files under `phase0c/`

## Live code
- `phase0c/g1/` — risk_gate.py, submit_validator.py, frozen_limits.py, tickers.py, json_strict.py, id_registry.py, finite_numbers.py, tests/test_g1.py
- Run tests: `cd phase0c/g1 && python3 tests/test_g1.py` (ordinary python3, no -S)
- Production registry fixed: `phase0c/g1/frozen_id_registry.jsonl`

## Hard limits (frozen)
20% per name (every symbol, holdings + ACCEPT/PENDING buys), 2% daily loss, 10% peak drawdown; no short, no leverage, whole shares; pending sells never credited as filled.

## Latest deliverables
- Report: `phase0c/G1-R4-IMPLEMENTATION-REPORT.md`
- Full ZIP: `phase0c/PHASE-0C-G1-R4-DELIVERABLE.zip` (sha in `G1-R4-ZIP.sha256`)
- Core ZIP: `phase0c/PHASE-0C-G1-R4-CORE.zip` (also at Mac `~/PHASE-0C-G1-R4-CORE.zip`)

## Working conventions
- Each correction cycle: archive previous build as g1-FAILED-<gate> first, then patch.
- Manifests never include their own hash.
- Deliver files to user's Mac home dir (chat attachments fail to save on their Mac).

## G2a scope (authorized)
Append-only ledger (cash, whole-share positions, synthetic fills, realized/unrealized P&L, equity, peak/drawdown, daily-loss stop state); deterministic fill engine on pre-supplied synthetic prices; Risk Gate approval before every risk-increasing action; NO_TRADE = audit record only; distinct PRED/DEC/GATE/FILL IDs + hashes; idempotent replay (no duplicate fills); equity = cash + marked value; replay reconstructs identical state; stops cannot be cleared by any Bot; DEMO separate from forward research. Zero-cost fills = engineering fixtures only, never performance.
Forbidden: Alpaca/broker API, real or paper API orders, live execution, schedules, paid services, new Bots, strategy promotion, M1 evidence changes.

## Next step
G2a submitted. STOP. Wait for independent G2a verdict. Do not start G2b.

## G2a deliverables
- Report: `phase0c/G2a-IMPLEMENTATION-REPORT.md`
- Hashes: `phase0c/G2a-HASHES.sha256`
- ZIP: `phase0c/PHASE-0C-G2a-DELIVERABLE.zip` (sha in `G2a-ZIP.sha256`)
- Gate path: G1 `evaluate_for_tests` + FIXTURE_EVAL policy + G2a-owned registry `g2a/g2a_registry.jsonl`

## Infrastructure (2026-11-03 15:46 UTC+8)
- GitHub connected as `ianchancoseon-wq`. Private repo `ianchancoseon-wq/trading-lab` verified (visibility=private, push/admin access). Repo currently empty-ish (size 0).
- NO lab code pushed yet. Initial import requires explicit user authorization. Engineering split (Codex/Cursor cloud agent for Python, Grok for decisions/learning) proposed, not yet adopted.
