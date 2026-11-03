L0-READINESS-REPORT — draft for Founder review

Date: 2026-11-03, Asia/Shanghai. Authorized gate: **L0-DESIGN ONLY**.
Design recommendation: **L0-DESIGN READY** for Founder review; pilot execution,
implementation, version activation and evidence collection are not authorized.

## Baseline and work performed

Read the latest fetched `main`, commit
`aada128c065854b30f28dbdbe61fd2b0784ff1a0`, through an isolated archive at
`/workspace/l0-design-2026-11-03/baseline-main`. Drafts are outside the checkout in
`/workspace/l0-design-2026-11-03/drafts`. The existing branch/worktree was not
switched, edited, committed, pushed, or merged. No PR or environment configuration
change was made in this task.

Inspected required baseline files: `phase0c/LAB-STATE.md`, both G1 prediction and
decision schemas, G1 validation/hash utilities, G2a source and schemas/reports,
`phase0c/G2a-R1-REVIEW.md`, and `predictions/PRED-M1-001.md`. Inspected available
record inventory for research, strategy, outcome and memory evidence. The Founder
confirmed Macro, News, Company, Market, Skeptic, Chief, Review and Memory as the
eight existing roles during this task. No Bots were started or added.

Read-only verification compared all **117 snapshot files** to their fetched-main
Git blobs. **77 frozen G1/M1 files** matched hashes in the original import
manifest. M1 exact-byte SHA-256 remains
`2317319d9ec2b33d9ccd2b8316c6c39b2f78d2d25e7fa7ad45aeb0e9274f224e`.
No historical file or manifest was rewritten. These are integrity checks, not
functional tests or new independent QA. No repository Python modules, simulator,
trading test fixtures, score runner, APIs, or orders were executed.

## Already implemented versus proposed

| Capability | Observed baseline / usable principle | L0 boundary |
| --- | --- | --- |
| Prediction and decision contracts | `prediction_v1` and `decision_v1`; separate PRED/DEC identities, hashes, explicit times, probability/band fields | Reuse field meanings and validation principles; no schema mutation. Additional metadata goes in separate referenced records |
| Strict validation/hash utilities | Finite-number handling, strict JSON, probability sums, timestamp ordering, canonical-body hashes, ID binding | Candidate implementation dependencies after permission. They do not verify external publication truth or custody |
| G1 risk controls | G1-R4 ACCEPTED, frozen; 20% per name, 2% daily loss, 10% peak drawdown, no short/leverage, whole shares, pending sells not treated as filled | Preserve completely. Forecast scoring does not invoke an execution/risk-gate path or change these limits |
| G2a-R1 durability | Accepted source contains transaction staging, atomic replacement, fsync, writer serialization, ID recovery and replay checks | Reuse durability/idempotency lessons in a future separate research record store. Existing trade ledger is not an outcome or learning store; no simulator use needed |
| Synthetic fills and price fixtures | DEMO/engineering artifacts; deterministic simulator and P&L reconciliation | Remain synthetic research/engineering evidence only; no forward-market outcome or performance inference |
| M1 frozen evidence | Immutable Markdown with IDs, strategy label, freeze time, probabilities, bounds, horizon and evidence pointers | Read-only worked mapping only. No replacement JSON prediction or score now |
| Learning loop | No implemented outcome verification, scoring/review/memory protocol or future paired comparison found | All four L0 documents propose these; none is deployed or running |

The authoritative LAB-STATE records PR #1/#2 merged and **G2a-R1 FOUNDER ACCEPTED
WITH INDEPENDENT QA WAIVED**. Historical R1 review/README wording still describes
the earlier pending-review stage; do not reinterpret it as current gate status
or edit historical evidence in this task. Existing reports contain developer
28/28 G2a results and G1 49/50 with the missing-archives failure. Those results
were read as historical evidence, not rerun or relabeled independent QA PASS.
The only G2a-tree difference between the R1 head and fetched main is the
post-merge integrity helper; simulator/ledger/scoring absence conclusions derive
from current-main source inspection, not the stale local correction branch.

