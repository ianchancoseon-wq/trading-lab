# L0 implementation report

Status: L0-IMPLEMENTATION — R2 CORRECTIONS SUBMITTED FOR INDEPENDENT QA / NOT ACCEPTED. This is an offline
engineering core, not an authorized Forward Pilot.

Base commit: `70aa77b1deee94b34f482e987ce7f98a0013539c` (fetched main).
Branch: `feat/l0-core`. The final delivery SHA is recorded in the accompanying
submission receipt and PR body. A commit cannot embed its own hash in its own
tracked report; resolve this report's delivery commit with `git rev-parse HEAD`.
The explicit 2026-11-03 Founder implementation contract supersedes main's older
implementation-not-authorized status. LAB-STATE and adopted documents are preserved.

## R2 minimal correction — 2026-11-04 (Asia/Shanghai)

R2 base: `fb1d408538daa35b9c3db3bcdb972e2b9ccf8d82`.
Branch/PR: existing `feat/l0-core`, Draft PR #4. Final pushed SHA is supplied in
the submission response; this report does not claim Founder acceptance or an
independent QA PASS. R1 sections below describe the prior correction history.

### QA-1: quarantine latch

Any explicit status write attempting QUARANTINED_PROVENANCE → UNASSESSED now
fails with QUARANTINE_LATCHED, including at SCORED, REVIEWED and MEMORY_PROPOSED.
Invalid status remains latched; no automatic clearance/authorization path is
introduced. Effect/state writes remain a single SQLite transaction.

### QA-2: latest-outcome score/review/memory binding

A new Review must have exactly one direct Score parent: the current score for
the latest Outcome. Missing current score or an old/mixed score parent is rejected.
A new Memory must use exactly the latest Review; that Review must itself bind
to the current score. A newly appended Outcome immediately makes an older
score/review insufficient for new records, even before its revised score exists.

Review and Memory revisions require `payload.supersedes` to reference the exact
latest predecessor and include it among ordered parents. The predecessor retains
its historical ancestry and counterevidence; it is not treated as the current
score/review input. All operative record references include exact ID/hash kind/
hash. Optional payload `score_ref` / `review_ref`, when supplied, must match the
operative parent. Supported record/protocol versions must match across the
Score→Review→Memory chain; R1 identity/version/hash checks remain enforced.

Revised scores are permitted from AWAIT_OUTCOME, SCORED, REVIEWED and
MEMORY_PROPOSED; revised reviews are permitted from SCORED, REVIEWED and
MEMORY_PROPOSED. Automatic status writes keep the greater of current and target
lifecycle stages, so a correction never demotes a sample from MEMORY_PROPOSED
to SCORED/REVIEWED or from REVIEWED to SCORED. Lifecycle is progress history,
not an assertion that the latest revision has finished downstream review.
Use current_score and explicit record lineage to determine revision readiness.

Identical retries of old immutable records remain idempotent historical retrieval;
they do not create a new review/memory or make stale evidence current. There is
no retroactive overwrite, new activation, eligibility promotion or trading path.

### Actual R2 evidence

