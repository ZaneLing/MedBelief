"""Independent rule verification, challenge strata, and cached-LLM audit."""
import ast
import collections
import csv
import json
from pathlib import Path

import numpy as np

from ddx_classifier_expansion import DATA, DISEASES, META, RAW, ROOT, dump, sha
from ddx_generator_audit import ALLOW, OUT, SUPPORT, compatible


def main():
    summary=json.loads((OUT/'summary.json').read_text())
    # Independently use Python sets rather than disease bit masks on all validation patients.
    counts=collections.Counter()
    with (RAW/'validate.csv').open() as f:
        for row in csv.DictReader(f):
            keys={t.partition('_@_')[0] for t in ast.literal_eval(row['EVIDENCES'])}
            candidates={d for d,allowed in ALLOW.items() if keys<=allowed}
            counts['n']+=1;counts['unique']+=len(candidates)==1
            counts['true_included']+=row['PATHOLOGY'] in candidates
    assert counts['unique']==summary['validation']['counts']['unique']
    assert counts['true_included']==counts['n']==132448
    # Check every stored certificate using independently constructed sets.
    witnesses=collections.Counter()
    for split in ['test','validate']:
        with (OUT/f'{split}_cases.csv').open() as f:
            for row in csv.DictReader(f):
                if row['candidate_count']!='1':continue
                ks=row['certificate'].split(';')
                ds={d for d,allowed in ALLOW.items() if set(ks)<=allowed}
                assert ds=={row['gold']}
                witnesses[split]+=1
    # Dependence-aware uncertainty: resample question groups, keeping all labels in each group.
    challenge={}
    for split in ['test','validate']:
        rows=list(csv.DictReader((OUT/f'native_challenge_{split}_predictions.csv').open()))
        groups=collections.defaultdict(list)
        for row in rows:groups[row['question_group_id']].append(row)
        gvalues=[]
        for rs in groups.values():
            v=sum(r['logistic_evidence_values']==r['gold'] for r in rs)
            q=sum(r['logistic_evidence_presence']==r['gold'] for r in rs)
            gvalues.append([v-q,len(rs)])
        a=np.array(gvalues);rng=np.random.default_rng(20261119)
        draws=rng.integers(0,len(a),size=(4000,len(a)))
        samples=a[draws].sum(axis=1)
        ci=np.quantile(samples[:,0]/samples[:,1],[.025,.975]).tolist()
        strata=collections.defaultdict(list)
        for rs in groups.values():
            pair=' | '.join(sorted({r['gold'] for r in rs}))
            strata[pair]+=rs
        stratum_results=[]
        for pair,rs in strata.items():
            stratum_results.append(dict(labels=pair,n=len(rs),
                presence_accuracy=sum(r['logistic_evidence_presence']==r['gold'] for r in rs)/len(rs),
                values_accuracy=sum(r['logistic_evidence_values']==r['gold'] for r in rs)/len(rs)))
        excluded={'Acute rhinosinusitis','Chronic rhinosinusitis'}
        other=[r for rs in groups.values() if not({r['gold'] for r in rs}&excluded) for r in rs]
        challenge[split]=dict(group_bootstrap_values_minus_presence95=ci,
            strata=sorted(stratum_results,key=lambda r:-r['n']),
            excluding_rhinosinusitis=dict(n=len(other),
                presence_accuracy=sum(r['logistic_evidence_presence']==r['gold'] for r in other)/len(other),
                values_accuracy=sum(r['logistic_evidence_values']==r['gold'] for r in other)/len(other)))
    # Original cached LLM outputs: descriptive retrospective audit, no new inference.
    cases=[json.loads(s) for s in (ROOT/'data/belief_v2/cases.private.jsonl').read_text().splitlines()]
    llm={}
    for name,run in [('Qwen3-1.7B-FP16','belief_v2'),('Qwen3-4B-8bit','belief_v2_4b')]:
        rdir=ROOT/'runs'/run
        diseases=json.loads((rdir/'manifest.json').read_text())['candidate_diseases']
        totals=collections.Counter();records=[]
        for c in cases:
            endpoint=len(c['orders']['base'])
            r=json.loads((rdir/'observations'/f"{c['case_id']}_append_base_t{endpoint:02d}.json").read_text())
            pred=diseases[int(np.argmax(r['q_sequence']))]
            keys={v['evidence_id'] for group in c['explicit_evidence_groups'].values() for v in group}
            ds={d for d,allowed in ALLOW.items() if keys<=allowed}
            ref=c['reference_differential'];top=max(ref,key=ref.get);gold=c['gold_disease']
            totals['n']+=1;totals['gold_correct']+=pred==gold
            totals['matches_reference_top']+=pred==top
            totals['prediction_in_reference']+=pred in ref
            totals['prediction_incompatible_with_catalog']+=pred not in ds
            totals['wrong']+=pred!=gold
            totals['wrong_but_in_reference']+=pred!=gold and pred in ref
            totals['wrong_and_matches_reference_top']+=pred!=gold and pred==top
            totals['codebook_singleton']+=len(ds)==1
            records.append(dict(case_id=c['case_id'],gold=gold,prediction=pred,
                reference_top=top,prediction_reference_score=ref.get(pred,0),
                catalog_candidates=sorted(ds)))
        llm[name]=dict(counts=dict(totals),records=records,
            caveat='Same selected 120 patients and historical scoring interface. Reference membership is not clinical correctness; full-name likelihood choice is not identical to unconstrained generation.')
    # Removing every individually identifying evidence need not remove combinations.
    reduced=collections.Counter()
    for c in map(json.loads,(DATA/'test_cases.jsonl').read_text().splitlines()):
        ks=[k for k in c['keys'] if SUPPORT[k].bit_count()>1]
        b=compatible(ks);reduced['n']+=1;reduced['unique']+=b.bit_count()==1
    dump(OUT/'followup.json',dict(independent_set_rule_validation=dict(counts),
        independently_verified_certificates=dict(witnesses),challenge_strata=challenge,
        cached_llm_audit=llm,no_exclusive_evidence_support=dict(reduced),
        source_code_sha256=sha(Path(__file__))))
    print('Independent rule:',dict(counts),'certificates:',dict(witnesses),flush=True)
    print('Challenge without rhinosinusitis:',{s:r['excluding_rhinosinusitis'] for s,r in challenge.items()},flush=True)
    print('Cached LLM:',{m:r['counts'] for m,r in llm.items()},flush=True)
    print('No exclusive evidence support',dict(reduced),flush=True)


if __name__=='__main__':main()
