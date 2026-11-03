#!/usr/bin/env python3
"""Deterministic prediction/decision submission validator (G1-R3)."""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _hashutil import content_sha256, verify_hash
from id_registry import IdRegistry
from json_strict import StrictJSONError, load_path
from finite_numbers import as_finite, is_bad_number
from tickers import canonicalize_ticker

PRED_ID_RE = re.compile(r"^PRED-[A-Za-z0-9._-]+$")
DEC_ID_RE = re.compile(r"^DEC-[A-Za-z0-9._-]+$")
SHA_RE = re.compile(r"^[a-f0-9]{64}$")
HORIZON_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PROB_EPS = 1e-9

PRED_REQUIRED = [
    "schema", "id", "strategy_version", "ticker", "baseline_price",
    "baseline_source_tier", "band", "horizon_end", "probs",
    "EVENT_EXPOSED", "knowledge_cutoff_utc", "frozen_at_utc", "content_sha256",
]
DEC_REQUIRED = [
    "schema", "id", "prediction_id", "intent", "size_pct",
    "rationale_digest", "memory_influence", "risk_ack",
    "decided_at_utc", "content_sha256",
]
PRED_ALLOWED = set(PRED_REQUIRED) | {"demo", "notes"}
DEC_ALLOWED = set(DEC_REQUIRED) | {"demo", "notes"}


class ValidationError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def _require_keys(obj: dict, required: list[str], allowed: set[str]) -> None:
    if not isinstance(obj, dict):
        raise ValidationError("INVALID_TYPE", "artifact must be object")
    for k in required:
        if k not in obj:
            raise ValidationError("MISSING_FIELD", f"missing required field '{k}'")
    extra = set(obj.keys()) - allowed
    if extra:
        raise ValidationError("UNEXPECTED_FIELD", f"unexpected fields: {sorted(extra)}")
    if "notes" in obj and not isinstance(obj["notes"], str):
        raise ValidationError("INVALID_TYPE", "notes must be string")


def parse_utc_aware(label: str, s: Any) -> datetime:
    if not isinstance(s, str) or not s:
        raise ValidationError("BAD_TIMESTAMP", f"{label} must be non-empty string")
    raw = s
    if not (raw.endswith("Z") or re.search(r"[+-]\d{2}:\d{2}$", raw)):
        raise ValidationError("TIMESTAMP_NOT_UTC_AWARE", f"{label} must be timezone-aware UTC")
    try:
        norm = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
        dt = datetime.fromisoformat(norm)
    except Exception as e:
        raise ValidationError("BAD_TIMESTAMP", f"{label} not parseable: {e}") from e
    if dt.tzinfo is None:
        raise ValidationError("TIMESTAMP_NOT_UTC_AWARE", f"{label} missing tzinfo")
    return dt.astimezone(timezone.utc)


