L0-EVALUATION-SPEC — draft for Founder review

Date: 2026-11-03, Asia/Shanghai. **L0-DESIGN ONLY; nothing is scored here.**
Baseline `main`: `aada128c065854b30f28dbdbe61fd2b0784ff1a0`.
See [protocol](L0-PROTOCOL.md), [roles](L0-ROLE-CONTRACT.md), and
[readiness](L0-READINESS-REPORT.md). All new rules below require adoption before
new samples; they cannot be imposed retrospectively to rewrite historical M1.

## 1. Prediction identity and immutable strategy

For a new forecast use existing `prediction_v1` without changes:

| Existing fields | L0 use |
| --- | --- |
| `schema`, `id`, `content_sha256` | Schema and unique PRED identity bound to canonical JSON body hash; conflicting reuse rejected before replay |
| `strategy_version` | Immutable strategy version; separate strategy record supplies version hash, parent hash and allowed memory snapshot |
| `ticker`, `baseline_price`, `baseline_source_tier` | Canonical instrument and positive finite baseline with provenance; tier is declared, not proof of source verification |
| `band`, `horizon_end` | Band parameter and exact target date; separate prefreeze measurement record defines units, exact bounds, session, timezone, currency, price basis and rounding |
| `probs` | Finite probabilities for exactly UP, FLAT, DOWN, each in [0,1], sum within existing G1 tolerance 1e-9; no silent renormalization |
| `EVENT_EXPOSED` | Chief's known event-exposure flag at freeze, backed by dated event inventory; not an outcome-dependent exclusion |
| `knowledge_cutoff_utc`, `frozen_at_utc` | Actual knowledge limit and freeze instant, UTC-aware and auditable; cutoff ≤ freeze < target observation |
| `demo`, `notes` | Fixture disclosure and limitations; separate evidence class is mandatory and cannot be inferred from demo alone |

G1's schema/validator does not establish source publication truth, band units,
exchange session validity, external timestamp authenticity, or learning quality.
L0 supplies separate checks; no frozen schema extension is proposed.

`decision_v1` is optional for this forecast-only loop. If later authorized for an
explicit audit purpose, it may express `NO_TRADE`, `size_pct: 0`, with its existing
prediction link, rationale, memory references and timestamps. Do not invent a
historical DEC body from an ID in Markdown. No submit/gate/simulator call or order
is needed to freeze or evaluate a forecast, including a NO_TRADE forecast.

## 2. Cutoff, publications and leakage

Every research claim must point to an archived source version: publisher, URL or
file locator, source publication time, first known availability time when
available, revision time, retrieval time, excerpt/field, and raw-byte hash. All
information actually supplied to any prefreeze role, including memory and
candidate strategy inputs, must be available at or before the common cutoff.
Freeze can be later for packaging, but it must introduce no new information.
Keep complete role inputs/outputs and access logs; record unobserved tool access
as a limitation. A source with unknown publication/version history is not
verified merely because it was retrieved or asserted to be old.

Source publication ≤ cutoff is necessary, but not sufficient: the exact version
and its prior availability must be supportable. Prefer contemporaneous stored
snapshots. Later retrieval is admissible as proof of earlier public availability
only with independent immutable as-of evidence; it cannot prove earlier Bot use.
Exclude later revisions, outcome data embedded in headlines, current constituent
lists used as historical lists, retrospective adjustments, and future memory.
A scheduled future event known at cutoff is admissible; its realized value is not.

Before freeze, audit every cited source and the declared input inventory. Before
scoring, compare source times/version hashes, transcript times, strategy and
memory availability, freeze custody, and target times. A detected post-cutoff
input is `INVALID_LEAKAGE`; an unresolved publication/timing gap is
`QUARANTINED_PROVENANCE`. Report both, even when the forecast appears correct.
Model pretraining or hidden external retrieval cannot be disproved by record
hashes. Capture model/version/access settings and disclose residual uncertainty;
no claim of perfectly independent or leakage-free cognition follows from logs.

## 3. Bands and observation contract

