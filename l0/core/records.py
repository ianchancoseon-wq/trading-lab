"""Strict record envelopes and frozen G1 validation (no risk-gate imports)."""
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'phase0c' / 'g1'))
from submit_validator import validate_prediction as _g1_validate, ValidationError

FIXTURE = 'SYNTHETIC_ENGINEERING_FIXTURE'
FORWARD = 'GENUINE_FORWARD_PREDICTION'
TIE = ['FLAT', 'DOWN', 'UP']


class Invalid(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise Invalid(reason)


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False)


def digest(obj):
    return hashlib.sha256(canonical({k: v for k, v in obj.items()
                                    if k != 'content_sha256'}).encode()).hexdigest()


def seal(obj):
    return dict(obj, content_sha256=digest(obj))


def verify(obj):
    require(isinstance(obj, dict) and obj.get('content_sha256') == digest(obj), 'HASH_MISMATCH')


def timestamp(value):
    require(isinstance(value, str), 'TIMESTAMP_REQUIRED')
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(dt.tzinfo is not None, 'TIMEZONE_REQUIRED')
    return dt


def decimal(value):
    require(isinstance(value, str), 'DECIMAL_STRING_REQUIRED')
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise Invalid('BAD_DECIMAL') from exc
    require(result.is_finite(), 'NONFINITE_DECIMAL')
    return result


def reference(record):
    return {'id': record['id'], 'hash_kind': 'canonical_json_sha256',
            'sha256': record['content_sha256']}


def primary(prediction, tie):
    require(tie == TIE, 'UNSUPPORTED_TIE_RULE')
    return max(tie, key=lambda label: prediction['probs'][label])


def record(rid, kind, prediction, at, actor, payload, parents=(), evidence_class=FIXTURE):
    return seal({'id': rid, 'kind': kind, 'prediction_ref': reference(prediction),
                 'created_at_utc': at, 'actor': actor, 'payload': payload,
                 'parents': list(parents), 'evidence_class': evidence_class})


def validate_envelope(r):
    verify(r)
    require(set(r) == {'id', 'kind', 'prediction_ref', 'created_at_utc', 'actor',
                       'payload', 'parents', 'evidence_class', 'content_sha256'}, 'ENVELOPE_FIELDS')
    require(isinstance(r['id'], str) and r['id'] and isinstance(r['payload'], dict), 'BAD_RECORD')
    timestamp(r['created_at_utc'])
    require(r['evidence_class'] in (FIXTURE, FORWARD), 'UNSUPPORTED_EVIDENCE_CLASS')
    require(isinstance(r['parents'], list), 'PARENTS_REQUIRED')


def measurement(m, p):
    require(m['session'] == p['horizon_end'], 'SESSION_MISMATCH')
    require(m['ticker'] == p['ticker'], 'TICKER_MISMATCH')
    require(decimal(m['lower']) <= decimal(m['upper']), 'BOUNDS_ORDER')
    require(decimal(m['lower']) > 0, 'BAD_BOUND')
    require(m['price_basis'] == 'official_regular_close', 'PRICE_BASIS')
    require(m['band_unit'] == 'percentage_points' and bool(m['rounding_rule']), 'BAND_RULE_REQUIRED')
    require(m['currency'] and m['market_timezone'], 'MEASUREMENT_REQUIRED')
    require(timestamp(m['target_at']).astimezone(ZoneInfo(m['market_timezone'])).date().isoformat() == m['session'], 'TARGET_SESSION_DATE')
    require(timestamp(m['target_at']) > timestamp(p['frozen_at_utc']), 'TARGET_BEFORE_FREEZE')
    primary(p, m['tie_priority'])


def validate_prediction(prediction):
    try:
        return _g1_validate(prediction)
    except ValidationError as exc:
        raise Invalid(str(exc)) from exc
