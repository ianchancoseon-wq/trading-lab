"""G2a offline simulator: validate → Risk Gate → fill → ledger (DEMO/synthetic only)."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from g2a_paths import FIXTURE_POLICY_PATH, ensure_g1_on_path
from fill_engine import FillError, build_fill
from ledger import Ledger, marked_equity, unrealized_from_avg
from prices import PriceBook

ensure_g1_on_path()
from id_registry import IdRegistry  # type: ignore  # noqa: E402
from json_strict import load_path  # type: ignore  # noqa: E402
from submit_validator import validate_bundle
from risk_gate import evaluate_for_tests  # type: ignore  # noqa: E402


class SimError(Exception):
    def __init__(self, code: str, message: str = "", detail: dict | None = None):
        self.code = code
        self.message = message
        self.detail = detail or {}
        super().__init__(f"{code}:{message}")


def _portfolio_from_ledger(state: dict[str, Any], marks: dict[str, float]) -> dict[str, Any]:
    positions = {t: int(q) for t, q in state["positions"].items() if int(q) != 0}
    # marks must cover positions + any outstanding pending tickers
    need = set(positions) | {p.get("ticker", "").upper() for p in state.get("outstanding_pending") or []}
    for t in need:
        if t and t not in marks:
            raise SimError("MISSING_PRICE", t)
    use_marks = {t: float(marks[t]) for t in marks}
    cash = float(state["cash"])
    equity, _mv = marked_equity(cash, positions, use_marks)
    unreal = unrealized_from_avg(positions, state.get("avg_costs") or {}, use_marks)
    # Holdings must include at least keys we have marks for when testing multi-name,
    # but gate requires holdings dict — use open positions (zeros optional).
    holdings = {t: int(q) for t, q in positions.items()}
    # Ensure mark tickers present even if flat (gate needs decision ticker mark)
    for t in use_marks:
        holdings.setdefault(t, 0)
    return {
        "cash": cash,
        "equity": float(equity),
        "peak_equity": float(state["peak_equity"]),
        "day_start_equity": float(state["day_start_equity"]),
        "unrealized_pnl": float(unreal),
        "holdings": holdings,
        "marks": use_marks,
        "pending_intents": copy.deepcopy(state.get("outstanding_pending") or []),
    }


class Simulator:
    """Minimum offline paper simulation. All results are DEMO / engineering fixtures."""

    def __init__(
        self,
        ledger_path: Path,
        registry_path: Path,
        price_book: PriceBook,
        *,
        initial_cash: float = 100_000.0,
        trading_day: str = "2026-11-03",
        policy_path: Path | None = None,
    ):
        self.prices = price_book
        self.ledger = Ledger(ledger_path, initial_cash=initial_cash, trading_day=trading_day)
        self.registry_path = Path(registry_path)
        self.registry = self._registry_from_ledger()
        self.policy = load_path(policy_path or FIXTURE_POLICY_PATH)

    @property
    def state(self) -> dict[str, Any]:
        return self.ledger.snapshot_state()

    def _registry_from_ledger(self):
        registry = IdRegistry(None)
        for event in self.ledger.events():
            if event["event_type"] != "GATE_RESULT":
                continue
            payload = event["payload"]
            if payload["gate_result"]["verdict"] != "ACCEPT":
                continue
            bindings = payload.get("bindings")
            if not bindings:
                raise SimError("LEGACY_LEDGER_REQUIRES_REVIEW", "accepted gate has no durable content bindings")
            status, _ = registry.check_and_register(bindings.items())
            if status == "ID_HASH_CONFLICT":
                raise SimError("ID_HASH_CONFLICT", "inconsistent durable bindings")
        # Never import orphan sidecar bindings: old G2a could save IDs before fills.
        legacy = IdRegistry(self.registry_path)
        if any(registry.check(k, v) != "ID_REPLAY_SAME" for k, v in legacy._map.items()):
            raise SimError("ORPHAN_REGISTRY_REQUIRES_REVIEW")
        return registry

    def _next_gate_id(self, decision_id: str) -> str:
        seq = 1 + sum(e["event_type"] == "GATE_RESULT" for e in self.ledger.events())
        return f"GATE-G2A-{seq:04d}-{decision_id}"

    def _next_fill_id(self, decision_id: str) -> str:
        seq = 1 + sum(e["event_type"] == "FILL" for e in self.ledger.events())
        return f"FILL-G2A-{seq:04d}-{decision_id}"

    def clear_stops(self, *a, **k):
        """No Bot may clear stops — always fails closed."""
        return self.ledger.attempt_clear_stops()

    def inject_pending(self, pending: list[dict], ts_utc: str) -> dict:
        return self.ledger.inject_outstanding_pending(pending, ts_utc)

    def mark_to_market(self, trading_day: str | None = None, ts_utc: str | None = None) -> dict:
        day = trading_day or self.ledger.state["trading_day"]
        marks = self.prices.marks_for(day)
        # Keep marks for currently held names; PriceBook day must include them
        held = [t for t, q in self.ledger.state["positions"].items() if q > 0]
        if held:
            marks = self.prices.marks_for(day, held + [t for t in marks if t not in held])
        ts = ts_utc or f"{day}T16:00:00Z"
        return self.ledger.mark_to_market(marks, ts)

    def start_new_day(self, trading_day: str, ts_utc: str | None = None) -> dict:
        marks = self.prices.marks_for(trading_day)
        held = [t for t, q in self.ledger.state["positions"].items() if q > 0]
        if held:
            # merge: require held marks
            marks = self.prices.marks_for(trading_day, list(set(held) | set(marks)))
        ts = ts_utc or f"{trading_day}T09:30:00Z"
        return self.ledger.start_new_day(trading_day, marks, ts)

    def submit(self, prediction: dict, decision: dict, *, evaluated_at_utc: str,
               fill_immediately: bool = True) -> dict[str, Any]:
        try:
            with self.ledger.transaction():
                self.registry = self._registry_from_ledger()
                result = self._submit(prediction, decision, evaluated_at_utc=evaluated_at_utc,
                                      fill_immediately=fill_immediately)
            return result
        except BaseException:
            self.registry = self._registry_from_ledger()
            raise

    def _submit(
        self,
        prediction: dict,
        decision: dict,
        *,
        evaluated_at_utc: str,
        fill_immediately: bool = True,
    ) -> dict[str, Any]:
        """Run gate then optionally fill. Idempotent on identical DEC already filled."""
        st = self.ledger.state
        dec_id = decision.get("id")

        # Idempotent: if this DEC already produced a fill, return replay without new fill
        if isinstance(dec_id, str) and dec_id in st["filled_decision_ids"]:
            bundle = validate_bundle(prediction, decision, self.registry, allow_id_replay=True)
            if not bundle["ok"]:
                raise SimError("INVALID_REPLAY_BUNDLE", detail=bundle)
            if bundle["prediction_replay"] != "identical" or bundle["decision_replay"] != "identical":
                raise SimError("ID_REPLAY_INCONSISTENT")
            return {
                "status": "OK_IDEMPOTENT_REPLAY",
                "fill_id": st["filled_decision_ids"][dec_id],
                "gate_result": None,
                "fill": None,
                "state": self.ledger.snapshot_state(),
            }

        # G2a latch: block risk-increasing BUY when stops latched (stronger than raw gate)
        intent = decision.get("intent")
        if intent == "PAPER_BUY":
            # Drawdown latch checked first (never auto-clears); daily next.
            if st.get("drawdown_stop_latched"):
                raise SimError("DRAWDOWN_STOP_LATCHED", "buy blocked by latched drawdown stop")
            if st.get("daily_loss_stop_latched"):
                raise SimError("DAILY_LOSS_STOP_LATCHED", "buy blocked by latched daily loss stop")

        day = st["trading_day"]
        ticker = str(prediction.get("ticker", "")).upper()
        # Build marks: all price-book marks for day + ensure decision ticker
        try:
            day_marks = self.prices.marks_for(day)
        except KeyError as e:
            raise SimError("MISSING_PRICE_DAY", str(e)) from e
        if ticker and ticker not in day_marks:
            raise SimError("MISSING_PRICE", ticker)
        # Include marks for holdings
        for t, q in st["positions"].items():
            if q > 0 and t not in day_marks:
                raise SimError("MISSING_PRICE", t)

        portfolio = _portfolio_from_ledger(st, day_marks)
        gate_id = self._next_gate_id(str(dec_id or "UNKNOWN"))

        gate = evaluate_for_tests(
            prediction,
            decision,
            portfolio,
            portfolio["pending_intents"],
            self.policy,
            gate_id=gate_id,
            evaluated_at_utc=evaluated_at_utc,
            registry=self.registry,
            allow_fixture_eval=True,
        )
        bindings = ({a["id"]: a["content_sha256"] for a in (prediction, decision)}
                    if gate["verdict"] == "ACCEPT" else {})
        gate_ev = self.ledger.record_gate(gate, evaluated_at_utc, bindings)

        out: dict[str, Any] = {
            "status": gate["verdict"],
            "gate_result": gate,
            "gate_event": gate_ev,
            "fill": None,
            "fill_event": None,
            "no_trade_event": None,
            "state": self.ledger.snapshot_state(),
            "portfolio_submitted": portfolio,
        }

        if gate["verdict"] != "ACCEPT":
            out["status"] = "REJECT"
            out["state"] = self.ledger.snapshot_state()
            return out

        # Idempotent gate replay of identical PRED+DEC with no prior fill
        if "OK_IDEMPOTENT_REPLAY" in gate.get("reason_codes", []):
            out["status"] = "OK_IDEMPOTENT_REPLAY"
            out["state"] = self.ledger.snapshot_state()
            return out

        if intent == "NO_TRADE":
            nt = self.ledger.record_no_trade(
                prediction_id=prediction["id"],
                decision_id=decision["id"],
                gate_result_id=gate["id"],
                ts_utc=evaluated_at_utc,
            )
            out["status"] = "OK_NO_TRADE"
            out["no_trade_event"] = nt
            out["state"] = self.ledger.snapshot_state()
            return out

        if not fill_immediately:
            # Leave as outstanding pending (engineering fixture path)
            snaps = gate.get("snapshots") or {}
            shares = int(snaps.get("whole_shares") or snaps.get("intended_shares") or 0)
            size_pct = float(decision["size_pct"])
            mark = float(day_marks[ticker])
            pending_row = {
                "ticker": ticker,
                "status": "ACCEPT",
                "intent": intent,
                "size_pct": size_pct,
                "shares": shares,
                "mark": mark,
                "notional": shares * mark,
                "reserved_cash": shares * mark if intent == "PAPER_BUY" else 0.0,
            }
            pend = list(st["outstanding_pending"]) + [pending_row]
            self.ledger.inject_outstanding_pending(pend, evaluated_at_utc)
            out["status"] = "ACCEPTED_PENDING"
            out["state"] = self.ledger.snapshot_state()
            return out

        # Execute synthetic fill at pre-supplied mark
        snaps = gate.get("snapshots") or {}
        shares = snaps.get("whole_shares")
        if shares is None:
            shares = snaps.get("intended_shares")
        shares_i = int(shares) if shares is not None else 0
        if shares_i <= 0:
            raise SimError("ZERO_SHARE_AFTER_ACCEPT", str(shares))

        px = float(day_marks[ticker])
        side = "BUY" if intent == "PAPER_BUY" else "SELL"

        # Pre-compute realized for sells (average-cost)
        realized = None
        if side == "SELL":
            avg = float(st["avg_costs"].get(ticker, 0.0))
            realized = shares_i * (px - avg)

        fill_id = self._next_fill_id(decision["id"])
        try:
            fill = build_fill(
                fill_id=fill_id,
                decision_id=decision["id"],
                prediction_id=prediction["id"],
                gate_result_id=gate["id"],
                ticker=ticker,
                side=side,
                shares=shares_i,
                price=px,
                filled_at_utc=evaluated_at_utc,
                realized_pnl=realized,
                notes="G2a synthetic engineering fixture fill; not formal performance",
            )
        except FillError as e:
            raise SimError(e.code, e.message) from e

        fill_ev = self.ledger.record_fill(fill, evaluated_at_utc)
        out["status"] = "FILLED"
        out["fill"] = fill
        out["fill_event"] = fill_ev
        out["state"] = self.ledger.snapshot_state()
        return out
