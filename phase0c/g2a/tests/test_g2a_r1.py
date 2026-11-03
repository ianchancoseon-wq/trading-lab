"""Offline correction regressions, including real process deaths at commit boundaries."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

G2A = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(G2A))
from artifacts import make_prediction, make_decision
from simulator import Simulator, SimError
from ledger import LedgerError
from prices import PriceBook
from replay import replay_ledger_file
from _hashutil import attach_hash

TS = '2026-11-03T10:05:00Z'


def bundle(n=1):
    pred = make_prediction(pid=f'PRED-R1-{n}', ticker='QQQ', baseline_price=500.,
                           frozen_at_utc='2026-11-03T10:00:00Z')
    dec = make_decision(did=f'DEC-R1-{n}', prediction_id=pred['id'], intent='PAPER_BUY',
                        size_pct=5., decided_at_utc=TS)
    return pred, dec


def new_sim(root):
    return Simulator(Path(root) / 'ledger.jsonl', Path(root) / 'registry.jsonl',
                     PriceBook.from_path(G2A / 'fixtures/prices_synth.json'))


class CorrectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sim = new_sim(self.tmp.name)
        self.pred, self.dec = bundle()

    def submit(self, sim=None, pred=None, dec=None, **kwargs):
        return (sim or self.sim).submit(pred or self.pred, dec or self.dec,
                                       evaluated_at_utc=TS, **kwargs)

    def assert_recovered(self, sim):
        self.assertEqual(sim.state, replay_ledger_file(sim.ledger.path)['state'])
        self.assertEqual(sim.state, new_sim(sim.ledger.path.parent).state)

    def test_changed_content_rejected_before_replay_live_and_restarted(self):
        self.submit()
        before = self.sim.ledger.path.read_bytes()
        for sim in (self.sim, new_sim(self.tmp.name)):
            for which in ('pred', 'dec'):
                for rehash in (False, True):
                    with self.subTest(which=which, rehash=rehash):
                        pred, dec = copy.deepcopy(self.pred), copy.deepcopy(self.dec)
                        artifact = pred if which == 'pred' else dec
                        artifact['notes'] = 'altered content under existing ID'
                        if rehash:
                            artifact.update(attach_hash(artifact))
                        with self.assertRaises(SimError):
                            self.submit(sim, pred, dec)
                        self.assertEqual(before, sim.ledger.path.read_bytes())
        self.assertEqual(self.submit()['status'], 'OK_IDEMPOTENT_REPLAY')

    def test_daily_halt_survives_new_day_recovery_and_blocks_buy(self):
        pred, dec = bundle()
        dec = attach_hash(dict(dec, size_pct=20.))
        self.submit(pred=pred, dec=dec)
        self.sim.ledger.mark_to_market({'QQQ': 400., 'SPY': 400.}, TS)
        self.assertTrue(self.sim.state['daily_loss_stop_latched'])
        self.assertFalse(self.sim.state['drawdown_stop_latched'])
        self.sim.start_new_day('2026-11-04')
        self.assertTrue(self.sim.state['daily_loss_stop_latched'])
        sim = new_sim(self.tmp.name)
        pred, dec = bundle(2)
        with self.assertRaises(SimError) as error:
            self.submit(sim, pred, dec)
        self.assertEqual(error.exception.code, 'DAILY_LOSS_STOP_LATCHED')
        self.assert_recovered(sim)

    def test_staging_failures_leave_no_binding_gate_or_fill(self):
        for target in ('simulator.build_fill', 'ledger.Ledger.record_gate',
                       'ledger.Ledger.record_fill', 'ledger.os.replace', 'ledger.os.fsync'):
            with self.subTest(target=target):
                before = self.sim.ledger.path.read_bytes()
                with patch(target, side_effect=OSError('injected')):
                    with self.assertRaises(OSError):
                        self.submit()
                self.assertEqual(before, self.sim.ledger.path.read_bytes())
                self.assertIsNone(self.sim.registry.check(self.dec['id'], self.dec['content_sha256']))
                self.assert_recovered(self.sim)
        self.assertEqual(self.submit()['status'], 'FILLED')
        self.assert_recovered(self.sim)

    def test_directory_fsync_failure_reconciles_committed_memory(self):
        original = os.fsync
        calls = []
        def fail_second(fd):
            calls.append(fd)
            if len(calls) == 2:
                raise OSError('directory fsync failed: commit outcome uncertain')
            original(fd)
        with patch('ledger.os.fsync', side_effect=fail_second):
            with self.assertRaises(OSError):
                self.submit()
        self.assert_recovered(self.sim)
        self.assertEqual(self.submit()['status'], 'OK_IDEMPOTENT_REPLAY')
        self.assertEqual(len([e for e in self.sim.ledger.events() if e['event_type'] == 'FILL']), 1)

    def test_direct_fill_duplicate_and_failed_mark_do_not_mutate_state(self):
        result = self.submit()
        before = self.sim.state
        with self.assertRaises(LedgerError):
            self.sim.ledger.record_fill(result['fill'], TS)
        with self.assertRaises(LedgerError):
            self.sim.ledger.mark_to_market({'SPY': 400.}, TS)
        self.assertEqual(before, self.sim.state)
        self.assert_recovered(self.sim)

    def child_code(self, boundary, root=None):
        return f'''
import sys, os
sys.dont_write_bytecode = True
sys.path.insert(0, {str(Path(__file__).parent)!r})
from test_g2a_r1 import new_sim, bundle, TS
sim = new_sim({str(root or self.tmp.name)!r})
import ledger, simulator
original = ledger.os.replace
def crash_replace(src, dst):
    if {boundary!r} == 'before_replace': os._exit(73)
    original(src, dst)
    if {boundary!r} == 'after_replace': os._exit(73)
ledger.os.replace = crash_replace
if {boundary!r} == 'after_binding':
    simulator.build_fill = lambda **kwargs: os._exit(73)
sim.submit(*bundle(), evaluated_at_utc=TS)
'''

    def test_real_process_death_does_not_lose_or_duplicate_fill(self):
        for boundary in ('after_binding', 'before_replace', 'after_replace'):
            with self.subTest(boundary=boundary):
                # Fresh isolated ledger per boundary.
                with tempfile.TemporaryDirectory() as root:
                    sim = new_sim(root)
                    result = subprocess.run([sys.executable, '-c', self.child_code(boundary, root)],
                                            capture_output=True, text=True, timeout=15)
                    self.assertEqual(result.returncode, 73, result.stderr)
                    sim = new_sim(root)
                    result = self.submit(sim)
                    expected = 'OK_IDEMPOTENT_REPLAY' if boundary == 'after_replace' else 'FILLED'
                    self.assertEqual(result['status'], expected)
                    self.assertEqual(sim.state['positions'], {'QQQ': 10})
                    self.assertEqual(len([e for e in sim.ledger.events() if e['event_type'] == 'FILL']), 1)
                    self.assert_recovered(sim)

    def test_restart_preserves_ids_and_deterministic_bytes(self):
        self.submit()
        pred2, dec2 = bundle(2)
        restarted = new_sim(self.tmp.name)
        self.submit(restarted, pred2, dec2)
        with tempfile.TemporaryDirectory() as root:
            uninterrupted = new_sim(root)
            self.submit(uninterrupted)
            self.submit(uninterrupted, pred2, dec2)
            self.assertEqual(restarted.ledger.path.read_bytes(), uninterrupted.ledger.path.read_bytes())
        self.assert_recovered(restarted)

    def test_concurrent_process_retries_fill_once(self):
        code = self.child_code('no_crash')
        processes = [subprocess.Popen([sys.executable, '-c', code], stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True) for _ in range(4)]
        for process in processes:
            _, err = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0, err)
        sim = new_sim(self.tmp.name)
        self.assertEqual(sim.state['positions'], {'QQQ': 10})
        self.assertEqual(len([e for e in sim.ledger.events() if e['event_type'] == 'FILL']), 1)
        self.assert_recovered(sim)

    def test_no_trade_and_pending_failure_roll_back_bindings(self):
        for intent, target, immediate in (
            ('NO_TRADE', 'ledger.Ledger.record_no_trade', True),
            ('PAPER_BUY', 'ledger.Ledger.inject_outstanding_pending', False),
        ):
            with self.subTest(intent=intent):
                dec = attach_hash(dict(self.dec, intent=intent, size_pct=0. if intent == 'NO_TRADE' else 5.))
                before = self.sim.ledger.path.read_bytes()
                with patch(target, side_effect=OSError('injected')):
                    with self.assertRaises(OSError):
                        self.submit(dec=dec, fill_immediately=immediate)
                self.assertEqual(before, self.sim.ledger.path.read_bytes())
                self.assertIsNone(self.sim.registry.check(dec['id'], dec['content_sha256']))

    def test_pending_retry_does_not_duplicate_reservation(self):
        self.assertEqual(self.submit(fill_immediately=False)['status'], 'ACCEPTED_PENDING')
        sim = new_sim(self.tmp.name)
        self.assertEqual(self.submit(sim)['status'], 'OK_IDEMPOTENT_REPLAY')
        self.assertEqual(len(sim.state['outstanding_pending']), 1)
        self.assertEqual(sim.state['filled_decision_ids'], {})
        self.assert_recovered(sim)

    def test_recovery_rejects_rehashed_forged_snapshot(self):
        self.submit()
        path = self.sim.ledger.path
        events = [json.loads(line) for line in path.read_text().splitlines()]
        events[-1]['state_after']['cash'] += 1
        events[-1] = attach_hash(events[-1])
        path.write_text(''.join(json.dumps(ev) + '\n' for ev in events))
        with self.assertRaises(LedgerError) as error:
            new_sim(self.tmp.name)
        self.assertEqual(error.exception.code, 'STATE_REPLAY_MISMATCH')

    def test_legacy_orphan_registry_fails_closed(self):
        path = Path(self.tmp.name) / 'registry.jsonl'
        path.write_text(json.dumps({'id': self.dec['id'], 'content_sha256': self.dec['content_sha256']}) + '\n')
        with self.assertRaises(SimError) as error:
            new_sim(self.tmp.name)
        self.assertEqual(error.exception.code, 'ORPHAN_REGISTRY_REQUIRES_REVIEW')


if __name__ == '__main__':
    unittest.main()
