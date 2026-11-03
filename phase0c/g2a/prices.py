"""Synthetic price fixtures — pre-supplied before any fill."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from g2a_paths import ensure_g1_on_path

ensure_g1_on_path()
from json_strict import StrictJSONError, load_path  # type: ignore  # noqa: E402
from finite_numbers import as_finite  # type: ignore  # noqa: E402


class PriceBook:
    """date (YYYY-MM-DD) -> ticker -> price. Fail-closed on missing/nonfinite."""

    def __init__(self, table: dict[str, dict[str, float]]):
        self._table = table

    @classmethod
    def from_path(cls, path: Path) -> "PriceBook":
        raw = load_path(path)
        if not isinstance(raw, dict) or "prices" not in raw:
            raise StrictJSONError("price_book_missing_prices")
        prices = raw["prices"]
        if not isinstance(prices, dict):
            raise StrictJSONError("price_book_prices_not_object")
        out: dict[str, dict[str, float]] = {}
        for day, marks in prices.items():
            if not isinstance(marks, dict):
                raise StrictJSONError(f"price_book_day_not_object:{day}")
            day_m: dict[str, float] = {}
            for t, px in marks.items():
                pf = as_finite(px)
                if pf is None or pf <= 0:
                    raise StrictJSONError(f"price_book_bad_price:{day}:{t}")
                day_m[str(t).upper()] = float(pf)
            out[str(day)] = day_m
        return cls(out)

    def marks_for(self, trading_day: str, tickers: list[str] | None = None) -> dict[str, float]:
        if trading_day not in self._table:
            raise KeyError(f"MISSING_PRICE_DAY:{trading_day}")
        day = self._table[trading_day]
        if tickers is None:
            return dict(day)
        out: dict[str, float] = {}
        for t in tickers:
            key = t.upper()
            if key not in day:
                raise KeyError(f"MISSING_PRICE:{trading_day}:{key}")
            out[key] = day[key]
        return out

    def price(self, trading_day: str, ticker: str) -> float:
        return self.marks_for(trading_day, [ticker])[ticker.upper()]
