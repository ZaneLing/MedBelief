"""Matched natural-history state transfers with recomputed downstream caches."""
import argparse,json,time,hashlib
import numpy as np
import mlx.core as mx
from belief_v4_core import *

def transfer_forward(model,e,layer,positions,delta):
    """Exact replacement also supports disjoint earlier-fact spans."""
    positions=np.asarray(positions);assert len(positions)>0 and np.all(np.diff(positions)>0)
    cuts=np.r_[0,np.flatnonzero(np.diff(positions)!=1)+1,len(positions)]
    h=model.model.embed_tokens(mx.array([e['ids']]));mask=create_attention_mask(h,None);cache=[]
    for l,b in enumerate(model.model.layers):
        cc=KVCache();h=b(h,mask=mask,cache=cc);cache.append(cc)
        if l+1==layer:
            before=h[0,mx.array(positions)];after=(before.astype(mx.float32)+mx.array(delta,mx.float32)).astype(h.dtype)
            parts=[];cursor=0
            for lo,hi in zip(cuts[:-1],cuts[1:]):
                start=int(positions[lo]);stop=int(positions[hi-1])+1
                parts.extend([h[:,cursor:start],after[None,lo:hi]]);cursor=stop
            parts.append(h[:,cursor:]);h=mx.concatenate(parts,axis=1)
    z=output_head(model,h[0,-1]).astype(mx.float32);mx.eval(z,before,after)
    return z,cache,np.array(before),np.array(after)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--limit',type=int,default=0);args=ap.parse_args()
    cases=[c for c in map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines()) if c['mechanism_capture']]
    cases.sort(key=lambda c:c['cohort']!='development')
    dest=RUN/'patches';dest.mkdir(parents=True,exist_ok=True)
    spec=dict(cases=len(cases),layers=[14,21],sites=['new','old','anchor'],conditions=['neutral_to_wrong','random_0','random_1','wrong_to_neutral'],self_checks_per_layer=1,conditions_per_case=26,source_sha256=sha(__file__),core_sha256=sha(ROOT/'src/belief_v4_core.py'),protocol_sha256=sha(ROOT/'research_v4/PROTOCOL.md'),cases_sha256=sha(DATA/'cases.private.jsonl'),api_cost_usd=0)
    if (dest/'manifest.json').exists():assert json.loads((dest/'manifest.json').read_text())==spec
    else:write_json(dest/'manifest.json',spec);(dest/'source_snapshot.py').write_bytes(Path(__file__).read_bytes())
    model,tok=load_model();start=time.time();done=0
    for i,c in enumerate(cases):
        p=dest/(c['case_id']+'.json')
        if p.exists():continue
        jj={r['condition']:r for r in jobs_for(c) if r['mode']=='name' and r['order']=='base' and r['round']==r['last_round'] and r['condition'] in ['neutral','wrong']}
        obs={k:json.loads((RUN/'observations'/(r['job_id']+'.json')).read_text()) for k,r in jj.items()}
        e={k:render(c,r,tok) for k,r in jj.items()}
        st={k:np.load(RUN/o['state_file']) for k,o in obs.items()}
        for k in e:assert hashlib.sha256(e[k]['prompt'].encode()).hexdigest()==obs[k]['prompt_sha256']
        records=[]
        for layer in [14,21]:
            for site in ['new','old','anchor']:
                pos={k:(np.array([len(x['ids'])-1]) if site=='anchor' else x[site+'_positions']) for k,x in e.items()}
                assert len(pos['neutral'])==len(pos['wrong'])>0
                assert [e['neutral']['ids'][j] for j in pos['neutral']]==[e['wrong']['ids'][j] for j in pos['wrong']]
                arr={k:st[k][f'{site}_L{layer}'].astype(np.float32) for k in st}
                delta=arr['neutral']-arr['wrong'];magnitude=float(np.linalg.norm(delta));seed=int(hashlib.sha256((c['case_id']+f':{layer}:{site}').encode()).hexdigest()[:8],16)
                trials=[('neutral_to_wrong','wrong',delta),('wrong_to_neutral','neutral',-delta)]
                for draw in [0,1]:
                    rd=np.random.default_rng(seed+draw).normal(size=delta.shape).astype(np.float32)
                    # Norm-matched random direction; no source diagnosis used.
                    rd*=magnitude/max(float(np.linalg.norm(rd)),1e-12);trials.append((f'random_{draw}','wrong',rd))
                if site=='anchor':trials.append(('self','wrong',np.zeros_like(delta)))
                for condition,recipient,dx in trials:
                    z,cache,before,after=transfer_forward(model,e[recipient],layer,pos[recipient],dx)
                    score=score_names(model,z,cache,e[recipient]);sham=None
                    if condition=='self':
                        sham=float(np.max(np.abs(np.array(score['log_probability'])-obs['wrong']['log_probability'])));assert sham<.05,(c['case_id'],layer,sham)
                    # Check the captured reference and intervention pre-state agree.
                    state_error=float(np.max(np.abs(before-arr[recipient])));assert state_error<.02,(c['case_id'],layer,site,state_error)
                    gen={}
                    if condition=='neutral_to_wrong' and site in ['new','anchor']:gen=decoded(model,tok,z,cache,e[recipient])
                    records.append(dict(layer=layer,site=site,condition=condition,recipient=recipient,seed=seed,token_count=len(pos[recipient]),position_offset=int(pos['wrong'][0]-pos['neutral'][0]),delta_norm=magnitude,requested_norm=float(np.linalg.norm(dx)),actual_norm=float(np.linalg.norm(after.astype(np.float32)-before.astype(np.float32))),state_error=state_error,sham_max_logp_error=sham,**score,**gen))
                    del z,cache;mx.clear_cache()
            print(json.dumps(dict(case=i+1,total=len(cases),dataset=c['dataset'],layer=layer,elapsed=round(time.time()-start,1))),flush=True)
        assert len(records)==26
        write_json(p,dict(case_id=c['case_id'],dataset=c['dataset'],cohort=c['cohort'],candidate_diseases=c['candidates'],neutral_log_probability=obs['neutral']['log_probability'],wrong_log_probability=obs['wrong']['log_probability'],conditions=records))
        done+=1
        if args.limit and done>=args.limit:break
    n=sum((dest/(c['case_id']+'.json')).exists() for c in cases)
    if n==len(cases):
        model_hashes=json.loads((RUN/'manifest.json').read_text())['model_hashes'];assert {name:sha(MODEL/name) for name in model_hashes}==model_hashes
        write_json(dest/'completion.json',dict(complete=True,patients=n,conditions=26*n,weights_unchanged=True,api_cost_usd=0))
    print(json.dumps(dict(completed_patients=n,expected=len(cases))),flush=True)

if __name__=='__main__':main()
