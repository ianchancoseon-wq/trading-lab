# LAB-STATE — AI Autonomous Trading Learning Lab (authoritative handoff)

**Updated:** 2026-11-04 (UTC+8), Founder-approved L0 Core R2 PR #4 merge and gate reconciliation
**Rule:** If chat history conflicts with this file, THIS FILE wins. Update it at every gate change.

## Current gate
- **G1-R4: ACCEPTED** (independent offline engineering acceptance, 2026-11-03). Frozen — do not modify `phase0c/g1/`.
- **G2a (original): FAILED** (independent audit, 2026-11-03). Three independently reproduced defects: altered-content ID replay bypass, NEW_DAY clearing a latched daily halt, and non-atomic registry/fill/ledger persistence. This historical verdict is not rewritten by the R1 merge.
- **G2a-R1: FOUNDER ACCEPTED WITH INDEPENDENT QA WAIVED / MERGED** (2026-11-03). The Founder explicitly accepted developer-reported 28/28 G2a tests, the historical G1 49/50 import result, disclosed residual risks, and waived additional independent QA. This is a Founder acceptance, **not** independent QA PASS. Correction merged in PR #2; no broker/API activation implied.
- **Migration PR #1: MERGED** (2026-11-03). Founder explicitly accepted omitted historical failed-build archives; archive-presence regression remains a recorded failure.
- **L0 Protocol v1.0: FOUNDER ADOPTED / MERGED** (2026-11-03). PR #3's four Markdown design documents were approved and merged to `main`; this was design adoption only at that historical gate.
- **L0 Core R2: FOUNDER ACCEPTED / MERGED** (2026-11-04). Founder explicitly authorized merge of PR #4 after reported independent offline QA 46/46 PASS (34 bundled tests plus 12 independently authored adversarial checks). Reviewed head `628542e2154e8189b57990d38e1c38173a6ede44`, merged to `main` as `634fa1dd9ec3bf8e1787421724f029a5f9953b44`. This is **offline engineering acceptance only**: no Forward Pilot, M1 scoring, external custody verification, outcome collection, Bot activation, broker/market/model API, trading orders or G2b authorization.
- **G2b: NOT AUTHORIZED.** Also not authorized: PAPER_ON, broker connections, real/paper/synthetic simulation orders, recurring automation/schedules, paid APIs, new Bots.

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
| L0-DESIGN | 2026-11-03 Founder adopted Protocol v1.0; PR #3 merged; implementation and pilot were not authorized at that gate |
| L0-IMPLEMENTATION R2 | 2026-11-04 independent offline QA reported 46/46 PASS; Founder explicitly authorized PR #4 merge; L0 Core merged, Pilot not authorized |

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

## L0 design adoption record (2026-11-03, UTC+8)
- Founder explicitly approved L0 Protocol v1.0 design, authorized PR #3 to be marked Ready and merged to `main`.
- PR #3 design head: `d4c7eaac2a40ea58c83397e0aaa4081accb092a4`; **MERGED** as `6e6b67393f8d215af4a0b9923316342576684438`.
- Adopted documentation files only: `l0/L0-PROTOCOL.md`, `l0/L0-ROLE-CONTRACT.md`, `l0/L0-EVALUATION-SPEC.md`, `l0/L0-READINESS-REPORT.md`.
- Design conventions: separate lifecycle/eligibility statuses; derived argmax primary call; immutable hash-referenced prediction and freeze custody evidence; original M1 remains frozen and unscored.
- Comparative thresholds of 30 blocks, 0.02 summed-Brier improvement and 95% paired CI are **PROPOSED / NOT ADOPTED**; they neither activate a cohort nor replace previously frozen formal strategy advancement requirements.
- At the 2026-11-03 design-only gate, L0 implementation and later execution were **NOT AUTHORIZED**. A separate Founder decision subsequently authorized bounded offline L0 Core implementation, and PR #4 was merged on 2026-11-04. Forward Pilot, M1 scoring, Bot runtime/identity activation, automated outcome collection, paid services, market/broker APIs, any orders, G2b and strategy activation remain **NOT AUTHORIZED**.

## L0 Core implementation and QA acceptance record (2026-11-04, UTC+8)
- Founder-authorized bounded offline L0 core implementation was developed on `feat/l0-core` and delivered in PR #4.
- R2 fixes specifically address quarantine rollback and stale Score/Review/Memory binding after outcome revisions.
- Final reviewed head: `628542e2154e8189b57990d38e1c38173a6ede44`; PR #4 was marked Ready and **MERGED** using a merge commit: `634fa1dd9ec3bf8e1787421724f029a5f9953b44`.
- Independent offline QA evidence supplied in conversation: 34/34 bundled tests, 12/12 additional adversarial tests; total **46/46 PASS**. SHA-256 integrity and frozen baseline preservation checked. QA files are conversation-delivered evidence, not falsely asserted to be incorporated into the repository.
- Accepted scope is local offline Prediction Registry, deterministic Outcome/Scorer core, append-only Review/Memory records and bounded synthetic engineering tests. No claim of model learning effect or verified genuine-forward evidence.
- Local role/identity labels are not authenticated identities; external custody, trusted market outcome provenance, cohort promotion and live integrations remain future gates.

## Next step
Preserve this merged offline L0 Core baseline. Any Forward Pilot, M1 outcome scoring, external data/model/broker integration, automated scheduling, order execution, G2b, or memory/strategy activation requires a **separate explicit Founder authorization**. No automatic experiment start or paid API activation.

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
