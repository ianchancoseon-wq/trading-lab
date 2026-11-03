"""SQLite is the sole authority. Immutable rows and a verified ordered hash chain."""
import json
import sqlite3
from contextlib import contextmanager
from .records import canonical, digest, verify, require, reference


class Storage:
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=15, isolation_level=None)
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
        self.snapshot()

    def close(self):
        self.db.close()

    def snapshot(self):
        require(self.db.execute('PRAGMA quick_check').fetchall() == [('ok',)], 'CORRUPT_STORAGE')
        records, prior = {}, '0' * 64
        for expected, (seq, rid, body, previous, chain) in enumerate(
                self.db.execute('SELECT * FROM records ORDER BY seq'), 1):
            r = json.loads(body)
            verify(r)
            require(seq == expected and rid == r['id'] and previous == prior, 'CHAIN_GAP')
            require(chain == digest({'seq': seq, 'body': r, 'previous': previous}), 'CHAIN_CORRUPTION')
            for ref in r.get('parents', []) + ([r['prediction_ref']] if 'prediction_ref' in r else []):
                require(ref['id'] in records and reference(records[ref['id']]) == ref, 'BROKEN_PARENT')
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
        verify(r)
        existing = self.db.execute('SELECT body FROM records WHERE id=?', (r['id'],)).fetchone()
        if existing:
            require(json.loads(existing[0]) == r, 'ID_HASH_CONFLICT')
            return False
        rows = self.snapshot()
        for ref in r.get('parents', []) + ([r['prediction_ref']] if 'prediction_ref' in r else []):
            require(ref['id'] in rows and reference(rows[ref['id']]) == ref, 'BAD_PARENT_REFERENCE')
        last = self.db.execute('SELECT seq,chain FROM records ORDER BY seq DESC LIMIT 1').fetchone()
        seq, previous = (last[0] + 1, last[1]) if last else (1, '0' * 64)
        self.db.execute('INSERT INTO records VALUES (?,?,?,?,?)',
                        (seq, r['id'], canonical(r), previous,
                         digest({'seq': seq, 'body': r, 'previous': previous})))
        return True
