"""Empty-input preferences and candidate-order controls after a template finding."""
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
    assert (RUN/'completion.json').exists();dest=RUN/'template_prior';dest.mkdir(exist_ok=True);data=ROOT/'data/belief_v2';panel=json.loads((data/'panel.json').read_text())
    rows=[r for r in map(json.loads,(data/'jobs.public.jsonl').read_text().splitlines()) if r['cohort']=='test' and r['deep_capture'] and r['view']=='panel' and r['order']=='base' and r['round']==r['last_round']];assert len(rows)==24
    spec={'source_sha256':sha(__file__),'protocol_sha256':sha(ROOT/'protocol/TEMPLATE_PRIOR_V2.md'),'cases':24,'observations':96,'api_cost_usd':0}
    if (dest/'manifest.json').exists():assert json.loads((dest/'manifest.json').read_text())==spec
    else:write_json(dest/'manifest.json',spec);(dest/'source_snapshot.py').write_bytes(Path(__file__).read_bytes())
    model,tok=load_model();start=time.time()
    for i,row in enumerate(rows):
        ds=row['candidate_diseases'];cid=row['case_id']
        conditions=[('empty_panel',{**row,'revealed_groups':[]}),('empty_append',{**row,'revealed_groups':[],'view':'append'}),('reverse_candidates',{**row,'candidate_diseases':list(reversed(ds))}),('rotate_candidates',{**row,'candidate_diseases':ds[16:]+ds[:16]})]
        for label,use in conditions:
            p=dest/f'{cid}_{label}.json'
            if p.exists():continue
            e=render(use,tok,panel);a,z,cache=capture(model,e['ids'],e['token_groups'],keep_cache=True);score=score_names(model,z,cache,e,validate=i==0 and label=='empty_panel')
            _,text,stop=greedy_answer(model,tok,z,clone(cache,len(e['ids'])),limit=48)
            try:generated=json.loads('{"diagnosis":"'+text)['diagnosis']
            except (ValueError,KeyError,TypeError):generated=None
            reindex=[use['candidate_diseases'].index(d) for d in ds]
            for key in ['q_sequence','q_token_mean','log_probability','token_log_probability']:score[key]=[score[key][j] for j in reindex]
            sp=dest/f'{cid}_{label}.npz';np.savez_compressed(sp,**{k:np.array(v) for k,v in a.items()},input_ids=e['ids'],token_groups=e['token_groups'])
            write_json(p,dict(case_id=cid,condition=label,canonical_diseases=ds,presented_diseases=use['candidate_diseases'],input_tokens=len(e['ids']),generated_disease=generated,generated_text=text,free_stop=stop,state_file=str(sp.relative_to(RUN)),state_sha256=sha(sp),prompt_sha256=hashlib.sha256(e['prompt'].encode()).hexdigest(),**score))
            del a,z,cache;mx.clear_cache()
        print(json.dumps({'prior_case':i+1,'total':24,'elapsed':round(time.time()-start,1)}),flush=True)
    hashes=json.loads((RUN/'manifest.json').read_text())['model_hashes'];assert {f:sha(MODEL/f) for f in hashes}==hashes;write_json(dest/'completion.json',dict(complete=True,observations=96,weights_unchanged=True,api_cost_usd=0))
if __name__=='__main__':main()
