from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from d0.examples.make_sample import sample
from d0.records import prepare, reference
from d0.store import Store
from l0.core.storage import Storage


def edit(record, **changes):
    return {
        **{key: value for key, value in record.items()
           if key not in ('content_sha256', 'data_status', 'timing_status', 'missing_fields')},
        **changes,
    }


class D0R1Tests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'd0.sqlite'
        self.rows = sample()

    def test_revision_subject_is_pinned_on_append_and_reopen(self):
        prediction, outcome, review, memory = self.rows[3:7]
        other_prediction = prepare(edit(prediction, id='PRED-B', series_id='PRED-B'))
        other_ref = reference(other_prediction)
        self.assertEqual(other_prediction['target_at_utc'], prediction['target_at_utc'])
        other_chain = []
        parent = other_prediction
        for original in (outcome, review, memory):
            rid = original['id'] + '-B'
            other_chain.append(prepare(edit(original, id=rid, series_id=rid,
                                            prediction_ref=other_ref, parents=[reference(parent)])))
            parent = other_chain[-1]

        for original, foreign_parent in zip((outcome, review, memory),
                                            [other_prediction, *other_chain[:2]]):
            with self.subTest(kind=original['kind']):
                valid = self.rows + [other_prediction] + other_chain
                supersedes = reference(original)
                revision = dict(id=original['id'] + '-REV2', version=2, supersedes=supersedes)
                switched = prepare(edit(original, **revision, prediction_ref=other_ref,
                                        parents=[supersedes, reference(foreign_parent)]))
                moved_target = prepare(edit(original, **revision,
                                            target_at_utc='2040-01-04T21:00:00Z',
                                            parents=original['parents'] + [supersedes]))
                good = prepare(edit(original, **revision, parents=original['parents'] + [supersedes]))
                path = self.path.with_name(original['kind'] + '.sqlite')
                with closing(Store(path)) as store:
                    store.import_records(valid)
                    with self.assertRaisesRegex(ValueError, 'REVISION_SUBJECT_MISMATCH'):
                        store.import_records([moved_target])
                    pending = prepare(edit(self.rows[0], id='PENDING', series_id='PENDING'))
                    before = path.read_bytes()
                    with self.assertRaisesRegex(ValueError, 'REVISION_SUBJECT_MISMATCH'):
                        store.import_records([pending, switched])
                    self.assertEqual(path.read_bytes(), before)
                    self.assertEqual(list(store.snapshot().values()), valid)
                    self.assertEqual(store.import_records([good]), dict(inserted=1, replayed=0))
                with closing(Store(path)) as store:
                    self.assertEqual(store.snapshot()[good['id']], good)

                legacy = path.with_name('legacy-' + path.name)
                with closing(Store(legacy)) as store:
                    store.import_records(valid)
                    store._append(switched)  # Valid seal/chain, as written by the original validator.
                    with self.assertRaisesRegex(ValueError, 'REVISION_SUBJECT_MISMATCH'):
                        store.snapshot()
                before = legacy.read_bytes()
                with self.assertRaisesRegex(ValueError, 'REVISION_SUBJECT_MISMATCH'):
                    with closing(Store(legacy)):
                        pass
                self.assertEqual(legacy.read_bytes(), before)

    def test_cutoff_chronology_uses_instants_and_allows_equality(self):
        cases = [
            ('2040-01-02T15:00:00+08:00', '2040-01-02T21:00:00Z',
             '2040-01-02T07:00:00Z', 'DECLARED_ONLY'),
            ('2040-01-03T05:00:00+08:00', '2040-01-02T21:00:00Z',
             '2040-01-03T05:00:00+08:00', 'RETROSPECTIVE'),
            ('2040-01-03T05:00:01+08:00', '2040-01-02T21:00:00Z',
             '2040-01-03T06:00:00+08:00', None),
            ('2040-01-02T15:00:01+08:00', '2040-01-02T21:00:00Z',
             '2040-01-02T07:00:00Z', None),
        ]
        for original in self.rows[2:4]:
            for cutoff, target, created, status in cases:
                with self.subTest(kind=original['kind'], cutoff=cutoff):
                    raw = edit(original, payload=dict(original['payload'], knowledge_cutoff_utc=cutoff),
                               target_at_utc=target, created_at_utc=created)
                    if status is None:
                        with self.assertRaisesRegex(ValueError, 'TIMING_CONFLICT'):
                            prepare(raw)
                    else:
                        result = prepare(raw)
                        self.assertEqual(result['timing_status'], status)
                        self.assertFalse(result['performance_eligible'])

    def test_special_missing_sentinels_roundtrip_and_nonempty_errors_reject(self):
        cases = [(0, 'close', 'broken'), (3, 'probs', 'broken'),
                 (2, 'knowledge_cutoff_utc', 'broken'), (3, 'knowledge_cutoff_utc', 'broken')]
        for index, key, malformed in cases:
            original = self.rows[index]
            for sentinel in (None, ''):
                with self.subTest(kind=original['kind'], field=key, sentinel=sentinel):
                    record = prepare(edit(original, payload=dict(original['payload'], **{key: sentinel})))
                    path = self.path.with_name(f'{index}-{key}-{sentinel}.sqlite')
                    with closing(Store(path)) as store:
                        store.import_records(self.rows[:index] + [record])
                    with closing(Store(path)) as store:
                        stored = store.snapshot()[record['id']]
                        self.assertEqual(stored, record)
                        self.assertEqual(stored['payload'][key], sentinel)
                        self.assertEqual(stored['missing_fields'], [key])
                        self.assertEqual(stored['data_status'], 'MISSING')
                        if key == 'knowledge_cutoff_utc':
                            self.assertEqual(stored['timing_status'], 'NOT_ASSESSED')
            with self.subTest(kind=original['kind'], field=key, sentinel=malformed):
                with self.assertRaises(ValueError):
                    prepare(edit(original, payload=dict(original['payload'], **{key: malformed})))

    def test_cross_open_preserves_bytes_schema_and_records_both_ways(self):
        l0_path = self.path.with_name('l0.sqlite')
        with closing(Store(self.path)) as store:
            store.import_records(self.rows)
            d0_rows = store.snapshot()
        with closing(Storage(l0_path)) as storage:
            l0_rows = storage.snapshot()

        for path, wrong_type, right_type, message, records in [
            (self.path, Storage, Store, 'NOT_AN_L0_DATABASE', d0_rows),
            (l0_path, Store, Storage, 'NOT_A_D0_DATABASE', l0_rows),
        ]:
            with self.subTest(path=path.name):
                def schema():
                    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
                        return db.execute('SELECT * FROM sqlite_master ORDER BY name').fetchall()

                before = path.read_bytes(), schema()
                with self.assertRaisesRegex(ValueError, message):
                    with closing(wrong_type(path)):
                        pass
                self.assertEqual((path.read_bytes(), schema()), before)
                with closing(right_type(path)) as reopened:
                    self.assertEqual(reopened.snapshot(), records)
