"""Pure arithmetic on a frozen bundle and manually supplied verified observation."""
from decimal import Decimal, localcontext
import math
from .records import (verify, require, validate_prediction, reference, measurement,
                      timestamp, decimal, primary, FIXTURE)


def score(prediction, freeze, measurement_record, outcome, *, as_of):
    for r in (prediction, freeze, measurement_record, outcome):
        verify(r)
    validate_prediction(prediction)
    require(prediction['id'] != 'PRED-M1-001', 'M1_SCORING_NOT_AUTHORIZED')
    require(freeze['kind'] == 'freeze' and measurement_record['kind'] == 'measurement'
            and outcome['kind'] == 'outcome', 'WRONG_RECORD_KIND')
    for r in (freeze, measurement_record, outcome):
        require(r['prediction_ref'] == reference(prediction), 'PREDICTION_REFERENCE')
        require(r['evidence_class'] == freeze['evidence_class'], 'EVIDENCE_CLASS_MISMATCH')
    require(reference(measurement_record) in freeze['parents'], 'UNFROZEN_MEASUREMENT')
    require(reference(freeze) in outcome['parents'], 'OUTCOME_FREEZE_REFERENCE')
    require(freeze['payload']['frozen_at_utc'] == prediction['frozen_at_utc'], 'FREEZE_TIME')
    m, o = measurement_record['payload'], outcome['payload']
    measurement(m, prediction)
    require(timestamp(as_of) >= timestamp(m['target_at']), 'OUTCOME_NOT_DUE')
    require(o['status'] == 'VERIFIED', 'OUTCOME_' + o['status'])
    for key in ('session', 'ticker', 'currency', 'price_basis', 'target_at'):
        require(o[key] == m[key], 'OUTCOME_' + key.upper())
    require(o['source_verified'] is True and o['session_verified'] is True
            and o['price_verified'] is True and o['final'] is True, 'UNVERIFIED_OUTCOME')
    require(bool(o['source_refs']) and all(ref in outcome['parents'] for ref in o['source_refs']),
            'OUTCOME_SOURCE_REFERENCES')
    require(timestamp(m['target_at']) <= timestamp(o['verified_at']) <= timestamp(as_of), 'OUTCOME_TIME')
    require(timestamp(outcome['created_at_utc']) >= timestamp(o['verified_at'])
            and timestamp(outcome['created_at_utc']) <= timestamp(as_of), 'OUTCOME_RECORD_TIME')
    close = decimal(o['close'])
    require(close > 0, 'BAD_CLOSE')
    actual = 'DOWN' if close < decimal(m['lower']) else 'UP' if close > decimal(m['upper']) else 'FLAT'
    with localcontext() as ctx:
        ctx.prec = 50
        probs = {k: Decimal(str(v)) for k, v in prediction['probs'].items()}
        brier = sum((probs[k] - int(k == actual)) ** 2 for k in ('UP', 'FLAT', 'DOWN'))
    p = probs[actual]
    return {'actual': actual, 'primary_call': primary(prediction, m['tie_priority']),
            'brier': str(brier), 'log_loss': None if p == 0 else -math.log(float(p)),
            'log_loss_status': 'POSITIVE_INFINITY' if p == 0 else 'FINITE',
            'directional_accuracy': int(primary(prediction, m['tie_priority']) == actual),
            'performance_eligible': False,
            'limitation': 'engineering only; no forward eligibility or performance aggregation is activated'}
