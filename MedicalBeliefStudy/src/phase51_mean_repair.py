"""Recompute auxiliary evidence means with FP32 reduction; preserve frozen outputs."""
import json,time
import numpy as np
import mlx.core as mx
from belief_v4_core import *

def main():
    dest=RUN/'mean_repair';dest.mkdir(parents=True,exist_ok=True)
    cases=list(map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines()))
    spec=dict(patients=len(cases),conditions=2*len(cases),source_sha256=sha(__file__),core_sha256=sha(ROOT/'src/belief_v4_core.py'),cases_sha256=sha(DATA/'cases.private.jsonl'),reason='Auxiliary FP16 mean reduction overflow; native forward and disease scores unchanged',api_cost_usd=0)
    if (dest/'manifest.json').exists():assert json.loads((dest/'manifest.json').read_text())==spec
    else:write_json(dest/'manifest.json',spec)
    model,tok=load_model();start=time.time();n=0;checks=[]
    for c in cases:
        for cond in ['neutral','wrong']:
            row=next(r for r in jobs_for(c) if r['mode']=='name' and r['order']=='base' and r['round']==r['last_round'] and r['condition']==cond)
            p=dest/(row['job_id']+'.npz')
            if p.exists():continue
            e=render(c,row,tok);h=model.model.embed_tokens(mx.array([e['ids']]));mask=create_attention_mask(h,None);means=[]
            for b in model.model.layers:
                h=b(h,mask=mask,cache=None);v=h[0].astype(mx.float32)
                means.append(mx.stack([v[mx.array(np.flatnonzero(e['token_groups']==g))].mean(0) for g in [2,1]]))
            a=mx.stack(means);mx.eval(a,h);a=np.array(a);assert np.isfinite(a).all()
            old=json.loads((RUN/'observations'/(row['job_id']+'.json')).read_text())
            with np.load(RUN/old['state_file']) as s:
                anchor_error=float(np.max(np.abs(np.array(h[0,-1]).astype(float)-s['residual_stages'][-1,-1].astype(float))))
                original_nonfinite=int((~np.isfinite(s['evidence_means'])).sum())
            assert anchor_error<.02
            np.savez_compressed(p,evidence_means=a,anchor_error=anchor_error,original_nonfinite=original_nonfinite)
            n+=1;del h,a;mx.clear_cache()
            if n==1 or n%100==0:print(json.dumps(dict(repaired=n,expected=2*len(cases),seconds=round(time.time()-start,1))),flush=True)
    files=list(dest.glob('*.npz'));assert len(files)==2*len(cases)
    hashes=json.loads((RUN/'manifest.json').read_text())['model_hashes'];assert {k:sha(MODEL/k) for k in hashes}==hashes
    write_json(dest/'completion.json',dict(complete=True,conditions=len(files),patients=len(cases),weights_unchanged=True,api_cost_usd=0))

if __name__=='__main__':main()
