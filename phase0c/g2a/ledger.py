"""Append-only simulation ledger with hash-chained JSONL events (G2a)."""
from __future__ import annotations

import copy
import hashlib
import math
from pathlib import Path
from typing import Any

from g2a_paths import ensure_g1_on_path

ensure_g1_on_path()
from _hashutil import attach_hash, content_sha256  # type: ignore  # noqa: E402
from finite_numbers import as_finite  # type: ignore  # noqa: E402
from json_strict import StrictJSONError, dumps_strict, loads  # type: ignore  # noqa: E402
import frozen_limits as FL  # type: ignore  # noqa: E402

GENESIS_PREV = "0" * 64


class LedgerError(Exception):
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message
        super().__init__(f"{code}:{message}")


def _empty_state(
    *,
    cash: float,
    trading_day: str,
    marks: dict[str, float] | None = None,
) -> dict[str, Any]:
    cash_f = as_finite(cash)
    if cash_f is None or cash_f < 0:
        raise LedgerError("BAD_INITIAL_CASH", str(cash))
    return {
        "schema": "ledger_state_v1",
        "cash": float(cash_f),
        "positions": {},  # ticker -> int shares
        "avg_costs": {},  # ticker -> avg cost per share
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "equity": float(cash_f),
        "peak_equity": float(cash_f),
        "drawdown_pct": 0.0,
        "day_start_equity": float(cash_f),
        "trading_day": trading_day,
        "daily_loss_stop_latched": False,
        "drawdown_stop_latched": False,
        "filled_decision_ids": {},  # dec_id -> fill_id
        "outstanding_pending": [],
        "marks": dict(marks or {}),
        "demo": True,
        "last_event_sha256": GENESIS_PREV,
        "last_seq": 0,
    }


def marked_equity(cash: float, positions: dict[str, int], marks: dict[str, float]) -> tuple[float, float]:
    """Return (equity, unrealized_pnl) using average-cost book for unrealized."""
    mv = 0.0
    for t, q in positions.items():
        if q == 0:
            continue
        if t not in marks:
            raise LedgerError("MISSING_MARK", t)
        px = as_finite(marks[t])
        if px is None or px <= 0:
            raise LedgerError("BAD_MARK", f"{t}:{marks[t]}")
        mv += float(q) * float(px)
    equity = float(cash) + mv
    return equity, mv  # caller computes unrealized from avg_costs


def unrealized_from_avg(
    positions: dict[str, int],
    avg_costs: dict[str, float],
    marks: dict[str, float],
) -> float:
    u = 0.0
    for t, q in positions.items():
        if q <= 0:
            continue
        if t not in marks:
            raise LedgerError("MISSING_MARK", t)
        cost = float(avg_costs.get(t, 0.0))
        u += float(q) * (float(marks[t]) - cost)
    return u


def apply_stop_latches(state: dict[str, Any]) -> None:
    """Latch stops from marked equity. Never clears drawdown; daily only via NEW_DAY."""
    equity = float(state["equity"])
    day_start = float(state["day_start_equity"])
    peak = float(state["peak_equity"])
    if day_start > 0:
        daily_loss_pct = max(0.0, (day_start - equity) / day_start * 100.0)
        if daily_loss_pct >= FL.MAX_DAILY_LOSS_PCT:
            state["daily_loss_stop_latched"] = True
    if peak > 0:
        dd = max(0.0, (peak - equity) / peak * 100.0)
        state["drawdown_pct"] = dd
        if dd >= FL.MAX_PEAK_DRAWDOWN_PCT:
            state["drawdown_stop_latched"] = True
    else:
        state["drawdown_pct"] = 0.0


def refresh_marks_and_equity(state: dict[str, Any], marks: dict[str, float]) -> None:
    # Ensure marks cover all open positions
    for t, q in state["positions"].items():
        if q > 0 and t not in marks:
            raise LedgerError("MISSING_MARK", t)
    state["marks"] = {k: float(v) for k, v in marks.items()}
    eq, _mv = marked_equity(state["cash"], state["positions"], state["marks"])
    if not math.isfinite(eq):
        raise LedgerError("NON_FINITE_EQUITY", str(eq))
    state["equity"] = eq
    state["unrealized_pnl"] = unrealized_from_avg(
        state["positions"], state["avg_costs"], state["marks"]
    )
    if eq > float(state["peak_equity"]):
        state["peak_equity"] = eq
    apply_stop_latches(state)


