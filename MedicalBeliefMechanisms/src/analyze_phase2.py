"""Stage 2 paired behavior analysis; eligible domains and diagnostic BP kept distinct."""
import argparse,json
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

def paired(rows,field,a,b,keys):
    groups=defaultdict(dict)
    for r in rows:
        if r.get(field) in [a,b]:
            key=tuple(r.get(k) for k in keys);assert r[field] not in groups[key]
            groups[key][r[field]]=r
    by_family=defaultdict(list);changes=[];positive=negative=0
    for g in groups.values():
        if set(g)!={a,b}:continue
        ra,rb=g[a],g[b];d=int(ra['prediction']!=ra['gold'])-int(rb['prediction']!=rb['gold'])
        by_family[ra['family_id']].append(d);positive+=d>0;negative+=d<0
        if ra['prediction']!=rb['prediction']:
            changes.append({'a_id':ra['id'],'b_id':rb['id'],'a_prediction':ra['prediction'],'b_prediction':rb['prediction'],'a_gold':ra['gold'],'b_gold':rb['gold'],'a_error_minus_b_error':d})
    means=np.array([np.mean(x) for x in by_family.values()]);rng=np.random.default_rng(20261118)
    boots=np.mean(rng.choice(means,size=(5000,len(means)),replace=True),axis=1) if len(means) else np.array([np.nan])
    return {'a':a,'b':b,'pairs':sum(map(len,by_family.values())),'family_clusters':len(by_family),'error_difference':float(means.mean()) if len(means) else None,
        'family_bootstrap_95_percentile':np.quantile(boots,[.025,.975]).tolist(),'a_hurts':int(positive),'a_helps':int(negative),
        'different_decisions':len(changes),'changes':changes,'caution':'Small family count; a degenerate zero bootstrap interval is not a population equivalence bound.'}

def cell(rr):
    return {'n':len(rr),'correct':sum(x['prediction']==x['gold'] for x in rr),'invalid':sum(x['prediction'] is None for x in rr),
        'answers':dict(Counter(str(x['prediction']) for x in rr)),'families':len({x['family_id'] for x in rr})}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-id',default='phase2_pilot_4b');a=ap.parse_args();run=ROOT/'runs'/a.run_id
    meta=json.loads((run/'metadata.json').read_text());stimuli={r['id']:r for r in map(json.loads,(ROOT/meta['data']).read_text().splitlines())}
    rr=list(map(json.loads,(run/'predictions.jsonl').read_text().splitlines()));assert len(rr)==len(stimuli) and {r['id'] for r in rr}==set(stimuli)
    subsets={'primary_aki_dvt':[r for r in rr if r['domain'] in ['aki','dvt']],'diagnostic_bp':[r for r in rr if r['domain']=='bp']}
    result={'run_id':a.run_id,'records':len(rr),'overall':cell(rr),'subsets':{},'generation_tokens':sum(r['generated_tokens'] for r in rr),'api_cost_usd':0}
    for scope,rows in subsets.items():
        if not rows:continue
        cells=[]
        sources=sorted({r['source'] for r in rows})
        histories=[h for h in ['current_only','old_facts','own_judgment_summary','own_raw_final'] if any(r['history']==h for r in rows)]
        for h in histories:
            for s in sources:
                r=[x for x in rows if x['history']==h and x['source']==s];cells.append({'history':h,'source':s,**cell(r)})
        effect=paired(rows,'history','own_judgment_summary','old_facts',['family_id','old_sign','current_sign','source'])
        counter=[r for r in rows if r['old_sign'] is not None and r['observed_initial'] in ['yes','no'] and r['observed_initial']!=r['current_sign']]
        details={}
        for s in sources:
            scoped=[r for r in counter if r['source']==s]
            details[s]={'paired_effect':paired(scoped,'history','own_judgment_summary','old_facts',['family_id','old_sign','current_sign','source'])}
            for h in [h for h in histories if h!='current_only']:
                x=[r for r in scoped if r['history']==h]
                details[s][h]={'n':len(x),'answers_follow_old_judgment':sum(r['prediction']==r['observed_initial'] for r in x),
                    'answers_follow_current_report_numbers':sum(r['prediction']==r['current_sign'] for r in x),'correct':sum(r['prediction']==r['gold'] for r in x)}
        baseline={}
        for d in sorted({r['domain'] for r in rows}):
            r=[x for x in rows if x['domain']==d and x['history']=='current_only'];c=cell(r)
            c['classes']={s:cell([x for x in r if x['gold']==s]) for s in ['yes','no','unknown']}
            c['accuracy_gate']=c['correct']/c['n']>=.9;c['class_gate']=all(v['correct']/v['n']>=.8 for v in c['classes'].values() if v['n'])
            c['option_rotation_gate']='Not re-estimated: one mapping per pilot family; original phase1B rotation check retained'
            baseline[d]=c
        item={'overall':cell(rows),'cells':cells,'old_judgment_effect':effect,'opposed_old_and_new':details,'current_only_checks':baseline}
        item['domain_details']={}
        for d in sorted({r['domain'] for r in rows}):
            dr=[r for r in rows if r['domain']==d]
            item['domain_details'][d]={'overall':cell(dr),'history_totals':{h:cell([r for r in dr if r['history']==h]) for h in histories},
                'summary_effect':paired(dr,'history','own_judgment_summary','old_facts',['family_id','old_sign','current_sign','source'])}
            if 'own_raw_final' in histories:item['domain_details'][d]['raw_effect']=paired(dr,'history','own_raw_final','old_facts',['family_id','old_sign','current_sign','source'])
        if 'own_raw_final' in histories:
            item['raw_answer_effect']=paired(rows,'history','own_raw_final','old_facts',['family_id','old_sign','current_sign','source'])
            correct_initial=[r for r in rows if r.get('initial_correct')]
            incorrect_initial=[r for r in rows if r.get('initial_correct') is False]
            item['initial_judgment_strata']={
                'reason':'Phase2B initial judgments had a natural error. Keep full assigned-branch analysis, and add transparent correct-initial-only sensitivity analysis; no stimuli or recorded answers changed.',
                'initial_correct_rows':cell(correct_initial),'initial_incorrect_rows':cell(incorrect_initial),
                'summary_effect_correct_initial':paired(correct_initial,'history','own_judgment_summary','old_facts',['family_id','old_sign','current_sign','source']),
                'raw_effect_correct_initial':paired(correct_initial,'history','own_raw_final','old_facts',['family_id','old_sign','current_sign','source'])}
            item['raw_branch_note']='Branches were assigned by old-report numeric direction, not retroactively by the observed model judgment. An incorrect initial answer may therefore not actually oppose current numerical evidence.'
        result['subsets'][scope]=item
    errors=[{**r,'messages':stimuli[r['id']].get('messages'),'prompt':stimuli[r['id']]['prompt']} for r in rr if r['prediction']!=r['gold']]
    (run/'analysis_v2.json').write_text(json.dumps(result,indent=2)+'\n');(run/'errors_with_inputs.json').write_text(json.dumps(errors,indent=2)+'\n')
    print(json.dumps({k:{'overall':v['overall'],'effect':{a:b for a,b in v['old_judgment_effect'].items() if a!='changes'}} for k,v in result['subsets'].items()},indent=2))

if __name__=='__main__':main()
