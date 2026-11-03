#!/usr/bin/env python3
"""Deterministic non-LLM Risk Gate — G1-R4.

Production entry: evaluate() — trusted policy file + fixed persistent ID registry.
Test/fixture entry: evaluate_for_tests() — separate, not used by production CLI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import frozen_limits as FL
from _hashutil import attach_hash
from finite_numbers import as_finite, is_bad_number
from id_registry import IdRegistry
from json_strict import StrictJSONError, dumps_strict, load_path
from submit_validator import validate_bundle
from tickers import canonicalize_ticker, index_by_canonical

ROOT = Path(__file__).resolve().parent
DEFAULT_POLICY_PATH = ROOT / FL.APPROVED_POLICY_PATH_NAME
DEFAULT_REGISTRY_PATH = ROOT / "frozen_id_registry.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sanitize_snapshots(snapshots: dict) -> dict:
    """Ensure gate diagnostics contain no NaN/Inf (replace with None + flag)."""
    out: dict[str, Any] = {}
    flags: list[str] = []

    def walk(x: Any, path: str) -> Any:
        if isinstance(x, float) and not math.isfinite(x):
            flags.append(path)
            return None
        if isinstance(x, dict):
            return {k: walk(v, f"{path}.{k}") for k, v in x.items()}
        if isinstance(x, list):
            return [walk(v, f"{path}[{i}]") for i, v in enumerate(x)]
        return x

    for k, v in snapshots.items():
        out[k] = walk(v, k)
    if flags:
        out["non_finite_fields_elided"] = flags
    return out


def _result(gate_id, decision, prediction, verdict, reason_codes, policy, snapshots, evaluated_at_utc, notes=None) -> dict:
    seen = set()
    ordered = []
    for c in reason_codes:
        if c not in seen:
            seen.add(c)
            ordered.append(c)
    body = {
        "schema": "gate_result_v1",
        "id": gate_id or f"GATE-{(decision or {}).get('id', 'UNKNOWN')}",
        "decision_id": (decision or {}).get("id"),
        "prediction_id": (prediction or {}).get("id"),
        "verdict": verdict,
        "reason_codes": ordered,
        "risk_policy_version": (policy or {}).get("version"),
        "lab_mode": (policy or {}).get("lab_mode"),
        "snapshots": _sanitize_snapshots(snapshots if isinstance(snapshots, dict) else {}),
        "evaluated_at_utc": evaluated_at_utc or _utc_now(),
    }
    if notes:
        body["notes"] = notes
    return attach_hash(body)


def policy_content_sha256(policy: dict) -> str:
    canon = json.dumps(policy, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(canon).hexdigest()


def load_approved_policy(path: Path | None = None) -> dict:
    p = path or DEFAULT_POLICY_PATH
    policy = load_path(p)
    if not isinstance(policy, dict):
        raise StrictJSONError("policy_not_object")
    return policy


def bind_approved_policy(policy: dict) -> list[str]:
    codes: list[str] = []
    if not isinstance(policy, dict):
        return ["POLICY_MISSING"]
    if "founder_override" in policy or policy.get("allow_hard_stop_bypass") is True:
        codes.append("POLICY_CONTAINS_FORBIDDEN_OVERRIDE")
    ver = policy.get("version")
    if ver != FL.APPROVED_POLICY_VERSION:
        codes.append("UNAUTHORIZED_POLICY_VERSION")
    try:
        h = policy_content_sha256(policy)
    except (ValueError, TypeError):
        codes.append("POLICY_CONTENT_NOT_SERIALIZABLE")
        return codes
    if h != FL.APPROVED_POLICY_SHA256:
        codes.append("UNAUTHORIZED_POLICY_CONTENT")
    # numeric hard limits must still match constants
    checks = [
        ("max_size_pct_per_name", FL.MAX_SIZE_PCT_PER_NAME),
        ("max_daily_loss_pct", FL.MAX_DAILY_LOSS_PCT),
        ("max_peak_drawdown_pct", FL.MAX_PEAK_DRAWDOWN_PCT),
        ("max_aggregate_long_exposure_pct", FL.MAX_AGGREGATE_LONG_EXPOSURE_PCT),
    ]
    for key, expected in checks:
        got = as_finite(policy.get(key))
        if got is None or abs(got - expected) > 1e-12:
            codes.append(f"UNAUTHORIZED_POLICY_MODIFICATION:{key}")
    if policy.get("allow_short") is not False:
        codes.append("UNAUTHORIZED_POLICY_MODIFICATION:allow_short")
    if policy.get("allow_leverage") is not False:
        codes.append("UNAUTHORIZED_POLICY_MODIFICATION:allow_leverage")
    if policy.get("require_whole_shares") is not True:
        codes.append("UNAUTHORIZED_POLICY_MODIFICATION:require_whole_shares")
    lab = policy.get("lab_mode")
    if lab not in FL.APPROVED_LAB_MODES_PRODUCTION:
        # production bind rejects FIXTURE_EVAL here; tests use evaluate_for_tests
        codes.append("POLICY_LAB_MODE_FORBIDDEN_OR_UNKNOWN")
    return codes


def resolve_pending_snapshot(
    portfolio: dict,
    caller_pending: list | None,
    reason_codes: list[str],
) -> list[dict] | None:
    """Single trusted pending snapshot. Contradictions fail closed.

    Rules:
    - Portfolio must contain pending_intents key when portfolio path is used (list, maybe empty).
    - If caller_pending is None: use portfolio pending.
    - If caller_pending is provided: must deep-equal portfolio pending; else PENDING_SNAPSHOT_CONFLICT.
      (Empty caller list cannot hide non-empty portfolio commitments.)
    """
    if "pending_intents" not in portfolio:
        reason_codes.append("MISSING_OR_INVALID:pending_intents")
        return None
    port_pending = portfolio.get("pending_intents")
    if not isinstance(port_pending, list):
        reason_codes.append("MISSING_OR_INVALID:pending_intents")
        return None

    if caller_pending is not None:
        if not isinstance(caller_pending, list):
            reason_codes.append("PENDING_CALLER_NOT_LIST")
            return None
        if caller_pending != port_pending:
            reason_codes.append("PENDING_SNAPSHOT_CONFLICT")
            return None
        chosen = caller_pending
    else:
        chosen = port_pending

    return _validate_pending_list(chosen, reason_codes)


def _validate_pending_list(pending_intents: list, reason_codes: list[str]) -> list[dict] | None:
    out: list[dict] = []
    for i, p in enumerate(pending_intents):
        if not isinstance(p, dict):
            reason_codes.append(f"PENDING_MALFORMED:{i}")
            continue
        for req in ("ticker", "status", "intent", "size_pct"):
            if req not in p:
                reason_codes.append(f"PENDING_MISSING_FIELD:{i}:{req}")
        status = p.get("status")
        if status not in ("ACCEPT", "PENDING", "REJECT"):
            reason_codes.append(f"PENDING_BAD_STATUS:{i}")
        # Unknown statuses already covered; reject other future tokens explicitly
        intent = p.get("intent")
        if intent not in ("NO_TRADE", "PAPER_BUY", "PAPER_SELL"):
            reason_codes.append(f"PENDING_BAD_INTENT:{i}")
        canon, err = canonicalize_ticker(str(p.get("ticker", "")))
        if err:
            reason_codes.append(f"PENDING_TICKER:{err}:{i}")
            continue
        if str(p.get("ticker")) != canon:
            reason_codes.append(f"PENDING_TICKER_NOT_CANONICAL:{i}")
        sp = as_finite(p.get("size_pct"))
        if sp is None or sp < 0 or sp > 100:
            reason_codes.append(f"PENDING_BAD_SIZE:{i}")
        for opt in ("shares", "notional", "reserved_cash", "mark"):
            if opt in p and is_bad_number(p[opt]):
                reason_codes.append(f"PENDING_BAD_NUMBER:{i}:{opt}")
        cleaned = dict(p)
        cleaned["_canon_ticker"] = canon
        out.append(cleaned)

    if any(
        c.startswith("PENDING_") or c.startswith("MISSING_OR_INVALID:pending")
        for c in reason_codes
    ):
        return None
    return out


def _pending_buy_reservation(
    pending: list[dict],
    equity: float,
    marks_f: dict[str, float],
    reason_codes: list[str],
    snapshots: dict,
) -> tuple[float, dict[str, float]]:
    """Conservatively reserve cash for outstanding ACCEPT and PENDING PAPER_BUY.

    Do NOT credit PENDING/ACCEPT sells as filled exposure reductions.
    Explicit shares/notional must agree with size_pct — never silently override size_pct.
    """
    reserved_cash = 0.0
    for p in pending:
        status = p.get("status")
        if status not in ("ACCEPT", "PENDING"):
            continue
        if p.get("intent") != "PAPER_BUY":
            # Sells (PENDING or ACCEPT) are never treated as filled reductions
            continue
        pt = p["_canon_ticker"]
        if pt not in marks_f:
            reason_codes.append(f"PENDING_MARK_MISSING:{pt}")
            continue
        mpx = marks_f[pt]
        psp = float(p["size_pct"])
        notional_from_size = equity * (psp / 100.0)
        expected_shares = (
            math.floor(notional_from_size / mpx + 1e-12)
            if FL.REQUIRE_WHOLE_SHARES
            else notional_from_size / mpx
        )
        if FL.REQUIRE_WHOLE_SHARES:
            expected_shares = int(expected_shares)

        if "mark" in p:
            pm = as_finite(p["mark"])
            if pm is None or abs(pm - mpx) > FL.NOTIONAL_EPS:
                reason_codes.append(f"PENDING_MARK_INCONSISTENT:{pt}")
                continue

        sh_i = expected_shares
        if "shares" in p:
            sh = as_finite(p["shares"])
            if sh is None or sh < 0 or (FL.REQUIRE_WHOLE_SHARES and abs(sh - round(sh)) > 1e-9):
                reason_codes.append(f"PENDING_SHARES_INVALID:{pt}")
                continue
            sh_i = int(round(sh)) if FL.REQUIRE_WHOLE_SHARES else sh
            if FL.REQUIRE_WHOLE_SHARES:
                if int(expected_shares) != sh_i:
                    reason_codes.append(f"PENDING_SHARES_SIZE_INCONSISTENT:{pt}")
                    continue
            else:
                if abs(float(expected_shares) - float(sh_i)) > 1e-9:
                    reason_codes.append(f"PENDING_SHARES_SIZE_INCONSISTENT:{pt}")
                    continue

        cost = float(sh_i) * mpx
        expected_cost = float(expected_shares) * mpx

        if "notional" in p:
            notion = as_finite(p["notional"])
            if notion is None:
                reason_codes.append(f"PENDING_NOTIONAL_INCONSISTENT:{pt}")
                continue
            # Must match shares*mark when shares present, and size-derived whole-share cost
            if abs(notion - cost) > FL.NOTIONAL_EPS:
                reason_codes.append(f"PENDING_NOTIONAL_INCONSISTENT:{pt}")
                continue
            if abs(notion - expected_cost) > FL.NOTIONAL_EPS:
                # size_pct and notional disagree even if shares matched somehow
                reason_codes.append(f"PENDING_FIELDS_INCONSISTENT:{pt}")
                continue

        # Cross-check: if both shares and notional present, they already matched cost;
        # size_pct remains the authority for expected_shares.
        if "shares" in p and "notional" in p and "size_pct" in p:
            if abs(float(sh_i) * mpx - notional_from_size) > max(mpx, FL.NOTIONAL_EPS) and int(expected_shares) != int(sh_i):
                reason_codes.append(f"PENDING_FIELDS_INCONSISTENT:{pt}")
                continue

        reserved_cash += float(cost)
        snapshots.setdefault("_pending_buy_adds", {})
        snapshots["_pending_buy_adds"][pt] = snapshots["_pending_buy_adds"].get(pt, 0) + float(sh_i)

    return reserved_cash, snapshots.get("_pending_buy_adds", {})


def _marked_equity_contract(cash, holdings, marks, reported_equity, reported_unrealized, reason_codes, snapshots):
    market_value = 0.0
    for t, qty in holdings.items():
        mark = marks.get(t)
        if mark is None:
            reason_codes.append(f"MISSING_OR_INVALID:marks.{t}")
            continue
        market_value += qty * mark
    marked = cash + market_value
    snapshots["market_value"] = market_value
    snapshots["marked_equity"] = marked
    snapshots["reported_equity"] = reported_equity
    snapshots["reported_unrealized_pnl"] = reported_unrealized
    if abs(reported_equity - marked) > FL.EQUITY_EPS:
        reason_codes.append("EQUITY_MARK_MISMATCH")
    if abs(reported_unrealized) > FL.EQUITY_EPS:
        alt = marked - reported_unrealized
        if abs(reported_equity - alt) <= FL.EQUITY_EPS and abs(reported_equity - marked) > FL.EQUITY_EPS:
            reason_codes.append("UNREALIZED_DOUBLE_COUNT")


def _ensure_trusted_registry() -> IdRegistry:
    """Open the fixed production registry path (create empty file if needed)."""
    DEFAULT_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DEFAULT_REGISTRY_PATH.exists():
        DEFAULT_REGISTRY_PATH.write_text("", encoding="utf-8")
    return IdRegistry(DEFAULT_REGISTRY_PATH)


def evaluate(
    prediction: dict,
    decision: dict,
    portfolio: dict | None,
    pending_intents: list | None,
    gate_id: str | None = None,
    evaluated_at_utc: str | None = None,
    *,
    policy_path: Path | None = None,
) -> dict:
    """Production Risk Gate entry.

    Always binds the trusted persistent registry at DEFAULT_REGISTRY_PATH.
    Caller cannot select an alternate registry path. Policy file is content-hash bound.
    """
    try:
        policy = load_approved_policy(policy_path)
    except Exception as e:
        return _result(gate_id, decision or {}, prediction or {}, "REJECT",
                       ["POLICY_LOAD_FAILED", type(e).__name__], {}, {}, evaluated_at_utc,
                       notes=str(e)[:200])
    registry = _ensure_trusted_registry()
    return _evaluate_inner(
        prediction, decision, portfolio, pending_intents, policy, gate_id, evaluated_at_utc,
        registry=registry,
        fixture_mode=False,
    )



def _commit_ids_or_reject(
    gate_id, decision, prediction, policy, snapshots, evaluated_at_utc, reason_ok_codes, registry, notes=None
):
    """On ACCEPT, atomically bind PRED/DEC IDs. Conflict → REJECT. Identical → keep ACCEPT."""
    if registry is None:
        # test entry without registry: accept without persistence
        return _result(gate_id, decision, prediction, "ACCEPT", reason_ok_codes, policy, snapshots, evaluated_at_utc, notes=notes)
    status, detail = registry.check_and_register(
        [
            (prediction["id"], prediction["content_sha256"]),
            (decision["id"], decision["content_sha256"]),
        ]
    )
    if status == "ID_HASH_CONFLICT":
        codes = ["ID_HASH_CONFLICT"]
        if detail.get("id"):
            codes.append(f"ID_HASH_CONFLICT:{detail['id']}")
        return _result(gate_id, decision, prediction, "REJECT", codes, policy, snapshots, evaluated_at_utc,
                       notes="frozen id rebound to different content hash")
    codes = list(reason_ok_codes)
    if status == "ok_replay" and "OK_IDEMPOTENT_REPLAY" not in codes:
        # Should not normally happen on fresh accept path; keep codes as-is
        pass
    return _result(gate_id, decision, prediction, "ACCEPT", codes, policy, snapshots, evaluated_at_utc, notes=notes)

def evaluate_for_tests(
    prediction: dict,
    decision: dict,
    portfolio: dict | None,
    pending_intents: list | None,
    policy: dict,
    gate_id: str | None = None,
    evaluated_at_utc: str | None = None,
    *,
    registry: IdRegistry | None = None,
    allow_fixture_eval: bool = False,
) -> dict:
    """Separate test entry point. Not wired to production CLI."""
    return _evaluate_inner(
        prediction, decision, portfolio, pending_intents, policy, gate_id, evaluated_at_utc,
        registry=registry,
        fixture_mode=allow_fixture_eval,
        test_entry=True,
    )


def _evaluate_inner(
    prediction, decision, portfolio, pending_intents, policy, gate_id, evaluated_at_utc,
    *, registry, fixture_mode: bool, test_entry: bool = False,
) -> dict:
    try:
        return _evaluate_core(
            prediction, decision, portfolio, pending_intents, policy, gate_id, evaluated_at_utc,
            registry=registry, fixture_mode=fixture_mode, test_entry=test_entry,
        )
    except Exception as e:
        return _result(
            gate_id, decision if isinstance(decision, dict) else {},
            prediction if isinstance(prediction, dict) else {},
            "REJECT", ["UNCAUGHT_EXCEPTION", type(e).__name__],
            policy if isinstance(policy, dict) else {},
            {"exception": str(e)[:500]}, evaluated_at_utc,
            notes="fail-closed: unexpected exception",
        )


def _evaluate_core(
    prediction, decision, portfolio, pending_intents, policy, gate_id, evaluated_at_utc,
    *, registry, fixture_mode, test_entry,
) -> dict:
    reason_codes: list[str] = []
    snapshots: dict[str, Any] = {}

    # Policy binding
    if test_entry and fixture_mode:
        # Fixture policy: must still match numeric hard limits; version may be FIXTURE labeled
        # but cannot weaken caps. Content hash may differ; enforce constants.
        if policy.get("lab_mode") != FL.FIXTURE_LAB_MODE:
            reason_codes.append("FIXTURE_MODE_REQUIRES_FIXTURE_LAB_MODE")
        for key, expected in [
            ("max_size_pct_per_name", FL.MAX_SIZE_PCT_PER_NAME),
            ("max_daily_loss_pct", FL.MAX_DAILY_LOSS_PCT),
            ("max_peak_drawdown_pct", FL.MAX_PEAK_DRAWDOWN_PCT),
            ("max_aggregate_long_exposure_pct", FL.MAX_AGGREGATE_LONG_EXPOSURE_PCT),
        ]:
            got = as_finite(policy.get(key))
            if got is None or abs(got - expected) > 1e-12:
                reason_codes.append(f"UNAUTHORIZED_POLICY_MODIFICATION:{key}")
        if policy.get("allow_short") is not False or policy.get("allow_leverage") is not False:
            reason_codes.append("UNAUTHORIZED_POLICY_MODIFICATION:short_or_leverage")
        if policy.get("require_whole_shares") is not True:
            reason_codes.append("UNAUTHORIZED_POLICY_MODIFICATION:require_whole_shares")
        if "founder_override" in policy or policy.get("allow_hard_stop_bypass") is True:
            reason_codes.append("POLICY_CONTAINS_FORBIDDEN_OVERRIDE")
        if prediction.get("demo") is not True or decision.get("demo") is not True:
            reason_codes.append("FIXTURE_REQUIRES_DEMO_FLAGS")
    else:
        reason_codes.extend(bind_approved_policy(policy))

    if reason_codes:
        return _result(gate_id, decision, prediction, "REJECT", reason_codes, policy, snapshots, evaluated_at_utc,
                       notes="fail-closed: policy/fixture binding failed")

    # Registry-enforced bundle validation (required on production; tests should pass registry too)
    if registry is None and not test_entry:
        return _result(gate_id, decision, prediction, "REJECT", ["REGISTRY_REQUIRED"], policy, snapshots, evaluated_at_utc)

    # Idempotent identical replay: allow_id_replay to detect identical vs conflict
    bundle = validate_bundle(prediction, decision, registry, allow_id_replay=True)
    if not bundle["ok"]:
        for e in bundle["errors"]:
            reason_codes.append(f"BUNDLE_{e['code']}")
        return _result(gate_id, decision, prediction, "REJECT", reason_codes, policy, snapshots, evaluated_at_utc,
                       notes="fail-closed: invalid submission bundle")

    identical = bundle["prediction_replay"] == "identical" and bundle["decision_replay"] == "identical"
    pred_only_new = bundle["prediction_replay"] == "none" and bundle["decision_replay"] == "none"
    # Conflicting reuse already raised as errors. Mixed replay (one identical one new) is reject.
    if bundle["prediction_replay"] != bundle["decision_replay"]:
        # allow pred identical + new dec (multiple decisions per pred) 
        if not (bundle["prediction_replay"] in ("identical", "none") and bundle["decision_replay"] == "none"):
            if bundle["decision_replay"] == "identical" and bundle["prediction_replay"] == "none":
                reason_codes.append("ID_REPLAY_INCONSISTENT")
                return _result(gate_id, decision, prediction, "REJECT", reason_codes, policy, snapshots, evaluated_at_utc)

    lab_mode = policy["lab_mode"]
    intent = decision["intent"]
    size_pct = float(decision["size_pct"])
    ticker, terr = canonicalize_ticker(prediction["ticker"])
    if terr or prediction["ticker"] != ticker:
        reason_codes.append(terr or "TICKER_NOT_CANONICAL")
        return _result(gate_id, decision, prediction, "REJECT", reason_codes, policy, snapshots, evaluated_at_utc)

    if intent != "NO_TRADE" and lab_mode in FL.APPROVED_LAB_MODES_PRODUCTION:
        reason_codes.append("LAB_MODE_BLOCKS_TRADE")
    if intent != "NO_TRADE" and not decision.get("risk_ack", False):
        reason_codes.append("RISK_ACK_REQUIRED")
    if size_pct > FL.MAX_SIZE_PCT_PER_NAME + 1e-12:
        reason_codes.append("SIZE_PCT_EXCEEDS_PER_NAME_CAP")

    # Identical full replay → explicit idempotent accept (no new trade effect)
    if identical:
        snapshots["idempotent"] = True
        if reason_codes:
            return _result(gate_id, decision, prediction, "REJECT", reason_codes, policy, snapshots, evaluated_at_utc)
        return _commit_ids_or_reject(
            gate_id, decision, prediction, policy, snapshots, evaluated_at_utc,
            ["OK_IDEMPOTENT_REPLAY"], registry,
            notes="identical PRED+DEC content replay; no new trade accepted",
        )

    if intent == "NO_TRADE" and lab_mode in FL.APPROVED_LAB_MODES_PRODUCTION:
        if reason_codes:
            return _result(gate_id, decision, prediction, "REJECT", reason_codes, policy, snapshots, evaluated_at_utc)
        return _commit_ids_or_reject(
            gate_id, decision, prediction, policy, snapshots, evaluated_at_utc,
            ["OK_NO_TRADE"], registry,
        )

    if portfolio is None or not isinstance(portfolio, dict):
        reason_codes.append("MISSING_PORTFOLIO")
        return _result(gate_id, decision, prediction, "REJECT", reason_codes, policy, snapshots, evaluated_at_utc)

    cash = as_finite(portfolio.get("cash"))
    equity = as_finite(portfolio.get("equity"))
    peak_equity = as_finite(portfolio.get("peak_equity"))
    day_start_equity = as_finite(portfolio.get("day_start_equity"))
    unrealized = as_finite(portfolio.get("unrealized_pnl"))
    for label, val in [("cash", cash), ("equity", equity), ("peak_equity", peak_equity),
                       ("day_start_equity", day_start_equity), ("unrealized_pnl", unrealized)]:
        if val is None:
            reason_codes.append(f"MISSING_OR_INVALID:{label}")
    if cash is not None and cash < 0:
        reason_codes.append("NEGATIVE_CASH")

    holdings_raw = portfolio.get("holdings")
    marks_raw = portfolio.get("marks")
    if not isinstance(holdings_raw, dict):
        reason_codes.append("MISSING_OR_INVALID:holdings")
        holdings_map, h_err = None, []
    else:
        holdings_map, h_err = index_by_canonical(holdings_raw)
    if not isinstance(marks_raw, dict):
        reason_codes.append("MISSING_OR_INVALID:marks")
        marks_map, m_err = None, []
    else:
        marks_map, m_err = index_by_canonical(marks_raw)
    reason_codes.extend(h_err)
    reason_codes.extend(m_err)
    if holdings_map is None or marks_map is None:
        return _result(gate_id, decision, prediction, "REJECT", reason_codes, policy, snapshots, evaluated_at_utc,
                       notes="fail-closed: holdings/marks alias or type failure before merge")

    holdings_f: dict[str, float] = {}
    marks_f: dict[str, float] = {}
    for t, q in holdings_map.items():
        qf = as_finite(q)
        if qf is None:
            reason_codes.append(f"MISSING_OR_INVALID:holdings.{t}")
        elif qf < 0 and not FL.ALLOW_SHORT:
            reason_codes.append(f"NEGATIVE_HOLDING:{t}")
        elif abs(qf - round(qf)) > 1e-9 and FL.REQUIRE_WHOLE_SHARES:
            reason_codes.append(f"FRACTIONAL_HOLDING:{t}")
        else:
            holdings_f[t] = float(qf)
    for t, px in marks_map.items():
        pf = as_finite(px)
        if pf is None or pf <= 0:
            reason_codes.append(f"MISSING_OR_INVALID:marks.{t}")
        else:
            marks_f[t] = pf

    pending = resolve_pending_snapshot(portfolio, pending_intents, reason_codes)
    if pending is None or cash is None or equity is None or peak_equity is None or day_start_equity is None or unrealized is None:
        return _result(gate_id, decision, prediction, "REJECT", reason_codes, policy, snapshots, evaluated_at_utc,
                       notes="fail-closed: critical risk/pending data")

    # any remaining critical codes
    if any(c.startswith("MISSING_OR_INVALID") or c.startswith("NEGATIVE_") or c.startswith("FRACTIONAL_")
           or c.startswith("TICKER_") for c in reason_codes):
        return _result(gate_id, decision, prediction, "REJECT", reason_codes, policy, snapshots, evaluated_at_utc)

    snapshots.update({
        "cash": cash, "equity": equity, "peak_equity": peak_equity,
        "day_start_equity": day_start_equity, "unrealized_pnl": unrealized,
        "holdings": dict(holdings_f), "pending_intents_count": len(pending),
    })
    _marked_equity_contract(cash, holdings_f, marks_f, equity, unrealized, reason_codes, snapshots)
    if "EQUITY_MARK_MISMATCH" in reason_codes or "UNREALIZED_DOUBLE_COUNT" in reason_codes:
        return _result(gate_id, decision, prediction, "REJECT", reason_codes, policy, snapshots, evaluated_at_utc)

    if day_start_equity > 0:
        daily_loss_pct = max(0.0, (day_start_equity - equity) / day_start_equity * 100.0)
        snapshots["daily_loss_pct"] = daily_loss_pct
        if daily_loss_pct >= FL.MAX_DAILY_LOSS_PCT:
            reason_codes.append("DAILY_LOSS_STOP")
    else:
        reason_codes.append("MISSING_OR_INVALID:day_start_equity")
    if peak_equity > 0:
        dd_pct = max(0.0, (peak_equity - equity) / peak_equity * 100.0)
        snapshots["drawdown_pct"] = dd_pct
        if dd_pct >= FL.MAX_PEAK_DRAWDOWN_PCT:
            reason_codes.append("PEAK_DRAWDOWN_STOP")
    else:
        reason_codes.append("MISSING_OR_INVALID:peak_equity")

    reserved_cash, buy_adds = _pending_buy_reservation(pending, equity, marks_f, reason_codes, snapshots)
    snapshots.pop("_pending_buy_adds", None)
    snapshots["reserved_cash"] = reserved_cash
    snapshots["pending_buy_adds"] = buy_adds
    available_cash = cash - reserved_cash
    snapshots["available_cash"] = available_cash
    if available_cash < -1e-9:
        reason_codes.append("PENDING_CASH_OVERRESERVE")

    # Projected exposure: current holdings + pending BUY adds only (sells not credited)
    projected = dict(holdings_f)
    for t, sh in buy_adds.items():
        projected[t] = projected.get(t, 0.0) + sh
    snapshots["projected_holdings_after_pending_buys"] = projected
    proj_long = sum(q * marks_f[t] for t, q in projected.items() if q > 0 and t in marks_f)
    for t, q in projected.items():
        if q > 0 and t not in marks_f:
            reason_codes.append(f"MISSING_OR_INVALID:marks.{t}")
    proj_exp = (proj_long / equity * 100.0) if equity > 0 else float("inf")
    if math.isfinite(proj_exp):
        snapshots["projected_long_exposure_pct_after_pending"] = proj_exp
        if proj_exp > FL.MAX_AGGREGATE_LONG_EXPOSURE_PCT + 1e-9:
            reason_codes.append("PENDING_POST_EXPOSURE_CAP")
    else:
        reason_codes.append("PROJECTED_EXPOSURE_NON_FINITE")

    # G1-R4: per-name 20% hard cap on COMPLETE projected portfolio (every symbol)
    projected_name_pct: dict[str, float] = {}
    name_cap_violators: list[str] = []
    for t, q in projected.items():
        if q <= 0:
            continue
        if t not in marks_f:
            continue
        if equity <= 0:
            reason_codes.append("PROJECTED_NAME_EXPOSURE_NON_FINITE")
            continue
        pct = (q * marks_f[t] / equity) * 100.0
        if not math.isfinite(pct):
            reason_codes.append(f"PROJECTED_NAME_EXPOSURE_NON_FINITE:{t}")
            continue
        projected_name_pct[t] = pct
        if pct > FL.MAX_SIZE_PCT_PER_NAME + 1e-9:
            name_cap_violators.append(t)
    name_cap_violators = sorted(set(name_cap_violators))
    snapshots["projected_name_pct_after_pending_buys"] = projected_name_pct
    snapshots["name_cap_violators_pre_trade"] = list(name_cap_violators)

    if intent == "NO_TRADE":
        if reason_codes:
            return _result(gate_id, decision, prediction, "REJECT", reason_codes, policy, snapshots, evaluated_at_utc)
        return _commit_ids_or_reject(
            gate_id, decision, prediction, policy, snapshots, evaluated_at_utc,
            ["OK_NO_TRADE"], registry,
        )

    if ticker not in marks_f:
        reason_codes.append(f"MISSING_OR_INVALID:marks.{ticker}")
        return _result(gate_id, decision, prediction, "REJECT", reason_codes, policy, snapshots, evaluated_at_utc)
    mark_f = marks_f[ticker]
    snapshots["mark_price"] = mark_f
    snapshots["baseline_price"] = float(prediction["baseline_price"])

    notional = equity * (size_pct / 100.0)
    raw_shares = notional / mark_f
    shares = int(math.floor(raw_shares + 1e-12)) if FL.REQUIRE_WHOLE_SHARES else raw_shares
    snapshots["raw_shares"] = raw_shares
    snapshots["whole_shares"] = shares
    if shares <= 0:
        reason_codes.append("ZERO_SHARE_TRADE")
        return _result(gate_id, decision, prediction, "REJECT", reason_codes, policy, snapshots, evaluated_at_utc,
                       notes="zero-share PAPER_BUY/SELL rejected")

    trade_notional = shares * mark_f
    snapshots["intended_shares"] = shares
    snapshots["intended_notional"] = trade_notional
    pos = projected.get(ticker, 0.0)
    snapshots["existing_position_after_pending_buys"] = pos

    if intent == "PAPER_BUY":
        if trade_notional > available_cash + 1e-9:
            reason_codes.append("INSUFFICIENT_CASH")
        post_pos = pos + shares
    else:
        # SELL uses actual holdings (not assuming pending sells filled)
        actual_pos = holdings_f.get(ticker, 0.0)
        snapshots["existing_position_actual"] = actual_pos
        if shares > actual_pos + 1e-12:
            reason_codes.append("SELL_EXCEEDS_LONG_NO_SHORT")
        post_pos = actual_pos - shares

    pending_same = [
        p for p in pending
        if p.get("status") in ("ACCEPT", "PENDING") and p.get("_canon_ticker") == ticker
    ]
    snapshots["pending_same_ticker"] = len(pending_same)
    if pending_same:
        reason_codes.append("PENDING_INTENT_CONFLICT")

    # G1-R4: risk-increasing PAPER_BUY rejected when ANY projected name already > 20%
    if intent == "PAPER_BUY":
        for t in name_cap_violators:
            code = f"NAME_EXPOSURE_CAP:{t}"
            if code not in reason_codes:
                reason_codes.append(code)

    # Post-trade: preserve ALL existing positions; update traded ticker
    post_holdings = dict(holdings_f)
    # include pending buy adds for exposure view of other symbols
    for t, sh in buy_adds.items():
        if t != ticker:
            post_holdings[t] = post_holdings.get(t, 0.0) + sh
    post_holdings[ticker] = post_pos if intent == "PAPER_SELL" else (projected.get(ticker, holdings_f.get(ticker, 0.0)) + (shares if intent == "PAPER_BUY" else 0))
    if intent == "PAPER_BUY":
        post_holdings[ticker] = projected.get(ticker, holdings_f.get(ticker, 0.0)) + shares
    elif intent == "PAPER_SELL":
        post_holdings[ticker] = holdings_f.get(ticker, 0.0) - shares

    long_value = 0.0
    for t, q in post_holdings.items():
        if q > 0:
            if t not in marks_f:
                reason_codes.append(f"MISSING_OR_INVALID:marks.{t}")
                continue
            long_value += q * marks_f[t]
    post_exposure_pct = (long_value / equity * 100.0) if equity > 0 else float("inf")
    if math.isfinite(post_exposure_pct):
        snapshots["post_trade_long_exposure_pct"] = post_exposure_pct
    snapshots["post_trade_holdings"] = post_holdings
    # Preserve assertion: every pre-existing symbol still present
    for t in holdings_f:
        if t not in post_holdings:
            reason_codes.append(f"HOLDING_DROPPED:{t}")
    if math.isfinite(post_exposure_pct) and post_exposure_pct > FL.MAX_AGGREGATE_LONG_EXPOSURE_PCT + 1e-9:
        reason_codes.append("POST_TRADE_EXPOSURE_CAP")

    # G1-R4: check frozen per-name 20% cap for EVERY symbol post-trade (not only decision ticker)
    post_name_pcts: dict[str, float] = {}
    for t, q in post_holdings.items():
        if q <= 0:
            continue
        if t not in marks_f or equity <= 0:
            continue
        pct = (max(q, 0.0) * marks_f[t] / equity) * 100.0
        if not math.isfinite(pct):
            reason_codes.append(f"POST_TRADE_NAME_EXPOSURE_NON_FINITE:{t}")
            continue
        post_name_pcts[t] = pct
        if pct > FL.MAX_SIZE_PCT_PER_NAME + 1e-9:
            code = f"POST_TRADE_NAME_EXPOSURE_CAP:{t}"
            if code not in reason_codes:
                reason_codes.append(code)
    snapshots["post_trade_name_pct_by_symbol"] = post_name_pcts
    # Preserve decision-ticker snapshot + unscoped code for prior diagnostics compatibility
    post_name_pct = post_name_pcts.get(ticker)
    if post_name_pct is None and equity > 0:
        post_name_pct = (max(post_holdings.get(ticker, 0.0), 0.0) * mark_f / equity * 100.0)
    if post_name_pct is not None and math.isfinite(post_name_pct):
        snapshots["post_trade_name_pct"] = post_name_pct
        if post_name_pct > FL.MAX_SIZE_PCT_PER_NAME + 1e-9:
            if "POST_TRADE_NAME_EXPOSURE_CAP" not in reason_codes:
                reason_codes.append("POST_TRADE_NAME_EXPOSURE_CAP")

    if reason_codes:
        return _result(gate_id, decision, prediction, "REJECT", reason_codes, policy, snapshots, evaluated_at_utc)

    ok = "OK_TRADE_FIXTURE" if (test_entry and fixture_mode) else "OK"
    return _commit_ids_or_reject(
        gate_id, decision, prediction, policy, snapshots, evaluated_at_utc,
        [ok], registry,
        notes="test fixture ACCEPT only" if ok == "OK_TRADE_FIXTURE" else None,
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Production Risk Gate CLI (G1-R4)")
    p.add_argument("--prediction", required=True, type=Path)
    p.add_argument("--decision", required=True, type=Path)
    p.add_argument("--portfolio", type=Path, default=None)
    p.add_argument("--pending", type=Path, default=None)
    p.add_argument("--policy", type=Path, default=DEFAULT_POLICY_PATH,
                   help="Must be the approved policy file (content-hash bound)")
    p.add_argument("--gate-id", type=str, default=None)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args(argv)

    try:
        pred = load_path(args.prediction)
        dec = load_path(args.decision)
        portfolio = load_path(args.portfolio) if args.portfolio else None
        pending = load_path(args.pending) if args.pending else None
    except StrictJSONError as e:
        err = _result(args.gate_id, {}, {}, "REJECT", ["STRICT_JSON", str(e)[:80]], {}, {}, None)
        text = dumps_strict(err, indent=2, sort_keys=True)
        print(text)
        return 1

    # Registry path is fixed (DEFAULT_REGISTRY_PATH); no caller --registry bypass.
    result = evaluate(
        pred, dec, portfolio, pending,
        gate_id=args.gate_id,
        policy_path=args.policy,
    )
    text = dumps_strict(result, indent=2, sort_keys=True)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
    return 0 if result["verdict"] == "ACCEPT" else 1


if __name__ == "__main__":
    sys.exit(main())
