"""Held-out disease-direction intervention at anchor and continuation positions."""
import hashlib,json,time
from pathlib import Path
import numpy as np
import mlx.core as mx
from mlx_lm.models.cache import KVCache
from mlx_lm.models.base import create_attention_mask
from phase6_measure import ROOT,MODEL,load_model,capture
from phase14_run import RUN,render
from phase9_names import score_names
from phase1_run_direct import sha,write_json,output_head

def add_direction(h,direction,scale,anchor):
    x=h[:,-1:] if anchor else h
    mag=mx.sqrt(mx.sum(x.astype(mx.float32)**2,axis=-1,keepdims=True))
    z=(x.astype(mx.float32)+scale*mag*direction).astype(h.dtype)
    return mx.concatenate([h[:,:-1],z],axis=1) if anchor else z

def prefill(model,ids,layer,direction,scale):
    h=model.model.embed_tokens(mx.array([ids]));mask=create_attention_mask(h,None);cache=[];before=None;after=None
    for l,b in enumerate(model.model.layers):
        c=KVCache();h=b(h,mask=mask,cache=c)
        if l==layer:
            before=h[0,-1];h=add_direction(h,direction,scale,True);after=h[0,-1]
        cache.append(c)
    z=output_head(model,h[0,-1]).astype(mx.float32);mx.eval(z,before,after)
    return z,cache,np.array(before),np.array(after)

class Continuation:
    def __init__(self,model,layer,direction,scale):self.model=model;self.layer=layer;self.direction=direction;self.scale=scale
    def __call__(self,ids,cache=None):
        h=self.model.model.embed_tokens(ids);mask=create_attention_mask(h,cache[0])
        for l,(b,c) in enumerate(zip(self.model.model.layers,cache)):
            h=b(h,mask=mask,cache=c)
            if l==self.layer:h=add_direction(h,self.direction,self.scale,False)
        return output_head(self.model,h)

