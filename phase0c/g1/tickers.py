"""Canonical ticker normalization; alias conflicts reject before any merge."""
from __future__ import annotations

import re

_ALIAS_MAP = {
    "BRK/B": "BRK.B",
    "BRK-B": "BRK.B",
    "BRKB": "BRK.B",
    "BF/B": "BF.B",
    "BF-B": "BF.B",
}

_VALID = re.compile(r"^[A-Z][A-Z0-9.]{0,11}$")


def canonicalize_ticker(raw: str) -> tuple[str | None, str | None]:
    if not isinstance(raw, str) or not raw.strip():
        return None, "TICKER_EMPTY"
    t = raw.strip().upper()
    t = _ALIAS_MAP.get(t, t)
    t = t.replace("/", ".").replace("-", ".")
    if not _VALID.match(t):
        return None, "TICKER_INVALID"
    return t, None


def index_by_canonical(mapping: dict) -> tuple[dict | None, list[str]]:
    """Return (canonical_map, errors). On any alias conflict, canonical_map is None (no merge).

    Conflicting raw keys are detected BEFORE uppercase merge. Distinct raw strings that
    normalize to the same canonical ticker are rejected — including case variants
    such as qqq vs QQQ (even when one quantity is zero).
    """
    if not isinstance(mapping, dict):
        return None, ["MISSING_OR_INVALID:mapping"]
    errors: list[str] = []
    owners: dict[str, list[str]] = {}
    for k in mapping.keys():
        raw = str(k)
        canon, err = canonicalize_ticker(raw)
        if err:
            errors.append(f"{err}:{k}")
            continue
        owners.setdefault(canon, []).append(raw)

    for canon, raws in owners.items():
        # Preserve first-seen order; keep case-distinct raw keys as conflicts
        uniq_raw = list(dict.fromkeys(raws))
        if len(uniq_raw) > 1:
            # Conflict BEFORE uppercase merge: any distinct raw key strings → reject
            label = "|".join(sorted(uniq_raw))
            errors.append(f"TICKER_ALIAS_CONFLICT:{label}->{canon}")

    if errors:
        return None, errors

    out: dict = {}
    for k, v in mapping.items():
        canon, err = canonicalize_ticker(str(k))
        if err:
            return None, [f"{err}:{k}"]
        out[canon] = v
    return out, []
