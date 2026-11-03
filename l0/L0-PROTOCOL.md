# L0-PROTOCOL — draft for Founder review

Date: 2026-11-03, Asia/Shanghai. Gate: **L0-DESIGN ONLY**.
Baseline: `main` at `aada128c065854b30f28dbdbe61fd2b0784ff1a0`.
This document proposes a protocol; no workflow described here is implemented or
executed by this task. Companion drafts: [roles](L0-ROLE-CONTRACT.md),
[evaluation](L0-EVALUATION-SPEC.md), [readiness](L0-READINESS-REPORT.md).

## Purpose and authority

Measure whether documented changes to research improve future probabilistic
forecasts. The loop is Grok Research → Chief frozen prediction → verified future
outcome → scoring → review → proposed memory → new strategy version → forward
validation. It requires no orders, simulation, execution ledger, broker, or new
Bot. Forecast quality and synthetic fill P&L are separate subjects.

Chief alone chooses the research forecast. Skeptic challenges it; Review assesses
it; Memory proposes lessons; Codex checks engineering integrity and arithmetic.
None of these roles can grant a gate, waive evidence, or authorize execution.
Founder controls pilot authorization, protocol changes, and strategy activation.
G1-R4 stays frozen. G2a-R1 remains Founder accepted with independent QA waived;
its acceptance is not independent QA PASS or learning evidence.

## Proposed minimum record convention

Use existing `prediction_v1` fields, unchanged. L0 metadata belongs in separate
records because that schema forbids additional fields. One manually assembled
freeze bundle and append-only records are sufficient; no service is proposed.

Each record has `record_type`, `record_id`, `record_version`, `created_at_utc`,
`actor_role`, `actor_identity`, `protocol_version`, `evidence_class`,
`content_sha256`, and ordered parent record ID/hash references. All outcome,
score, review, memory, and strategy-change evidence records MUST also carry
`prediction_ref = {id, hash_kind, sha256}` for every original prediction used.
Cross-prediction memory lists all such refs; a path or summary alone is inadequate.

Before freeze, research records reference a request ID and an immutable draft
revision ID/hash. Freeze binds those exact research/challenge records to the
original prediction ID/hash. IDs are unique across classes. The same ID with a
different hash is rejected before any replay shortcut; identical records replay
without creating a second sample. JSON content hashes follow the existing G1
canonical-body convention; Markdown and source snapshots use SHA-256 of exact
bytes. Hash kind is explicit, never inferred or interchanged. A record's hash
excludes only its own hash field. No historical manifest is regenerated.

The evidence classes are:

| Label | Meaning and permitted use |
| --- | --- |
| `SYNTHETIC_ENGINEERING_FIXTURE` | Fabricated data or demo artifacts; engineering checks only |
| `GENUINE_FORWARD_PREDICTION` | Prospectively frozen forecast with verifiable timing and provenance |
| `VERIFIED_FUTURE_MARKET_OUTCOME` | Verified observation for the exact future target/session; never a research input before it exists |
| `EXPERIMENTAL_STRATEGY_COMPARISON` | Registered future paired comparison; references its underlying forecasts and outcomes |

Classes do not convert automatically. `demo: false` alone does not establish
forward validity. M1 is historical frozen forward evidence with unresolved
provenance gaps; it is not a synthetic example or a completed valid sample.

## Allowed state transitions

For clarity, L0 records two **independent status axes**:

- `lifecycle_status`: RESEARCH, CHALLENGED, CHIEF_FINAL, FROZEN,
  AWAIT_OUTCOME, SCORED, REVIEWED, MEMORY_PROPOSED, NEXT_VERSION_ELIGIBLE,
  or an explicit pre-freeze abort/block state.
- `eligibility_status`: UNASSESSED, ELIGIBLE, QUARANTINED_PROVENANCE,
  INVALID_INTEGRITY, INVALID_LEAKAGE, INVALID_SAMPLE, or a specifically
  documented exclusion/appeal status.

An artifact can simultaneously be `AWAIT_OUTCOME` and
`QUARANTINED_PROVENANCE`. Never collapse lifecycle timing into sample eligibility;
all status changes are append-only and reason-coded.

Only the following forward lifecycle transitions are allowed. Each requires an
appended transition record containing prior-state record/hash, inputs, checks,
owner, UTC timestamp, and any applicable Founder authorization reference.

