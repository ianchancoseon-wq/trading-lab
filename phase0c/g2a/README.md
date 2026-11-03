# G2a — Minimum Offline Simulation Ledger (DEMO / synthetic)

Paper-only, offline, deterministic ledger. Uses G1-R4 Risk Gate via `evaluate_for_tests`
with FIXTURE_EVAL policy and a **G2a-owned** IdRegistry. Production `evaluate()` is never called.

All fills carry `engineering_fixture: true` and `demo: true` — never formal performance.

Run tests: `cd phase0c/g2a && PYTHONDONTWRITEBYTECODE=1 python3 tests/test_g2a.py`