def main():
    assert (RUN/'completion.json').exists()
    dest=RUN/'disease_interventions';dest.mkdir(exist_ok=True)
    data=ROOT/'data/belief_v2';jobs=[json.loads(s) for s in (data/'jobs.public.jsonl').read_text().splitlines()];panel=json.loads((data/'panel.json').read_text())
    private={c['case_id']:c for c in map(json.loads,(data/'cases.private.jsonl').read_text().splitlines())}
    selected=[r for r in jobs if r['cohort']=='test' and r['deep_capture'] and r['view'] in ['append','panel'] and r['order']=='base' and r['round']==r['last_round']//2];assert len(selected)==48
    headfile=ROOT/'results/14_fixed_panel/training_heads.npz';heads=np.load(headfile);classes=heads['classes'].tolist();diseases=jobs[0]['candidate_diseases'];sub=[diseases.index(d) for d in classes]
    spec={'source_sha256':sha(__file__),'heads_sha256':sha(headfile),'protocol_sha256':sha(ROOT/'protocol/MECHANISM_CONTINUATION_V2.md'),
        'position_addendum_sha256':sha(ROOT/'protocol/CAUSAL_POSITION_IMPLEMENTATION.md'),
        'cases':24,'views':['append','panel'],'layers':[21,28],'primary_scale':.05,'sensitivity_scale':.02,'sites':['anchor','all_answer_positions'],
        'anchor_conditions':['toward','away','random','toward_small'],'continuation_conditions':['toward','away','random'],'active_conditions':672,'shams':48,'api_cost_usd':0}
    if (dest/'manifest.json').exists():assert json.loads((dest/'manifest.json').read_text())==spec
    else:write_json(dest/'manifest.json',spec);(dest/'source_snapshot.py').write_bytes(Path(__file__).read_bytes())
    model,tok=load_model();start=time.time()
    for i,row in enumerate(selected):
        path=dest/f"{row['case_id']}_{row['view']}.json"
        if path.exists():continue
        cid=row['case_id'];view=row['view'];gold=private[cid]['gold_disease'];yi=classes.index(gold);gi=diseases.index(gold)
        baseline=json.loads((RUN/'observations'/f"{row['job_id']}.json").read_text());bq=np.array(baseline['q_sequence']);competitor=max((j for j in range(24) if j!=yi),key=lambda j:bq[sub[j]])
        e=render(row,tok,panel);assert hashlib.sha256(e['prompt'].encode()).hexdigest()==baseline['prompt_sha256']
        name_indices=[]
        for d in diseases:
            enc=tok._tokenizer(e['prompt']+d+'"}',add_special_tokens=False,return_offsets_mapping=True)
            offsets=enc['offset_mapping'][len(e['ids']):];name_indices.append([j for j,(a,b) in enumerate(offsets) if a<len(e['prompt'])+len(d) and b>len(e['prompt'])])
        zero=mx.zeros(2048,mx.float32);z,cache,_,_=prefill(model,e['ids'],20,zero,0)
        sham=score_names(Continuation(model,20,zero,0),z,cache,e);del z,cache;mx.clear_cache()
        q=np.array(sham['q_sequence']);m=(q+bq)/2;distance=float(.5*np.sum(q*np.log((q+1e-30)/(m+1e-30))+bq*np.log((bq+1e-30)/(m+1e-30))))
        stable=distance<1e-5 and q.argmax()==bq.argmax();conditions=[];state_records={}
        base_arrays,base_z,base_cache=capture(model,e['ids'],keep_cache=True)
        for l in [20,27]:
            W=heads[f'weights_{view}_0.1'][l];direction=W[:,yi]-W[:,competitor];direction/=np.linalg.norm(direction)
            seed=int(hashlib.sha256((cid+view+str(l)+':direction-control').encode()).hexdigest()[:8],16);rng=np.random.default_rng(seed);rd=rng.normal(size=2048);rd-=rd@direction*direction;rd/=np.linalg.norm(rd)
            conditionspec=[('toward',direction,.05),('away',-direction,.05),('random',rd,.05),('toward_small',direction,.02)]
            for label,d,scale in conditionspec:
                dm=mx.array(d,mx.float32)
                if l==27:
                    bh=base_arrays['residual_stages'][27,4];ah=add_direction(bh[None,None,:],dm,scale,True)[0,0]
                    z=output_head(model,ah).astype(mx.float32);cache=base_cache;mx.eval(z,ah);before=np.array(bh);after=np.array(ah)
                else:z,cache,before,after=prefill(model,e['ids'],l,dm,scale)
                for tag,value in [('before',before),('after',after),('unit_direction',d)]:state_records[f'L{l+1}_{label}_{tag}']=np.asarray(value)
                for site in (['anchor'] if label=='toward_small' else ['anchor','all_answer_positions']):
                    scorer=model if site=='anchor' else Continuation(model,l,dm,scale)
                    scored=score_names(scorer,z,cache,e)
                    w=W[:,yi]-W[:,competitor];bn=before.astype(float)/np.linalg.norm(before.astype(float));an=after.astype(float)/np.linalg.norm(after.astype(float))
                    conditions.append(dict(layer=l+1,site=site,condition=label,scale=scale,random_seed=seed,
                        actual_relative_change=float(np.linalg.norm(after.astype(float)-before)/np.linalg.norm(before.astype(float))),
                        external_readout_margin_change=float((an-bn)@w),**scored))
                del z,cache;mx.clear_cache()
        statepath=dest/f'{cid}_{view}.npz';np.savez_compressed(statepath,**state_records)
        write_json(path,dict(case_id=cid,view=view,round=row['round'],gold=gold,competitor=classes[competitor],gold_index49=gi,competitor_index49=sub[competitor],
            first_token_ids=[s[0] for s in e['suffix']],name_token_indices=name_indices,baseline=baseline,sham=sham,sham_js=distance,numerically_stable=bool(stable),intervention_state_file=str(statepath.relative_to(RUN)),intervention_state_sha256=sha(statepath),conditions=conditions))
        del base_arrays,base_z,base_cache;mx.clear_cache()
        print(json.dumps({'intervention_prefix':i+1,'total':48,'view':view,'sham_js':distance,'stable':bool(stable),'elapsed':round(time.time()-start,1)}),flush=True)
    assert len(list(dest.glob('ddx*.json')))==48
    hashes=json.loads((RUN/'manifest.json').read_text())['model_hashes'];assert {f:sha(MODEL/f) for f in hashes}==hashes
    write_json(dest/'completion.json',dict(complete=True,prefixes=48,active_conditions=672,shams=48,weights_unchanged=True,api_cost_usd=0))
if __name__=='__main__':main()
