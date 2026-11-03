# G2a — Minimum Offline Simulation Ledger (DEMO / synthetic)

Paper-only, offline, deterministic ledger. Uses G1-R4 Risk Gate via `evaluate_for_tests`
with FIXTURE_EVAL policy and a **G2a-owned** IdRegistry. Production `evaluate()` is never called.

All fills carry `engineering_fixture: true` and `demo: true` — never formal performance.

Run tests: `cd phase0c/g2a && PYTHONDONTWRITEBYTECODE=1 python3 tests/test_g2a.py`

G2a is FAIL / R1 CORRECTION AUTHORIZED; R1 awaits independent review.
Run without writing historical evidence: from the repository root,
`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s phase0c/g2a/tests -v`.

R1 stores accepted ID/hash bindings in GATE_RESULT payloads. The ledger is the
sole durable authority; registry_path is retained only to detect incompatible
legacy sidecars. An entire submit (binding, gate, fill / NO_TRADE / pending) is
staged under a process lock and published through same-directory atomic replace,
file fsync, and directory fsync. Events remain logically append-only and hash
chained. Recovery verifies hashes and reconstructs every state snapshot. Stops
stay latched across NEW_DAY. Gate/fill sequences derive from committed events.

Use a local POSIX filesystem supporting flock, atomic replace and fsync. The
implementation rewrites the complete ledger for each transaction: suitable for
this minimum offline lab, not a high-volume execution system. Failed commits may
have an uncertain acknowledgement; retry the identical artifacts to resolve
against durable state. A process death may leave an unused temporary file.
Legacy accepted ledgers without durable bindings and orphan registry sidecars
fail closed for explicit review; no automatic migration or data deletion occurs.
Pending acceptance remains a reservation only; replay does not execute it.
No halt-clearance API is provided. No broker integration is authorized.
