"""Apply the frozen calibration gates, counting censored outputs as failures."""
from pathlib import Path
from collections import defaultdict
import argparse,json
ROOT=Path(__file__).resolve().parents[1]

def analyze(run_id):
    run=ROOT/'runs'/run_id
    rows=[json.loads(x) for x in (run/'predictions.jsonl').read_text().splitlines()]
    assert len(rows)==162 and len({r['id'] for r in rows})==162
    result={'run_id':run_id,'records':len(rows),'domains':{},'all_gates_pass':True,'errors':[]}
    for domain in ['aki','bp','dvt']:
        rr=[r for r in rows if r['domain']==domain]
        classes={c:{'correct':sum(r['prediction']==c for r in rr if r['gold']==c),'n':sum(r['gold']==c for r in rr)} for c in ['yes','no','unknown']}
        for v in classes.values():v['accuracy']=v['correct']/v['n']
        groups=defaultdict(list)
        for r in rr:groups[r['scenario_id']].append(r)
        assert all(len(v)==3 for v in groups.values())
        consistent=sum(all(r['prediction'] is not None for r in g) and len({r['prediction'] for r in g})==1 for g in groups.values())
        correct=sum(r['prediction']==r['gold'] for r in rr);accuracy=correct/len(rr)
        item={'correct':correct,'n':len(rr),'accuracy':accuracy,'classes':classes,'rotation_consistent':consistent,'rotation_scenarios':len(groups),'rotation_consistency':consistent/len(groups),'invalid_or_censored':sum(r['prediction'] is None for r in rr)}
        item['passes']={'domain_accuracy':accuracy>=.9,'class_accuracy':all(c['accuracy']>=.8 for c in classes.values()),'rotation_consistency':item['rotation_consistency']>=.95}
        item['all_gates_pass']=all(item['passes'].values());result['domains'][domain]=item
        result['all_gates_pass'] &= item['all_gates_pass']
    result['errors']=[{k:r[k] for k in ['id','domain','gold','prediction','finish_reason','generated_tokens']} for r in rows if r['prediction']!=r['gold']]
    (run/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='errors'},indent=2))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run_id');analyze(p.parse_args().run_id)
