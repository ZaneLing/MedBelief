"""Paired exploratory results; variants are not independent patients."""
from pathlib import Path
from collections import defaultdict,Counter
import json
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

def grouped_difference(rows,key,value_a,value_b,match_keys):
    pairs=defaultdict(dict)
    for r in rows:
        if r[key] in [value_a,value_b]:pairs[tuple(r[k] for k in match_keys)][r[key]]=r
    family=defaultdict(list);changes=[]
    for pair in pairs.values():
        if set(pair)!={value_a,value_b}:continue
        a,b=pair[value_a],pair[value_b]
        diff=int(a['prediction']!=a['gold'])-int(b['prediction']!=b['gold'])
        family[a['family_id']].append(diff)
        if a['prediction']!=b['prediction']:changes.append({'a_id':a['id'],'b_id':b['id'],'a_prediction':a['prediction'],'b_prediction':b['prediction'],'a_gold':a['gold'],'b_gold':b['gold']})
    means=np.array([np.mean(v) for v in family.values()]);rng=np.random.default_rng(20261118)
    boot=np.array([np.mean(rng.choice(means,size=len(means),replace=True)) for _ in range(5000)])
    return {'error_difference_a_minus_b':float(means.mean()),'family_bootstrap_95_percentile':np.quantile(boot,[.025,.975]).tolist(),
        'family_clusters':len(family),'paired_rows':sum(map(len,family.values())),'different_decisions':len(changes),'changes':changes}

def main():
    run=ROOT/'runs/phase2_pilot_4b';rr=[json.loads(x) for x in (run/'predictions.jsonl').read_text().splitlines()]
    stimuli={r['id']:r for r in map(json.loads,(ROOT/'data/phase2_pilot_current.jsonl').read_text().splitlines())}
    assert len(rr)==len(stimuli) and {r['id'] for r in rr}==set(stimuli)
    tables=[]
    for d in ['all','aki','bp','dvt']:
        for history in ['current_only','old_facts','own_judgment_summary']:
            for source in ['both_valid','relevant_withdrawn','irrelevant_withdrawn']:
                r=[r for r in rr if (d=='all' or r['domain']==d) and r['history']==history and r['source']==source]
                tables.append({'domain':d,'history':history,'source':source,'n':len(r),'correct':sum(x['prediction']==x['gold'] for x in r),
                    'invalid':sum(x['prediction'] is None for x in r),'answers':dict(Counter(str(x['prediction']) for x in r))})
    own=grouped_difference(rr,'history','own_judgment_summary','old_facts',['family_id','old_sign','current_sign','source'])
    withdrawal={h:grouped_difference([r for r in rr if r['history']==h],'source','relevant_withdrawn','irrelevant_withdrawn',['family_id','old_sign','current_sign']) for h in ['current_only','old_facts','own_judgment_summary']}
    errors=[{**r,'prompt':stimuli[r['id']]['prompt'],'messages':stimuli[r['id']]['messages']} for r in rr if r['prediction']!=r['gold']]
    result={'records':len(rr),'families':len({r['family_id'] for r in rr}),'correct':sum(r['prediction']==r['gold'] for r in rr),
        'invalid':sum(r['prediction'] is None for r in rr),'cells':tables,'own_versus_facts':own,'withdrawal_error_difference':withdrawal,
        'generation_tokens':sum(r['generated_tokens'] for r in rr),'api_cost_usd':0}
    (run/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    (run/'errors_with_inputs.json').write_text(json.dumps(errors,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['cells','withdrawal_error_difference']},indent=2))

if __name__=='__main__':main()
