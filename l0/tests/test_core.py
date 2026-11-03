import copy
import json
import math
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from l0.core.registry import Registry
from l0.core.records import seal, reference, record, primary, TIE, Invalid
from l0.core.scoring import score
from fixtures import prediction, setup, scored, outcome, transition, EARLY, FREEZE, LATE


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = str(Path(self.tmp.name)/'records.db')
        self.reg = Registry(self.path)
        self.addCleanup(self.reg.close)

    def test_registration_idempotency_and_conflict(self):
        p = prediction()
        self.reg.register(p, at=EARLY)
        before = self.reg.snapshot()
        self.reg.register(p, at=EARLY)
        self.assertEqual(before, self.reg.snapshot())
        for rehash in (False, True):
            q = dict(p, baseline_price=110.)
            if rehash: q = seal(q)
            with self.assertRaises(ValueError): self.reg.register(q, at=EARLY)
        self.assertEqual(self.reg.snapshot()[p['id']], p)
        self.assertEqual(len([r for r in self.reg.snapshot().values() if r.get('kind')=='attempt']), 2)

    def test_schema_and_probabilities(self):
        for field, value in [('schema','wrong'), ('extra','bad'), ('probs',{'UP': .2,'FLAT': .2,'DOWN': .2}),
                             ('probs',{'UP': -1,'FLAT': 1,'DOWN': 1})]:
            with self.subTest(field=field, value=value):
                p = seal(dict(prediction(), **{field:value}))
                with self.assertRaises(ValueError): self.reg.register(p, at=EARLY)
        p=prediction(); del p['strategy_version']; p=seal(p)
        with self.assertRaises(ValueError): self.reg.register(p, at=EARLY)
        for x in (float('nan'), float('inf'), float('-inf')):
            p=prediction(); p['probs']['UP']=x
            with self.assertRaises(ValueError): self.reg.register(p, at=EARLY)

    def test_lifecycle_and_eligibility(self):
        p=prediction(); self.reg.register(p,at=EARLY)
        with self.assertRaises(ValueError): transition(self.reg,p,'FROZEN','Chief',FREEZE)
        with self.assertRaises(ValueError): transition(self.reg,p,'CHALLENGED','Skeptic',EARLY)
        self.assertEqual(self.reg.state(p['id'])['lifecycle_status'],'RESEARCH')
        self.assertEqual(self.reg.state(p['id'])['eligibility_status'],'UNASSESSED')

    def test_missing_chief_dispositions_and_custody(self):
        p,m,f,ev=setup(self.reg)
        self.assertEqual(self.reg.state(p['id'])['eligibility_status'],'QUARANTINED_PROVENANCE')
        # Replay fixture preparation in a fresh DB, intercept only freeze insertion.
        for mutation in ('dispositions','custody'):
            r=Registry(str(Path(self.tmp.name)/(mutation+'.db')))
            self.addCleanup(r.close)
            original=r._put
            def altered(x):
                if x['kind']=='freeze':
                    x=copy.deepcopy(x)
                    if mutation=='custody': x['payload']['custody_status']='VERIFIED'
                    else: x['parents']=[v for v in x['parents'] if not v['id'].startswith('DISPOSITION')]
                    x=seal(x)
                return original(x)
            with patch.object(r,'_put',side_effect=altered):
                with self.assertRaises(ValueError): setup(r)
            self.assertFalse(any(v.get('kind')=='freeze' for v in r.snapshot().values()))

    def test_classes_bounds_and_arithmetic(self):
        p,m,f,ev=setup(self.reg)
        for close,actual in [('98','DOWN'),('99','FLAT'),('100','FLAT'),('101','FLAT'),('102','UP')]:
            result=score(p,f,m,outcome(p,f,ev,close),as_of=LATE)
            self.assertEqual(result['actual'],actual)
            self.assertFalse(result['performance_eligible'])
        result=score(p,f,m,outcome(p,f,ev),as_of=LATE)
        self.assertAlmostEqual(float(result['brier']),.26)
        self.assertAlmostEqual(result['log_loss'],.5108256238)
        self.assertEqual(result['directional_accuracy'],1)

    def test_tie_and_zero_probability(self):
        p=prediction(); p['probs']={'UP':.5,'FLAT':.5,'DOWN':0.}; p=seal(p)
        self.assertEqual(primary(p,TIE),'FLAT')
        r=Registry(str(Path(self.tmp.name)/'zero.db')); self.addCleanup(r.close)
        # Build the matching freeze bundle from the alternative synthetic probabilities.
        import fixtures
        with patch.object(fixtures,'prediction',return_value=p):
            _,m,_,ev=setup(r)
        f=r.snapshot()['FREEZE-UNIT']
        result=score(p,f,m,outcome(p,f,ev,'98'),as_of=LATE)
        self.assertIsNone(result['log_loss']); self.assertEqual(result['log_loss_status'],'POSITIVE_INFINITY')
        json.dumps(result,allow_nan=False)

    def test_scoring_guards(self):
        p,m,f,ev=setup(self.reg)
        o=outcome(p,f,ev)
        with self.assertRaises(ValueError): score(p,f,m,o,as_of=FREEZE)
        for key,value in [('status','PENDING'),('status','DISPUTED'),('session','2040-01-04'),
                          ('price_basis','adjusted_close'),('source_verified',False),('final',False)]:
            q=copy.deepcopy(o); q['payload'][key]=value; q=seal(q)
            with self.subTest(key=key,value=value), self.assertRaises(ValueError): score(p,f,m,q,as_of=LATE)
        q=copy.deepcopy(m); q['payload']['lower']='1'; q=seal(q)
        with self.assertRaises(ValueError): score(p,f,q,o,as_of=LATE)
        q=copy.deepcopy(p); q['probs']['UP']=.5
        with self.assertRaises(ValueError): score(q,f,m,o,as_of=LATE)

    def test_outcome_revisions_and_score_retry(self):
        p,m,f,ev,o,s=scored(self.reg)
        self.reg.put(s)
        q=seal(dict(s,id='SCORE-DUPLICATE'))
        with self.assertRaises(ValueError): self.reg.put(q)
        o2=outcome(p,f,ev,'98',rid='OUTCOME-REVISION')
        o2['payload'].update(supersedes=reference(o),revision_reason='invented source restatement')
        o2['parents'].append(reference(o)); o2=seal(o2); self.reg.put(o2)
        self.assertIsNone(self.reg.current_score(p['id']))
        s2=record('SCORE-REVISION','score',p,LATE,'Codex',
                  {'freeze_ref':reference(f),'measurement_ref':reference(m),'outcome_ref':reference(o2),
                   'result':score(p,f,m,o2,as_of=LATE),'supersedes':reference(s)},
                  [reference(f),reference(m),reference(o2),reference(s)])
        self.reg.put(s2)
        self.assertEqual(self.reg.current_score(p['id']),s2)
        self.assertEqual(self.reg.snapshot()[s['id']],s)
        self.assertEqual(len([v for v in self.reg.snapshot().values() if v.get('kind')=='score']),2)

    def review_and_memory(self):
        p,m,f,ev,o,s=scored(self.reg)
        review=record('REVIEW-UNIT','review',p,LATE,'Review',
                      {'findings':['arithmetic only'],'contrary_evidence':['invented counterexample'],
                       'limitations':['no performance evidence']},[reference(s)])
        self.reg.put(review)
        memory=record('MEMORY-UNIT','memory',p,LATE,'Memory',
                      {'lesson':'unproven proposal','scope':'unit tests','confidence':.2,
                       'falsification_condition':'contradictory future evidence','review_trigger':'next review',
                       'contrary_evidence':['counterexample'],'status':'PROPOSED', 'proposed_at':LATE,
                       'available_at':LATE,'approved_at':None,'effective_at':None},[reference(review)])
        return p,review,memory

    def test_review_memory_and_rejected_revision(self):
        p,review,memory=self.review_and_memory(); self.reg.put(memory)
        rejected=copy.deepcopy(memory); rejected['id']='MEMORY-REJECTED'
        rejected['payload'].update(status='REJECTED',supersedes=reference(memory))
        rejected['parents'].append(reference(memory)); rejected=seal(rejected); self.reg.put(rejected)
        self.assertEqual(self.reg.snapshot()[memory['id']]['payload']['status'],'PROPOSED')
        self.assertEqual(self.reg.snapshot()[p['id']],p)
        self.assertIsNone(self.reg.snapshot()[rejected['id']]['payload']['effective_at'])

    def test_parent_and_memory_guards(self):
        p,review,memory=self.review_and_memory()
        for change in ('missing','altered','backdate','activate'):
            r=copy.deepcopy(memory)
            if change=='missing':r['parents'][0]['id']='MISSING'
            elif change=='altered':r['parents'][0]['sha256']='0'*64
            elif change=='backdate':r['payload']['available_at']=EARLY
            else:r['payload']['effective_at']=LATE
            r=seal(r)
            with self.subTest(change=change),self.assertRaises(ValueError):self.reg.put(r)

    def test_atomic_rollback_and_restart(self):
        p=prediction(); self.reg.register(p,at=EARLY)
        ev=record('EV-BATCH','evidence',p,EARLY,'Market',
                  {'description':'unit','artifact_sha256':'a'*64,'locator':'fixture:unit','available_at':EARLY})
        bad=seal(dict(ev,id='EV-BAD',parents=[{'id':'MISSING','hash_kind':'canonical_json_sha256','sha256':'0'*64}]))
        with self.assertRaises(ValueError):self.reg.put_batch([ev,bad])
        self.assertNotIn(ev['id'],self.reg.snapshot())
        reopened=Registry(self.path)
        try:self.assertEqual(self.reg.snapshot(),reopened.snapshot())
        finally:reopened.close()

    def test_concurrent_registration(self):
        def register(_):
            r=Registry(self.path)
            try:r.register(prediction(),at=EARLY)
            finally:r.close()
        with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(register,range(8)))
        self.assertEqual(len(self.reg.snapshot()),2)

    def test_process_death_before_and_after_commit(self):
        for boundary in ('before','after'):
            path=str(Path(self.tmp.name)/(boundary+'.db'))
            code=f'''import os
from l0.core.registry import Registry
from l0.core.records import seal
r=Registry({path!r})
with r.storage.transaction():
 r.storage.append(seal({{'id':'UNIT-CRASH','kind':'attempt','reason':'invented'}}))
 if {boundary!r}=='before':os._exit(73)
os._exit(73)
'''
            result=subprocess.run([sys.executable,'-B','-c',code],timeout=15)
            self.assertEqual(result.returncode,73)
            reopened=Registry(path)
            try:self.assertEqual('UNIT-CRASH' in reopened.snapshot(),boundary=='after')
            finally:reopened.close()

    def test_freeze_and_status_crash_is_atomic(self):
        code = f"""import sys,os
sys.path.insert(0, 'l0/tests')
from fixtures import setup
from l0.core.registry import Registry
r=Registry({self.path!r})
original=r.storage.append
def crash(record):
 if record['id']=='STATE-FREEZE-UNIT':os._exit(73)
 return original(record)
r.storage.append=crash
setup(r)
"""
        result=subprocess.run([sys.executable,'-B','-c',code],timeout=15)
        self.assertEqual(result.returncode,73)
        self.assertNotIn('FREEZE-UNIT',self.reg.snapshot())
        self.assertEqual(self.reg.state('PRED-UNIT-001')['lifecycle_status'],'CHIEF_FINAL')
        other=Registry(str(Path(self.tmp.name)/'reference.db'))
        try:
            _,_,freeze,_=setup(other)
        finally:other.close()
        self.reg.put(freeze)
        self.reg.put(freeze)
        self.assertEqual(self.reg.state('PRED-UNIT-001')['lifecycle_status'],'FROZEN')
        self.assertIn('FREEZE-UNIT',self.reg.snapshot())

    def test_future_evidence_cannot_enter_memory_snapshot(self):
        import fixtures
        original_record=fixtures.record
        def future(*a,**kw):
            r=original_record(*a,**kw)
            if r['id']=='EV-UNIT':
                r['payload']['available_at']=FREEZE; r=seal(r)
            return r
        with patch.object(fixtures,'record',side_effect=future):
            with self.assertRaisesRegex(ValueError,'POST_CUTOFF'):setup(self.reg)
        self.assertNotIn('FREEZE-UNIT',self.reg.snapshot())

    def test_strategy_is_proposal_only(self):
        p,review,memory=self.review_and_memory(); self.reg.put(memory)
        parent=self.reg.snapshot()['EV-UNIT']
        strategy=record('STRATEGY-PROPOSED','strategy',p,LATE,'Chief',
                        {'version':'unit-v2','rules':'hypothesis only','change_reason':'review',
                         'parent_version_ref':reference(parent),'status':'PROPOSED',
                         'approved_at':None,'effective_at':None},[reference(parent),reference(memory)])
        self.reg.put(strategy)
        self.assertEqual(self.reg.state(p['id'])['lifecycle_status'],'MEMORY_PROPOSED')
        bad=copy.deepcopy(strategy); bad['id']='STRATEGY-ACTIVE'; bad['payload']['status']='ACTIVE'
        with self.assertRaises(ValueError):self.reg.put(seal(bad))
        with self.assertRaises(ValueError):transition(self.reg,p,'NEXT_VERSION_ELIGIBLE','Chief',LATE)

    def test_corrupted_storage_fails_closed(self):
        self.reg.register(prediction(),at=EARLY)
        with sqlite3.connect(self.path) as db:
            db.execute('DROP TRIGGER immutable_update')
            db.execute("UPDATE records SET body=replace(body,'100.0','900.0') WHERE seq=1")
        with self.assertRaises(ValueError):self.reg.snapshot()
        with self.assertRaises(ValueError):Registry(self.path)


if __name__=='__main__': unittest.main()