For new L0 predictions the proposed explicit convention is `band` in percentage
points: 0.3 means ±0.3%, not a fraction 0.3. This convention is not established by
the existing schema and requires Founder adoption. A prefreeze L0 measurement
record freezes baseline session, unadjusted regular-session official close price
basis, currency, market timezone, target session/date, calendar source/version,
band units, exact lower `L` and upper `U` bounds, decimal tick/rounding rule, and
classification inequalities. Compute new bounds with decimal arithmetic and the
precommitted instrument tick/rounding convention. Persist exact bounds; never
recompute them at scoring using a different convention. Zero band is permitted
only with the equality rule explicitly frozen.

For a verified target close C, classify DOWN if C < L, FLAT if L ≤ C ≤ U, UP if
C > U. No intraday, extended-hours, indicative, synthetic, or adjusted-close
substitution. If corporate actions make the frozen basis unusable, quarantine
under a predeclared corporate-action rule; do not retrofit bands. Horizon date
must be an approved trading session; a closure or missing session has no automatic
next-day fallback. Resolve before freeze or retain an invalid/unresolved sample.

For future pilots, the Founder must approve a primary official-close source and
an independent corroborating source, a price/tick tolerance, official/final status
checks, and revision policy before first freeze. Review verifies the exact
instrument/session, close type, units, publication status and agreement. Retain
both snapshots and any discrepancy. A quote labeled close is not proof of an
exchange official regular-session close. No providers are contacted in this task.

## 4. Freeze receipt and dependent records

A new JSON prediction's content hash follows G1's canonical JSON body convention
(sorted keys, compact separators, UTF-8, finite numbers, excluding its own
`content_sha256`). Exact Markdown/source byte hashes have a different hash kind.
Freeze receipt binds prediction ID/hash kind/hash, strategy version/hash, source
inventory/hash, memory snapshot/hash, final Chief draft/challenge-response hashes,
measurement rules/hash, evaluation version/hash, and freeze time. Chief authorizes;
a separately retained contemporaneous custody receipt anchors existence before
the outcome. A self-written timestamp or Git author date is insufficient proof.
Minimum proposed custody: store exact frozen bytes and hashes in immutable,
versioned storage, with a separately retained, verifiable server-recorded receipt
created before the target observation. A local mtime or Git author timestamp is
not adequate; a later self-asserted receipt cannot establish original timing.
Document authorized writers/readers, archival retention and the exact third-party
receipt service before the first pilot. No service is accessed by this design task.
Founder must approve the custody location and authorized writer/read permissions.

The following are proposed record contracts, not new schema/code files:

| Record | Required contents beyond common envelope and original `prediction_ref` |
| --- | --- |
| `outcome_record` | Target instrument/session, observation UTC time, close type/price/units, provider/version snapshot refs, verification actor/time/status, revision parent, source conflict flags |
| `score_record` | Freeze/evaluation refs, exact probabilities/bounds/outcome refs, one-hot outcome, Brier/Log Loss/directional results or explicit null-with-reason, eligibility, denominator class, scorer version/hash and verification |
| `review_record` | Score/outcome refs, reasoning/data/process findings, challenge dispositions, hindsight warnings, alternative explanations, uncertainty, leakage/exclusion decision and Chief response ref |
| `memory_revision` | Parent memory ref, original prediction refs, review refs, proposed lesson/change, counterevidence, scope/confidence/expiry/falsifier, approved/available/effective timestamps and actor |
| `strategy_version_record` | Parent version/hash, complete immutable rules/prompt bundle, changed components, memory evidence refs and original prediction refs, approval/effective timestamps, comparison-plan ref |
| `comparison_record` | Plan/hash, baseline/candidate versions, every paired original prediction ID/hash, common outcome refs, exclusions/coverage, aggregate metrics/uncertainty and decision status |

Every derived record carries its own hash and parent refs. Identical reprocessing
returns the existing result; same record ID with changed inputs is an integrity
failure. Correction creates a new version/ref, preserving earlier bytes and
reasons. A revised official outcome can yield a revised score but never a revised
forecast. Reports show original versus revised results and the impact on paired
comparisons; no overwrite or favorable revision selection.

## 5. Scores and reporting

For class order (UP, FLAT, DOWN), frozen probabilities p and verified one-hot
outcome y, primary **multiclass Brier Score** is:

`BS = Σ_k (p_k − y_k)^2`, summed over all three classes, range [0,2]; lower is
better. Do not silently divide by three or mix conventions. Report each sample
and the arithmetic mean over eligible samples, together with all counts.

