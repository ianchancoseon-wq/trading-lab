"""QA-1/QA-2 adversarial regressions, synthetic record arithmetic only."""
import copy
import unittest
from unittest.mock import patch
import test_core as baseline
from fixtures import LATE, outcome, scored
from l0.core.records import record, reference, seal
from l0.core.registry import Registry
from l0.core.scoring import score


class R2Tests(unittest.TestCase):
    setUp = baseline.CoreTests.setUp
    review_and_memory = baseline.CoreTests.review_and_memory

    def review(self, p, s, previous=None, rid='REVIEW-R2'):
        payload={'findings':['unit'],'contrary_evidence':['unit'],'limitations':['synthetic']}
        parents=[reference(s)]
        if previous:
            payload['supersedes']=reference(previous); parents.append(reference(previous))
        return record(rid,'review',p,LATE,'Review',payload,parents)

    def revise(self):
        rows=self.reg.snapshot()
        p=rows['PRED-UNIT-001']; m=rows['MEASURE-UNIT']; f=rows['FREEZE-UNIT']; ev=rows['EV-UNIT']
        old=rows['OUTCOME-UNIT']; oldscore=rows['SCORE-UNIT']
        new=outcome(p,f,ev,'98',rid='OUTCOME-R2')
        new['payload'].update(supersedes=reference(old),revision_reason='invented revision')
        new['parents'].append(reference(old)); new=seal(new)
        s=record('SCORE-R2','score',p,LATE,'Codex',
                 {'freeze_ref':reference(f),'measurement_ref':reference(m),'outcome_ref':reference(new),
                  'result':score(p,f,m,new,as_of=LATE),'supersedes':reference(oldscore)},
                 [reference(f),reference(m),reference(new),reference(oldscore)])
        self.reg.put(new)
        return new,s

    def test_quarantine_latched_at_all_post_score_stages(self):
        p,_,_,_,_,s=scored(self.reg)
        review=self.review(p,s); memory=None
        for stage,actor,effect in [('SCORED','Codex',s),('REVIEWED','Review',review),('MEMORY_PROPOSED','Memory',None)]:
            if stage=='REVIEWED':self.reg.put(review)
            if stage=='MEMORY_PROPOSED':
                memory=record('MEMORY-R2','memory',p,LATE,'Memory',
                    {'lesson':'unit','scope':'unit','confidence':.1,'falsification_condition':'unit',
                     'review_trigger':'unit','contrary_evidence':['unit'],'status':'PROPOSED',
                     'proposed_at':LATE,'available_at':LATE,'approved_at':None,'effective_at':None},[reference(review)])
                self.reg.put(memory);effect=memory
            previous=[v for v in self.reg.snapshot().values() if v.get('kind')=='status'][-1]
            rollback=record('ROLLBACK-'+stage,'status',p,LATE,actor,
                {'lifecycle_status':stage,'eligibility_status':'UNASSESSED','reason':'unauthorized downgrade'},
                [reference(previous),reference(effect)])
            with self.subTest(stage=stage),self.assertRaisesRegex(ValueError,'QUARANTINE'):
                self.reg.put(rollback)
            self.assertEqual(self.reg.state(p['id'])['eligibility_status'],'QUARANTINED_PROVENANCE')

    def test_invalid_remains_latched(self):
        p,_,_,_,_,s=scored(self.reg)
        previous=self.reg.snapshot()['STATE-SCORE-UNIT']
        invalid=record('INVALID-R2','status',p,LATE,'Codex',
            {'lifecycle_status':'SCORED','eligibility_status':'INVALID_INTEGRITY','reason':'fixture'},
            [reference(previous),reference(s)])
        self.reg.put(invalid)
        reset=copy.deepcopy(invalid);reset['id']='RESET-R2';reset['parents']=[reference(invalid),reference(s)]
        reset['payload']['eligibility_status']='QUARANTINED_PROVENANCE'
        with self.assertRaisesRegex(ValueError,'INVALID_STATUS_LATCHED'):self.reg.put(seal(reset))
        with self.assertRaisesRegex(ValueError,'INVALID_SAMPLE_HALTED'):self.reg.put(self.review(p,s))

    def test_unscored_latest_outcome_blocks_review_and_memory(self):
        p,review,memory=self.review_and_memory()
        self.revise()
        with self.assertRaisesRegex(ValueError,'CURRENT_SCORE'):
            self.reg.put(self.review(p,self.reg.snapshot()['SCORE-UNIT'],review))
        with self.assertRaisesRegex(ValueError,'CURRENT_SCORE'):self.reg.put(memory)
        self.assertIsNone(self.reg.current_score(p['id']))

    def test_revision_chain_after_memory_never_regresses(self):
        p,oldreview,oldmemory=self.review_and_memory();self.reg.put(oldmemory)
        old_snapshot=self.reg.snapshot()
        new,s=self.revise();self.reg.put(s)
        self.assertEqual(self.reg.state(p['id'])['lifecycle_status'],'MEMORY_PROPOSED')
        with self.assertRaisesRegex(ValueError,'CURRENT_SCORE'):
            self.reg.put(self.review(p,old_snapshot['SCORE-UNIT'],oldreview,rid='STALE-REVIEW'))
        with self.assertRaisesRegex(ValueError,'CURRENT_REVIEW'):
            self.reg.put(seal(dict(oldmemory,id='STALE-MEMORY')))
        review=self.review(p,s,oldreview);self.reg.put(review)
        memory=copy.deepcopy(oldmemory);memory['id']='MEMORY-REVISION'
        memory['payload']['supersedes']=reference(oldmemory)
        memory['parents']=[reference(review),reference(oldmemory)];memory=seal(memory)
        self.reg.put(memory)
        for v in (s,review,memory):self.reg.put(v)
        for rid,value in old_snapshot.items():self.assertEqual(self.reg.snapshot()[rid],value)
        self.assertEqual(self.reg.state(p['id'])['lifecycle_status'],'MEMORY_PROPOSED')
        r=Registry(self.path)
        try:self.assertEqual(r.snapshot(),self.reg.snapshot());self.assertEqual(r.current_score(p['id']),s)
        finally:r.close()

    def test_revision_after_review_is_allowed(self):
        p,oldreview,_=self.review_and_memory();_,s=self.revise();self.reg.put(s)
        self.assertEqual(self.reg.state(p['id'])['lifecycle_status'],'REVIEWED')
        self.reg.put(self.review(p,s,oldreview))
        self.assertEqual(self.reg.state(p['id'])['lifecycle_status'],'REVIEWED')

    def test_revision_batch_rolls_back_when_current_binding_is_wrong(self):
        p,oldreview,_=self.review_and_memory();_,s=self.revise()
        stale=self.review(p,self.reg.snapshot()['SCORE-UNIT'],oldreview)
        with self.assertRaises(ValueError):self.reg.put_batch([s,stale])
        self.assertNotIn(s['id'],self.reg.snapshot());self.assertIsNone(self.reg.current_score(p['id']))
        self.assertEqual(self.reg.state(p['id'])['lifecycle_status'],'REVIEWED')

    def test_versions_explicit_refs_and_predecessors_must_match(self):
        p,oldreview,memory=self.review_and_memory();_,s=self.revise();self.reg.put(s)
        valid=self.review(p,s,oldreview)
        for field,value in [('record_version','2.0'),('protocol_version','forged')]:
            with self.subTest(field=field),self.assertRaises(ValueError):self.reg.put(seal(dict(valid,**{field:value})))
        for change in ('old_score_ref','missing_predecessor','wrong_predecessor_hash'):
            bad=copy.deepcopy(valid)
            if change=='old_score_ref':bad['payload']['score_ref']=reference(self.reg.snapshot()['SCORE-UNIT'])
            elif change=='missing_predecessor':bad['payload'].pop('supersedes')
            else:bad['payload']['supersedes']['sha256']='0'*64
            with self.subTest(change=change),self.assertRaises(ValueError):self.reg.put(seal(bad))
        self.reg.put(valid)
        memory['parents']=[reference(valid)]
        memory['payload']['review_ref']=reference(oldreview)
        with self.assertRaises(ValueError):self.reg.put(seal(memory))
        changed=seal(dict(valid,payload=dict(valid['payload'],findings=['changed'])))
        with self.assertRaisesRegex(ValueError,'ID_HASH_CONFLICT'):self.reg.put(changed)

    def test_revision_status_failure_rolls_back_score(self):
        p,_,_=self.review_and_memory();_,s=self.revise()
        append=self.reg.storage.append
        def fail(r):
            if r['id']=='STATE-'+s['id']:raise OSError('injected status write failure')
            return append(r)
        with patch.object(self.reg.storage,'append',side_effect=fail),self.assertRaises(OSError):self.reg.put(s)
        self.assertNotIn(s['id'],self.reg.snapshot())
        self.assertEqual(self.reg.state(p['id'])['lifecycle_status'],'REVIEWED')
