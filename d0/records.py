"""Small unified research envelope; content hashes match L0 canonical semantics."""
from datetime import datetime
from l0.core.records import canonical, digest, seal, reference, require
import hashlib
import json

KINDS = {'market', 'news', 'research', 'prediction', 'outcome', 'review', 'memory'}
REQUIRED = {'market': ('session', 'close'), 'news': ('summary',),
            'research': ('question', 'knowledge_cutoff_utc'),
            'prediction': ('probs', 'rationale', 'knowledge_cutoff_utc'),
            'outcome': ('observation',), 'review': ('findings', 'contrary_evidence'),
            'memory': ('lesson', 'scope', 'falsification_condition')}


def time(value):
    require(isinstance(value, str), 'TIMESTAMP_REQUIRED')
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(dt.tzinfo is not None, 'TIMEZONE_REQUIRED')
    return dt


def load(text):
    def pairs(items):
        obj = {}
        for k, v in items:
            require(k not in obj, 'DUPLICATE_JSON_KEY')
            obj[k] = v
        return obj
    def invalid(value):
        raise ValueError('NONFINITE_JSON:' + value)
    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)


def build(rid, kind, payload, *, source, acquired_at, target_at, created_at,
          parents=(), series_id=None, version=1, supersedes=None,
          prediction_ref=None, actor_identity='manual:unverified', origin='MANUAL'):
    """Manual helpers also support deliberately labeled synthetic examples."""
    return prepare({'schema': 'd0_record_v1', 'id': rid, 'kind': kind, 'symbol': 'SPY',
                    'series_id': rid if series_id is None else series_id, 'version': version,
                    'supersedes': supersedes, 'parents': list(parents), 'prediction_ref': prediction_ref,
                    'source': dict(source, acquired_at_utc=acquired_at), 'payload': payload,
                    'target_at_utc': target_at, 'created_at_utc': created_at,
                    'actor_identity': actor_identity, 'origin': origin, 'evidence_class': 'RESEARCH_ONLY'})


def prepare(raw):
    # Canonical roundtrip copies input and rejects NaN/Infinity, including overflow.
    require(isinstance(raw, dict), 'RECORD_OBJECT_REQUIRED')
    claimed = 'content_sha256' in raw
    r = load(canonical(raw))
    claim = r.pop('content_sha256', None)
    fields = {'schema', 'id', 'kind', 'symbol', 'series_id', 'version', 'supersedes', 'parents',
              'prediction_ref', 'source', 'payload', 'target_at_utc', 'created_at_utc',
              'actor_identity', 'origin', 'evidence_class'}
    derived = {'missing_fields', 'data_status', 'timing_status', 'performance_eligible'}
    require(set(r) - derived == fields, 'ENVELOPE_FIELDS')
    require(r['schema'] == 'd0_record_v1' and r['kind'] in KINDS, 'SCHEMA_KIND')
    require(r['symbol'] == 'SPY' and r['evidence_class'] == 'RESEARCH_ONLY', 'RESEARCH_SPY_ONLY')
    for name in ('id', 'series_id', 'actor_identity'):
        require(isinstance(r[name], str) and r[name].strip(), 'REQUIRED_' + name)
    require(r['id'] != 'PRED-M1-001', 'M1_READ_ONLY')
    require(type(r['version']) is int and r['version'] >= 1, 'BAD_VERSION')
    require(r['origin'] in ('MANUAL', 'SYNTHETIC'), 'ORIGIN_REQUIRED')
    require(isinstance(r['parents'], list) and isinstance(r['payload'], dict), 'PARENTS_PAYLOAD')
    s = r['source']
    require(isinstance(s, dict) and set(s) - {'sha256'} == {'name', 'uri', 'content', 'acquired_at_utc'}, 'SOURCE_FIELDS')
    require(all(isinstance(s[k], str) and s[k].strip() for k in ('name', 'uri')), 'SOURCE_ID_REQUIRED')
    require(isinstance(s['content'], str), 'SOURCE_TEXT_REQUIRED')
    sha = hashlib.sha256(s['content'].encode('utf-8')).hexdigest()
    require(s.get('sha256', sha) == sha, 'SOURCE_HASH_MISMATCH')
    s['sha256'] = sha
    target = time(r['target_at_utc'])
    created = time(r['created_at_utc'])
    acquired = time(s['acquired_at_utc'])
    missing = [key for key in REQUIRED[r['kind']] if r['payload'].get(key) in (None, '', [])]
    if not s['content']: missing.append('source.content')
    probs = r['payload'].get('probs')
    if r['kind'] == 'prediction' and probs not in (None, ''):
        require(isinstance(probs, dict) and set(probs) == {'UP', 'FLAT', 'DOWN'}, 'BAD_PROBS')
        require(all(type(v) in (int, float) and 0 <= v <= 1 for v in probs.values()) and
                abs(sum(probs.values()) - 1) <= 1e-9, 'BAD_PROBS')
    value = r['payload'].get('close')
    if r['kind'] == 'market' and value not in (None, ''):
        from decimal import Decimal, InvalidOperation
        require(isinstance(value, str), 'BAD_CLOSE')
        try:
            price = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError('BAD_CLOSE') from exc
        require(price.is_finite() and price > 0, 'BAD_CLOSE')
    cutoff = r['payload'].get('knowledge_cutoff_utc')
    timing = 'NOT_ASSESSED'
    if cutoff not in (None, ''):
        limit = time(cutoff)
        require(limit <= target and limit <= created, 'TIMING_CONFLICT')
        timing = 'RETROSPECTIVE' if created >= target or acquired > limit else 'DECLARED_ONLY'
    derived_values = {'missing_fields': missing, 'data_status': 'MISSING' if missing else 'RECORDED_UNVERIFIED',
                      'timing_status': timing, 'performance_eligible': False}
    for key, value in derived_values.items():
        require(key not in r or r[key] == value, 'FORGED_DERIVED_' + key)
        r[key] = value
    result = seal(r)
    require(not claimed or claim == result['content_sha256'], 'HASH_MISMATCH')
    return result
