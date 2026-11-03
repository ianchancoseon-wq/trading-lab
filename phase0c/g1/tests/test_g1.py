#!/usr/bin/env python3
"""G1-R4 portable regressions + adversarial bypass tests (ordinary python3, no -S)."""
from __future__ import annotations

import hashlib
import inspect
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .../g1
PHASE0C = ROOT.parent
LAB_ROOT = PHASE0C.parent
sys.path.insert(0, str(ROOT))

from _hashutil import attach_hash, verify_hash  # noqa: E402
from finite_numbers import as_finite  # noqa: E402
from id_registry import IdRegistry  # noqa: E402
from json_strict import StrictJSONError, loads as strict_loads  # noqa: E402
from risk_gate import (  # noqa: E402
    bind_approved_policy,
    evaluate,
    evaluate_for_tests,
    load_approved_policy,
    policy_content_sha256,
)
from submit_validator import ValidationError, validate_bundle, validate_decision, validate_prediction  # noqa: E402
import frozen_limits as FL  # noqa: E402
import risk_gate as rg  # noqa: E402
from tickers import index_by_canonical  # noqa: E402

FIX = ROOT / "fixtures"
POLICY_OFF = load_approved_policy(ROOT / "risk_policy.json")
POLICY_FIX = json.loads((FIX / "policy_fixture_eval.json").read_text())


def load(name: str):
    return json.loads((FIX / name).read_text())


def empty_registry() -> IdRegistry:
    return IdRegistry(None)


