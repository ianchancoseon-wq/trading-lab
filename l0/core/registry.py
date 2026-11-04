"""Research registry. All dependent writes use one SQLite transaction."""
import uuid
from .storage import Storage
from .records import (record, seal, digest, reference, verify, require, validate_envelope,
                      validate_prediction, timestamp, primary, measurement, FIXTURE, FORWARD, validate_lineage)
from .scoring import score
from .review_memory import validate as validate_review_memory

STATES = ['RESEARCH', 'CHALLENGED', 'CHIEF_FINAL', 'FROZEN', 'AWAIT_OUTCOME',
          'SCORED', 'REVIEWED', 'MEMORY_PROPOSED', 'NEXT_VERSION_ELIGIBLE']


class Registry:
    def __init__(self, path, *, actor_bindings=None):
        self.storage = Storage(path, actor_bindings)

    def close(self):
        self.storage.close()

    def snapshot(self):
        return self.storage.snapshot()

    def state(self, prediction_id):
        rows = self.snapshot()
        require(prediction_id in rows and rows[prediction_id].get('schema') == 'prediction_v1', 'UNKNOWN_PREDICTION')
        states = [r for r in rows.values() if r.get('kind') == 'status'
                  and r['prediction_ref']['id'] == prediction_id]
        return states[-1]['payload']

    def current_score(self, prediction_id):
        """Never select an older favorable score while a revised outcome is unscored."""
        own = [v for v in self.snapshot().values()
               if v.get('prediction_ref', {}).get('id') == prediction_id]
        outcomes = [v for v in own if v.get('kind') == 'outcome']
        if not outcomes:
            return None
        scores = [v for v in own if v.get('kind') == 'score'
                  and v['payload']['outcome_ref'] == reference(outcomes[-1])]
        return scores[-1] if scores else None

    def _attempt(self, rid, at, error):
        # Rejection evidence persists separately after the invalid operation rolled back.
        with self.storage.transaction():
            self.storage.append(seal({'id': 'ATTEMPT-' + uuid.uuid4().hex, 'kind': 'attempt', 'schema': 'l0_attempt_v1',
                                      'attempted_id': rid, 'at': at, 'reason': str(error)}))

    def register(self, prediction, *, at, evidence_class=FIXTURE):
        try:
            with self.storage.transaction():
                validate_prediction(prediction)
                require(prediction['id'] != 'PRED-M1-001', 'M1_READ_ONLY')
                require(evidence_class in (FIXTURE, FORWARD), 'EVIDENCE_CLASS')
                require(prediction.get('demo') is (evidence_class == FIXTURE), 'DEMO_CLASS_MISMATCH')
                require(timestamp(at) <= timestamp(prediction['frozen_at_utc']), 'REGISTRATION_AFTER_FREEZE')
                if self.storage.append(prediction):
                    initial = record('REGISTER-' + prediction['id'], 'status', prediction, at, 'Chief',
                                     {'lifecycle_status': 'RESEARCH', 'eligibility_status': 'UNASSESSED',
                                      'reason': 'registered; no independent custody proof'}, evidence_class=evidence_class, actor_identity=self.storage.actor_bindings['Chief'])
                    self.storage.append(initial)
                else:
                    old = self.snapshot()['REGISTER-' + prediction['id']]
                    require(old['evidence_class'] == evidence_class, 'CLASS_REBINDING')
            return reference(prediction)
        except Exception as exc:
            self._attempt(prediction.get('id'), at, exc)
            raise

    def put(self, r):
        return self.put_batch([r])

    def put_batch(self, records):
        try:
            with self.storage.transaction():
                for r in records:
                    self._put(r)
        except Exception as exc:
            self._attempt(records[-1].get('id'), records[-1].get('created_at_utc'), exc)
            raise

    def _put(self, r):
        self.storage.validate_record(r)
        rows = self.snapshot()
        pred = rows.get(r['prediction_ref']['id'])
        require(pred is not None and reference(pred) == r['prediction_ref'], 'PREDICTION_REFERENCE')
        for ref in r['parents']:
            require(ref['id'] in rows and reference(rows[ref['id']]) == ref, 'BAD_PARENT_REFERENCE')
        validate_lineage(r, rows)
        parents = [rows[ref['id']] for ref in r['parents']]
        require(all(timestamp(v['created_at_utc']) <= timestamp(r['created_at_utc'])
                    for v in parents if 'created_at_utc' in v), 'PARENT_FROM_FUTURE')
        require(r['evidence_class'] == rows['REGISTER-' + pred['id']]['evidence_class'], 'CLASS_MISMATCH')
        if r['id'] in rows:
            require(rows[r['id']] == r, 'ID_HASH_CONFLICT')
            return
        kind, p = r['kind'], r['payload']
        state = self.state(pred['id'])
        require(not state['eligibility_status'].startswith('INVALID') or kind == 'status', 'INVALID_SAMPLE_HALTED')
        own = [v for v in rows.values() if v.get('prediction_ref') == reference(pred)]
        if kind in ('review', 'memory', 'strategy', 'outcome', 'score'):
            require(any(v['kind'] == 'freeze' for v in own), 'NOT_FROZEN')
        if kind in ('review', 'score', 'outcome', 'freeze', 'status'):
            require(all(v.get('prediction_ref') == reference(pred) for v in parents
                        if v.get('kind') in ('freeze', 'measurement', 'outcome', 'score', 'challenge', 'disposition')),
                    'CROSS_PREDICTION_PARENT')
        if kind in ('review', 'memory', 'strategy'):
            validate_review_memory(r, parents)
            if kind == 'review':
                require(state['lifecycle_status'] in ('SCORED', 'REVIEWED', 'MEMORY_PROPOSED'), 'REVIEW_STAGE')
                self._current_review_binding(r, self.current_score(pred['id']), rows)
                self._revision_parent(r, own, 'review')
            if kind == 'memory':
                require(state['lifecycle_status'] in ('REVIEWED', 'MEMORY_PROPOSED'), 'MEMORY_STAGE')
                current_score = self.current_score(pred['id'])
                require(current_score is not None, 'CURRENT_SCORE_REQUIRED')
                reviews = [v for v in own if v['kind'] == 'review']
                require(reviews, 'CURRENT_REVIEW_REQUIRED')
                current_review = reviews[-1]
                try:
                    self._current_review_binding(current_review, current_score, rows)
                except ValueError as exc:
                    raise ValueError('CURRENT_REVIEW_REQUIRED') from exc
                require(r['record_version'] == current_review['record_version'] and
                        r['protocol_version'] == current_review['protocol_version'], 'REVIEW_MEMORY_VERSION')
                refs = [reference(v) for v in parents if v.get('kind') == 'review']
                require(refs == [reference(current_review)], 'CURRENT_REVIEW_REQUIRED')
                if 'review_ref' in p:
                    require(p['review_ref'] == reference(current_review), 'CURRENT_REVIEW_REFERENCE')
                self._revision_parent(r, own, 'memory')
        elif kind == 'founder_decision':
            require(r['actor'] == 'Founder' and p['decision'] in ('APPROVE', 'REJECT', 'DEFER'), 'FOUNDER_DECISION')
            require(p['target_ref'] in r['parents'] and p['external_evidence_ref'] in r['parents'], 'FOUNDER_EVIDENCE')
            require(timestamp(p['decided_at']) <= timestamp(r['created_at_utc']), 'FOUNDER_DECISION_TIME')
            require(p['scope'] and p['reason'], 'FOUNDER_DECISION_SCOPE')
        elif kind == 'measurement':
            require(state['lifecycle_status'] in STATES[:3], 'MEASUREMENT_AFTER_FREEZE')
            measurement(p, pred)
        elif kind == 'evidence':
            require(p['description'] and p['artifact_sha256'] and p['locator'], 'EVIDENCE_REQUIRED')
            require(len(p['artifact_sha256']) == 64 and all(c in '0123456789abcdef' for c in p['artifact_sha256']), 'ARTIFACT_HASH')
            timestamp(p['available_at'])
        elif kind == 'challenge':
            require(state['lifecycle_status'] == 'RESEARCH' and r['actor'] == 'Skeptic', 'CHALLENGE_STAGE')
            for field in ('claim', 'failure_mechanism', 'alternative', 'forecast_impact', 'resolution_test'):
                require(bool(p.get(field)), 'SUBSTANTIVE_CHALLENGE_REQUIRED')
            require(parents, 'CHALLENGE_EVIDENCE_REQUIRED')
        elif kind == 'disposition':
            require(state['lifecycle_status'] == 'CHALLENGED' and r['actor'] == 'Chief', 'DISPOSITION_STAGE')
            require(p['challenge_ref'] in r['parents'] and p['reason']
                    and p['decision'] in ('ACCEPTED', 'REJECTED', 'DEFERRED'), 'CHIEF_DISPOSITION_REQUIRED')
        elif kind == 'freeze':
            require(state['lifecycle_status'] == 'CHIEF_FINAL' and r['actor'] == 'Chief', 'FREEZE_STAGE')
            require(not any(v['kind'] == 'freeze' for v in own), 'ALREADY_FROZEN')
            require(p['frozen_at_utc'] == pred['frozen_at_utc'] == r['created_at_utc'], 'FREEZE_TIME')
            require(p['strategy_version'] == pred['strategy_version'], 'STRATEGY_VERSION')
            for field in ('strategy_ref', 'research_ref', 'memory_snapshot_ref', 'measurement_ref', 'evaluation_ref'):
                require(p[field] in r['parents'], 'FREEZE_PARENT_' + field)
            measure = rows[p['measurement_ref']['id']]
            require(measure['kind'] == 'measurement', 'MEASUREMENT_KIND')
            measurement(measure['payload'], pred)
            require(p['primary_call'] == primary(pred, measure['payload']['tie_priority']), 'PRIMARY_CALL')
            require(p['custody_status'] in ('UNVERIFIED', 'PENDING'), 'EXTERNAL_CUSTODY_NOT_VERIFIED_BY_CORE')
            if p.get('custody_ref'):
                require(p['custody_ref'] in r['parents'], 'CUSTODY_REFERENCE')
            challenges = [v for v in own if v['kind'] == 'challenge']
            dispositions = [v for v in own if v['kind'] == 'disposition']
            require(len({canonical_challenge(v) for v in challenges}) >= 3, 'THREE_CHALLENGES_REQUIRED')
            require(all(reference(c) in r['parents'] and any(
                d['payload']['challenge_ref'] == reference(c) and reference(d) in r['parents']
                for d in dispositions) for c in challenges), 'MISSING_CHIEF_DISPOSITION')
            ancestors = {v['id']: v for v in parents}
            pending = list(parents)
            while pending:
                for ref in pending.pop().get('parents', []):
                    if ref['id'] not in ancestors:
                        ancestors[ref['id']] = rows[ref['id']]
                        pending.append(rows[ref['id']])
            for v in ancestors.values():
                if v.get('kind') in ('evidence', 'memory'):
                    require(timestamp(v['payload']['available_at']) <= timestamp(pred['knowledge_cutoff_utc']), 'POST_CUTOFF_MEMORY_OR_SOURCE')
        elif kind == 'status':
            require(p['eligibility_status'] in ('UNASSESSED', 'QUARANTINED_PROVENANCE',
                    'INVALID_INTEGRITY', 'INVALID_LEAKAGE', 'INVALID_SAMPLE'), 'NO_ELIGIBILITY_PROMOTION')
            if state['eligibility_status'] == 'QUARANTINED_PROVENANCE':
                require(p['eligibility_status'] != 'UNASSESSED', 'QUARANTINE_LATCHED')
            if state['eligibility_status'].startswith('INVALID'):
                require(p['eligibility_status'] == state['eligibility_status'] and p['lifecycle_status'] == state['lifecycle_status'], 'INVALID_STATUS_LATCHED')
            current, target = state['lifecycle_status'], p['lifecycle_status']
            require(target in STATES and target != 'NEXT_VERSION_ELIGIBLE', 'NO_VERSION_ELIGIBILITY')
            require(p['reason'], 'STATUS_REASON_REQUIRED')
            prior = [v for v in own if v['kind'] == 'status'][-1]
            require(reference(prior) in r['parents'], 'PREVIOUS_STATUS_REQUIRED')
            require(target == current or STATES.index(target) == STATES.index(current) + 1, 'ILLEGAL_TRANSITION')
            owners = {'CHALLENGED': 'Skeptic', 'CHIEF_FINAL': 'Chief', 'FROZEN': 'Chief',
                      'AWAIT_OUTCOME': 'Chief', 'SCORED': 'Codex', 'REVIEWED': 'Review', 'MEMORY_PROPOSED': 'Memory'}
            require(r['actor'] == owners.get(target, 'Chief'), 'TRANSITION_OWNER')
            needed = {'FROZEN': 'freeze', 'SCORED': 'score', 'REVIEWED': 'review', 'MEMORY_PROPOSED': 'memory'}
            if target in needed:
                require(any(v.get('kind') == needed[target] for v in parents), 'TRANSITION_EVIDENCE')
            if target == 'CHALLENGED':
                require(len({canonical_challenge(v) for v in own if v['kind'] == 'challenge'}) >= 3, 'THREE_CHALLENGES_REQUIRED')
            if target in ('FROZEN', 'AWAIT_OUTCOME'):
                require(p['eligibility_status'] == 'QUARANTINED_PROVENANCE', 'CUSTODY_PENDING')
        elif kind == 'outcome':
            require(r['actor'] == 'Review' and p['status'] in ('PENDING', 'DISPUTED', 'VERIFIED'), 'OUTCOME_STATUS')
            require(any(v['kind'] == 'freeze' for v in parents), 'OUTCOME_FREEZE_REQUIRED')
            previous = [v for v in own if v['kind'] == 'outcome']
            if previous:
                require(p.get('supersedes') == reference(previous[-1]) and p['supersedes'] in r['parents']
                        and bool(p.get('revision_reason')), 'OUTCOME_REVISION_REQUIRED')
        elif kind == 'score':
            require(r['actor'] == 'Codex', 'SCORE_OWNER')
            require(state['lifecycle_status'] in ('AWAIT_OUTCOME', 'SCORED', 'REVIEWED', 'MEMORY_PROPOSED'), 'SCORE_STAGE')
            inputs = {k: rows[p[k]['id']] for k in ('freeze_ref', 'measurement_ref', 'outcome_ref')}
            require(all(p[k] in r['parents'] for k in inputs), 'SCORE_PARENTS')
            outcomes = [v for v in own if v['kind'] == 'outcome']
            require(outcomes and p['outcome_ref'] == reference(outcomes[-1]), 'STALE_OUTCOME_SELECTION')
            expected = score(pred, inputs['freeze_ref'], inputs['measurement_ref'], inputs['outcome_ref'], as_of=r['created_at_utc'])
            require(p['result'] == expected, 'SCORE_MISMATCH')
            previous = [v for v in own if v['kind'] == 'score']
            require(not any(v['payload']['outcome_ref'] == p['outcome_ref'] for v in previous), 'DUPLICATE_SCORE')
            if previous:
                require(p.get('supersedes') == reference(previous[-1]) and p['supersedes'] in r['parents'], 'SCORE_REVISION_REQUIRED')
        else:
            require(False, 'UNKNOWN_RECORD_KIND')
        self.storage.append(r)
        # Receipt/effect and resulting lifecycle state are one durable transaction.
        targets = {'freeze': 'FROZEN', 'score': 'SCORED', 'review': 'REVIEWED', 'memory': 'MEMORY_PROPOSED'}
        if kind in targets:
            prior = [v for v in own if v['kind'] == 'status'][-1]
            status = record('STATE-' + r['id'], 'status', pred, r['created_at_utc'], r['actor'],
                            {'lifecycle_status': max((state['lifecycle_status'], targets[kind]), key=STATES.index),
                             'eligibility_status': 'QUARANTINED_PROVENANCE',
                             'reason': 'atomic ' + kind + ' record; custody not independently verified'},
                            [reference(prior), reference(r)], r['evidence_class'], actor_identity=r['actor_identity'])
            self.storage.append(status)


    @staticmethod
    def _current_review_binding(review, current_score, rows):
        require(current_score is not None, 'CURRENT_SCORE_REQUIRED')
        scores = [ref for ref in review['parents'] if rows[ref['id']].get('kind') == 'score']
        require(scores == [reference(current_score)], 'CURRENT_SCORE_REFERENCE')
        require(review['record_version'] == current_score['record_version'] and
                review['protocol_version'] == current_score['protocol_version'], 'SCORE_REVIEW_VERSION')
        if 'score_ref' in review['payload']:
            require(review['payload']['score_ref'] == reference(current_score), 'CURRENT_SCORE_REFERENCE')

    @staticmethod
    def _revision_parent(r, own, kind):
        previous = [v for v in own if v['kind'] == kind]
        if previous:
            ref = reference(previous[-1])
            require(r['payload'].get('supersedes') == ref and ref in r['parents'],
                    kind.upper() + '_REVISION_REQUIRED')
        else:
            require('supersedes' not in r['payload'], kind.upper() + '_UNEXPECTED_PREDECESSOR')


def canonical_challenge(r):
    return digest(r['payload'])
