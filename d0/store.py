"""Separate SQLite authority for research; never opens or writes an L0 database."""
import sqlite3
from .records import canonical, digest, reference, require, prepare, load, time

NEEDS = {'research': {'market', 'news', 'memory'}, 'prediction': {'research'},
         'outcome': {'prediction'}, 'review': {'outcome'}, 'memory': {'review'}}


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=15, isolation_level=None)
        try:
            # Reject an existing non-D0 database instead of silently adding tables.
            tables = {v[0] for v in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            require(not tables or tables == {'d0_records'}, 'NOT_A_D0_DATABASE')
            self.db.execute('PRAGMA synchronous=FULL')
            self.db.executescript('''
            CREATE TABLE IF NOT EXISTS d0_records(seq INTEGER PRIMARY KEY, id TEXT UNIQUE NOT NULL,
                body TEXT NOT NULL, previous TEXT NOT NULL, chain TEXT NOT NULL);
            CREATE TRIGGER IF NOT EXISTS d0_no_update BEFORE UPDATE ON d0_records
                BEGIN SELECT RAISE(ABORT,'immutable'); END;
            CREATE TRIGGER IF NOT EXISTS d0_no_delete BEFORE DELETE ON d0_records
                BEGIN SELECT RAISE(ABORT,'immutable'); END;
            ''')
            self.snapshot()
        except BaseException:
            self.db.close(); raise

    def close(self):
        self.db.close()

    @staticmethod
    def validate(r, rows):
        for ref in r['parents']:
            require(ref['id'] in rows and reference(rows[ref['id']]) == ref, 'BAD_PARENT')
            require(time(rows[ref['id']]['created_at_utc']) <= time(r['created_at_utc']), 'PARENT_AFTER_RECORD')
        parents = [rows[v['id']] for v in r['parents']]
        require(len({v['id'] for v in r['parents']}) == len(r['parents']), 'DUPLICATE_PARENT')
        if r['kind'] in NEEDS:
            require(any(v['kind'] in NEEDS[r['kind']] for v in parents), 'REQUIRED_PARENT_KIND')
        prior = [v for v in rows.values() if v['series_id'] == r['series_id']]
        if prior:
            last = prior[-1]
            require(r['kind'] == last['kind'] and r['version'] == last['version'] + 1
                    and r['supersedes'] == reference(last) and reference(last) in r['parents'], 'REVISION_CHAIN')
        else:
            require(r['version'] == 1 and r['supersedes'] is None, 'FIRST_VERSION')
        if r['kind'] in ('outcome', 'review', 'memory'):
            ref = r['prediction_ref']
            if prior:
                original = prior[0]
                require(ref == original['prediction_ref'] and
                        r['target_at_utc'] == original['target_at_utc'], 'REVISION_SUBJECT_MISMATCH')
            require(isinstance(ref, dict) and ref['id'] in rows and
                    reference(rows[ref['id']]) == ref and rows[ref['id']]['kind'] == 'prediction', 'PREDICTION_REF')
            require(r['target_at_utc'] == rows[ref['id']]['target_at_utc'], 'TARGET_MISMATCH')
            own = [v for v in rows.values() if v['prediction_ref'] == ref]
            if r['kind'] == 'outcome':
                require(ref in r['parents'], 'OUTCOME_PREDICTION_PARENT')
            else:
                needed = 'outcome' if r['kind'] == 'review' else 'review'
                history = [v for v in own if v['kind'] == needed]
                require(history, 'MISSING_SUBJECT_HISTORY')
                active = [v for v in parents if v['kind'] == needed]
                require(active == [history[-1]], 'STALE_SUBJECT_PARENT')
                if r['kind'] == 'memory':
                    outcomes = [v for v in own if v['kind'] == 'outcome']
                    require(outcomes and reference(outcomes[-1]) in active[0]['parents'], 'STALE_REVIEW')
        else:
            require(r['prediction_ref'] is None, 'UNEXPECTED_PREDICTION_REF')
        # Cross-round Memory is deliberate research input, with exact transitive references.
        # It does not activate a strategy or change formal L0 eligibility.

    def snapshot(self):
        require(self.db.execute('PRAGMA quick_check').fetchall() == [('ok',)], 'CORRUPT_DATABASE')
        rows, prev = {}, '0'*64
        for expected, (seq, rid, body, previous, chain) in enumerate(
                self.db.execute('SELECT * FROM d0_records ORDER BY seq'), 1):
            r = prepare(load(body))
            require(seq == expected and rid == r['id'] and previous == prev and
                    chain == digest({'seq': seq, 'record': r, 'previous': prev}), 'CHAIN_CORRUPTION')
            self.validate(r, rows)
            rows[rid] = r; prev = chain
        return rows

    def import_records(self, records):
        """Atomic batch; identical IDs replay, changed IDs/versions never overwrite."""
        require(isinstance(records, list), 'EXPECTED_RECORD_ARRAY')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            rows = self.snapshot()
            inserted = replayed = 0
            for raw in records:
                r = prepare(raw)
                if r['id'] in rows:
                    require(rows[r['id']] == r, 'ID_HASH_CONFLICT')
                    replayed += 1; continue
                self.validate(r, rows)
                self._append(r)
                rows[r['id']] = r; inserted += 1
            self.db.execute('COMMIT')
            return {'inserted': inserted, 'replayed': replayed}
        except BaseException:
            if self.db.in_transaction: self.db.execute('ROLLBACK')
            raise

    def _append(self, r):
        last = self.db.execute('SELECT seq,chain FROM d0_records ORDER BY seq DESC LIMIT 1').fetchone()
        seq, previous = (last[0]+1,last[1]) if last else (1,'0'*64)
        self.db.execute('INSERT INTO d0_records VALUES (?,?,?,?,?)',
                        (seq,r['id'],canonical(r),previous,digest({'seq':seq,'record':r,'previous':previous})))

    def status(self):
        rows = self.snapshot()
        return {'evidence_class': 'RESEARCH_ONLY', 'records': len(rows),
                'missing': sum(r['data_status']=='MISSING' for r in rows.values()),
                'by_kind': {k: sum(r['kind']==k for r in rows.values()) for k in sorted({r['kind'] for r in rows.values()})},
                'performance_eligible': False}