def apply_fill_to_state(state: dict[str, Any], fill: dict[str, Any]) -> float:
    """Mutate state with fill. Returns realized_pnl for this fill (0 for buys). Average-cost."""
    ticker = fill["ticker"].upper()
    side = fill["side"]
    shares = int(fill["shares"])
    price = float(fill["price"])
    positions = state["positions"]
    avg_costs = state["avg_costs"]
    realized = 0.0

    if side == "BUY":
        notional = shares * price
        if float(state["cash"]) + 1e-9 < notional:
            raise LedgerError("INSUFFICIENT_CASH_LEDGER", f"need {notional}")
        prev_q = int(positions.get(ticker, 0))
        prev_cost = float(avg_costs.get(ticker, 0.0))
        new_q = prev_q + shares
        if new_q <= 0:
            raise LedgerError("BAD_POSITION", str(new_q))
        new_avg = ((prev_q * prev_cost) + notional) / new_q if new_q else 0.0
        positions[ticker] = new_q
        avg_costs[ticker] = new_avg
        state["cash"] = float(state["cash"]) - notional
    elif side == "SELL":
        prev_q = int(positions.get(ticker, 0))
        if shares > prev_q:
            raise LedgerError("SHORT_FORBIDDEN", f"{ticker}:{shares}>{prev_q}")
        prev_cost = float(avg_costs.get(ticker, 0.0))
        realized = shares * (price - prev_cost)
        new_q = prev_q - shares
        state["cash"] = float(state["cash"]) + shares * price
        state["realized_pnl"] = float(state["realized_pnl"]) + realized
        if new_q == 0:
            positions.pop(ticker, None)
            avg_costs.pop(ticker, None)
        else:
            positions[ticker] = new_q
            # avg cost unchanged on partial sell
    else:
        raise LedgerError("BAD_SIDE", side)

    # Update marks for traded ticker at fill price if not present
    marks = dict(state.get("marks") or {})
    marks[ticker] = price
    refresh_marks_and_equity(state, marks)
    return realized