Secondary **Log Loss** is `LL = −ln(p_observed_class)`, natural logarithm. If the
observed class was assigned zero probability, report positive infinity explicitly
(e.g. null numeric field plus `POSITIVE_INFINITY` status for strict JSON). It is
not missing data and remains in the denominator; aggregate LL is infinite if any
eligible sample has infinite LL. Do not clip probabilities after seeing results.

Secondary **directional accuracy** is the fraction whose frozen primary argmax
class matches the realized UP/FLAT/DOWN class. The primary call MUST be computed
from the frozen probability vector, not independently selected or edited by Chief.
For new forecasts preregister tie handling; proposed default is deterministic
priority FLAT, DOWN, UP. Report tie
counts. M1 has a unique DOWN argmax, so this adds no historical rule to M1.
Binary UP/DOWN-only accuracy, if ever shown, is exploratory with an explicit
conditional denominator and is never substituted for the primary metric.

No score is calculated from synthetic fill prices, realized/unrealized P&L,
fill-engine outputs, gate verdicts, rationale persuasiveness, or a remembered
alternative forecast. No trading return, alpha, Sharpe ratio, or financial
performance claim follows from these metrics. Calibration summaries need multiple
samples; one success or failure cannot demonstrate learning improvement.

## 6. Missing data and invalid samples

Maintain an immutable attempt/registration roster with two independent status
axes: lifecycle_status (e.g. AWAIT_OUTCOME or SCORED) and eligibility_status
(e.g. ELIGIBLE, QUARANTINED_PROVENANCE, INVALID_LEAKAGE). An outcome may still
be pending while sample eligibility is quarantined; never merge the two axes.
For every cohort report:
registered, frozen, target-not-due, outcome-pending, disputed, quarantined,
invalid, and eligible/scored counts, with mutually exclusive current statuses
and full transition history. Publish reason codes and per-arm missingness for
paired comparisons. No silent deletion or zero imputation.

Target not yet reached or unverified close → AWAIT_OUTCOME, all scores null with
reason. A bad hash, altered probabilities/bands/times/strategy, duplicate sample,
proven future input, or failed timing proof → invalid/quarantined as appropriate.
Source unavailability and delayed outcomes remain visible until resolved or a
preregistered missing-data deadline closes the cohort. A delayed record may be
resolved using verifiable history, never by inventing an earlier timestamp.
Narrative invalidation, missed regime calls, adverse prices or large losses are
not valid exclusion reasons. Any technical failure can bias selection and must
be reported even when the pair is excluded from the metric calculation.

## 7. Baseline versus candidate on future paired samples

No claim of improved learning is permitted from M1 alone or from retrospective
refitting. The smallest comparison freezes one unchanged baseline strategy and
one candidate, both with full version hashes, before collecting new holdout
outcomes. A candidate may be motivated by past reviews; that development data
cannot also count as its future validation cohort.

Preregister the instrument/session/horizon roster, common cutoff and information
packet, forecast deadline, exact bands/price basis, source policy, eligible memory
snapshot, probability metric convention, exclusions, missing-data deadline,
minimum cohort size, fixed stopping rule, uncertainty method, meaningful effect
threshold, and decision rule. Same research Bots can produce two labeled arms
only under later approval; they remain the same eight Bots. Keep arm contexts
separate so baseline does not inherit candidate memory or outcomes during the
cohort. Both arms face the same targets and as-of information. Freeze both before
the outcome; missing either arm is an unpaired attempt, not an invitation to
recreate the missing forecast later.

For each eligible pair i, `d_i = BS_baseline,i − BS_candidate,i`; positive mean d
favors candidate. Report both arm means, mean paired difference, all paired IDs,
counts, coverage, and uncertainty. Proposal for Founder review: at least 30
non-overlapping outcome blocks, candidate advantage at least 0.02 summed-Brier
units, and a 95% paired block-bootstrap confidence interval for mean d with lower
bound > 0, at a fixed cohort endpoint. Precommit the block definition, 10,000
resamples and fixed seed in the plan; maintain within-pair/within-block dependence
and do not treat overlapping horizons as independent observations. These numbers are PROPOSED / NOT ADOPTED and are not a substitute for the
separately frozen formal trading-strategy advancement thresholds. This sample
minimum is an operational floor, not a power guarantee; revise or reject the plan
before starting if it cannot support the intended inference.

