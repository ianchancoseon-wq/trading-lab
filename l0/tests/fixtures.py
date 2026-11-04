"""Invented arithmetic records only. No market observations or trading fixtures."""
from l0.core.records import seal, record, reference, FIXTURE, TIE, primary
from l0.core.scoring import score

EARLY = '2040-01-01T00:00:00Z'
FREEZE = '2040-01-02T00:00:00Z'
LATE = '2040-01-03T22:00:00Z'


def prediction():
    return seal({'schema': 'prediction_v1', 'id': 'PRED-UNIT-001', 'strategy_version': 'unit-v1',
                 'ticker': 'SPY', 'baseline_price': 100., 'baseline_source_tier': 'synthetic',
                 'band': 1., 'horizon_end': '2040-01-03', 'probs': {'UP': .6, 'FLAT': .3, 'DOWN': .1},
                 'EVENT_EXPOSED': False, 'knowledge_cutoff_utc': EARLY,
                 'frozen_at_utc': FREEZE, 'demo': True})


def setup(reg):
    p = prediction()
    reg.register(p, at=EARLY)
    ev = record('EV-UNIT', 'evidence', p, EARLY, 'Market',
                {'description': 'Invented unit-test source/strategy/memory bundle',
                 'artifact_sha256': 'a'*64, 'locator': 'fixture:invented', 'available_at': EARLY})
    reg.put(ev)
    m = record('MEASURE-UNIT', 'measurement', p, EARLY, 'Chief',
               {'session': p['horizon_end'], 'ticker': p['ticker'], 'lower': '99', 'upper': '101',
                'currency': 'USD', 'price_basis': 'official_regular_close', 'market_timezone': 'UTC',
                'target_at': '2040-01-03T21:00:00Z', 'band_unit': 'percentage_points',
                'rounding_rule': 'exact decimal unit bounds', 'tie_priority': TIE})
    reg.put(m)
    challenges = [record('CHALLENGE-'+str(i), 'challenge', p, EARLY, 'Skeptic',
                         {'claim': 'invented claim '+str(i), 'failure_mechanism': 'mechanism '+str(i),
                          'alternative': 'alternative '+str(i), 'forecast_impact': 'uncertain',
                          'resolution_test': 'review evidence'}, [reference(ev)]) for i in range(3)]
    reg.put_batch(challenges)
    transition(reg, p, 'CHALLENGED', 'Skeptic', EARLY)
    dispositions = [record('DISPOSITION-'+str(i), 'disposition', p, EARLY, 'Chief',
                           {'challenge_ref': reference(c), 'reason': 'disclosed uncertainty', 'decision': 'ACCEPTED'},
                           [reference(c)]) for i, c in enumerate(challenges)]
    reg.put_batch(dispositions)
    transition(reg, p, 'CHIEF_FINAL', 'Chief', EARLY)
    f = record('FREEZE-UNIT', 'freeze', p, FREEZE, 'Chief',
               {'frozen_at_utc': FREEZE, 'strategy_version': 'unit-v1',
                'strategy_ref': reference(ev), 'research_ref': reference(ev),
                'memory_snapshot_ref': reference(ev), 'measurement_ref': reference(m),
                'evaluation_ref': reference(ev), 'primary_call': primary(p, TIE),
                'custody_status': 'UNVERIFIED', 'custody_ref': None},
               [reference(v) for v in [ev, m] + challenges + dispositions])
    reg.put(f)
    transition(reg, p, 'FROZEN', 'Chief', FREEZE, [reference(f)], 'QUARANTINED_PROVENANCE')
    transition(reg, p, 'AWAIT_OUTCOME', 'Chief', FREEZE, [], 'QUARANTINED_PROVENANCE')
    return p, m, f, ev


def transition(reg, p, target, actor, at, parents=(), eligibility='UNASSESSED'):
    previous = [r for r in reg.snapshot().values() if r.get('kind') == 'status'][-1]
    r = record('STATUS-'+target, 'status', p, at, actor,
               {'lifecycle_status': target, 'eligibility_status': eligibility, 'reason': 'unit-test transition'},
               [reference(previous)] + list(parents))
    reg.put(r)
    return r


def outcome(p, f, ev, close='102', rid='OUTCOME-UNIT', status='VERIFIED'):
    return record(rid, 'outcome', p, LATE, 'Review',
                  {'status': status, 'session': p['horizon_end'], 'ticker': p['ticker'],
                   'currency': 'USD', 'price_basis': 'official_regular_close',
                   'target_at': '2040-01-03T21:00:00Z', 'verified_at': LATE,
                   'source_verified': True, 'session_verified': True, 'price_verified': True,
                   'final': True, 'source_refs': [reference(ev)], 'close': close},
                  [reference(f), reference(ev)])


def scored(reg):
    p, m, f, ev = setup(reg)
    o = outcome(p, f, ev)
    reg.put(o)
    s = record('SCORE-UNIT', 'score', p, LATE, 'Codex',
               {'freeze_ref': reference(f), 'measurement_ref': reference(m), 'outcome_ref': reference(o),
                'result': score(p, f, m, o, as_of=LATE)}, [reference(f), reference(m), reference(o)])
    reg.put(s)
    return p, m, f, ev, o, s