def validate_prediction(pred: dict, registry: IdRegistry | None = None, *, allow_id_replay: bool = False) -> dict:
    """Returns status dict: {ok notes, replay: identical|none}."""
    _require_keys(pred, PRED_REQUIRED, PRED_ALLOWED)
    if pred.get("schema") != "prediction_v1":
        raise ValidationError("BAD_SCHEMA", "schema must be prediction_v1")
    pid = pred["id"]
    if not isinstance(pid, str) or not PRED_ID_RE.match(pid):
        raise ValidationError("BAD_ID", f"prediction id must match PRED-*: {pid}")
    if not isinstance(pred["strategy_version"], str) or not pred["strategy_version"]:
        raise ValidationError("INVALID_TYPE", "strategy_version must be non-empty string")
    canon, terr = canonicalize_ticker(pred["ticker"])
    if terr:
        raise ValidationError(terr, f"ticker: {pred['ticker']}")
    if pred["ticker"] != canon:
        raise ValidationError("TICKER_NOT_CANONICAL", f"ticker must be canonical '{canon}'")
    px = as_finite(pred["baseline_price"])
    if px is None or px <= 0:
        raise ValidationError("BAD_PRICE", "baseline_price must be finite and > 0")
    if not isinstance(pred["baseline_source_tier"], str) or not pred["baseline_source_tier"]:
        raise ValidationError("INVALID_TYPE", "baseline_source_tier must be non-empty string")
    band = as_finite(pred["band"])
    if band is None or band < 0:
        raise ValidationError("BAD_BAND", "band must be finite and >= 0")
    he = pred["horizon_end"]
    if not isinstance(he, str) or not HORIZON_RE.match(he):
        raise ValidationError("BAD_HORIZON_END", "horizon_end must be YYYY-MM-DD")
    # calendar sanity
    try:
        datetime.strptime(he, "%Y-%m-%d")
    except ValueError as e:
        raise ValidationError("BAD_HORIZON_END", f"horizon_end invalid date: {e}") from e

    probs = pred["probs"]
    if not isinstance(probs, dict) or set(probs.keys()) != {"UP", "FLAT", "DOWN"}:
        raise ValidationError("BAD_PROBS", "probs must have exactly UP, FLAT, DOWN")
    for k in ("UP", "FLAT", "DOWN"):
        if is_bad_number(probs[k]):
            raise ValidationError("BAD_PROB", f"probs.{k} must be finite number")
        v = float(probs[k])
        if v < 0.0 or v > 1.0:
            raise ValidationError("BAD_PROB", f"probs.{k} out of [0,1]")
    s = float(probs["UP"]) + float(probs["FLAT"]) + float(probs["DOWN"])
    if abs(s - 1.0) > PROB_EPS:
        raise ValidationError("PROB_SUM", f"probs must sum to 1.0, got {s}")
    if not isinstance(pred["EVENT_EXPOSED"], bool):
        raise ValidationError("INVALID_TYPE", "EVENT_EXPOSED must be bool")
    if "demo" in pred and not isinstance(pred["demo"], bool):
        raise ValidationError("INVALID_TYPE", "demo must be bool")
    kc = parse_utc_aware("knowledge_cutoff_utc", pred["knowledge_cutoff_utc"])
    fr = parse_utc_aware("frozen_at_utc", pred["frozen_at_utc"])
    if fr < kc:
        raise ValidationError("TIMESTAMP_ORDER", "frozen_at_utc must be >= knowledge_cutoff_utc")
    h = pred["content_sha256"]
    if not isinstance(h, str) or not SHA_RE.match(h):
        raise ValidationError("BAD_HASH", "content_sha256 must be 64 hex chars")
    if not verify_hash(pred):
        raise ValidationError("HASH_MISMATCH", f"content_sha256 mismatch; expected {content_sha256(pred)}")

    replay = "none"
    if registry is not None:
        code = registry.check(pid, h)
        if code == "ID_HASH_CONFLICT":
            raise ValidationError("ID_HASH_CONFLICT", f"frozen id {pid} bound to different content hash")
        if code == "ID_REPLAY_SAME":
            replay = "identical"
            if not allow_id_replay:
                raise ValidationError("ID_REUSE", f"prediction id already frozen: {pid}")
    return {"replay": replay}


