"""Fully invented example. Scripted records, not an AI/model learning result."""
import json
from d0.records import build, reference


def sample():
    rows = []
    def add(rid, kind, payload, at, target, parents=(), subject=None):
        r = build(rid, kind, payload, source={'name':'Invented engineering example',
                  'uri':'fixture:synthetic-d0', 'content':json.dumps(payload,sort_keys=True)},
                  acquired_at=at, created_at=at, target_at=target, parents=[reference(v) for v in parents],
                  prediction_ref=reference(subject) if subject else None,
                  actor_identity='synthetic:scripted-example', origin='SYNTHETIC')
        rows.append(r); return r
    first='2040-01-01T18:00:00Z'; target='2040-01-02T21:00:00Z'; later='2040-01-02T22:00:00Z'
    market=add('D0-MARKET-1','market',{'session':'2040-01-01','close':'100.00',
               'price_basis':'invented; not an official market close'},first,first)
    news=add('D0-NEWS-1','news',{'summary':'Invented mixed signals; no real publication.'},first,target)
    research=add('D0-RESEARCH-1','research',{'question':'What should be examined in this invented scenario?',
                 'knowledge_cutoff_utc':first},first,target,[market,news])
    pred=add('D0-PREDICTION-1','prediction',{'probs':{'UP':.6,'FLAT':.3,'DOWN':.1},
             'rationale':'Scripted optimistic hypothesis, not a model call.', 'knowledge_cutoff_utc':first},first,target,[research])
    outcome=add('D0-OUTCOME-1','outcome',{'observation':'Invented terminal value 98.00; lower than baseline 100.00.',
                'close':'98.00','verification':'UNVERIFIED_SYNTHETIC'},later,target,[pred],pred)
    review=add('D0-REVIEW-1','review',{'findings':['UP was the highest declared probability; invented observation moved lower.'],
               'contrary_evidence':['Mixed scenario signals were underweighted in this scripted rationale.'],
               'limitations':['One synthetic example cannot establish learning or forecast skill.']},later,target,[outcome],pred)
    memory=add('D0-MEMORY-1','memory',{'lesson':'Hypothesis: explicitly consider opposing signals next round.',
                'scope':'this synthetic research exercise only',
                'falsification_condition':'Further examples may show no useful difference.',
                'status':'PROPOSED_RESEARCH_NOTE'},later,target,[review],pred)
    add('D0-RESEARCH-2','research',{'question':'Examine opposing signals using the prior proposed note.',
        'knowledge_cutoff_utc':'2040-01-03T18:00:00Z','memory_use':'Explicit research input; not strategy activation.'},
        '2040-01-03T18:00:00Z','2040-01-04T21:00:00Z',[memory])
    return rows


if __name__=='__main__':
    print(json.dumps(sample(),indent=2,ensure_ascii=False,allow_nan=False))
