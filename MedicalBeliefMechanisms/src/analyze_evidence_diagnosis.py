"""Descriptive cross-task checks. Each question is a separate forward/generation."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]

def main():
    load=lambda p:list(map(json.loads,(ROOT/p).read_text().splitlines()))
    old={r['id']:r for r in load('runs/phase1b_confirm_4b/predictions.jsonl') if r['domain']=='bp'}
    repeat={r['id']:r for r in load('runs/phase1b_bp_repeat/predictions.jsonl')}
    branches=load('runs/phase1b_bp_decomposition/predictions.jsonl')
    assert len(old)==len(repeat)==54 and len(branches)==108
    branch={(r['original_id'],r['task']):r for r in branches}
    pairs=[]
    for id,r in old.items():
        numeric=branch[(id,'numeric_content')];source=branch[(id,'source_eligibility')]
        pairs.append({'id':id,'family_id':r['family_id'],'mapping':r['mapping'],'gold':r['gold'],
            'unusable_report':source['gold']=='no','numeric_correct':numeric['prediction']==numeric['gold'],
            'source_correct':source['prediction']==source['gold'],'decision_seed1_correct':r['prediction']==r['gold'],
            'decision_seed2_correct':repeat[id]['prediction']==r['gold'],
            'numeric_prediction':numeric['prediction'],'source_prediction':source['prediction'],
            'decision_seed1':r['prediction'],'decision_seed2':repeat[id]['prediction']})
    groups={}
    for name,pp in [('all',pairs),('present_but_unusable',[r for r in pairs if r['unusable_report']])]:
        groups[name]={'n':len(pp),'families':len({r['family_id'] for r in pp})}
        for field in ['numeric_correct','source_correct','decision_seed1_correct','decision_seed2_correct']:
            groups[name][field]=sum(r[field] for r in pp)
        for seed in [1,2]:
            groups[name][f'both_branches_correct_decision_seed{seed}_wrong']=sum(r['numeric_correct'] and r['source_correct'] and not r[f'decision_seed{seed}_correct'] for r in pp)
        groups[name]['both_seeds_wrong']=sum(not r['decision_seed1_correct'] and not r['decision_seed2_correct'] for r in pp)
        groups[name]['both_branches_correct_both_decision_seeds_wrong']=sum(r['numeric_correct'] and r['source_correct'] and not r['decision_seed1_correct'] and not r['decision_seed2_correct'] for r in pp)
        groups[name]['both_branches_correct_both_decision_seeds_wrong_families']=len({r['family_id'] for r in pp if r['numeric_correct'] and r['source_correct'] and not r['decision_seed1_correct'] and not r['decision_seed2_correct']})
    result={'groups':groups,'paired_records':pairs,'api_cost_usd':0,
        'warning':'Post-hoc selected domain and reused cases. Separate branch questions can change attention; this is no proof of simultaneous knowledge, internal belief, or causal mechanism.'}
    out=ROOT/'runs/phase1b_bp_decomposition';(out/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(groups,indent=2))

if __name__=='__main__':main()
