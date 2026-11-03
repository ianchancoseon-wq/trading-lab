# G2a-R1 engineering review

Status: G2a FAIL / R1 CORRECTION AUTHORIZED. Correction awaits independent review;
no acceptance or merge is implied. G1-R4 remains ACCEPTED and frozen.

## Migration review

PR #1 head ref and `import/g1r4-g2a` both resolve to
`042bee94dfd34e765b38bf17720024df7e427a1f`. Its 105 import-manifest entries
verified byte-for-byte before edits. All 107 tracked files were scanned for
private-key markers, common token formats, and credential assignments; no matches
were found. This is a heuristic scan, not proof that no credential exists.
The frozen M1 SHA-256 is
`2317319d9ec2b33d9ccd2b8316c6c39b2f78d2d25e7fa7ad45aeb0e9274f224e`.
Historical manifests and implementation reports remain unchanged. The original
import manifest describes the original import, not this corrected tree.

LAB-STATE's stale submitted/pending status and infrastructure handoff are updated
on the correction branch. The migration branch is untouched. Missing historical
failed-build archives, audit copy, and ZIP deliverables are not fabricated.
GitHub API metadata is currently unavailable: proxy CONNECT to api.github.com
returns 403. Git transport works. PR state must be confirmed before creating the
stacked draft PR; do not merge either PR without explicit Founder approval.

## Corrected behavior

1. A filled decision can replay only after full bundle validation verifies the
   submitted hashes, frozen IDs, and prediction/decision linkage. Both stale-hash
   and rehashed altered content are rejected before the filled-ID shortcut.
2. NEW_DAY can update the day and day-start equity but cannot clear either daily
   loss or drawdown latches. Recovery follows the same rule. No Bot clearance API
   exists.
3. Registry bindings are stored with accepted gates in the ledger. Binding, gate,
   synthetic fill generation, ledger effects, NO_TRADE records, and pending
   reservations share one staged transaction. A process lock serializes writers;
   same-directory atomic replacement, file fsync, and directory fsync publish the
   entire logical append. Memory rolls back or reloads the committed version when
   errors occur. Recovery reconstructs effects and verifies every state snapshot.
   Sequences derive from durable events, preserving IDs across restarts. Repeated
   fills are rejected at the ledger boundary as well.

G1 code and its risk limits remain byte-identical: 20% per name across holdings
and accepted/pending buys, 2% daily loss, 10% peak drawdown, no short/leverage,
whole shares, no credit for unfilled sells. Only synthetic/offline activity ran.

## Validation

Python 3.12.14, standard library only. From repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s phase0c/g2a/tests -v
PYTHONDONTWRITEBYTECODE=1 python3 phase0c/g2a/verify_integrity.py
```

- G2a: 28 tests passed (16 existing, with corrected daily-latch expectation;
  12 targeted regressions). Includes real child-process death after binding,
  before replace, and after replace; file/directory sync failures; fill-generation
  and ledger failures; concurrent retries; pending/no-trade rollback; orphan
  registry rejection; forged snapshot rejection; deterministic restart/replay.
- Independent runs with fixed artifacts/timestamps, including an intervening
  restart, produce identical ledger bytes. Live state exactly equals pure replay
  and reopened state in correction recovery tests.
- Frozen G1 suite, executed from a temporary copy: 50 tests ran, 49 passed,
  1 failed (`test_failed_archives_present`) because the import intentionally omits
  historical failed-build archives. This known packaging failure is not marked
  skipped, expected-failure, or passed. Original source and tests were not edited.
- Original import reproductions: altered replay accepted (8 failing subcases),
  NEW_DAY cleared daily halt, post-binding failure retried with replay status and
  zero fills, failed write left memory day ahead of durable day.
- Detailed current-run logs and baseline reproductions: `g2a/r1_evidence/`.
- `verify_integrity.py` verifies the import at its pinned commit, current frozen
  files, untouched historical manifests, and all R1 manifest entries.

## Limitations and independent review

- Local POSIX filesystem required (flock, same-filesystem atomic rename, fsync).
  Whole-file replacement is intentionally simple and O(ledger size) per commit.
- Process-death tests exercise crash boundaries; physical power loss and storage
  controller failures were not tested. An fsync error means uncertain
  acknowledgement; an identical retry reconciles whichever complete ledger is
  present. Do not substitute new IDs on retry.
- Legacy accepted ledgers lacking durable bindings and orphan sidecar registries
  fail closed for manual review. No automatic repair, migration, or deletion.
- Pending acceptance reserves exposure but has no later execution API in scope.
  No halt-clearance workflow is added. A crash may leave an unused temporary file.
- SHA-256 chains provide corruption detection, not authenticated signatures.
- No broker/Alpaca connections, real/paper API orders, PAPER_ON, recurring
  automation, paid APIs, additional Bots, or G2b work was performed.

Delivery branch: `fix/g2a-r1`, based on the pinned import. Intended draft PR base:
`import/g1r4-g2a` while PR #1 remains unmerged. Neither PR may be merged by this
engineering task. If API access remains blocked, the branch and prepared PR text
are reviewable but a draft PR has not yet been created.