Secondary metrics cannot rescue a failed primary decision. No optional stopping,
choosing the best candidate among undisclosed trials, or tuning on the holdout.
Log every candidate and attempted cohort. An exhausted/inconclusive cohort yields
`NO_IMPROVEMENT_ESTABLISHED`, not automatic continuation until success. New tuning
creates a new version and a new future holdout. Even a favorable comparison is
limited evidence requiring Founder review, not permission to trade or promote.

## 8. Memory revision and prospective use

Review records lessons as hypotheses, with supporting and opposing cases. Memory
proposes a new immutable revision; Chief selects a candidate change; Founder
approves eligibility and later activation. Record creation, approval,
availability, and effective times separately; effective time cannot precede
approval or availability. A forecast can use only approved memory and a strategy
version effective by its knowledge cutoff. Freeze the exact snapshot in its
receipt. Old predictions remain evaluated under their original strategy and
memory, forever. Revoking a lesson appends a new revision; it does not erase its
prior influence. Candidate comparisons receive new evidence-class labels and
must not be presented as verified learning improvement before their endpoint.

## 9. M1 read-only worked mapping — NO SCORE

Authoritative source: `predictions/PRED-M1-001.md`, exact-byte SHA-256
`2317319d9ec2b33d9ccd2b8316c6c39b2f78d2d25e7fa7ad45aeb0e9274f224e`.
This table is a **non-authoritative derivative reading**, not a new freeze,
replacement prediction, or schema-valid `prediction_v1` artifact.

| Frozen item | Authoritative value / treatment |
| --- | --- |
| Prediction / decision IDs | PRED-M1-001 / DEC-M1-001; DEC body is not present |
| Strategy | strat-m1-v0.1; executable rules/prompt/version hash not present |
| Freeze | 2026-11-03T03:25:50Z; external custody receipt not present in repository |
| Instrument / baseline | SPY; 752.10 USD; baseline session 2026-11-02 |
| Baseline source as recorded | Yahoo Finance, with helper cross-checks FT/Google/StockAnalysis; frozen statement, not newly verified data |
| Band | ±0.3%; exact frozen inclusive FLAT interval [749.84, 754.36] |
| Probabilities | UP 0.28, FLAT 0.32, DOWN 0.40; primary DOWN |
| Target | Official SPY regular-session close, 2026-11-10, America/New_York |
| Original outcome rule | UP >754.36; DOWN <749.84; otherwise FLAT, including both boundaries |
| Cutoff | Exact `knowledge_cutoff_utc` absent; do not substitute freeze time or a fixture default |
| Event flag / source tier | No explicit schema `EVENT_EXPOSED` boolean or baseline_source_tier; event narrative exists but is not a replacement field |
| Original artifact hash kind | Raw Markdown bytes; do not label this as a JSON canonical content hash |
| Current status in this design | AWAIT_OUTCOME; provenance gaps recorded; no score, outcome label or learning claim |

The explicit frozen bounds control; do not replace them with newly calculated
unrounded ±0.3% bounds. Respect the original invalidation condition: a verified
close ≥749.84 makes the primary DOWN call wrong. Narrative regime change does
not change its price-based outcome rule.

**Do not score M1 before the official November 10, 2026 regular-session close is
available and verified.** In Asia/Shanghai this will be on the following calendar
day under the expected New York session schedule; confirm the exchange calendar
and actual final publication rather than scheduling by this note. No close has
been requested or verified in this task; no actual or hypothetical M1 scores are
computed. Later scoring also requires separate pilot authorization and evidence
resolution; passage of the date alone is insufficient.

Referenced research files and original challenge responses are missing here.
A later authorized descriptive score could be labeled provenance-limited if the
Founder approves that reporting scope, but unresolved evidence cannot be waived
into an eligible clean paired-learning sample. M1 cannot be retrofitted with a
candidate frozen before its historical cutoff. Do not create a schema-valid
structured M1 object by inventing missing fields; any later derivative must
retain original ID/hash refs, a distinct derivative identity, mapping caveats and
its own hash without rebinding PRED-M1-001 to different content.