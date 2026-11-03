"""Strict finite-number parsing for fail-closed risk inputs (G1-R3).

Named finite_numbers to avoid shadowing Python's standard library `numbers`.
"""
from __future__ import annotations

import math
from typing import Any


def is_bad_number(x: Any) -> bool:
    if isinstance(x, bool) or x is None:
        return True
    if isinstance(x, str):
        return True
    if not isinstance(x, (int, float)):
        return True
    try:
        return not math.isfinite(float(x))
    except Exception:
        return True


def as_finite(x: Any) -> float | None:
    if is_bad_number(x):
        return None
    return float(x)