Command: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s l0/tests -v`.
Final result: **34 tests run, 34 passed**, zero failures/errors/skips. The original
26 tests are unchanged and pass; eight new adversarial R2 tests are in
`l0/tests/test_r2.py`. Log: `l0/evidence/unit-tests.txt`.

Before the fix, these eight R2 tests produced 3 failures and 4 errors (one pass),
including missing quarantine rejection and unsupported late-stage score revisions.
Original reproduction output is retained in `l0/evidence/r2-before-tests.txt`.

R2 checks quarantine rollback at all three requested stages; INVALID retention;
unscored latest outcome blocking Review/Memory; stale-score and stale-review
rejection; full revised Score/Review/Memory chain with immutable predecessors;
non-regressing lifecycle at REVIEWED/MEMORY_PROPOSED; protocol/record version,
explicit reference and predecessor mismatch rejection; exact restart reconstruction
and idempotent retries. A bad Review rolls back its preceding Score in the same
batch. Injected status-write failure rolls back the revised Score. The existing
subprocess crash, concurrent registration, storage corruption and ID/hash conflict
tests remain included and passed. These are developer tests, not independent QA.

### Integrity and scope

`r2-integrity.json` records unchanged hashes for every original main-baseline
file and every pre-R2 file outside the four authorized modified paths. The
original main baseline has 121 files, including frozen G1/G2a, M1, historical
manifests and all four adopted L0 documents; every byte is preserved. Prior R1
integrity evidence and all 26 prior tests are unchanged. The active L0 changed-file
manifest is regenerated as requested; historical G1/G2a/import manifests are not.

R2 modifies only `l0/core/registry.py`, this implementation report,
`l0/evidence/unit-tests.txt`, and the active `l0/evidence/changed-files.sha256`.
It adds `l0/tests/test_r2.py`, `l0/evidence/r2-before-tests.txt` and
`l0/evidence/r2-integrity.json`.

No known remaining QA-1/QA-2 failure was observed in the full offline suite.
Independent QA is still pending. Existing limitations remain: local identity
binding is not authentication, custody remains PENDING/UNVERIFIED, performance
eligibility stays false, cross-prediction memory is unsupported, and privileged
coherent database rewriting cannot be disproved without an external anchor.
No G1 risk-gate execution, G2a simulator, M1 scoring, real outcome collection,
API trading, orders, paid service, Pilot, deployment or G2b occurred. Proposed
30-block / 0.02 / 95% thresholds remain unadopted. Keep PR #4 Draft and unmerged.

## Implementation

- `l0/core/records.py`: strict envelopes, original prediction references, G1
  prediction validation adapter and compatible canonical hashing, decimal-string
  boundaries, timestamps, measurement contract and FLAT/DOWN/UP tie priority.
- `l0/core/storage.py`: one local SQLite authority; serialized transactions,
  synchronous FULL, immutable rows, complete parent-link checks, ordered hash
  chain, read/restart reconstruction and corruption detection.
- `l0/core/registry.py`: immutable prediction registration, attempt roster,
  lifecycle/eligibility axes, guarded actor/state transitions, freeze receipts,
  atomic receipt/effect plus lifecycle writes, outcome/score revisions, and
  current-score selection against the latest outcome. Failed batches roll back;
  rejection reasons are then appended separately. Identity checks precede replay.
- `l0/core/scoring.py`: pure classification using exact decimal bounds, summed
  multiclass Brier, natural-log loss with explicit JSON-safe infinity, and
  derived directional accuracy. Requires a frozen measurement, matching target,
  verification flags and source references. No fetching, fill or P&L inputs.
- `l0/core/review_memory.py`: review findings/counterevidence, immutable memory
  proposals with scope/confidence/falsifier/review trigger, and strategy proposal
  records. Rejected/deferred/superseded records remain auditable. No activation.
- `l0/tests/fixtures.py`: invented IDs, dates, prices, source assertions and
  probabilities; SYNTHETIC_ENGINEERING_FIXTURE only. Uses an existing schema
  ticker for compatibility, not an actual market observation or broker ID.
- `l0/tests/test_core.py`: isolated standard-library tests, including subprocess
  interruption and independent concurrent SQLite connections.
- `l0/evidence/`: actual test log, baseline preservation evidence and changed-file
  hashes. These are engineering evidence, never learning/performance statistics.

All implementation changes are confined to L0 source, tests and engineering evidence. R1 modifies the prior L0 implementation; all 121 original main-baseline files, including the adopted documents, remain byte-identical.
The changed-file manifest lists each added source, test and report path. The
manifest excludes its own digest, which is reported in the submission receipt.


## R1 response to Founder review 6607510100

R1 base/head-before-correction: `0b9d4e5bd3db7247d8b26c97c8abe2bfd34a6064`.
Exact final R1 SHA is supplied in the submission receipt/response, avoiding a
self-referential commit hash in this tracked report.

### R1-1: adopted envelope mapping and strict identity/version binding

The stored field mapping is deterministic and explicit:

| Adopted contract | Stored field / encoding |
| --- | --- |
| record_id | id |
| record_type | kind; review_record → review, memory_revision → memory, strategy_version_record → strategy; other existing kinds retain their documented names |
| actor_role | actor |
| record_version | record_version, exactly the supported string `1.0` |
| protocol_version | protocol_version, exactly `L0-v1.0` |
| actor_identity | actor_identity, nonempty trimmed string matching the database's pinned role binding |
| created_at_utc, evidence_class, content_sha256, prediction_ref | same names and meanings |
| ordered parent ID/hash refs | parents, ordered array; ordering participates in canonical hashing |

All derived records, including automatically generated registration and lifecycle
records, carry these fields. Unsupported/missing/malformed versions and identities
fail closed before replay. All fields participate in the unchanged canonical-body
hash algorithm. Changing a version or actor under a reused ID is rejected either
by version/identity validation or immutable ID conflict; no caller can rehash a
change into an accepted retry. G1 prediction schema/hash behavior is untouched.

`Registry(path, actor_bindings=...)` accepts an explicit complete role/identity
mapping. It is pinned atomically as a hash-bound internal configuration record;
reopening with a changed mapping fails closed. Default identities are explicitly
`fixture:<role>`, not claimed deployed Grok/Founder identities. Automatic status
records inherit the validated actor identity; initial registration uses the pinned
Chief identity. These are attribution bindings, not cryptographic authentication.

Two internal schema exceptions are explicit: `l0_actor_bindings_v1` (id, kind,
schema, bindings, content_sha256) and `l0_attempt_v1` (id, kind, schema,
attempted_id, at, reason, content_sha256). Invalid attempted timestamps may remain
in attempt evidence exactly as supplied; they are not accepted lifecycle times.
Internal schemas cannot substitute for a derived research envelope. Both write
and restart/read verification enforce derived envelopes and pinned identities.

Pre-R1 prototype SQLite databases with incomplete envelopes are rejected; no
silent migration, guessed identity/version, or rewritten historical hashes are
performed. Fresh isolated databases are used by the tests. Frozen G1/M1 files
are neither migrated nor extended.

### R1-2: recursive single-prediction lineage

Review, Memory and Strategy require every parent and recursive ancestor to bind
to their exact original prediction ID, hash kind and SHA-256. Raw prediction
parents are checked against their own original reference. Every traversed parent
must exist with the exact referenced hash. Validation runs on append and replay,
so a same-prediction evidence wrapper cannot launder a foreign ancestor.
Cross-prediction memory is **not supported** in R1. No declaration field or
annotation bypass is provided; it requires separate authorization and a complete
provenance contract in a future change. Valid same-prediction predecessors,
contrary evidence and rejected/superseded revisions remain immutable and usable.

### R1-3: actual tests, preservation and scope

Full command: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s l0/tests -v`.
Actual result: **26 tests passed**, zero failures/errors/skips. Nine new tests
cover missing/forged envelope fields, stale and recomputed identity/version hashes,
idempotent replay, database identity mismatch on reopen, custom role identity,
foreign Review→Memory, foreign Memory/strategy predecessors, indirect foreign
evidence, altered/missing parents, and low-level storage envelope bypass rejection.
Original 17 tests remain included: process death before/after commit,
freeze/status atomicity, rollback, concurrent retries, restart reconstruction,
corruption, scoring boundaries/revisions, custody and cutoff restrictions.

