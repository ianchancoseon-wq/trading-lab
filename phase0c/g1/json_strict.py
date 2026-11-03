"""Strict JSON load/dump: reject NaN/Infinity/nonstandard numeric constants and overflow."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


class StrictJSONError(ValueError):
    pass


def _reject_constant(name: str):
    raise StrictJSONError(f"nonstandard_json_constant:{name}")


def _reject_nonfinite(obj: Any, path: str = "$") -> Any:
    """Walk decoded JSON and reject any non-finite float (e.g. 1e999 → Inf)."""
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise StrictJSONError(f"non_finite_float:{path}")
        return obj
    if isinstance(obj, dict):
        return {k: _reject_nonfinite(v, f"{path}.{k}") for k, v in obj.items()}
    if isinstance(obj, list):
        return [_reject_nonfinite(v, f"{path}[{i}]") for i, v in enumerate(obj)]
    return obj


def loads(text: str) -> Any:
    try:
        obj = json.loads(text, parse_constant=_reject_constant)
    except StrictJSONError:
        raise
    except json.JSONDecodeError as e:
        raise StrictJSONError(f"json_decode:{e}") from e
    return _reject_nonfinite(obj)


def load_path(path: Path) -> Any:
    return loads(path.read_text(encoding="utf-8"))


def dumps_strict(obj: Any, **kwargs) -> str:
    clean = _reject_nonfinite(obj)
    return json.dumps(clean, allow_nan=False, **kwargs)
