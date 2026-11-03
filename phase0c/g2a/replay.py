"""Rebuild ledger state from events; must equal live tip state."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from ledger import (
    GENESIS_PREV,
    LedgerError,
    _empty_state,
    apply_fill_to_state,
    refresh_marks_and_equity,
)
from g2a_paths import ensure_g1_on_path

ensure_g1_on_path()
from _hashutil import content_sha256  # type: ignore  # noqa: E402
from json_strict import StrictJSONError, loads  # type: ignore  # noqa: E402


def replay_ledger_file(path: Path) -> dict[str, Any]:
    """Pure replay from JSONL bytes. Fail-closed on tamper/corruption."""
    text = Path(path).read_text(encoding="utf-8")
    prev = GENESIS_PREV
    state: dict[str, Any] | None = None
    events: list[dict] = []

    for i, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            raise LedgerError("EMPTY_LEDGER_LINE", str(i))
        try:
            ev = loads(line)
        except StrictJSONError as e:
            raise LedgerError("CORRUPT_LEDGER_JSON", f"line={i}:{e}") from e
        if ev.get("prev_event_sha256") != prev:
            raise LedgerError("HASH_CHAIN_BREAK", f"line={i}")
        body = {k: v for k, v in ev.items() if k != "content_sha256"}
        actual = content_sha256(body)
        if ev.get("content_sha256") != actual:
            raise LedgerError("EVENT_HASH_MISMATCH", f"line={i}")
        if int(ev["seq"]) != i:
            raise LedgerError("SEQ_GAP", f"line={i}")
        events.append(ev)
        prev = ev["content_sha256"]

        et = ev["event_type"]
        payload = ev.get("payload") or {}
        sa = ev.get("state_after") if isinstance(ev.get("state_after"), dict) else {}

        if et == "GENESIS":
            state = _empty_state(
                cash=float(payload["initial_cash"]),
                trading_day=str(payload["trading_day"]),
            )
        elif et == "GATE_RESULT":
            if state is None:
                raise LedgerError("REPLAY_NO_STATE", str(i))
        elif et == "NO_TRADE_RECORD":
            if state is None:
                raise LedgerError("REPLAY_NO_STATE", str(i))
        elif et == "FILL":
            if state is None:
                raise LedgerError("REPLAY_NO_STATE", str(i))
            fill = payload["fill"]
            if fill["decision_id"] in state["filled_decision_ids"]:
                raise LedgerError("DUPLICATE_FILL", fill["decision_id"])
            apply_fill_to_state(state, fill)
            state["filled_decision_ids"][fill["decision_id"]] = fill["id"]
        elif et == "MARK_TO_MARKET":
            if state is None:
                raise LedgerError("REPLAY_NO_STATE", str(i))
            refresh_marks_and_equity(state, payload["marks"])
        elif et == "NEW_DAY":
            if state is None:
                raise LedgerError("REPLAY_NO_STATE", str(i))
            marks = sa.get("marks") or state.get("marks") or {}
            refresh_marks_and_equity(state, marks)
            state["trading_day"] = payload["trading_day"]
            state["day_start_equity"] = float(payload["day_start_equity"])
        elif et == "PENDING_INJECT":
            if state is None:
                raise LedgerError("REPLAY_NO_STATE", str(i))
            state["outstanding_pending"] = copy.deepcopy(payload.get("outstanding_pending") or [])
        else:
            raise LedgerError("UNKNOWN_EVENT_TYPE", et)

        expected = copy.deepcopy(state)
        expected.pop("last_event_sha256", None)
        expected.pop("last_seq", None)
        if sa != expected:
            raise LedgerError("STATE_REPLAY_MISMATCH", f"line={i}")

    if state is None:
        raise LedgerError("EMPTY_REPLAY")
    state["last_event_sha256"] = prev
    state["last_seq"] = len(events)
    state["demo"] = True
    return {"state": state, "events": events, "event_count": len(events)}


def states_equal(a: dict[str, Any], b: dict[str, Any], *, eps: float = 1e-9) -> tuple[bool, str]:
    keys = [
        "cash", "realized_pnl", "unrealized_pnl", "equity", "peak_equity",
        "drawdown_pct", "day_start_equity", "trading_day",
        "daily_loss_stop_latched", "drawdown_stop_latched", "demo",
    ]
    for k in keys:
        av, bv = a.get(k), b.get(k)
        if isinstance(av, (int, float)) and isinstance(bv, (int, float)):
            if abs(float(av) - float(bv)) > eps:
                return False, f"mismatch:{k}:{av}:{bv}"
        elif av != bv:
            return False, f"mismatch:{k}:{av}:{bv}"
    if {k: int(v) for k, v in (a.get("positions") or {}).items()} != {
        k: int(v) for k, v in (b.get("positions") or {}).items()
    }:
        return False, "mismatch:positions"
    ac, bc = a.get("avg_costs") or {}, b.get("avg_costs") or {}
    if set(ac) != set(bc):
        return False, "mismatch:avg_costs_keys"
    for t in ac:
        if abs(float(ac[t]) - float(bc[t])) > eps:
            return False, f"mismatch:avg_cost:{t}"
    if dict(a.get("filled_decision_ids") or {}) != dict(b.get("filled_decision_ids") or {}):
        return False, "mismatch:filled_decision_ids"
    if list(a.get("outstanding_pending") or []) != list(b.get("outstanding_pending") or []):
        return False, "mismatch:outstanding_pending"
    return True, "ok"