class _TempRegistry:
    """Patch production DEFAULT_REGISTRY_PATH to an isolated temp file."""

    def __init__(self):
        self._tmpdir = None
        self._old = None
        self.path = None

    def __enter__(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "frozen_id_registry.jsonl"
        self.path.write_text("", encoding="utf-8")
        self._old = rg.DEFAULT_REGISTRY_PATH
        rg.DEFAULT_REGISTRY_PATH = self.path
        return self

    def __exit__(self, *exc):
        rg.DEFAULT_REGISTRY_PATH = self._old
        self._tmpdir.cleanup()


class TestValidator(unittest.TestCase):
    def test_positive_bundle(self):
        r = validate_bundle(load("prediction_ok.json"), load("decision_no_trade.json"))
        self.assertTrue(r["ok"], r)

    def test_probs_must_sum_to_one(self):
        with self.assertRaises(ValidationError) as cm:
            validate_prediction(load("prediction_bad_probs.json"))
        self.assertEqual(cm.exception.code, "PROB_SUM")

    def test_hash_mismatch(self):
        with self.assertRaises(ValidationError) as cm:
            validate_decision(load("decision_bad_hash.json"), load("prediction_ok.json"))
        self.assertEqual(cm.exception.code, "HASH_MISMATCH")

    def test_decision_before_freeze(self):
        with self.assertRaises(ValidationError) as cm:
            validate_decision(load("decision_before_freeze.json"), load("prediction_ok.json"))
        self.assertEqual(cm.exception.code, "TIMESTAMP_ORDER")

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(ValidationError) as cm:
            validate_prediction(load("prediction_naive_ts.json"))
        self.assertEqual(cm.exception.code, "TIMESTAMP_NOT_UTC_AWARE")

    def test_inf_price_rejected(self):
        with self.assertRaises(ValidationError) as cm:
            validate_prediction(load("prediction_nan_price.json"))
        self.assertEqual(cm.exception.code, "BAD_PRICE")

    def test_notes_must_be_string(self):
        pred = load("prediction_ok.json")
        bad = {k: v for k, v in pred.items() if k != "content_sha256"}
        bad["notes"] = 123
        bad = attach_hash(bad)
        with self.assertRaises(ValidationError) as cm:
            validate_prediction(bad)
        self.assertEqual(cm.exception.code, "INVALID_TYPE")

    def test_id_hash_conflict(self):
        reg = IdRegistry(FIX / "id_registry.jsonl")
        with self.assertRaises(ValidationError) as cm:
            validate_prediction(load("prediction_id_conflict.json"), reg)
        self.assertEqual(cm.exception.code, "ID_HASH_CONFLICT")

    def test_strict_json_rejects_nan_token(self):
        with self.assertRaises(StrictJSONError):
            strict_loads('{"a": NaN}')

    def test_strict_json_rejects_exponent_overflow(self):
        with self.assertRaises(StrictJSONError):
            strict_loads('{"a": 1e999}')


class TestRuntimeCompatibility(unittest.TestCase):
    def test_numbers_module_is_stdlib(self):
        # g1 is on sys.path; stdlib numbers must not be shadowed
        import numbers as std_numbers
        self.assertTrue(
            "site-packages" in (std_numbers.__file__ or "")
            or "/lib/python" in (std_numbers.__file__ or "").replace("\\", "/"),
            std_numbers.__file__,
        )
        self.assertNotIn("g1", (std_numbers.__file__ or "").replace("\\", "/"))
        self.assertIsNotNone(as_finite(3.0))
        self.assertIsNone(as_finite(float("inf")))

    def test_no_numbers_py_in_g1(self):
        self.assertFalse((ROOT / "numbers.py").exists())
        self.assertTrue((ROOT / "finite_numbers.py").exists())


class TestRiskGateProduction(unittest.TestCase):
    def test_no_trade_accept(self):
        with _TempRegistry():
            g = evaluate(load("prediction_ok.json"), load("decision_no_trade.json"), None, None)
            self.assertEqual(g["verdict"], "ACCEPT")
            self.assertIn("OK_NO_TRADE", g["reason_codes"])

    def test_production_evaluate_has_no_allow_fixture_or_registry_param(self):
        sig = inspect.signature(evaluate)
        self.assertNotIn("allow_fixture_eval", sig.parameters)
        self.assertNotIn("policy", sig.parameters)
        self.assertNotIn("registry", sig.parameters)  # fixed trusted path only

    def test_buy_blocked_paper_off(self):
        with _TempRegistry():
            g = evaluate(
                load("prediction_ok.json"), load("decision_buy_ok.json"),
                load("portfolio_ok.json"), None,
            )
            self.assertEqual(g["verdict"], "REJECT")
            self.assertIn("LAB_MODE_BLOCKS_TRADE", g["reason_codes"])

    def test_cli_has_no_registry_flag(self):
        src = (ROOT / "risk_gate.py").read_text(encoding="utf-8")
        self.assertNotIn('add_argument("--registry"', src)
        # help/parser description
        from risk_gate import main
        # argparse reject unknown --registry
        with self.assertRaises(SystemExit):
            main(["--prediction", str(FIX / "prediction_ok.json"),
                  "--decision", str(FIX / "decision_no_trade.json"),
                  "--registry", "/tmp/evil_registry.jsonl"])

    def test_tampered_policy_file_rejected(self):
        with _TempRegistry():
            g = evaluate(
                load("prediction_ok.json"), load("decision_no_trade.json"), None, None,
                policy_path=FIX / "policy_tampered_content.json",
            )
            self.assertEqual(g["verdict"], "REJECT")
            self.assertIn("UNAUTHORIZED_POLICY_CONTENT", g["reason_codes"])

    def test_approved_policy_hash_matches_frozen(self):
        pol = load_approved_policy(ROOT / "risk_policy.json")
        self.assertEqual(pol["version"], FL.APPROVED_POLICY_VERSION)
        self.assertEqual(policy_content_sha256(pol), FL.APPROVED_POLICY_SHA256)
        self.assertEqual(bind_approved_policy(pol), [])

    def test_idempotent_replay(self):
        with _TempRegistry() as tr:
            pred = load("prediction_ok.json")
            dec = load("decision_no_trade.json")
            g1 = evaluate(pred, dec, None, None)
            self.assertEqual(g1["verdict"], "ACCEPT")
            self.assertIn("OK_NO_TRADE", g1["reason_codes"])
            g2 = evaluate(pred, dec, None, None)
            self.assertEqual(g2["verdict"], "ACCEPT")
            self.assertIn("OK_IDEMPOTENT_REPLAY", g2["reason_codes"])
            # binding persisted
            reg = IdRegistry(tr.path)
            self.assertEqual(reg.check(pred["id"], pred["content_sha256"]), "ID_REPLAY_SAME")

    def test_rehashed_prediction_conflict_after_accept(self):
        with _TempRegistry():
            pred = load("prediction_ok.json")
            dec = load("decision_no_trade.json")
            g1 = evaluate(pred, dec, None, None)
            self.assertEqual(g1["verdict"], "ACCEPT")
            conflict = load("prediction_id_conflict.json")
            # different content, same PRED id
            g2 = evaluate(conflict, dec, None, None)
            self.assertEqual(g2["verdict"], "REJECT")
            self.assertTrue(any("ID_HASH_CONFLICT" in c for c in g2["reason_codes"]), g2["reason_codes"])

    def test_alternate_registry_path_ignored(self):
        """Production evaluate has no registry kwarg; bindings go only to DEFAULT_REGISTRY_PATH."""
        with _TempRegistry() as tr:
            pred = load("prediction_ok.json")
            dec = load("decision_no_trade.json")
            g = evaluate(pred, dec, None, None)
            self.assertEqual(g["verdict"], "ACCEPT")
            # Evil alternate path must remain empty / unused
            evil = Path(tempfile.mkdtemp()) / "evil.jsonl"
            evil.write_text("", encoding="utf-8")
            evil_reg = IdRegistry(evil)
            self.assertIsNone(evil_reg.check(pred["id"], pred["content_sha256"]))
            trusted = IdRegistry(tr.path)
            self.assertEqual(trusted.check(pred["id"], pred["content_sha256"]), "ID_REPLAY_SAME")


class TestRiskGateFixtures(unittest.TestCase):
    def test_buy_accept_fixture_entry_only(self):
        g = evaluate_for_tests(
            load("prediction_ok.json"), load("decision_buy_ok.json"),
            load("portfolio_ok.json"), None, POLICY_FIX,
            allow_fixture_eval=True, registry=empty_registry(),
        )
        self.assertEqual(g["verdict"], "ACCEPT", g)
        self.assertIn("OK_TRADE_FIXTURE", g["reason_codes"])

    def test_fixture_requires_demo(self):
        g = evaluate_for_tests(
            load("prediction_non_demo.json"), load("decision_buy_non_demo.json"),
            load("portfolio_ok.json"), None, POLICY_FIX,
            allow_fixture_eval=True, registry=empty_registry(),
        )
        self.assertEqual(g["verdict"], "REJECT")
        self.assertIn("FIXTURE_REQUIRES_DEMO_FLAGS", g["reason_codes"])

    def test_zero_share_trade_rejected(self):
        g = evaluate_for_tests(
            load("prediction_ok.json"), load("decision_buy_zero_share.json"),
            load("portfolio_ok.json"), None, POLICY_FIX,
            allow_fixture_eval=True, registry=empty_registry(),
        )
        self.assertEqual(g["verdict"], "REJECT")
        self.assertIn("ZERO_SHARE_TRADE", g["reason_codes"])

    def test_oversize_rejected(self):
        g = evaluate_for_tests(
            load("prediction_ok.json"), load("decision_buy_oversize.json"),
            load("portfolio_ok.json"), None, POLICY_FIX,
            allow_fixture_eval=True, registry=empty_registry(),
        )
        self.assertEqual(g["verdict"], "REJECT")
        self.assertIn("SIZE_PCT_EXCEEDS_PER_NAME_CAP", g["reason_codes"])

    def test_insufficient_cash(self):
        g = evaluate_for_tests(
            load("prediction_ok.json"), load("decision_buy_ok.json"),
            load("portfolio_tight_cash.json"), None, POLICY_FIX,
            allow_fixture_eval=True, registry=empty_registry(),
        )
        self.assertEqual(g["verdict"], "REJECT")
        self.assertIn("INSUFFICIENT_CASH", g["reason_codes"])

    def test_peak_drawdown_stop(self):
        g = evaluate_for_tests(
            load("prediction_ok.json"), load("decision_buy_ok.json"),
            load("portfolio_drawdown.json"), None, POLICY_FIX,
            allow_fixture_eval=True, registry=empty_registry(),
        )
        self.assertEqual(g["verdict"], "REJECT")
        self.assertIn("PEAK_DRAWDOWN_STOP", g["reason_codes"])

    def test_daily_loss_stop(self):
        g = evaluate_for_tests(
            load("prediction_ok.json"), load("decision_buy_ok.json"),
            load("portfolio_daily_loss.json"), None, POLICY_FIX,
            allow_fixture_eval=True, registry=empty_registry(),
        )
        self.assertEqual(g["verdict"], "REJECT")
        self.assertIn("DAILY_LOSS_STOP", g["reason_codes"])

    def test_relaxed_cap_rejected_even_in_fixture_entry(self):
        g = evaluate_for_tests(
            load("prediction_ok.json"), load("decision_buy_ok.json"),
            load("portfolio_ok.json"), None, load("policy_relaxed_cap.json"),
            allow_fixture_eval=True, registry=empty_registry(),
        )
        self.assertEqual(g["verdict"], "REJECT")
        self.assertTrue(any(c.startswith("UNAUTHORIZED_POLICY_MODIFICATION") for c in g["reason_codes"]))


class TestPendingAdversarial(unittest.TestCase):
    def test_empty_caller_pending_cannot_hide_portfolio(self):
        port = load("portfolio_pending.json")
        self.assertTrue(len(port["pending_intents"]) > 0)
        g = evaluate_for_tests(
            load("prediction_ok.json"), load("decision_buy_ok.json"),
            port, [], POLICY_FIX,
            allow_fixture_eval=True, registry=empty_registry(),
        )
        self.assertEqual(g["verdict"], "REJECT")
        self.assertIn("PENDING_SNAPSHOT_CONFLICT", g["reason_codes"])

    def test_matching_caller_pending_ok_path_still_conflicts_same_ticker(self):
        port = load("portfolio_pending.json")
        g = evaluate_for_tests(
            load("prediction_ok.json"), load("decision_buy_ok.json"),
            port, port["pending_intents"], POLICY_FIX,
            allow_fixture_eval=True, registry=empty_registry(),
        )
        self.assertEqual(g["verdict"], "REJECT")
        self.assertIn("PENDING_INTENT_CONFLICT", g["reason_codes"])

    def test_malformed_pending_fail_closed(self):
        g = evaluate_for_tests(
            load("prediction_ok.json"), load("decision_buy_ok.json"),
            load("portfolio_pending_malformed.json"), None, POLICY_FIX,
            allow_fixture_eval=True, registry=empty_registry(),
        )
        self.assertEqual(g["verdict"], "REJECT")
        self.assertTrue(any(c.startswith("PENDING_") for c in g["reason_codes"]))

    def test_pending_shares_size_notional_mismatch(self):
        """shares+notional agree with each other but contradict size_pct → reject (no silent override)."""
        g = evaluate_for_tests(
            load("prediction_ok.json"), load("decision_buy_ok.json"),
            load("portfolio_pending_inconsistent_shares.json"), None, POLICY_FIX,
            allow_fixture_eval=True, registry=empty_registry(),
        )
        self.assertEqual(g["verdict"], "REJECT")
        self.assertTrue(
            any(
                "PENDING_SHARES_SIZE_INCONSISTENT" in c or "PENDING_FIELDS_INCONSISTENT" in c
                for c in g["reason_codes"]
            ),
            g["reason_codes"],
        )

    def test_pending_fields_inconsistent_notional(self):
        g = evaluate_for_tests(
            load("prediction_ok.json"), load("decision_buy_ok.json"),
            load("portfolio_pending_fields_inconsistent.json"), None, POLICY_FIX,
            allow_fixture_eval=True, registry=empty_registry(),
        )
        self.assertEqual(g["verdict"], "REJECT")
        self.assertTrue(
            any(
                "PENDING_NOTIONAL_INCONSISTENT" in c or "PENDING_FIELDS_INCONSISTENT" in c
                for c in g["reason_codes"]
            ),
            g["reason_codes"],
        )

    def test_pending_status_pending_reserves_cash(self):
        g = evaluate_for_tests(
            load("prediction_ok.json"), load("decision_buy_ok.json"),
            load("portfolio_pending_status_pending.json"), None, POLICY_FIX,
            allow_fixture_eval=True, registry=empty_registry(),
        )
        self.assertEqual(g["verdict"], "REJECT")
        self.assertTrue(
            "INSUFFICIENT_CASH" in g["reason_codes"]
            or "PENDING_POST_EXPOSURE_CAP" in g["reason_codes"]
            or "PENDING_CASH_OVERRESERVE" in g["reason_codes"],
            g["reason_codes"],
        )
        self.assertGreater(g["snapshots"].get("reserved_cash", 0), 0)

    def test_pending_sell_not_credited_as_filled(self):
        g = evaluate_for_tests(
            load("prediction_spy.json"), load("decision_spy_buy.json"),
            load("portfolio_pending_sell_not_filled.json"), None, POLICY_FIX,
            allow_fixture_eval=True, registry=empty_registry(),
        )
        self.assertEqual(g["verdict"], "REJECT", g)
        self.assertTrue(
            "POST_TRADE_EXPOSURE_CAP" in g["reason_codes"]
            or "PENDING_POST_EXPOSURE_CAP" in g["reason_codes"]
            or "SIZE_PCT_EXCEEDS_PER_NAME_CAP" in g["reason_codes"],
            g["reason_codes"],
        )
        self.assertEqual(g["snapshots"]["holdings"].get("QQQ"), 200)

    def test_pending_other_symbol_reserves_cash(self):
        port = load("portfolio_pending_other_symbol.json")
        port["pending_intents"] = [
            {"ticker": "SPY", "status": "ACCEPT", "intent": "PAPER_BUY", "size_pct": 95.0, "decision_id": "DEC-SPY"}
        ]
        g = evaluate_for_tests(
            load("prediction_ok.json"), load("decision_buy_ok.json"),
            port, None, POLICY_FIX, allow_fixture_eval=True, registry=empty_registry(),
        )
        self.assertEqual(g["verdict"], "REJECT")
        self.assertTrue(
            "INSUFFICIENT_CASH" in g["reason_codes"] or "PENDING_POST_EXPOSURE_CAP" in g["reason_codes"],
            g["reason_codes"],
        )


class TestTickerAdversarial(unittest.TestCase):
    def test_qqq_case_alias_conflict(self):
        mapped, errs = index_by_canonical({"qqq": 0, "QQQ": 10})
        self.assertIsNone(mapped)
        self.assertTrue(any("TICKER_ALIAS_CONFLICT" in e for e in errs), errs)
        g = evaluate_for_tests(
            load("prediction_ok.json"), load("decision_buy_ok.json"),
            load("portfolio_qqq_case_conflict.json"), None, POLICY_FIX,
            allow_fixture_eval=True, registry=empty_registry(),
        )
        self.assertEqual(g["verdict"], "REJECT")
        self.assertTrue(any("TICKER_ALIAS_CONFLICT" in c for c in g["reason_codes"]), g["reason_codes"])

    def test_alias_conflict_rejects_before_merge(self):
        g = evaluate_for_tests(
            load("prediction_ok.json"), load("decision_buy_ok.json"),
            load("portfolio_alias_conflict.json"), None, POLICY_FIX,
            allow_fixture_eval=True, registry=empty_registry(),
        )
        self.assertEqual(g["verdict"], "REJECT")
        self.assertTrue(any("TICKER_ALIAS_CONFLICT" in c for c in g["reason_codes"]), g["reason_codes"])

    def test_post_trade_preserves_other_symbols(self):
        dec = attach_hash({
            "schema": "decision_v1",
            "id": "DEC-G1-FIXTURE-SMALL",
            "prediction_id": "PRED-G1-FIXTURE-001",
            "intent": "PAPER_BUY",
            "size_pct": 5.0,
            "rationale_digest": "small",
            "memory_influence": [],
            "risk_ack": True,
            "decided_at_utc": "2026-11-03T01:05:00Z",
            "demo": True,
        })
        g = evaluate_for_tests(
            load("prediction_ok.json"), dec,
            load("portfolio_two_names.json"), None, POLICY_FIX,
            allow_fixture_eval=True, registry=empty_registry(),
        )
        if g["verdict"] == "ACCEPT":
            self.assertIn("SPY", g["snapshots"]["post_trade_holdings"])
            self.assertIn("QQQ", g["snapshots"]["post_trade_holdings"])
            self.assertEqual(g["snapshots"]["post_trade_holdings"]["SPY"], 60)
        else:
            if "holdings" in g["snapshots"]:
                self.assertIn("SPY", g["snapshots"]["holdings"])


class TestNumericAndDiagnostics(unittest.TestCase):
    def test_inf_holding_fail_closed(self):
        g = evaluate_for_tests(
            load("prediction_ok.json"), load("decision_buy_ok.json"),
            load("portfolio_inf_holding.json"), None, POLICY_FIX,
            allow_fixture_eval=True, registry=empty_registry(),
        )
        self.assertEqual(g["verdict"], "REJECT")
        json.dumps(g, allow_nan=False)

    def test_equity_mark_mismatch(self):
        g = evaluate_for_tests(
            load("prediction_ok.json"), load("decision_buy_ok.json"),
            load("portfolio_equity_mismatch.json"), None, POLICY_FIX,
            allow_fixture_eval=True, registry=empty_registry(),
        )
        self.assertEqual(g["verdict"], "REJECT")
        self.assertIn("EQUITY_MARK_MISMATCH", g["reason_codes"])

    def test_garbage_portfolio_no_uncaught(self):
        g = evaluate_for_tests(
            load("prediction_ok.json"), load("decision_buy_ok.json"),
            {"cash": "nope", "holdings": None, "marks": math.nan},
            None, POLICY_FIX, allow_fixture_eval=True, registry=empty_registry(),
        )
        self.assertEqual(g["verdict"], "REJECT")
        json.dumps(g, allow_nan=False)


class TestSeparateProcessRegistry(unittest.TestCase):
    def test_separate_process_id_reuse_conflict(self):
        """Two CLI processes: second with modified PRED same id must REJECT."""
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            reg_path = td_path / "frozen_id_registry.jsonl"
            reg_path.write_text("", encoding="utf-8")
            pred = load("prediction_ok.json")
            dec = load("decision_no_trade.json")
            # Unique ids for isolation from other tests' default registry
            pred = attach_hash({**{k: v for k, v in pred.items() if k != "content_sha256"},
                                "id": "PRED-G1-R3-PROC-001"})
            dec = attach_hash({**{k: v for k, v in dec.items() if k != "content_sha256"},
                               "id": "DEC-G1-R3-PROC-001", "prediction_id": pred["id"]})
            pred_path = td_path / "pred.json"
            dec_path = td_path / "dec.json"
            pred_path.write_text(json.dumps(pred), encoding="utf-8")
            dec_path.write_text(json.dumps(dec), encoding="utf-8")

            env = os.environ.copy()
            # Run CLI with patched registry via env? We patch by writing a tiny runner.
            runner = td_path / "run_gate.py"
            runner.write_text(
                f"""
import json, sys
from pathlib import Path
sys.path.insert(0, {str(ROOT)!r})
import risk_gate as rg
rg.DEFAULT_REGISTRY_PATH = Path({str(reg_path)!r})
from json_strict import load_path
pred = load_path(Path(sys.argv[1]))
dec = load_path(Path(sys.argv[2]))
result = rg.evaluate(pred, dec, None, None)
print(json.dumps({{"verdict": result["verdict"], "reason_codes": result["reason_codes"]}}))
sys.exit(0 if result["verdict"] == "ACCEPT" else 1)
""",
                encoding="utf-8",
            )
            r1 = subprocess.run(
                [sys.executable, str(runner), str(pred_path), str(dec_path)],
                capture_output=True, text=True, cwd=str(ROOT),
            )
            self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
            out1 = json.loads(r1.stdout.strip().splitlines()[-1])
            self.assertEqual(out1["verdict"], "ACCEPT")

            # Modified prediction, same id
            conflict = attach_hash({
                **{k: v for k, v in pred.items() if k != "content_sha256"},
                "notes": "tampered after freeze",
            })
            self.assertEqual(conflict["id"], pred["id"])
            self.assertNotEqual(conflict["content_sha256"], pred["content_sha256"])
            cpath = td_path / "conflict.json"
            cpath.write_text(json.dumps(conflict), encoding="utf-8")
            r2 = subprocess.run(
                [sys.executable, str(runner), str(cpath), str(dec_path)],
                capture_output=True, text=True, cwd=str(ROOT),
            )
            self.assertNotEqual(r2.returncode, 0, r2.stdout + r2.stderr)
            out2 = json.loads(r2.stdout.strip().splitlines()[-1])
            self.assertEqual(out2["verdict"], "REJECT")
            self.assertTrue(any("ID_HASH_CONFLICT" in c for c in out2["reason_codes"]), out2)


class TestAllSymbolNameCap(unittest.TestCase):
    """G1-R4: 20% single-name hard cap applies to EVERY symbol in the projected portfolio."""

    def _buy_qqq(self, portfolio_name: str):
        return evaluate_for_tests(
            load("prediction_ok.json"), load("decision_buy_ok.json"),
            load(portfolio_name), None, POLICY_FIX,
            allow_fixture_eval=True, registry=empty_registry(),
        )

    def _assert_spy_name_cap_reject(self, g):
        self.assertEqual(g["verdict"], "REJECT", g)
        codes = g["reason_codes"]
        self.assertTrue(
            any(c == "NAME_EXPOSURE_CAP:SPY" or c.startswith("NAME_EXPOSURE_CAP:SPY")
                or c == "POST_TRADE_NAME_EXPOSURE_CAP:SPY" for c in codes),
            codes,
        )

    def test_existing_spy_30_blocks_qqq_buy(self):
        g = self._buy_qqq("portfolio_spy_30_existing.json")
        self._assert_spy_name_cap_reject(g)
        self.assertIn("NAME_EXPOSURE_CAP:SPY", g["reason_codes"])

    def test_pending_spy_30_blocks_qqq_buy(self):
        g = self._buy_qqq("portfolio_spy_30_pending.json")
        self._assert_spy_name_cap_reject(g)
        self.assertIn("NAME_EXPOSURE_CAP:SPY", g["reason_codes"])

    def test_two_pending_spy_24_blocks_qqq_buy(self):
        g = self._buy_qqq("portfolio_spy_two_pending_24.json")
        self._assert_spy_name_cap_reject(g)
        self.assertIn("NAME_EXPOSURE_CAP:SPY", g["reason_codes"])

    def test_existing_19_2_plus_pending_4_8_blocks_qqq_buy(self):
        g = self._buy_qqq("portfolio_spy_19_2_plus_pending_4_8.json")
        self._assert_spy_name_cap_reject(g)
        self.assertIn("NAME_EXPOSURE_CAP:SPY", g["reason_codes"])


class TestHistoricalPortable(unittest.TestCase):
    def test_pred_m1_hash(self):
        expected = "2317319d9ec2b33d9ccd2b8316c6c39b2f78d2d25e7fa7ad45aeb0e9274f224e"
        candidates = [
            LAB_ROOT / "predictions" / "PRED-M1-001.md",
            PHASE0C / "audit-evidence" / "PRED-M1-001.md",
        ]
        found = [p for p in candidates if p.exists()]
        self.assertTrue(found, "PRED-M1-001.md not found relative to lab layout")
        for p in found:
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), expected, p)

    def test_failed_archives_present(self):
        self.assertTrue((PHASE0C / "g1-FAILED-G1").exists())
        self.assertTrue((PHASE0C / "g1-FAILED-G1-R1").exists())
        self.assertTrue((PHASE0C / "g1-FAILED-G1-R2").exists())
        self.assertTrue((PHASE0C / "g1-FAILED-G1-R3").exists())
        self.assertTrue((PHASE0C / "g1-FAILED-G1-R2" / "g1" / "risk_gate.py").exists())
        self.assertTrue((PHASE0C / "g1-FAILED-G1-R3" / "g1" / "risk_gate.py").exists())


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    out = ROOT / "out" / "test_results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "build": "G1-R4",
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "ok": result.wasSuccessful(),
        "failure_details": [{"test": str(t), "trace": tb} for t, tb in result.failures + result.errors],
    }
    out.write_text(json.dumps(payload, indent=2) + "\n")
    console = ROOT / "out" / "test_run_console.txt"
    # TextTestRunner already printed to stdout; mirror summary
    summary = (
        f"G1-R4 tests_run={result.testsRun} ok={result.wasSuccessful()} "
        f"failures={len(result.failures)} errors={len(result.errors)}\n"
    )
    (ROOT / "out" / "test_log.txt").write_text(summary)
    # console captured by external tee when present
    if not console.exists() or console.stat().st_size < 100:
        console.write_text(summary)
    sys.exit(0 if result.wasSuccessful() else 1)
