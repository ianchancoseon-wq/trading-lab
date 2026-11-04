"""Founder review 6607510100: envelope binding and fail-closed lineage."""
import copy
from pathlib import Path
from unittest.mock import patch
import unittest
import fixtures
from fixtures import EARLY, LATE
import test_core as baseline
from l0.core.records import record, reference, seal, validate_envelope, DEFAULT_IDENTITIES
from l0.core.registry import Registry


class R1Tests(unittest.TestCase):
    setUp = baseline.CoreTests.setUp
    review_and_memory = baseline.CoreTests.review_and_memory

    def foreign(self):
        p2 = seal(dict(fixtures.prediction(), id='PRED-R1-FOREIGN'))
        builder = fixtures.record
        def prefixed(rid, *args, **kwargs):
            return builder('FOREIGN-' + rid, *args, **kwargs)
        with patch.object(fixtures, 'prediction', return_value=p2), patch.object(fixtures, 'record', side_effect=prefixed):
            _, _, _, ev, _, score = fixtures.scored(self.reg)
        review = record('FOREIGN-REVIEW', 'review', p2, LATE, 'Review',
                        {'findings':['invented'], 'contrary_evidence':['invented'], 'limitations':['fixture']},
                        [reference(score)])
        self.reg.put(review)
        memory = record('FOREIGN-MEMORY', 'memory', p2, LATE, 'Memory',
                        {'lesson':'invented', 'scope':'fixture', 'confidence':.1,
                         'falsification_condition':'counterexample', 'review_trigger':'later review',
                         'contrary_evidence':['invented'], 'status':'PROPOSED', 'proposed_at':LATE,
                         'available_at':LATE, 'approved_at':None, 'effective_at':None}, [reference(review)])
        self.reg.put(memory)
        return ev, review, memory

    def test_required_version_identity_fields(self):
        p, review, memory = self.review_and_memory()
        for field in ('record_version', 'protocol_version', 'actor_identity'):
            for value in ('MISSING', '', ' ', 1, 'forged-version-or-identity'):
                with self.subTest(field=field, value=value):
                    r = copy.deepcopy(memory)
                    if value == 'MISSING': del r[field]
                    else: r[field] = value
                    with self.assertRaises(ValueError): self.reg.put(seal(r))
        self.assertNotIn(memory['id'], self.reg.snapshot())

    def test_hash_and_reused_id_bind_versions_and_identity(self):
        _, _, memory = self.review_and_memory()
        self.reg.put(memory)
        before = self.reg.snapshot()
        self.reg.put(memory)
        self.assertEqual(before, self.reg.snapshot())
        for field, value in [('actor_identity', DEFAULT_IDENTITIES['Chief']),
                             ('record_version', '2.0'), ('protocol_version', 'L0-v2.0')]:
            for rehash in (False, True):
                with self.subTest(field=field, rehash=rehash):
                    altered = dict(memory, **{field:value})
                    with self.assertRaises(ValueError): self.reg.put(seal(altered) if rehash else altered)
        self.assertEqual(self.reg.snapshot()[memory['id']], memory)

    def test_all_derived_envelopes_and_pinned_identity_reopen(self):
        p, review, memory = self.review_and_memory()
        self.reg.put(memory)
        for r in self.reg.snapshot().values():
            if 'prediction_ref' in r:
                validate_envelope(r)
                self.assertEqual(r['actor_identity'], DEFAULT_IDENTITIES[r['actor']])
        altered = dict(DEFAULT_IDENTITIES, Memory='forged:Memory')
        with self.assertRaises(ValueError): Registry(self.path, actor_bindings=altered)
        reopened = Registry(self.path)
        try: self.assertEqual(self.reg.snapshot(), reopened.snapshot())
        finally: reopened.close()

    def test_declared_custom_identity_bound_to_role(self):
        bindings = dict(DEFAULT_IDENTITIES, Chief='local-test:chief-1')
        path = str(Path(self.tmp.name) / 'identity.db')
        r = Registry(path, actor_bindings=bindings)
        self.addCleanup(r.close)
        p = fixtures.prediction(); r.register(p, at=EARLY)
        self.assertEqual(r.snapshot()['REGISTER-' + p['id']]['actor_identity'], 'local-test:chief-1')
        ev = record('LOCAL-EV', 'evidence', p, EARLY, 'Chief',
                    {'description':'invented', 'artifact_sha256':'a'*64,'locator':'fixture:local','available_at':EARLY},
                    actor_identity='local-test:chief-1')
        r.put(ev)
        bad = seal(dict(ev, id='LOCAL-BAD', actor_identity=DEFAULT_IDENTITIES['Chief']))
        with self.assertRaises(ValueError): r.put(bad)

    def test_cross_prediction_review_used_as_memory_parent(self):
        _, _, memory = self.review_and_memory()
        _, foreign_review, _ = self.foreign()
        bad = seal(dict(memory, parents=[reference(foreign_review)]))
        with self.assertRaisesRegex(ValueError, 'CROSS_PREDICTION_LINEAGE'): self.reg.put(bad)
        self.reg.put(memory)
        self.assertEqual(self.reg.snapshot()[memory['id']], memory)

    def test_foreign_memory_and_strategy_predecessor_rejected(self):
        p, _, memory = self.review_and_memory(); self.reg.put(memory)
        ev, _, foreign_memory = self.foreign()
        for parents in ([reference(foreign_memory),reference(ev)], [reference(memory),reference(ev)]):
            strategy = record('BAD-STRATEGY', 'strategy', p, LATE, 'Chief',
                              {'version':'unit-v2', 'rules':'invented', 'change_reason':'review',
                               'parent_version_ref':reference(ev), 'status':'PROPOSED',
                               'approved_at':None, 'effective_at':None}, parents)
            with self.assertRaisesRegex(ValueError, 'CROSS_PREDICTION_LINEAGE'): self.reg.put(strategy)

    def test_review_foreign_evidence_and_indirect_memory_evidence(self):
        p, review, memory = self.review_and_memory()
        foreign, _, _ = self.foreign()
        bad_review = seal(dict(review, id='BAD-REVIEW', parents=review['parents']+[reference(foreign)]))
        with self.assertRaisesRegex(ValueError, 'CROSS_PREDICTION_LINEAGE'): self.reg.put(bad_review)
        # A same-prediction evidence wrapper must not launder a foreign ancestor.
        wrapper = record('WRAPPER', 'evidence', p, LATE, 'Market',
                         {'description':'invented wrapper','artifact_sha256':'c'*64,
                          'locator':'fixture:wrapper','available_at':LATE}, [reference(foreign)])
        self.reg.put(wrapper)
        bad_memory = seal(dict(memory, parents=memory['parents']+[reference(wrapper)]))
        with self.assertRaisesRegex(ValueError, 'CROSS_PREDICTION_LINEAGE'): self.reg.put(bad_memory)

    def test_missing_or_altered_parent_hash_and_same_prediction_preserved(self):
        _, _, memory = self.review_and_memory()
        for key,value in [('id','MISSING'), ('sha256','0'*64), ('hash_kind','raw_bytes_sha256')]:
            bad=copy.deepcopy(memory); bad['parents'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.reg.put(seal(bad))
        self.reg.put(memory)
        self.assertEqual(self.reg.snapshot()[memory['id']],memory)

    def test_storage_boundary_rejects_incomplete_derived_record(self):
        _, _, memory=self.review_and_memory()
        del memory['protocol_version']; memory=seal(memory)
        with self.assertRaises(ValueError),self.reg.storage.transaction():self.reg.storage.append(memory)
        self.assertNotIn(memory['id'],self.reg.snapshot())
