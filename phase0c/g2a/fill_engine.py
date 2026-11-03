"""Deterministic synthetic fill engine. Prices must be supplied before execution."""
from __future__ import annotations

from typing import Any

from g2a_paths import ensure_g1_on_path

ensure_g1_on_path()
from _hashutil import attach_hash  # type: ignore  # noqa: E402
from finite_numbers import as_finite  # type: ignore  # noqa: E402


class FillError(Exception):
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message
        super().__init__(f"{code}:{message}")


def build_fill(
    *,
    fill_id: str,
    decision_id: str,
    prediction_id: str,
    gate_result_id: str,
    ticker: str,
    side: str,
    shares: int,
    price: float,
    filled_at_utc: str,
    realized_pnl: float | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    pf = as_finite(price)
    if pf is None or pf <= 0:
        raise FillError("BAD_FILL_PRICE", str(price))
    if not isinstance(shares, int) or shares <= 0:
        raise FillError("BAD_FILL_SHARES", str(shares))
    if side not in ("BUY", "SELL"):
        raise FillError("BAD_FILL_SIDE", side)
    notional = float(shares) * float(pf)
    body: dict[str, Any] = {
        "schema": "fill_v1",
        "id": fill_id,
        "decision_id": decision_id,
        "prediction_id": prediction_id,
        "gate_result_id": gate_result_id,
        "ticker": ticker.upper(),
        "side": side,
        "shares": int(shares),
        "price": float(pf),
        "notional": notional,
        "filled_at_utc": filled_at_utc,
        "engineering_fixture": True,
        "demo": True,
    }
    if realized_pnl is not None:
        rp = as_finite(realized_pnl)
        if rp is None:
            raise FillError("BAD_REALIZED_PNL", str(realized_pnl))
        body["realized_pnl"] = float(rp)
    if notes is not None:
        body["notes"] = notes
    return attach_hash(body)
