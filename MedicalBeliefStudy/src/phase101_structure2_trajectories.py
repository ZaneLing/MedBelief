"""Fixed24-case cumulative evidence audit: complete names, support, internal states."""
from structure2_compat import *
from phase6_name_control import clone

def collect(model,e):
    cache=make_prompt_cache(model);h=model.model.embed_tokens(mx.array([e['ids']]));mask=create_attention_mask(h,cache[0]);states=[]
    for b,cc in zip(model.layers,cache):h=b(h,mask,cc);states.append(h[0,-1])
    before=model.model.norm.original(h[0,-1]) if isinstance(model.model.norm,AdaptedNorm) else model.model.norm(h[0,-1]);after=model.model.norm(h[0,-1]);z=model.model.embed_tokens.as_linear(after).astype(mx.float32)
    if isinstance(model,ContrastModel):
        ze=model.model.embed_tokens.as_linear(model.model.norm(states[model.config['contrast_layer']-1])).astype(mx.float32);allowed=z>=mx.max(z)+np.log(model.config['plausibility']);z=mx.where(allowed,z-model.config['contrast_strength']*ze,-1e9)
    state=mx.stack(states);mx.eval(state,z,before,after);return state,before,after,z,cache

def score_candidates(model,e,z,cache,constrained):
    scores=[];N=len(e['ids'])
    for suffix in e['suffix']:
        cc=clone(cache,N);cur=z;total=0.;prefix=[]
        for j,k in enumerate(suffix):
            if constrained:
                allowed=sorted({s[j] for s in e['suffix'] if len(s)>j and s[:j]==prefix});zz=cur[mx.array(allowed)];lp=mx.log(mx.softmax(zz)[allowed.index(k)]+1e-30)
            else:lp=cur[k]-mx.logsumexp(cur)
            total+=float(lp.item());prefix.append(k)
            if j<len(suffix)-1:cur=prefill(model,[k],cc);mx.eval(cur)
        scores.append(total)
    a=np.array(scores);p=np.exp(a-a.max());p/=p.sum();m=a/np.array(list(map(len,e['suffix'])));q=np.exp(m-m.max());q/=q.sum();return dict(log_probability=scores,q_sequence=p.tolist(),q_token_mean=q.tolist(),support_definition='Candidate-trie normalized sequence probabilities' if constrained else 'Full-vocabulary name sequence probabilities, renormalized over four complete strings')

def main():
    verify_amendment()
    spec=read(RUN/'confirmation_selection.json');dest=RUN/'trajectories';dest.mkdir(exist_ok=True);lookup={c['case_id']:c for c in cases()};cs=[lookup[cid] for cid in spec['trajectory_cases']];prefixes=sum(len(c['sentences']) for c in cs)
    manifest=dict(cases=spec['trajectory_cases'],configurations=spec['trajectory_configurations'],prefixes=prefixes,selection_sha256=sha(RUN/'confirmation_selection.json'),source_sha256=sha(ROOT/'src/phase101_structure2_trajectories.py'))
    if (dest/'manifest.json').exists():assert read(dest/'manifest.json')==manifest
    else:write(dest/'manifest.json',manifest)
    for cfg in spec['trajectory_configurations']:
        model,tok=load_model();model=assemble(model,cfg);start=time.time()
        for i,c in enumerate(cs):
            p=dest/(c['case_id']+'_'+cfg['name']+'.json')
            if p.exists():continue
            rr=[];arrays={}
            for cond in ['neutral','wrong']:
                for t in range(1,len(c['sentences'])+1):
                    e=encode(c,tok,cond,t);state,before,after,z,cache=collect(model,e);support=score_candidates(model,e,z,cache,cfg.get('constrained',False));o=(constrained_generate if cfg.get('constrained') else generate)(model,tok,e)
                    rr.append(dict(condition=cond,round=t,correct=o['generated_disease']==c['gold_disease'],listed=o['generated_disease'] in c['candidates'],adapter_relative_change=float(mx.sqrt(mx.mean((after.astype(mx.float32)-before.astype(mx.float32))**2)/(mx.mean(before.astype(mx.float32)**2)+1e-12)).item()),**support,**o));arrays[f'{cond}_t{t}_layers']=np.array(state);arrays[f'{cond}_t{t}_readout']=np.stack([np.array(before),np.array(after)]);mx.clear_cache()
            np.savez_compressed(p.with_suffix('.npz'),**arrays);write(p,dict(case_id=c['case_id'],dataset=c['dataset'],configuration=cfg,conditions=rr,state_sha256=sha(p.with_suffix('.npz'))));print(json.dumps(dict(trajectory=cfg['name'],case=i+1,total=24,elapsed=round(time.time()-start,1))),flush=True)
        del model;mx.clear_cache()
    write(dest/'completion.json',dict(complete=True,cases=24,prefixes=prefixes,configurations=len(spec['trajectory_configurations']),conditions=prefixes*2*len(spec['trajectory_configurations']),api_cost_usd=0))
if __name__=='__main__':main()
