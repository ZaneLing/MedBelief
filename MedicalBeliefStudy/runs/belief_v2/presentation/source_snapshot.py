"""Same clinical facts, matched question-set positions, and removal of unknown rows."""
import hashlib,json,time
from pathlib import Path
import numpy as np
import mlx.core as mx
from phase14_run import ROOT,RUN,render
from phase6_measure import MODEL,load_model,capture
from phase9_names import score_names
from phase6_name_control import clone
from phase1_run_direct import sha,write_json,greedy_answer
def main():
    assert (RUN/'completion.json').exists();dest=RUN/'presentation';dest.mkdir(exist_ok=True);data=ROOT/'data/belief_v2'
    panel=json.loads((data/'panel.json').read_text());rows=[r for r in map(json.loads,(data/'jobs.public.jsonl').read_text().splitlines()) if r['cohort']=='test' and r['deep_capture'] and r['view']=='panel' and r['order']=='base' and r['round']==r['last_round']];assert len(rows)==24
    classes=np.load(ROOT/'results/14_fixed_panel/training_heads.npz')['classes'].tolist()
    spec={'source_sha256':sha(__file__),'protocol_sha256':sha(ROOT/'protocol/PRESENTATION_FOLLOWUP_V2.md'),'cases':24,'conditions':['known_first','known_last','compact','public_24','append_24'],'observations':120,'api_cost_usd':0}
    if (dest/'manifest.json').exists():assert json.loads((dest/'manifest.json').read_text())==spec
    else:write_json(dest/'manifest.json',spec);(dest/'source_snapshot.py').write_bytes(Path(__file__).read_bytes())
    model,tok=load_model();start=time.time()
    for i,row in enumerate(rows):
        cid=row['case_id'];known={v['evidence_id'] for g in row['revealed_groups'] for v in g['items']};kp=[v for v in panel if v['evidence_id'] in known];up=[v for v in panel if v['evidence_id'] not in known]
        base=render(row,tok,panel)
        for condition,fields in [('known_first',kp+up),('known_last',up+kp),('compact',kp),('public_24',panel),('append_24',panel)]:
            path=dest/f'{cid}_{condition}.json'
            if path.exists():continue
            use={**row,'candidate_diseases':classes,'view':'append' if condition=='append_24' else 'panel'} if condition.endswith('_24') else row
            e=render(use,tok,fields);a,z,cache=capture(model,e['ids'],e['token_groups'],keep_cache=True);score=score_names(model,z,cache,e,validate=i==0 and condition=='known_first')
            _,text,stop=greedy_answer(model,tok,z,clone(cache,len(e['ids'])),limit=48)
            try:generated=json.loads('{"diagnosis":"'+text)['diagnosis']
            except (ValueError,KeyError,TypeError):generated=None
            sp=dest/f'{cid}_{condition}.npz';np.savez_compressed(sp,**{k:np.array(v) for k,v in a.items()},input_ids=e['ids'],token_groups=e['token_groups'])
            write_json(path,dict(case_id=cid,condition=condition,candidate_diseases=use['candidate_diseases'],original_job_id=row['job_id'],input_tokens=len(e['ids']),baseline_tokens=len(base['ids']),field_order=[v['evidence_id'] for v in fields],known_evidence_ids=sorted(known),group_labels=e['group_labels'][:int(e['token_groups'].max())+1],group_token_counts=np.bincount(e['token_groups']).tolist(),generated_disease=generated,generated_text=text,free_stop=stop,state_file=str(sp.relative_to(RUN)),state_sha256=sha(sp),prompt_sha256=hashlib.sha256(e['prompt'].encode()).hexdigest(),**score))
            del a,z,cache;mx.clear_cache()
        print(json.dumps({'presentation_case':i+1,'total':24,'elapsed':round(time.time()-start,1)}),flush=True)
    hashes=json.loads((RUN/'manifest.json').read_text())['model_hashes'];assert {f:sha(MODEL/f) for f in hashes}==hashes
    write_json(dest/'completion.json',dict(complete=True,new_observations=120,weights_unchanged=True,api_cost_usd=0))
if __name__=='__main__':main()
