import copy
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from d0.records import build, prepare, reference, load
from d0.store import Store
from d0.examples.make_sample import sample


class D0Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=str(Path(self.tmp.name)/'d0.sqlite')
        self.store=Store(self.path);self.addCleanup(self.store.close)
        self.rows=sample()

    def test_complete_loop_and_restart(self):
        self.assertEqual(self.store.import_records(self.rows),{'inserted':8,'replayed':0})
        self.assertEqual(self.store.snapshot()['D0-RESEARCH-2']['parents'],[reference(self.rows[-2])])
        reopened=Store(self.path)
        try:self.assertEqual(self.store.snapshot(),reopened.snapshot())
        finally:reopened.close()
        self.assertTrue(all(r['evidence_class']=='RESEARCH_ONLY' and r['performance_eligible'] is False
                            for r in self.store.snapshot().values()))
        self.assertEqual(self.store.status()['missing'],0)

    def test_repeated_import_is_idempotent(self):
        self.store.import_records(self.rows)
        self.assertEqual(self.store.import_records(self.rows),{'inserted':0,'replayed':8})
        self.assertEqual(self.store.status()['records'],8)

    def test_prediction_is_immutable_stale_or_rehashed(self):
        self.store.import_records(self.rows)
        for rehash in (False,True):
            bad=copy.deepcopy(self.rows[3]);bad['payload']['rationale']='changed after save'
            if rehash:bad.pop('content_sha256');bad=prepare(bad)
            with self.assertRaises(ValueError):self.store.import_records([bad])
        self.assertEqual(self.store.snapshot()[self.rows[3]['id']],self.rows[3])

    def test_prediction_revision_has_new_id_and_preserves_old(self):
        self.store.import_records(self.rows[:4]);old=self.rows[3]
        r=copy.deepcopy(old);r.pop('content_sha256');r['id']='D0-PREDICTION-REV2'
        r['version']=2;r['supersedes']=reference(old);r['parents'].append(reference(old))
        r['payload']['rationale']='Revised research hypothesis';r=prepare(r)
        self.store.import_records([r])
        self.assertEqual(self.store.snapshot()[old['id']],old)
        bad=copy.deepcopy(r);bad.pop('content_sha256');bad['id']='REV3-WRONG';bad['version']=3
        with self.assertRaises(ValueError):self.store.import_records([bad])

    def test_missing_data_retained_without_invented_value(self):
        r=copy.deepcopy(self.rows[0]);r.pop('content_sha256');r['payload']['close']=None
        r.pop('missing_fields');r.pop('data_status');r=prepare(r)
        self.store.import_records([r])
        self.assertEqual(self.store.snapshot()[r['id']]['payload']['close'],None)
        self.assertEqual(r['missing_fields'],['close']);self.assertEqual(self.store.status()['missing'],1)

    def test_source_and_envelope_metadata_errors(self):
        for key in ('source','target_at_utc','actor_identity'):
            r=copy.deepcopy(self.rows[0]);r.pop('content_sha256');r.pop(key)
            with self.subTest(key=key),self.assertRaises(ValueError):self.store.import_records([r])
        r=copy.deepcopy(self.rows[0]);r['source']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'SOURCE_HASH'):self.store.import_records([r])

    def test_incorrect_or_missing_parent_rolls_back_batch(self):
        r=copy.deepcopy(self.rows[1]);r.pop('content_sha256');r['parents']=[dict(reference(self.rows[0]),sha256='0'*64)]
        with self.assertRaises(ValueError):self.store.import_records([self.rows[0],r])
        self.assertEqual(self.store.snapshot(),{})
        with self.assertRaises(ValueError):self.store.import_records([self.rows[-1]])
        self.store.import_records(self.rows[:4])
        mismatch=copy.deepcopy(self.rows[4]);mismatch.pop('content_sha256')
        mismatch['target_at_utc']='2041-01-01T00:00:00Z'
        with self.assertRaisesRegex(ValueError,'TARGET_MISMATCH'):self.store.import_records([mismatch])

    def test_nonfinite_probabilities_and_duplicate_json_keys(self):
        for value in (float('nan'),float('inf'),float('-inf'),-1):
            r=copy.deepcopy(self.rows[3]);r.pop('content_sha256');r['payload']['probs']['UP']=value
            with self.subTest(value=value),self.assertRaises(ValueError):prepare(r)
        with self.assertRaises(ValueError):load('{"x":1,"x":2}')
        with self.assertRaises(ValueError):prepare(dict(self.rows[0],payload={'close':float('inf')}))

    def test_no_formal_class_or_symbol_or_eligibility_bypass(self):
        for key,value in [('symbol','QQQ'),('evidence_class','GENUINE_FORWARD_PREDICTION'),('performance_eligible',True)]:
            r=copy.deepcopy(self.rows[0]);r.pop('content_sha256');r[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.store.import_records([r])

    def test_historical_import_is_retrospective_and_stays_research(self):
        r=copy.deepcopy(self.rows[3]);r.pop('content_sha256');r.pop('timing_status')
        r['created_at_utc']='2040-02-01T00:00:00Z';r['source']['acquired_at_utc']=r['created_at_utc']
        r=prepare(r)
        self.store.import_records(self.rows[:3]+[r])
        self.assertEqual(r['timing_status'],'RETROSPECTIVE');self.assertFalse(r['performance_eligible'])

    def test_stale_review_cannot_drive_new_memory(self):
        self.store.import_records(self.rows[:7]);old=self.rows[4]
        r=copy.deepcopy(old);r.pop('content_sha256');r['id']='OUTCOME-REV2';r['version']=2
        r['supersedes']=reference(old);r['parents'].append(reference(old));r=prepare(r)
        self.store.import_records([r])
        mem=copy.deepcopy(self.rows[6]);mem.pop('content_sha256');mem['id']='MEMORY-REV2'
        mem['version']=2;mem['supersedes']=reference(self.rows[6]);mem['parents'].append(reference(self.rows[6]))
        with self.assertRaisesRegex(ValueError,'STALE_REVIEW'):self.store.import_records([mem])

    def test_existing_l0_database_is_rejected(self):
        from l0.core.registry import Registry
        path=str(Path(self.tmp.name)/'l0.sqlite');reg=Registry(path);reg.close()
        before=Path(path).read_bytes()
        with self.assertRaisesRegex(ValueError,'NOT_A_D0_DATABASE'):Store(path)
        self.assertEqual(before,Path(path).read_bytes())

    def test_injected_write_error_is_atomic(self):
        original=self.store._append
        def fail(r):
            if r['id']==self.rows[2]['id']:raise OSError('injected')
            original(r)
        with patch.object(self.store,'_append',side_effect=fail),self.assertRaises(OSError):self.store.import_records(self.rows)
        self.assertEqual(self.store.snapshot(),{})
        self.store.import_records(self.rows)

    def test_concurrent_duplicate_imports(self):
        def attempt(_):
            store=Store(self.path)
            try:return store.import_records(self.rows)
            finally:store.close()
        with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(attempt,range(3)))
        self.assertEqual(sum(r['inserted'] for r in results),8)
        self.assertEqual(self.store.status()['records'],8)

    def test_process_interruption_commit_and_recovery(self):
        for boundary in ('before','after'):
            path=str(Path(self.tmp.name)/(boundary+'.sqlite'))
            code=f'''import os
from d0.store import Store
from d0.examples.make_sample import sample
s=Store({path!r})
if {boundary!r}=='before':
 original=s._append
 def crash(r):
  original(r)
  if r['kind']=='prediction':os._exit(73)
 s._append=crash
s.import_records(sample())
os._exit(73)
'''
            result=subprocess.run([sys.executable,'-B','-c',code],timeout=15)
            self.assertEqual(result.returncode,73)
            store=Store(path)
            try:self.assertEqual(store.status()['records'],0 if boundary=='before' else 8)
            finally:store.close()

    def test_corruption_fails_closed(self):
        self.store.import_records(self.rows)
        with sqlite3.connect(self.path) as db:
            db.execute('DROP TRIGGER d0_no_update')
            db.execute("UPDATE d0_records SET chain='forged' WHERE seq=1")
        with self.assertRaises(ValueError):self.store.snapshot()

    def test_bad_price_and_null_hash_rejected(self):
        for value in ('not-a-price','NaN','Infinity','-1'):
            bad=copy.deepcopy(self.rows[0]);bad.pop('content_sha256');bad['payload']['close']=value
            with self.subTest(value=value),self.assertRaises(ValueError):prepare(bad)
        bad=dict(self.rows[0],content_sha256=None)
        with self.assertRaises(ValueError):prepare(bad)
        with self.assertRaises(ValueError):self.store.import_records({'wrong':'shape'})

    def test_cli_import_status_export_and_error(self):
        p=Path(self.tmp.name)/'records.json';p.write_text(json.dumps(self.rows))
        for args in (['import',str(p)],['status'],['export']):
            result=subprocess.run([sys.executable,'-B','-m','d0','--db',self.path]+args,capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr);json.loads(result.stdout)
        p.write_text('{broken')
        result=subprocess.run([sys.executable,'-B','-m','d0','--db',self.path,'import',str(p)],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,2);self.assertIn('D0 error:',result.stderr)
