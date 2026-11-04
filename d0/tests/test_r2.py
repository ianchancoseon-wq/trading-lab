"""D0 R2: lock initialization and verify persisted bodies without repair."""
from contextlib import closing
from copy import deepcopy
from pathlib import Path
import json
import queue
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from d0.examples.make_sample import sample
from d0.store import Store
from l0.core.storage import Storage


class D0R2Tests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'records.sqlite'
        self.rows = sample()

    def race(self, first_type, second_type):
        """Pause after type check, before first DDL; use real SQLite locks/connections."""
        connect = sqlite3.connect
        paused, release, second_begin = (threading.Event() for _ in range(3))
        outcomes = queue.Queue()
        trace_states = []
        def traced(*args, **kwargs):
            db = connect(*args, **kwargs)
            name = threading.current_thread().name
            def trace(sql):
                command = sql.strip().upper()
                if name == 'first-init' and command.startswith('CREATE TABLE'):
                    trace_states.append(db.in_transaction)
                    paused.set()
                    if not release.wait(10):
                        outcomes.put(('trace-timeout', None))
                if name == 'second-init' and command.startswith('BEGIN IMMEDIATE'):
                    second_begin.set()
            db.set_trace_callback(trace)
            return db
        def worker(name, cls):
            try:
                with closing(cls(self.path)) as obj:
                    if cls is Store:
                        obj.import_records(self.rows[:1])
                outcomes.put((name, None))
            except BaseException as exc:
                outcomes.put((name, exc))
        with patch('sqlite3.connect', side_effect=traced):
            first = threading.Thread(target=worker, args=('first', first_type), name='first-init')
            second = threading.Thread(target=worker, args=('second', second_type), name='second-init')
            first.start()
            try:
                self.assertTrue(paused.wait(10), 'first initializer never reached DDL')
                second.start()
                self.assertTrue(second_begin.wait(10), 'contender never attempted write lock')
                # The owner has not executed CREATE yet. No other constructor may publish DDL.
                with closing(connect(self.path)) as observer:
                    visible = observer.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                self.assertEqual(visible, [])
            finally:
                release.set()
                first.join(20)
                if second.ident is not None:
                    second.join(20)
            self.assertFalse(first.is_alive()); self.assertFalse(second.is_alive())
        result = dict(outcomes.queue)
        self.assertNotIn('trace-timeout', result)
        self.assertTrue(trace_states and all(trace_states), 'DDL ran outside write transaction')
        self.assertIsNone(result['first'])
        if first_type is second_type:
            self.assertIsNone(result['second'])
        else:
            self.assertIsInstance(result['second'], ValueError)
        with closing(first_type(self.path)) as reopened:
            if first_type is Store:
                self.assertEqual(list(reopened.snapshot().values()), self.rows[:1])
            else:
                self.assertIn('INTERNAL-ACTOR-BINDINGS', reopened.snapshot())
        if first_type is not second_type:
            before = self.path.read_bytes()
            with self.assertRaises(ValueError):
                second_type(self.path)
            self.assertEqual(self.path.read_bytes(), before)

    def test_l0_wins_cross_type_initialization(self):
        self.race(Storage, Store)

    def test_d0_wins_cross_type_initialization(self):
        self.race(Store, Storage)

    def test_l0_same_type_concurrent_initialization(self):
        self.race(Storage, Storage)

    def test_d0_same_type_concurrent_initialization(self):
        self.race(Store, Store)

    def test_schema_check_and_ddl_share_one_transaction(self):
        connect = sqlite3.connect
        for cls in (Storage, Store):
            with self.subTest(cls=cls.__name__):
                if self.path.exists():
                    self.path.unlink()
                statements = []
                def tracked(*args, **kwargs):
                    db = connect(*args, **kwargs)
                    db.set_trace_callback(lambda sql: statements.append((sql.strip().upper(), db.in_transaction)))
                    return db
                with patch('sqlite3.connect', side_effect=tracked), closing(cls(self.path)):
                    pass
                checks = [(sql, active) for sql, active in statements
                          if 'SQLITE_MASTER' in sql or sql.startswith(('CREATE TABLE', 'CREATE TRIGGER'))]
                self.assertTrue(checks)
                self.assertTrue(all(active for _, active in checks), checks)
                self.assertEqual(sum(sql == 'BEGIN IMMEDIATE' for sql, _ in statements), 1)
                self.assertEqual(sum(sql == 'COMMIT' for sql, _ in statements), 1)
                self.path.unlink()

    def test_failed_ddl_rolls_back_all_schema_changes(self):
        connect = sqlite3.connect
        class FailDDL(sqlite3.Connection):
            def execute(self, sql, *args, **kwargs):
                if sql.strip().upper().startswith('CREATE TRIGGER'):
                    raise sqlite3.OperationalError('injected DDL failure')
                return super().execute(sql, *args, **kwargs)
        for cls in (Storage, Store):
            with self.subTest(cls=cls.__name__):
                if self.path.exists():
                    self.path.unlink()
                def fail(*args, **kwargs):
                    return connect(*args, factory=FailDDL, **kwargs)
                with patch('sqlite3.connect', side_effect=fail), self.assertRaisesRegex(
                        sqlite3.OperationalError, 'injected DDL failure'):
                    cls(self.path)
                with closing(connect(self.path)) as db:
                    self.assertEqual(db.execute('SELECT name FROM sqlite_master').fetchall(), [])
                with closing(cls(self.path)):
                    pass
                self.path.unlink()

    def damage(self, mutations):
        """Restore the exact trigger; leave chain columns and all hashes untouched."""
        if self.path.exists():
            self.path.unlink()
        with closing(Store(self.path)) as store:
            store.import_records(self.rows)
            original = self.rows[3]
            damaged = deepcopy(original)
            for key, action in mutations:
                target = damaged
                path = key.split('.')
                for part in path[:-1]:
                    target = target[part]
                if action == 'delete':
                    del target[path[-1]]
                else:
                    value = target[path[-1]]
                    target[path[-1]] = (0 if key == 'performance_eligible' else
                                       ['changed'] if isinstance(value, list) else
                                       value + 1 if type(value) is int else 'changed')
            with closing(sqlite3.connect(self.path)) as db:
                before = db.execute('SELECT previous,chain FROM d0_records WHERE id=?', (original['id'],)).fetchone()
                trigger = db.execute("SELECT sql FROM sqlite_master WHERE name='d0_no_update'").fetchone()[0]
                db.execute('DROP TRIGGER d0_no_update')
                db.execute('UPDATE d0_records SET body=? WHERE id=?', (json.dumps(damaged), original['id']))
                db.execute(trigger)
                self.assertEqual(db.execute('SELECT previous,chain FROM d0_records WHERE id=?',
                                            (original['id'],)).fetchone(), before)
                db.commit()
            with self.assertRaises((ValueError, KeyError, TypeError)):
                store.snapshot()
        before = self.path.read_bytes()
        with self.assertRaises((ValueError, KeyError, TypeError)):
            Store(self.path)
        self.assertEqual(self.path.read_bytes(), before)
        self.path.unlink()

    def test_qa_four_missing_fields_cannot_be_repaired(self):
        self.damage([(k, 'delete') for k in ('content_sha256', 'source.sha256',
                                            'timing_status', 'performance_eligible')])

    def test_each_persisted_required_field_deletion_fails_closed(self):
        keys = list(self.rows[3]) + ['source.' + k for k in self.rows[3]['source']]
        for key in keys:
            with self.subTest(key=key):
                self.damage([(key, 'delete')])

    def test_each_persisted_required_field_modification_fails_closed(self):
        keys = list(self.rows[3]) + ['source.' + k for k in self.rows[3]['source']]
        for key in keys:
            with self.subTest(key=key):
                self.damage([(key, 'modify')])

    def test_new_import_still_computes_optional_hash_and_derived_fields(self):
        raw = deepcopy(self.rows)
        for r in raw:
            for key in ('content_sha256', 'missing_fields', 'data_status', 'timing_status', 'performance_eligible'):
                r.pop(key)
            r['source'].pop('sha256')
        with closing(Store(self.path)) as store:
            self.assertEqual(store.import_records(raw), dict(inserted=8, replayed=0))
            self.assertEqual(list(store.snapshot().values()), self.rows)
            self.assertEqual(store.import_records(raw), dict(inserted=0, replayed=8))