| Transition | Owner | Required evidence and conditions |
| --- | --- | --- |
| Start → RESEARCH | Chief, after pilot approval | Registered question, instrument, horizon/session, cutoff, source policy, strategy version/hash, active-memory snapshot, evidence class; bounded research request to existing specialists |
| RESEARCH → CHALLENGED | Skeptic | At least **three substantive distinct challenges** to the exact draft revision; each has claim, cited evidence/uncertainty, alternative explanation and possible forecast impact |
| CHALLENGED → CHIEF_FINAL | Chief | Response to every challenge, with accepted/rejected/deferred disposition and rationale; final probabilities, exact bands, sources, assumptions and known limitations |
| CHIEF_FINAL → FROZEN | Chief authorizes; Codex verifies only | Valid complete prediction, final challenge/response bundle, immutable strategy and source inventory, cutoff checks, exact thresholds/outcome rule, deterministic primary call from probability argmax, freeze receipt/hash with contemporaneous custody evidence, no critical unresolved integrity issue |
| FROZEN → AWAIT_OUTCOME | Chief records custody handoff | Verified freeze receipt before target; original prediction locked. No new research may modify it |
| AWAIT_OUTCOME → SCORED | Codex arithmetic, Review verification | Target close has occurred and verified outcome is available; original ID/hash match; source/session/price validation; deterministic scores under the precommitted evaluation version |
| SCORED → REVIEWED | Review | Independent explanation of forecast versus outcome, source quality/leakage checks, numerical versus narrative findings, sample eligibility, and uncertainty; Chief response attached without rewriting Review |
| REVIEWED → MEMORY_PROPOSED | Memory | Atomic proposed lesson with supporting/counterevidence refs, scope, confidence, falsification condition, prospective change, and proposed expiry; no automatic active-memory write |
| MEMORY_PROPOSED → NEXT_VERSION_ELIGIBLE | Chief proposes; Founder authorizes eligibility | Accepted/rejected memory disposition, immutable parent/candidate strategy diff and hash, no backdating, registered future paired evaluation plan and explicit scope approval |

`NEXT_VERSION_ELIGIBLE` means eligible for a separately authorized forward
validation cohort, not improved, promoted, or live. The next forecast starts a
new RESEARCH record with a new prediction ID. Candidate and unchanged baseline
are frozen before each common target. Completion of an evaluation cohort produces
a comparison report and another Founder decision, not automatic promotion.

Before FROZEN, a material Chief revision returns to RESEARCH with a new draft
revision; Skeptic challenges the new revision again. Preserve superseded drafts
and all responses. No backward transitions after freeze. Parallel post-freeze
annotations cannot change the frozen artifact or research view.

## Failure, delay, and correction handling

| Condition | Required treatment |
| --- | --- |
| Missing third substantive challenge or Chief response | `BLOCKED_PRE_FREEZE`; no freeze |
| Missing source publication/version evidence or unknown cutoff | `QUARANTINED_PROVENANCE`; preserve artifact, exclude from primary eligible cohort until independently resolved |
| Future information, altered ID content, broken hash/custody, unauthorized state transition | `INVALID_INTEGRITY` or `INVALID_LEAKAGE`; halt that sample's progression, retain full reason and report to Founder |
| Target not closed, provisional/missing/conflicting data | Stay AWAIT_OUTCOME with `OUTCOME_PENDING`/`OUTCOME_DISPUTED`; no estimated score or replacement session |
| Forecast exists but protocol/evidence defect prevents valid scoring | `INVALID_SAMPLE`; denominator and exclusion reason remain visible |
| Chief abandons an unfinished forecast | `ABORTED_PRE_FREEZE`; retain attempt and reason, never erase selection history |
| Market restates an observed close | New outcome and score revision, linked to original and prior revision; preserve both, show impact; never revise prediction |
| Memory lacks evidence or conflicts with established limitations | Record `MEMORY_REJECTED` or `MEMORY_DEFERRED`; no candidate activation |

A late-arriving source can document an earlier publication only if independent
version evidence establishes exactly what was available then. It cannot establish
that the Bot actually used it at the time without contemporaneous input records.
Narrative regret, a regime change, or an adverse outcome is not an exclusion.
Human review cannot turn contaminated evidence into valid prospective evidence.

## Freeze custody (minimum proposal, not activated)

Before any future pilot, Founder must adopt custody location/access policy.
The minimum is the immutable original bytes and explicit hash-kind digest,
an append-only freeze register, and a separately retained, verifiable
server-recorded receipt proving the bundle existed before its target outcome.
A local file mtime, self-asserted UTC timestamp or Git author date alone cannot
independently prove pre-outcome custody. No storage or external timestamp service
is used by this documentation task.

## Human boundaries and stopping rule

Current authorization ends at delivering these four drafts in a GitHub **Draft
PR** for review, not merging or implementing them. Separate explicit Founder
approvals are needed for protocol adoption, implementation, existing Bot
identity bindings, custody/data procedures, pilot scope and start, and any
candidate forward-validation cohort. Strategy activation requires a further
Founder decision based on the registered evidence. Comparison thresholds such
as 30 blocks / 0.02 Brier improvement / 95% CI are PROPOSED / NOT ADOPTED;
they do not supersede the project's formal trading-strategy gates.

No approval here grants G2b, PAPER_ON, orders of any kind, API connections,
recurring automation, paid services, new Bots, or changes to frozen risk limits.

Stop at the first failed evidence guard for that sample. Other already-authorized
independent documentation may continue; no Bot may waive a guard. After this
L0-DESIGN delivery, await Founder instructions.
