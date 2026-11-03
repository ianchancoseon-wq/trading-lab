"""Build demo PRED/DEC artifacts with correct content hashes (G2a fixtures)."""
from __future__ import annotations

from typing import Any

from g2a_paths import ensure_g1_on_path

ensure_g1_on_path()
from _hashutil import attach_hash  # type: ignore  # noqa: E402


def make_prediction(
    *,
    pid: str,
    ticker: str,
    baseline_price: float,
    frozen_at_utc: str,
    horizon_end: str = "2026-11-10",
    knowledge_cutoff_utc: str = "2026-11-03T00:00:00Z",
    notes: str = "G2a DEMO synthetic prediction; not a formal forward score",
) -> dict[str, Any]:
    body = {
        "schema": "prediction_v1",
        "id": pid,
        "strategy_version": "g2a-v0.1",
        "ticker": ticker.upper(),
        "baseline_price": float(baseline_price),
        "baseline_source_tier": "synthetic",
        "band": 0.5,
        "horizon_end": horizon_end,
        "probs": {"UP": 0.4, "FLAT": 0.3, "DOWN": 0.3},
        "EVENT_EXPOSED": True,
        "knowledge_cutoff_utc": knowledge_cutoff_utc,
        "frozen_at_utc": frozen_at_utc,
        "demo": True,
        "notes": notes,
    }
    return attach_hash(body)


def make_decision(
    *,
    did: str,
    prediction_id: str,
    intent: str,
    size_pct: float,
    decided_at_utc: str,
    rationale: str = "G2a DEMO synthetic decision",
) -> dict[str, Any]:
    body = {
        "schema": "decision_v1",
        "id": did,
        "prediction_id": prediction_id,
        "intent": intent,
        "size_pct": float(size_pct),
        "rationale_digest": rationale,
        "memory_influence": [],
        "risk_ack": True,
        "decided_at_utc": decided_at_utc,
        "demo": True,
        "notes": "G2a DEMO; engineering fixture only",
    }
    return attach_hash(body)