These are developer tests, **not independent QA PASS**. Synthetic arithmetic
only; `performance_eligible: false`, PENDING/UNVERIFIED custody, M1 prohibition,
and all prospective-only/verification guards remain unchanged. Comparison
thresholds 30 blocks / 0.02 Brier / 95% CI remain PROPOSED / NOT ADOPTED.
No Pilot, model/market/broker API, payment, order, simulator, Bot, timer,
deployment or G2b ran. Only authorized Git transport is used for delivery.

Changed R1 paths: core/records.py, core/registry.py, core/storage.py,
tests/test_core.py, new tests/test_r1.py, evidence/unit-tests.txt,
evidence/changed-files.sha256, new evidence/r1-integrity.json, and this report.
Remaining limitations: real identity authentication and external custody are not
implemented; cross-prediction memory and legacy-database migration are deliberately
unavailable. No new known blocking implementation issue was found in these tests;
Founder review remains required. Keep PR #4 Draft and unmerged.

## API and trust boundaries

Use `Registry(path)` with a local SQLite path and close the handle after use.
`register` accepts a verified G1 prediction and creates an initial roster/state
atomically. `put` / `put_batch` accept sealed record envelopes. A batch is atomic;
missing or altered parents reject the whole batch. `snapshot` reconstructs the
ordered stored records; `state` returns separate lifecycle/eligibility fields.
`current_score` returns only the score for the latest outcome or None while that
revision is pending/unscored. Earlier scores remain available for audit, not as
alternative favorable current results. Database handles are thread-affine; use
one Registry per worker, as the concurrency test does.

Freeze receipts bind the original prediction reference/hash kind, strategy,
research, memory, measurement and evaluation references; included referenced
records carry their own content/artifact hashes. Freeze requires three distinct
structured challenges and Chief dispositions. References preserve full ancestry;
source/memory availability is checked recursively against the original cutoff.
Chief authorizes freeze; no software-generated primary call contradicts argmax.
The implementation checks structure and distinct content, not the intellectual
quality of objections. Human review must establish that challenges are substantive.

Evidence records carry descriptions, artifact hashes, locators and availability
assertions. They are supplied inputs, not fetched or independently authenticated
by this core. Outcome verification flags represent a separately performed manual
verification contract; the scorer cannot prove an exchange published a close.
Do not manufacture these assertions for real outcomes. A separately recorded
Founder decision preserves external evidence but grants no activation in code.

