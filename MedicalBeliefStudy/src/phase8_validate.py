"""Check cached anchor replay against complete patched-prompt recomputation."""
import json
import numpy as np
import mlx.core as mx
from mlx_lm.models.base import create_attention_mask
from phase6_measure import ROOT, load_model, render, capture
from phase1_run_direct import output_head, scores, write_json, sha
from content_and_depth import replay_anchor

def full_patched(model,ids,layer,patch):
    h=model.model.embed_tokens(mx.array([ids]));mask=create_attention_mask(h,None)
    for l,b in enumerate(model.model.layers):
        h=b(h,mask,None)
        if l==layer:h=mx.concatenate([h[:,:-1,:],patch[None,None,:]],axis=1)
    return output_head(model,h[0,-1]).astype(mx.float32)

def main():
    run=ROOT/'runs/full49_v1';assert (run/'completion.json').exists()
    rows=[json.loads(s) for s in (ROOT/'data/full49_v1/jobs.public.jsonl').read_text().splitlines()]
    selected=[];families=set();lookup={(r['case_id'],r['order'],r['round'],r['rotation']):r for r in rows}
    for r in rows:
        if r['family'] not in families and r['order']=='base' and r['round']==r['last_round']//2 and r['rotation']==0:
            selected.append(r);families.add(r['family'])
    assert len(selected)==6;model,tok=load_model();checks=[]
    for row in selected:
        e=render(row,tok);old=render(lookup[row['case_id'],'base',row['round']-1,0],tok)
        a,z,cache=capture(model,e['ids'],keep_cache=True);b,_,_=capture(model,old['ids']);states=a['residual_stages'];oldstates=b['residual_stages']
        for l in [25,27]:
            pre,att,mid,mlp,post=[states[l,j] for j in range(5)];block=model.model.layers[l]
            mids=pre+oldstates[l,1];attpatch=mids+block.mlp(block.post_attention_layernorm(mids));mlppatch=mid+oldstates[l,3]
            for name,patch in [('old_attention',attpatch),('old_mlp',mlppatch)]:
                cached=replay_anchor(model,patch[None,:],l,cache,len(e['ids']))[0];full=full_patched(model,e['ids'],l,patch)
                zc,_,qc=scores(cached,e['candidate_ids']);zf,_,qf=scores(full,e['candidate_ids'])
                m=(qc+qf)/2;distance=float(.5*np.sum(qc*np.log((qc+1e-12)/(m+1e-12))+qf*np.log((qf+1e-12)/(m+1e-12))))
                record={'case_id':row['case_id'],'family':row['family'],'layer':l+1,'patch':name,'max_candidate_logit_error':float(np.max(np.abs(zc-zf))),
                        'distribution_js':distance,'same_argmax':bool(qc.argmax()==qf.argmax())}
                record['passed']=record['same_argmax'] and distance<1e-5 and record['max_candidate_logit_error']<.1;checks.append(record)
                print(json.dumps(record),flush=True)
        del a,b,cache,states,oldstates;mx.clear_cache()
    write_json(run/'replay_validation.json',{'source_sha256':sha(__file__),'checks':checks,'all_pass':all(r['passed'] for r in checks)})
    assert all(r['passed'] for r in checks)

if __name__=='__main__':main()
