"""Content hashing: sha256 over body excluding content_sha256 (canonical JSON)."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


def canonical_bytes(obj: Mapping[str, Any]) -> bytes:
    body = {k: v for k, v in obj.items() if k != "content_sha256"}
    # allow_nan=False rejects Inf/NaN produced by overflow before hashing
    return json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def content_sha256(obj: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def attach_hash(obj: dict) -> dict:
    out = dict(obj)
    out.pop("content_sha256", None)
    out["content_sha256"] = content_sha256(out)
    return out


def verify_hash(obj: Mapping[str, Any]) -> bool:
    claimed = obj.get("content_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        return False
    return claimed == content_sha256(obj)