Freeze custody accepts PENDING/UNVERIFIED only. No external custody verifier or
approval-policy binding has been adopted for execution; a local VERIFIED flag
is explicitly rejected. Frozen samples remain QUARANTINED_PROVENANCE. The core
cannot promote them to ELIGIBLE or NEXT_VERSION_ELIGIBLE. Review and memory
records cannot activate memory/strategies; approved/effective timestamps remain
explicit nulls in proposals, separately from proposed/available times. This is
an intentional fail-closed boundary pending separate Founder authorization.

The implemented evidence classes are SYNTHETIC_ENGINEERING_FIXTURE and
GENUINE_FORWARD_PREDICTION as asserted record namespaces. Genuine-forward records
cannot establish verified eligibility here. Every scoring result explicitly has
`performance_eligible: false`. Verified outcomes are outcome records within the
originating sample's namespace, with explicit VERIFIED/PENDING/DISPUTED status;
this does not convert synthetic observations into genuine market evidence.
EXPERIMENTAL_STRATEGY_COMPARISON, aggregation and promotion are not implemented.
The proposed 30-block / 0.02 / 95% thresholds are not adopted in code.

## Validation actually performed

Command from repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s l0/tests -v
```

Result: **34 tests passed** (17 original + 9 R1 + 8 R2 tests), including parameterized subcases; zero failed,
skipped or expected-failure tests. Full output is `l0/evidence/unit-tests.txt`.

Coverage includes schema/required fields; stale/recomputed hash reuse; identical
retries; invalid probabilities/NaN/Infinity; state/eligibility separation; missing
challenges/dispositions; unverifiable custody; all three outcomes and exact FLAT
boundaries; Brier 0.26 and Log Loss approximately 0.5108256238; zero-probability
infinity; tie handling; early/pending/disputed/wrong-session/wrong-basis outcomes;
changed bounds/hash; revised outcomes with linked scores and duplicate exclusion;
missing/altered parents; rejected memory retained; backdated availability and
post-cutoff sources rejected; strategy proposals do not activate.

Recovery evidence: child-process death before commit leaves no record; after
commit preserves it. A process killed after staging the freeze receipt but before
its status insert leaves neither persisted; identical receipt retry succeeds.
An invalid second batch record rolls back its first record. Eight concurrent
registration attempts produce one prediction and initial state. Reopened state
exactly equals persisted reconstruction. Altered SQLite row content fails closed.

Only L0 tests ran. No G1 Risk Gate execution, G2a simulator/fill generator, trading
fixtures, external AI, market/broker APIs, real outcomes or M1 scoring ran. G1's
known missing-historical-archives failure is not rerun, hidden or relabeled PASS;
its historical 49/50 result remains as recorded on main.

## Integrity, limits and remaining delivery work

`l0/evidence/baseline-integrity.json` lists SHA-256 for every file at the exact
base and verifies unchanged bytes. This covers frozen G1, G2a-R1, M1, all
historical manifests and all four adopted L0 documents. M1 remains
`2317319d9ec2b33d9ccd2b8316c6c39b2f78d2d25e7fa7ad45aeb0e9274f224e`.
No replacement M1 JSON was created; registry/scorer explicitly reject its ID.

Security checks: new files scanned for private-key markers and common credential
formats; no matches. Core has no network client imports, API access, scheduler,
broker/execution path or live service dependency. Python standard library only.

Limitations: SQLite guarantees depend on local storage/fsync behavior; physical
power-loss/controller failures were not tested. The hash chain is not a signature
or external timestamp. A privileged actor can rewrite a coherent database or
truncate its tail; without an external anchor such wholesale changes are not
provably detectable. Stored actor names and source attestations are not identity
authentication. File permissions, backups and external custody require a later
approved operational policy. Full snapshot verification is deliberately O(n),
and repeated validation can be O(n²) across a batch; suitable for this minimal
record system, not high-volume storage. No automatic source validation, semantic
challenge judgment, trusted clock, dataset selection, active memory, comparison
cohort, formal pilot, deployment or learning claim is provided.

R1 addresses both blocking review findings with developer regressions. No independent QA or Founder acceptance is claimed; reviewer confirmation remains required. These checks are developer tests,
not independent QA. Delivery uses existing Draft PR #4 and branch feat/l0-core. The Founder review comment 6607510100 was supplied verbatim by the user after GitHub API reads were denied. Git push updates the existing PR; no new PR or merge is requested.
Neither this report nor passing tests declares Founder acceptance.

Recommendation: **L0-CORE READY FOR REVIEW**. Do not merge or run a pilot.
