# LAB-STATE — AI Autonomous Trading Learning Lab (authoritative handoff)

**Updated:** 2026-11-03 (UTC+8), Founder-authorized PR merges and status reconciliation
**Rule:** If chat history conflicts with this file, THIS FILE wins. Update it at every gate change.

## Current gate
- **G1-R4: ACCEPTED** (independent offline engineering acceptance, 2026-11-03). Frozen — do not modify `phase0c/g1/`.
- **G2a (original): FAILED** (independent audit, 2026-11-03). Three independently reproduced defects: altered-content ID replay bypass, NEW_DAY clearing a latched daily halt, and non-atomic registry/fill/ledger persistence. This historical verdict is not rewritten by the R1 merge.
- **G2a-R1: FOUNDER ACCEPTED WITH INDEPENDENT QA WAIVED / MERGED** (2026-11-03). The Founder explicitly accepted developer-reported 28/28 G2a tests, the historical G1 49/50 import result, disclosed residual risks, and waived additional independent QA. This is a Founder acceptance, **not** independent QA PASS. Correction merged in PR #2; no broker/API activation implied.
- **Migration PR #1: MERGED** (2026-11-03). Founder explicitly accepted omitted historical failed-build archives; archive-presence regression remains a recorded failure.
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
| G2a | FAIL; R1 CORRECTION AUTHORIZED 2026-11-03 |
| G2a-R1 | 2026-11-03 Founder acceptance with independent QA WAIVED; PR #2 merged; developer-reported 28/28, not independently rerun |

## Immutable evidence (never modify)
- `predictions/PRED-M1-001.md` sha256 `2317319d9ec2b33d9ccd2b8316c6c39b2f78d2d25e7fa7ad45aeb0e9274f224e`
- Historical copy `phase0c/audit-evidence/PRED-M1-001.md` was not imported; canonical evidence above is present.
- Historical failed builds `phase0c/g1-FAILED-G1`, `-G1-R1`, `-G1-R2`, `-G1-R3` were not imported. The archive-presence test therefore fails; do not manufacture replacement evidence.
- All prior reports / HASHES files under `phase0c/`

## Live code
- `phase0c/g1/` — risk_gate.py, submit_validator.py, frozen_limits.py, tickers.py, json_strict.py, id_registry.py, finite_numbers.py, tests/test_g1.py
- Run tests: `cd phase0c/g1 && python3 tests/test_g1.py` (ordinary python3, no -S)
- Production registry fixed: `phase0c/g1/frozen_id_registry.jsonl`

## Hard limits (frozen)
20% per name (every symbol, holdings + ACCEPT/PENDING buys), 2% daily loss, 10% peak drawdown; no short, no leverage, whole shares; pending sells never credited as filled.

## Historical G1 deliverables (ZIPs were not imported)
- Report: `phase0c/G1-R4-IMPLEMENTATION-REPORT.md`
- Full ZIP: `phase0c/PHASE-0C-G1-R4-DELIVERABLE.zip` (sha in `G1-R4-ZIP.sha256`)
- Core ZIP: `phase0c/PHASE-0C-G1-R4-CORE.zip` (also at Mac `~/PHASE-0C-G1-R4-CORE.zip`)

## Working conventions
- Preserve previous correction builds. This G2a-R1 correction was developed on a separate Git branch; the original import commit remains intact in Git history. Never archive by modifying accepted G1-R4.
- Manifests never include their own hash.
- Deliver files to user's Mac home dir (chat attachments fail to save on their Mac).

## G2a scope (authorized)
Append-only ledger (cash, whole-share positions, synthetic fills, realized/unrealized P&L, equity, peak/drawdown, daily-loss stop state); deterministic fill engine on pre-supplied synthetic prices; Risk Gate approval before every risk-increasing action; NO_TRADE = audit record only; distinct PRED/DEC/GATE/FILL IDs + hashes; idempotent replay (no duplicate fills); equity = cash + marked value; replay reconstructs identical state; stops cannot be cleared by any Bot; DEMO separate from forward research. Zero-cost fills = engineering fixtures only, never performance.
Forbidden: Alpaca/broker API, real or paper API orders, live execution, schedules, paid services, new Bots, strategy promotion, M1 evidence changes.

## PR merge and Founder decision record (2026-11-03, UTC+8)
- Founder explicitly authorized sequential merges of PR #1 and PR #2 to `main`, acknowledged the missing historical archives, waived independent QA and accepted disclosed residual risks.
- PR #1 import head: `042bee94dfd34e765b38bf17720024df7e427a1f`; **MERGED** as `b518f5f898731d3f3dc15305ade64a9d1a4bb3f6`.
- PR #2 correction head: `5d5c218ede04a469e55ecb8659c70ac2578e4d06`; retargeted to `main`, marked ready, **MERGED** as `1880790b574f52d4fa48913ad61da50b858c596f`.
- G2a-R1 developer tests: 28/28 reported PASS. G1 import tests: 49/50 reported PASS, with `test_failed_archives_present` failing because historical failed-build archives were omitted. Neither result is claimed as freshly executed independent QA.
- Original import Manifest and R1 Manifest remain untouched. The R1 Manifest identifies the pinned R1 commit; later `LAB-STATE.md` status updates and the integrity helper are deliberately versioned as post-merge commits. `verify_integrity.py` verifies frozen R1 bytes at pinned R1 SHA and checks preserved working files separately.
- Residual limitations accepted for this offline gate: POSIX local filesystem assumption; whole-file atomic replacement O(ledger size); power-loss/controller failure not simulated; legacy ledger/registry incompatibility fails closed; no pending execution API or halt recovery workflow; checksum chains are not signatures; heuristic credential scan only.
- No G2b authorization, no PAPER_ON, no broker/Alpaca connections, real or paper orders, paid APIs, schedules or additional Bots. No real funds.

## Next step
PR #1 and #2 are merged. Verify `main` contents, frozen evidence and PR status; then submit a **separate Founder decision** for any next offline research/learning gate. Do not start G2b or connect brokers without a separate explicit approval.

## G2a deliverables
- Report: `phase0c/G2a-IMPLEMENTATION-REPORT.md`
- Hashes: `phase0c/G2a-HASHES.sha256`
- ZIP: `phase0c/PHASE-0C-G2a-DELIVERABLE.zip` (sha in `G2a-ZIP.sha256`)
- Gate path: G1 `evaluate_for_tests` + FIXTURE_EVAL policy + G2a-owned registry `g2a/g2a_registry.jsonl`

## Engineering handoff (2026-11-03)
- Codex owns Python engineering, debugging, testing, quality, and Pull Requests.
- Grok Chief Trading and existing specialist Bots retain research, prediction, trading decisions, reflection, and learning responsibility.
- Source imported in PR #1 from `import/g1r4-g2a`, commit `042bee94dfd34e765b38bf17720024df7e427a1f`.
- R1 branch: `fix/g2a-r1`; report: `phase0c/G2a-R1-REVIEW.md`.
- Import manifest remains immutable historical evidence. Use `G2a-R1-HASHES.sha256` for the correction; never rewrite historical manifests to hide changes.
- Frozen G1-R4 remains ACCEPTED and byte-identical; 20% per name, 2% daily loss, 10% peak drawdown, no short/leverage, whole shares, no pending-sell credit.
- All activity remains offline, DEMO/synthetic. No real trades, broker Paper API orders, PAPER_ON, Alpaca, recurring automation, paid APIs, or additional Bots.