def validate_decision(
    dec: dict,
    pred: dict | None = None,
    registry: IdRegistry | None = None,
    *,
    allow_id_replay: bool = False,
) -> dict:
    _require_keys(dec, DEC_REQUIRED, DEC_ALLOWED)
    if dec.get("schema") != "decision_v1":
        raise ValidationError("BAD_SCHEMA", "schema must be decision_v1")
    did = dec["id"]
    if not isinstance(did, str) or not DEC_ID_RE.match(did):
        raise ValidationError("BAD_ID", f"decision id must match DEC-*: {did}")
    pref = dec["prediction_id"]
    if not isinstance(pref, str) or not PRED_ID_RE.match(pref):
        raise ValidationError("BAD_ID", f"prediction_id must match PRED-*: {pref}")
    if did == pref:
        raise ValidationError("ID_COLLISION", "decision.id must != prediction_id")
    intent = dec["intent"]
    if intent not in ("NO_TRADE", "PAPER_BUY", "PAPER_SELL"):
        raise ValidationError("BAD_INTENT", f"invalid intent: {intent}")
    size = as_finite(dec["size_pct"])
    if size is None or size < 0 or size > 100:
        raise ValidationError("BAD_SIZE", "size_pct must be finite in [0,100]")
    if intent == "NO_TRADE" and size != 0:
        raise ValidationError("SIZE_NO_TRADE", "NO_TRADE requires size_pct == 0")
    if intent != "NO_TRADE" and size <= 0:
        raise ValidationError("SIZE_TRADE", f"{intent} requires size_pct > 0")
    if not isinstance(dec["rationale_digest"], str) or not dec["rationale_digest"]:
        raise ValidationError("INVALID_TYPE", "rationale_digest must be non-empty string")
    mi = dec["memory_influence"]
    if not isinstance(mi, list) or any(not isinstance(x, str) for x in mi):
        raise ValidationError("INVALID_TYPE", "memory_influence must be list[str]")
    if not isinstance(dec["risk_ack"], bool):
        raise ValidationError("INVALID_TYPE", "risk_ack must be bool")
    if "demo" in dec and not isinstance(dec["demo"], bool):
        raise ValidationError("INVALID_TYPE", "demo must be bool")
    parse_utc_aware("decided_at_utc", dec["decided_at_utc"])
    h = dec["content_sha256"]
    if not isinstance(h, str) or not SHA_RE.match(h):
        raise ValidationError("BAD_HASH", "content_sha256 must be 64 hex chars")
    if not verify_hash(dec):
        raise ValidationError("HASH_MISMATCH", f"content_sha256 mismatch; expected {content_sha256(dec)}")

    replay = "none"
    if registry is not None:
        code = registry.check(did, h)
        if code == "ID_HASH_CONFLICT":
            raise ValidationError("ID_HASH_CONFLICT", f"frozen id {did} bound to different content hash")
        if code == "ID_REPLAY_SAME":
            replay = "identical"
            if not allow_id_replay:
                raise ValidationError("ID_REUSE", f"decision id already frozen: {did}")

    if pred is not None:
        if pref != pred.get("id"):
            raise ValidationError("PRED_REF_MISMATCH", f"decision.prediction_id != prediction.id")
        pred_body = {k: v for k, v in pred.items() if k != "content_sha256"}
        dec_body = {k: v for k, v in dec.items() if k != "content_sha256"}
        if pred_body == dec_body:
            raise ValidationError("CLONE_BODY", "decision body identical to prediction body")
        for banned in ("probs", "baseline_price", "frozen_at_utc", "EVENT_EXPOSED", "horizon_end"):
            if banned in dec:
                raise ValidationError("PRED_FIELDS_IN_DEC", f"decision must not carry '{banned}'")
        fr = parse_utc_aware("frozen_at_utc", pred["frozen_at_utc"])
        de = parse_utc_aware("decided_at_utc", dec["decided_at_utc"])
        if de < fr:
            raise ValidationError("TIMESTAMP_ORDER", "decided_at_utc must be >= prediction.frozen_at_utc")
        if bool(pred.get("demo")) != bool(dec.get("demo")) and (
            pred.get("demo") is True or dec.get("demo") is True
        ):
            raise ValidationError("DEMO_FLAG_MISMATCH", "prediction.demo and decision.demo must agree when set")
    return {"replay": replay}


def validate_bundle(
    pred: dict,
    dec: dict,
    registry: IdRegistry | None = None,
    *,
    allow_id_replay: bool = False,
) -> dict:
    errors: list[dict] = []
    pred_meta = {"replay": "none"}
    dec_meta = {"replay": "none"}
    try:
        pred_meta = validate_prediction(pred, registry, allow_id_replay=allow_id_replay)
    except ValidationError as e:
        errors.append({"code": e.code, "message": e.message, "artifact": "prediction"})
    try:
        dec_meta = validate_decision(dec, pred if not errors else None, registry, allow_id_replay=allow_id_replay)
    except ValidationError as e:
        errors.append({"code": e.code, "message": e.message, "artifact": "decision"})
    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "prediction_replay": pred_meta.get("replay", "none"),
        "decision_replay": dec_meta.get("replay", "none"),
    }


def main(argv: list[str] | None = None) -> int:
    import json

    p = argparse.ArgumentParser()
    p.add_argument("--prediction", required=True, type=Path)
    p.add_argument("--decision", required=True, type=Path)
    p.add_argument("--registry", type=Path, default=None)
    p.add_argument("--allow-id-replay", action="store_true")
    args = p.parse_args(argv)
    try:
        pred = load_path(args.prediction)
        dec = load_path(args.decision)
    except StrictJSONError as e:
        print(json.dumps({"ok": False, "errors": [{"code": "STRICT_JSON", "message": str(e)}]}, indent=2))
        return 1
    reg = IdRegistry(args.registry) if args.registry else None
    result = validate_bundle(pred, dec, reg, allow_id_replay=args.allow_id_replay)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