class Ledger:
    def __init__(self, path: Path, *, initial_cash: float = 100_000.0, trading_day: str = "2026-11-03"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.state = _empty_state(cash=initial_cash, trading_day=trading_day)
        self._events: list[dict[str, Any]] = []
        if self.path.exists() and self.path.stat().st_size > 0:
            self._load_and_verify()
        else:
            self._append_genesis()

    def _load_and_verify(self) -> None:
        text = self.path.read_text(encoding="utf-8")
        prev = GENESIS_PREV
        events: list[dict[str, Any]] = []
        state = None
        for i, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                raise LedgerError("EMPTY_LEDGER_LINE", str(i))
            try:
                ev = loads(line)
            except StrictJSONError as e:
                raise LedgerError("CORRUPT_LEDGER_JSON", f"line={i}:{e}") from e
            if not isinstance(ev, dict):
                raise LedgerError("CORRUPT_LEDGER_TYPE", str(i))
            if ev.get("prev_event_sha256") != prev:
                raise LedgerError("HASH_CHAIN_BREAK", f"line={i}")
            claimed = ev.get("content_sha256")
            body = {k: v for k, v in ev.items() if k != "content_sha256"}
            try:
                actual = content_sha256(body)
            except (ValueError, TypeError) as e:
                raise LedgerError("CORRUPT_LEDGER_HASH", f"line={i}:{e}") from e
            if claimed != actual:
                raise LedgerError("EVENT_HASH_MISMATCH", f"line={i}")
            if int(ev.get("seq", -1)) != i:
                raise LedgerError("SEQ_GAP", f"line={i} seq={ev.get('seq')}")
            events.append(ev)
            prev = claimed
            if "state_after" in ev and isinstance(ev["state_after"], dict):
                state = copy.deepcopy(ev["state_after"])
        if state is None:
            raise LedgerError("NO_STATE_AFTER", "ledger has no state_after")
        state["last_event_sha256"] = prev
        state["last_seq"] = len(events)
        self._events = events
        self.state = state

    def _append_genesis(self) -> None:
        payload = {
            "initial_cash": self.state["cash"],
            "trading_day": self.state["trading_day"],
            "note": "G2a DEMO synthetic ledger genesis",
        }
        self._append_event(
            event_type="GENESIS",
            ts_utc=f"{self.state['trading_day']}T00:00:00Z",
            payload=payload,
            event_id="LEV-GENESIS-001",
        )

    def _append_event(
        self,
        *,
        event_type: str,
        ts_utc: str,
        payload: dict[str, Any],
        event_id: str | None = None,
    ) -> dict[str, Any]:
        seq = int(self.state["last_seq"]) + 1
        eid = event_id or f"LEV-{seq:06d}"
        # Snapshot state AFTER caller already mutated self.state
        state_after = copy.deepcopy(self.state)
        # Strip volatile mirror fields that are derived from chain tip
        state_after.pop("last_event_sha256", None)
        state_after.pop("last_seq", None)
        body = {
            "schema": "ledger_event_v1",
            "event_id": eid,
            "seq": seq,
            "event_type": event_type,
            "ts_utc": ts_utc,
            "prev_event_sha256": self.state["last_event_sha256"],
            "payload": payload,
            "state_after": state_after,
        }
        ev = attach_hash(body)
        line = dumps_strict(ev, sort_keys=True, separators=(",", ":"))
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
        self._events.append(ev)
        self.state = copy.deepcopy(state_after)
        self.state["last_event_sha256"] = ev["content_sha256"]
        self.state["last_seq"] = seq
        self.state["demo"] = True
        return ev

    def snapshot_state(self) -> dict[str, Any]:
        return copy.deepcopy(self.state)

    def events(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._events)

    def record_gate(self, gate_result: dict[str, Any], ts_utc: str) -> dict[str, Any]:
        return self._append_event(
            event_type="GATE_RESULT",
            ts_utc=ts_utc,
            payload={"gate_result": gate_result},
        )

    def record_no_trade(
        self,
        *,
        prediction_id: str,
        decision_id: str,
        gate_result_id: str,
        ts_utc: str,
    ) -> dict[str, Any]:
        return self._append_event(
            event_type="NO_TRADE_RECORD",
            ts_utc=ts_utc,
            payload={
                "prediction_id": prediction_id,
                "decision_id": decision_id,
                "gate_result_id": gate_result_id,
                "position_unchanged": True,
            },
        )

    def record_fill(self, fill: dict[str, Any], ts_utc: str) -> dict[str, Any]:
        # Apply fill then append (fill must already carry content_sha256)
        realized = apply_fill_to_state(self.state, fill)
        fill_out = dict(fill)
        if "realized_pnl" not in fill_out:
            fill_out["realized_pnl"] = float(realized)
            fill_out = attach_hash(fill_out)
        dec_id = fill_out["decision_id"]
        self.state["filled_decision_ids"][dec_id] = fill_out["id"]
        return self._append_event(
            event_type="FILL",
            ts_utc=ts_utc,
            payload={"fill": fill_out, "realized_pnl": float(realized)},
        )

    def mark_to_market(self, marks: dict[str, float], ts_utc: str) -> dict[str, Any]:
        refresh_marks_and_equity(self.state, marks)
        return self._append_event(
            event_type="MARK_TO_MARKET",
            ts_utc=ts_utc,
            payload={"marks": dict(marks)},
        )

    def start_new_day(self, trading_day: str, marks: dict[str, float], ts_utc: str) -> dict[str, Any]:
        """New trading day: reset daily stop latch; drawdown latch NEVER clears."""
        refresh_marks_and_equity(self.state, marks)
        self.state["trading_day"] = trading_day
        self.state["day_start_equity"] = float(self.state["equity"])
        self.state["daily_loss_stop_latched"] = False
        # drawdown_stop_latched intentionally unchanged
        return self._append_event(
            event_type="NEW_DAY",
            ts_utc=ts_utc,
            payload={
                "trading_day": trading_day,
                "day_start_equity": self.state["day_start_equity"],
                "drawdown_stop_still_latched": self.state["drawdown_stop_latched"],
            },
        )

    def inject_outstanding_pending(self, pending: list[dict[str, Any]], ts_utc: str) -> dict[str, Any]:
        """Engineering fixture: set outstanding pending snapshot (DEMO only)."""
        if not isinstance(pending, list):
            raise LedgerError("PENDING_NOT_LIST")
        self.state["outstanding_pending"] = copy.deepcopy(pending)
        return self._append_event(
            event_type="PENDING_INJECT",
            ts_utc=ts_utc,
            payload={"outstanding_pending": pending, "demo": True},
        )

    def attempt_clear_stops(self, *args, **kwargs) -> dict[str, Any]:
        """Explicitly unavailable — stops cannot be cleared by any Bot."""
        raise LedgerError(
            "STOP_CLEAR_FORBIDDEN",
            "daily/drawdown stop latches cannot be cleared by Bot API",
        )

    def file_sha256(self) -> str:
        return hashlib.sha256(self.path.read_bytes()).hexdigest()
