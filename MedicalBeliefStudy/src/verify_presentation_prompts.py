"""Rebuild each presentation prompt and verify its exact input, without model inference."""
import hashlib,json
import numpy as np
from mlx_lm.tokenizer_utils import load
from phase14_run import ROOT,RUN,render
from phase6_measure import MODEL
def main():
    tok=load(MODEL);panel=json.loads((ROOT/'data/belief_v2/panel.json').read_text())
    rows=[r for r in map(json.loads,(ROOT/'data/belief_v2/jobs.public.jsonl').read_text().splitlines()) if r['cohort']=='test' and r['deep_capture'] and r['view']=='panel' and r['order']=='base' and r['round']==r['last_round']]
    classes=np.load(ROOT/'results/14_fixed_panel/training_heads.npz')['classes'].tolist();checked=[]
    for row in rows:
        known={v['evidence_id'] for g in row['revealed_groups'] for v in g['items']};kp=[v for v in panel if v['evidence_id'] in known];up=[v for v in panel if v['evidence_id'] not in known]
        for cond,fields in [('known_first',kp+up),('known_last',up+kp),('compact',kp),('public_24',panel),('append_24',panel)]:
            r=json.loads((RUN/'presentation'/f"{row['case_id']}_{cond}.json").read_text())
            use={**row,'candidate_diseases':classes,'view':'append' if cond=='append_24' else 'panel'} if cond.endswith('_24') else row
            e=render(use,tok,fields);assert hashlib.sha256(e['prompt'].encode()).hexdigest()==r['prompt_sha256']
            with np.load(RUN/r['state_file']) as a:assert np.array_equal(a['input_ids'],e['ids']) and np.array_equal(a['token_groups'],e['token_groups'])
            checked.append({'case_id':row['case_id'],'condition':cond,'actual_view':use['view'],'candidate_count':len(use['candidate_diseases']),'prompt_sha256':r['prompt_sha256']})
    (RUN/'presentation/prompt_verification.json').write_text(json.dumps({'verified_prompts':len(checked),'all_exact_match':True,'model_inference':False,'records':checked},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'verified_prompts':len(checked),'all_exact_match':True}),flush=True)
if __name__=='__main__':main()
