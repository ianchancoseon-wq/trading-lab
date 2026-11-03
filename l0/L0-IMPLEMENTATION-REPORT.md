# L0 implementation report

Status: L0-CORE READY FOR REVIEW. Founder acceptance is pending. This is an offline
engineering core, not an authorized Forward Pilot.

Base commit: `70aa77b1deee94b34f482e987ce7f98a0013539c` (fetched main).
Branch: `feat/l0-core`. The final delivery SHA is recorded in the accompanying
submission receipt and PR body. A commit cannot embed its own hash in its own
tracked report; resolve this report's delivery commit with `git rev-parse HEAD`.
The explicit 2026-11-03 Founder implementation contract supersedes main's older
implementation-not-authorized status. LAB-STATE and adopted documents are preserved.

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

All code changes are additions under `l0/`; no existing tracked file is modified.
The changed-file manifest lists each added source, test and report path. The
manifest excludes its own digest, which is reported in the submission receipt.

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

Result: **17 tests passed**, including parameterized subcases; zero failed,
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

No known unresolved P0/P1 issue within this bounded, unauthenticated offline
engineering contract after the recorded tests. These checks are developer tests,
not independent QA. Draft PR delivery is subject to GitHub API access: current
requests to api.github.com return Forbidden although Git transport works.
Neither this report nor passing tests declares Founder acceptance.

Recommendation: **L0-CORE READY FOR REVIEW**. Do not merge or run a pilot.
