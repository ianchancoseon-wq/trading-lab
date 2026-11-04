from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from d0.records import prepare, reference
from d0.store import Store
from l0.core.registry import Registry

SAMPLE = Path('d0/examples/synthetic-loop.json').resolve()


class AdversarialQA(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.path = self.dir / 'research.sqlite'
        self.rows = json.loads(SAMPLE.read_bytes())

    def store(self):
        store = Store(self.path)
        self.addCleanup(store.close)
        return store

    def cli(self, db, *args):
        return subprocess.run([sys.executable, '-B', '-m', 'd0', '--db', str(db), *map(str, args)],
                              capture_output=True, text=True, timeout=15)

    def result(self, db, *args):
        result = self.cli(db, *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    @staticmethod
    def edit(record, **changes):
        raw = deepcopy(record)
        for field in ('content_sha256', 'data_status', 'timing_status', 'missing_fields'):
            raw.pop(field)
        raw.update(changes)
        return raw

    def test_cli_full_export_reimports_into_new_db_and_replays(self):
        self.assertEqual(self.result(self.path, 'import', SAMPLE), dict(inserted=8, replayed=0))
        exported = self.result(self.path, 'export')
        self.assertEqual(exported, self.rows)
        export_path = self.dir / 'export.json'
        export_path.write_text(json.dumps(exported, ensure_ascii=False), encoding='utf-8')
        fresh = self.dir / 'fresh.sqlite'
        self.assertEqual(self.result(fresh, 'import', export_path), dict(inserted=8, replayed=0))
        self.assertEqual(self.result(fresh, 'import', SAMPLE), dict(inserted=0, replayed=8))
        self.assertEqual(self.result(fresh, 'export'), self.rows)
        self.assertTrue(all(type(r['performance_eligible']) is bool and not r['performance_eligible']
                            and r['evidence_class'] == 'RESEARCH_ONLY' for r in exported))

    def test_revision_competing_branch_and_direct_update_rejected(self):
        store = self.store()
        store.import_records(self.rows)
        old = self.rows[3]
        second = prepare(self.edit(old, id='PRED-REV2', version=2,
                                   supersedes=reference(old), parents=old['parents']+[reference(old)]))
        self.assertEqual(store.import_records([second]), dict(inserted=1, replayed=0))
        with self.assertRaisesRegex(ValueError, 'REVISION_CHAIN'):
            store.import_records([self.edit(second, id='COMPETING-REV2')])
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'immutable'):
            store.db.execute("DELETE FROM d0_records WHERE id=?", (old['id'],))
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'immutable'):
            store.db.execute("UPDATE d0_records SET body='{}' WHERE id=?", (old['id'],))
        self.assertEqual(store.snapshot()[old['id']], old)
        self.assertEqual(store.snapshot()[second['id']], second)

    def test_cross_subject_review_parent_rejected(self):
        store = self.store()
        original = self.rows[3]
        other = prepare(self.edit(original, id='PRED-B', series_id='PRED-B'))
        store.import_records(self.rows + [other])
        foreign_outcome = prepare(self.edit(self.rows[4], id='OUT-B', series_id='OUT-B',
                                            parents=[reference(other)], prediction_ref=reference(other)))
        store.import_records([foreign_outcome])
        review = self.edit(self.rows[5], id='WRONG-REVIEW', series_id='WRONG-REVIEW',
                           parents=[reference(foreign_outcome)])
        with self.assertRaisesRegex(ValueError, 'STALE_SUBJECT_PARENT'):
            store.import_records([review])

    def test_outcome_revision_cannot_switch_prediction_subject(self):
        store = self.store()
        other = prepare(self.edit(self.rows[3], id='PRED-B', series_id='PRED-B'))
        store.import_records(self.rows + [other])
        original = self.rows[4]
        reassigned = self.edit(original, id='OUT-REV2-FOREIGN', version=2,
                               supersedes=reference(original), parents=[reference(original), reference(other)],
                               prediction_ref=reference(other))
        try:
            result = store.import_records([reassigned])
        except ValueError:
            return
        persisted = store.snapshot()[reassigned['id']]
        self.fail(f"{result}; {persisted['series_id']} v{persisted['version']} changed prediction "
                  f"from {original['prediction_ref']['id']} to {persisted['prediction_ref']['id']}")

    def test_sqlite_failure_rolls_back_existing_db_then_retry_succeeds(self):
        store = self.store()
        store.import_records(self.rows[:2])
        before = self.path.read_bytes()
        store.db.execute("""CREATE TEMP TRIGGER abort_prediction BEFORE INSERT ON main.d0_records
                            WHEN NEW.id='D0-PREDICTION-1'
                            BEGIN SELECT RAISE(ABORT,'independent fault'); END""")
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'independent fault'):
            store.import_records(self.rows[2:])
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(store.snapshot().values()), self.rows[:2])
        store.db.execute('DROP TRIGGER abort_prediction')
        self.assertEqual(store.import_records(self.rows), dict(inserted=6, replayed=2))
        self.assertEqual(list(store.snapshot().values()), self.rows)

    def test_d0_rejects_l0_db_and_m1_id(self):
        registry = Registry(self.dir / 'l0.sqlite')
        self.addCleanup(registry.close)
        l0_db = self.dir / 'l0.sqlite'
        original = l0_db.read_bytes()
        attempt = self.cli(l0_db, 'import', SAMPLE)
        self.assertEqual(attempt.returncode, 2)
        self.assertIn('NOT_A_D0_DATABASE', attempt.stderr)
        self.assertEqual(l0_db.read_bytes(), original)
        with self.assertRaisesRegex(ValueError, 'M1_READ_ONLY'):
            self.store().import_records([self.edit(self.rows[0], id='PRED-M1-001')])

    def test_l0_cannot_mix_its_tables_into_d0_database(self):
        store = self.store()
        store.import_records(self.rows)
        store.close()
        before = self.path.read_bytes()
        try:
            registry = Registry(self.path)
        except ValueError:
            self.assertEqual(self.path.read_bytes(), before)
        else:
            registry.close()
            with sqlite3.connect(self.path) as db:
                names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            with self.assertRaisesRegex(ValueError, 'NOT_A_D0_DATABASE'):
                Store(self.path)
            self.fail(f"L0 opened the D0 file, left tables {names}, and D0 now rejects the file on reopen")

    def test_schema_source_finite_and_timezone_rejections_are_atomic(self):
        store = self.store()
        valid = self.rows[0]
        malformed = [
            self.edit(self.rows[1], target_at_utc='2040-01-01T18:00:00'),
            self.edit(self.rows[1], unknown_field='value'),
            self.edit(self.rows[1], source=dict(self.rows[1]['source'], content='forged')),
            self.edit(self.rows[1], payload={'summary':'valid', 'nonfinite':float('inf')}),
        ]
        for bad in malformed:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    store.import_records([valid, bad])
                self.assertEqual(store.snapshot(), {})

    def test_documented_empty_string_marks_special_fields_missing(self):
        for record, key in ((self.rows[0], 'close'), (self.rows[3], 'probs'),
                            (self.rows[2], 'knowledge_cutoff_utc')):
            with self.subTest(key=key):
                raw = self.edit(record, payload=dict(record['payload'], **{key:''}))
                try:
                    prepared = prepare(raw)
                except ValueError as exc:
                    self.fail(f"Documented empty-string missing marker for {key} rejected: {exc}")
                self.assertEqual(prepared['data_status'], 'MISSING')
                self.assertIn(key, prepared['missing_fields'])

    def test_post_target_knowledge_cutoff_is_not_declared_only(self):
        prediction = self.rows[3]
        cutoff = '2040-01-03T18:00:00Z'
        raw = self.edit(prediction, payload=dict(prediction['payload'], knowledge_cutoff_utc=cutoff))
        store = self.store()
        try:
            store.import_records(self.rows[:3] + [raw])
        except ValueError:
            return
        actual = store.snapshot()[raw['id']]
        self.assertEqual(actual['timing_status'], 'RETROSPECTIVE',
                         f"cutoff {cutoff} is after target {actual['target_at_utc']}")

    def test_future_parent_rejected_without_partial_import(self):
        store = self.store()
        market = prepare(self.edit(self.rows[0], created_at_utc='2040-01-02T18:00:00Z'))
        news, research = self.rows[1:3]
        research = self.edit(research, parents=[reference(market), reference(news)])
        with self.assertRaisesRegex(ValueError, 'PARENT_AFTER_RECORD'):
            store.import_records([market, news, research])
        self.assertEqual(store.snapshot(), {})


if __name__ == '__main__':
    unittest.main(verbosity=2)