## Four proposed documents

- [L0-PROTOCOL.md](L0-PROTOCOL.md): complete transition chain, record lineage,
  evidence classes, failure states and Founder boundaries.
- [L0-ROLE-CONTRACT.md](L0-ROLE-CONTRACT.md): exact role-level inputs/outputs for
  eight confirmed Grok roles and Codex, Chief-only forecast authority, minimum
  three substantive Skeptic challenges, immutable Review/Memory boundaries.
- [L0-EVALUATION-SPEC.md](L0-EVALUATION-SPEC.md): existing-field mapping, cutoff
  and provenance checks, fixed outcomes, freeze receipts, Brier primary metric,
  secondary scores, invalid/missing rules, M1 no-score mapping, prospective
  memory/versioning and registered future paired comparison.
- This report: implementation/evidence distinction, gaps, risks and approvals.

These are documentation drafts. Proposed role envelopes, research records,
score calculations, memory rules, sample-size/effect thresholds, custody and
comparison procedures are not existing working features.

## Evidence available and known gaps

| Evidence already available | What remains missing or unverified |
| --- | --- |
| Frozen M1 Markdown and matching raw-byte hash | Referenced REQ research files, Chief baseline, full challenge/response packet, contemporaneous source snapshots and externally anchored freeze custody |
| M1 forecast and explicit interval [749.84,754.36], probabilities DOWN .40 / FLAT .32 / UP .28 | Exact original knowledge cutoff, source-tier field, explicit event boolean, structured DEC body, full strategy rules/prompt hash; do not infer or backfill these |
| Original source names and baseline session/price as recorded | Independent verification of original baseline source/version and helper checks; no new market-data verification performed |
| Future target specified: November 10, 2026 official SPY regular-session close | Verified future close is unavailable in this task; M1 remains AWAIT_OUTCOME and unscored |
| Founder-confirmed eight-role roster | Deployed identity bindings, prompt/model versions, input/tool access logs, access restrictions and review independence evidence |
| Current schemas, accepted code and historical engineering reports | Adopted L0 band units, source/final-close verification policy, calendar/corporate-action handling, custody plan and retention/access permissions |
| Proposed metrics and paired design | Active strategy/memory registry, complete baseline strategy snapshot, authorized candidate, registered future cohort, adequate power/dependence plan and holdout evidence |

A single historical prediction cannot establish improvement. Missing historical
proof cannot be repaired by assigning plausible values now. A future descriptive
M1 score with unresolved provenance must remain explicitly limited and cannot
become a clean paired prospective comparison by waiver.

## Smallest eventual implementation — not authorized now

After a separate implementation approval, use one offline, manually invoked
research-record writer/validator and a deterministic scoring/report function on
manually supplied verified records. Store content-addressed research/freeze,
outcome, score, review, memory and strategy records with append-only lineage and
one immutable sample roster. No database service, trading engine, new Bot,
recurring job, API integration or simulator dependency is required.

The implementation should reject ID/hash conflicts before replay, enforce legal
transitions and time guards, atomically persist dependent records, and recover
without duplicate sample/score inclusion. Import historical M1 only as a labeled
non-authoritative mapping with its original raw-byte reference; missing fields
remain missing. Numeric scoring must be blocked unless an authorized eligible
outcome is verified. Verification can use abstract arithmetic examples and
record-only fault cases after approval; no trading fixtures are needed.

Review/Memory outputs can initially be manually assembled under these contracts.
Codex verifies links and arithmetic rather than becoming a market researcher or
approving lessons. Chief owns proposed research changes; Founder owns eligibility
and activation. Do not build an architecture beyond this bounded record workflow.

## Risks and acceptance criteria

