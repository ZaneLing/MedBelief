"""Frozen selected components followed through every evidence prefix, 47 cases."""
import time
from structural_v1_variants import *
def main():
    _,_,test=groups();cs=[c for c in test if c['mechanism_capture']];assert len(cs)==47
    sel=read(DEST/'selected.json');names=['baseline']+sel['mlp_pair']+[sel['repair_candidate']];configs=[next(v for v in sel['candidates'] if v['name']==n) for n in names];dest=DEST/'trajectories';dest.mkdir(exist_ok=True)
    spec=dict(cases=[c['case_id'] for c in cs],candidates=configs,source_sha256=sha(__file__),selection_sha256=sha(DEST/'selected.json'),api_cost_usd=0)
    if (dest/'manifest.json').exists():assert read(dest/'manifest.json')==spec
    else:write_json(dest/'manifest.json',spec)
    start=time.time()
    for config in configs:
        paths=[dest/(c['case_id']+'_'+config['name']+'.json') for c in cs]
        if all(p.exists() for p in paths):continue
        model,tok=load_model();model=materialize(model,config)
        for ci,(c,p) in enumerate(zip(cs,paths)):
            if p.exists():continue
            rr=[]
            for cond in ['neutral','wrong']:
                for rot in [0,2]:
                    for t in range(1,len(c['sentences'])+1):
                        e=encoded(c,tok,cond,rot,t);heads=None
                        if config['name']=='baseline':
                            rec,mask=capture(model,e);hs=mx.stack([r['post'][0,-1] for r in rec]);heads=np.stack([np.array(r['attention']) for r in rec]).tolist()
                        else:
                            h=model.model.embed_tokens(mx.array([e['ids']]));mask=create_attention_mask(h,None);states=[]
                            for b in model.model.layers:h=b(h,mask=mask,cache=None);states.append(h[0,-1])
                            hs=mx.stack(states)
                        o=outcome(model,hs,codes(e),True)
                        # Match the endpoint scoring kernel exactly: batched
                        # FP16 vocabulary projection can round differently.
                        final=outcome(model,hs[-1],codes(e),True);batch_error=float(np.max(np.abs(np.array(o['q'][-1])-final['q'])))
                        o['q'][-1]=final['q'];o['candidate_mass'][-1]=final['candidate_mass']
                        rr.append(dict(condition=cond,rotation=rot,round=t,layer_q=o['q'],layer_mass=o['candidate_mass'],attention_by_group=heads,last_layer_batched_projection_q_error=batch_error))
                        if config['name']=='baseline':del rec
                        del hs;mx.clear_cache()
            write_json(p,dict(case_id=c['case_id'],dataset=c['dataset'],candidate=config['name'],conditions=rr));print(json.dumps(dict(candidate=config['name'],case=ci+1,total=47,elapsed=round(time.time()-start,1))),flush=True)
        del model;mx.clear_cache()
    n=sum(len(c['sentences']) for c in cs)
    write_json(dest/'completion.json',dict(complete=True,cases=47,prefixes=n,configurations=4,conditions=n*4*4,api_cost_usd=0))
if __name__=='__main__':main()
