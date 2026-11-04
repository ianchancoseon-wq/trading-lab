"""Review, memory and strategy proposals. No activation or promotion API."""
from .records import require, timestamp


def validate(r, parents):
    p, kind = r['payload'], r['kind']
    kinds = {v['kind'] for v in parents if 'kind' in v}
    if kind == 'review':
        require(r['actor'] == 'Review' and 'score' in kinds, 'REVIEW_SCORE_REQUIRED')
        for field in ('findings', 'contrary_evidence', 'limitations'):
            require(isinstance(p.get(field), list) and p[field], 'REVIEW_' + field.upper())
    elif kind == 'memory':
        require(r['actor'] == 'Memory' and 'review' in kinds, 'MEMORY_REVIEW_REQUIRED')
        for field in ('lesson', 'scope', 'falsification_condition', 'review_trigger', 'contrary_evidence'):
            require(bool(p.get(field)), 'MEMORY_' + field.upper())
        require(type(p['confidence']) in (int, float) and 0 <= p['confidence'] <= 1, 'CONFIDENCE')
        require(p['status'] in ('PROPOSED', 'REJECTED', 'DEFERRED', 'SUPERSEDED'), 'NO_MEMORY_ACTIVATION')
        require(p['approved_at'] is None and p['effective_at'] is None, 'EXTERNAL_APPROVAL_NOT_ACTIVATION')
        require(timestamp(p['proposed_at']) <= timestamp(r['created_at_utc'])
                <= timestamp(p['available_at']), 'BACKDATED_MEMORY')
        require(all(timestamp(v['created_at_utc']) <= timestamp(p['proposed_at'])
                    for v in parents), 'MEMORY_BEFORE_EVIDENCE')
        if p.get('supersedes'):
            require(p['supersedes'] in r['parents'], 'SUPERSEDED_PARENT_REQUIRED')
    elif kind == 'strategy':
        require(r['actor'] == 'Chief' and 'memory' in kinds, 'STRATEGY_MEMORY_REQUIRED')
        require(p['status'] == 'PROPOSED' and p['approved_at'] is None
                and p['effective_at'] is None, 'NO_STRATEGY_ACTIVATION')
        require(p['version'] and p['rules'] and p['change_reason'], 'STRATEGY_FIELDS')
        require(p['parent_version_ref'] in r['parents'], 'STRATEGY_PARENT_REQUIRED')
