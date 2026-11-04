"""SQLite is the sole authority. Immutable rows and a verified ordered hash chain."""
import json
import sqlite3
from contextlib import contextmanager
from .records import canonical, digest, verify, require, reference, validate_envelope, validate_lineage, DEFAULT_IDENTITIES


class Storage:
    def __init__(self, path, actor_bindings=None):
        self.actor_bindings = dict(DEFAULT_IDENTITIES if actor_bindings is None else actor_bindings)
        require(set(self.actor_bindings) == set(DEFAULT_IDENTITIES) and
                all(isinstance(v, str) and v and v.strip() == v for v in self.actor_bindings.values()), 'ACTOR_BINDINGS')
        self.db = sqlite3.connect(path, timeout=15, isolation_level=None)
        try:
            d0_table = self.db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='d0_records' COLLATE NOCASE"
            ).fetchone()
            require(d0_table is None, 'NOT_AN_L0_DATABASE')
        except BaseException:
            self.db.close()
            raise
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS records (
          seq INTEGER PRIMARY KEY, id TEXT UNIQUE NOT NULL, body TEXT NOT NULL,
          previous TEXT NOT NULL, chain TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS immutable_update BEFORE UPDATE ON records
          BEGIN SELECT RAISE(ABORT, 'immutable records'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_delete BEFORE DELETE ON records
          BEGIN SELECT RAISE(ABORT, 'immutable records'); END;
        ''')
        # Pin the deployment's role/identity bindings in this database, never guess on reopen.
        try:
            with self.transaction():
                from .records import seal
                self.append(seal({'id': 'INTERNAL-ACTOR-BINDINGS', 'kind': 'internal_config',
                                  'schema': 'l0_actor_bindings_v1', 'bindings': self.actor_bindings}))
        except BaseException:
            self.db.close()
            raise

    def validate_record(self, r):
        verify(r)
        if r.get('schema') == 'prediction_v1':
            from .records import validate_prediction
            validate_prediction(r)
        elif r.get('kind') == 'internal_config':
            require(set(r) == {'id', 'kind', 'schema', 'bindings', 'content_sha256'} and
                    r['id'] == 'INTERNAL-ACTOR-BINDINGS' and r['schema'] == 'l0_actor_bindings_v1' and
                    r['bindings'] == self.actor_bindings, 'ACTOR_BINDINGS_MISMATCH')
        elif r.get('kind') == 'attempt':
            require(r.get('schema') == 'l0_attempt_v1' and
                    set(r) == {'id', 'kind', 'schema', 'attempted_id', 'at', 'reason', 'content_sha256'},
                    'INTERNAL_ATTEMPT_SCHEMA')
        else:
            validate_envelope(r)
            require(r['actor_identity'] == self.actor_bindings[r['actor']], 'ACTOR_IDENTITY_MISMATCH')

    def close(self):
        self.db.close()

    def snapshot(self):
        require(self.db.execute('PRAGMA quick_check').fetchall() == [('ok',)], 'CORRUPT_STORAGE')
        records, prior = {}, '0' * 64
        for expected, (seq, rid, body, previous, chain) in enumerate(
                self.db.execute('SELECT * FROM records ORDER BY seq'), 1):
            r = json.loads(body)
            self.validate_record(r)
            require(seq == expected and rid == r['id'] and previous == prior, 'CHAIN_GAP')
            require(chain == digest({'seq': seq, 'body': r, 'previous': previous}), 'CHAIN_CORRUPTION')
            for ref in r.get('parents', []) + ([r['prediction_ref']] if 'prediction_ref' in r else []):
                require(ref['id'] in records and reference(records[ref['id']]) == ref, 'BROKEN_PARENT')
            validate_lineage(r, records)
            records[rid] = r
            prior = chain
        return records

    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            self.snapshot()
            yield
            self.db.execute('COMMIT')
        except BaseException:
            if self.db.in_transaction:
                self.db.execute('ROLLBACK')
            raise

    def append(self, r):
        require(self.db.in_transaction, 'TRANSACTION_REQUIRED')
        self.validate_record(r)
        existing = self.db.execute('SELECT body FROM records WHERE id=?', (r['id'],)).fetchone()
        if existing:
            require(json.loads(existing[0]) == r, 'ID_HASH_CONFLICT')
            return False
        rows = self.snapshot()
        for ref in r.get('parents', []) + ([r['prediction_ref']] if 'prediction_ref' in r else []):
            require(ref['id'] in rows and reference(rows[ref['id']]) == ref, 'BAD_PARENT_REFERENCE')
        validate_lineage(r, rows)
        last = self.db.execute('SELECT seq,chain FROM records ORDER BY seq DESC LIMIT 1').fetchone()
        seq, previous = (last[0] + 1, last[1]) if last else (1, '0' * 64)
        self.db.execute('INSERT INTO records VALUES (?,?,?,?,?)',
                        (seq, r['id'], canonical(r), previous,
                         digest({'seq': seq, 'body': r, 'previous': previous})))
        return True