| Risk | Required acceptance evidence before relevant pilot stage |
| --- | --- |
| Hindsight leakage or evolving web sources | Archived source versions/publication times, cutoff inventory, complete role input records and explicit unknowns; contaminated samples excluded with reasons |
| Mutable freezes / altered IDs / missing custody | Reproducible hashes, unique IDs, external contemporaneous receipt, immutable copies, revision-only corrections; hashes alone are not signatures |
| Conflicting or adjusted close data / wrong session | Approved official-close and corroboration policy, calendar/session checks, frozen price basis and tolerance, documented resolution of discrepancies |
| Hindsight narrative changing a target | Exact frozen bounds/probabilities/strategy/times; immutable original outcome definition; no outcome-dependent exclusions |
| Correlated samples, small N, selective reporting | Complete registered attempt roster, fixed endpoint, paired arm coverage, dependence-aware uncertainty, all candidates/trials disclosed; no single-sample learning claim |
| Shared Bot/model beliefs and weak review independence | Identity/prompt logs and declared shared inputs; Founder acceptance of the independence limitation or approved human verification |
| Overfitted memory or candidate | Lesson counterevidence/falsifier, versioned prospective effect, unchanged baseline, common future packets and independent holdout; new tuning requires a new cohort |
| Persistence failures / platform assumptions | Separately reviewed record-write/recovery checks on the intended storage; known POSIX/power-loss limits disclosed; no alteration of accepted G2a |
| Scope creep into trading or infrastructure | No order path, simulator invocation, broker/API setup, deployment or recurring automation in the implementation/pilot permission; explicit stop condition |

Design review acceptance requires internally consistent transitions, role
contracts and metric definitions; an honest inventory of existing versus missing
evidence; preserved frozen artifacts; and no execution implied by a READY label.
These drafts meet that documentation scope subject to Founder review and the
four explicit amendments: separate lifecycle/eligibility state; deterministic
argmax primary call; prospective comparison thresholds remain PROPOSED /
NOT ADOPTED; and a minimum immutable freeze/custody receipt process. Pilot acceptance additionally
requires all applicable evidence guards and approvals below; it is **not ready
to execute** under current authorization.

## Specific Founder approvals needed

1. Adopt a versioned L0 protocol and role contracts, including the confirmed role
   roster's deployed identity/prompt bindings, Chief authority and Skeptic quota.
2. Separately authorize the bounded offline record/scorer implementation and its
   record-only validation scope. No accepted G1/G2a changes are included.
3. Approve custody/storage and source access/verification: manual free source
   snapshots, actual source identities, official-close status, corroboration,
   tolerances, calendar/corporate-action/revision handling, retention and access.
   Approval of L0 does not authorize market-data API connections or paid services.
4. Approve an explicitly manual, forecast-only pilot: instruments, target
   sessions/horizons, cutoff/deadlines, participant identity bindings, evidence
   classes, stopping conditions and an initial strategy/memory snapshot. No
   schedules or orders of any type are included.
5. Decide M1's eventual evaluation scope after November 10 official close is
   available and verified: resolve historical evidence gaps or permit a separately
   labeled provenance-limited descriptive report. Never waive gaps into valid
   forward-learning comparison evidence; never rewrite the freeze.
6. Before candidate validation, approve candidate/parent hashes and exact change,
   future paired roster, sample/dependence/power plan, primary effect threshold,
   fixed stopping rule and complete reporting. The proposed 30 blocks / 0.02
   Brier / 95% interval rule is a reviewable proposal, not an adopted standard.
7. After registered forward evidence is reviewed, make a separate activation,
   rejection or inconclusive decision. Eligibility or apparent improvement is
   not strategy activation or trading permission.

No further action is taken in this design task. No G2b, Alpaca/broker/market-data
API connection, paid service, real/paper/synthetic simulation order, simulator or
trading-fixture run, recurring research/trading automation, new Bot, risk-limit
change, historical edit, deployment, push, merge or PR creation occurred.
M1 was not scored. Stop here and await further Founder authorization.

**Recommendation: L0-DESIGN READY.** This is design readiness only, not authority
to implement, run a pilot, collect outcomes, activate a strategy or trade.