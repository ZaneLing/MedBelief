"""Factorial attention-path interventions, with no claim of additive mediation."""
import argparse,hashlib,json,time
import numpy as np
import mlx.core as mx
from belief_v4_core import *
from phase6_name_control import log_softmax

ROUTES={'full':(False,False),'block_to_facts':(True,False),'block_to_decision':(False,True),'block_both':(True,True)}

def spans(e,tok):
    enc=tok._tokenizer(e['prompt'],add_special_tokens=False,return_offsets_mapping=True);assert enc['input_ids']==e['ids']
    mark=e['prompt'].index('An earlier partial record was assessed.')
    hstart=next(j for j,(a,b) in enumerate(enc['offset_mapping']) if b>a and a<=mark<b)
    fp=np.flatnonzero((e['token_groups']==1)|(e['token_groups']==2));first,last=int(fp[0]),int(fp[-1]);assert hstart<first<=last<len(e['ids'])-1
    return dict(history_start=hstart,facts_start=first,facts_end=last+1,decision_start=last+1,total=len(e['ids']))

def forward(model,e,spec,route):
    ids=e['ids'];N=len(ids);h=model.model.embed_tokens(mx.array([ids]));bf,bd=ROUTES[route]
    if not bf and not bd:mask=create_attention_mask(h,None)
    else:
        allowed=np.tri(N,dtype=bool);hs,fs,fe=spec['history_start'],spec['facts_start'],spec['facts_end']
        if bf:allowed[fs:fe,hs:fs]=False
        if bd:allowed[fe:,hs:fs]=False
        mask=mx.array(np.where(allowed,0.,-np.inf),dtype=h.dtype)
    for b in model.model.layers:
        x=b.input_layernorm(h);a=b.self_attn;B,L,D=x.shape
        q=a.q_norm(a.q_proj(x).reshape(B,L,a.n_heads,-1)).transpose(0,2,1,3);k=a.k_norm(a.k_proj(x).reshape(B,L,a.n_kv_heads,-1)).transpose(0,2,1,3);v=a.v_proj(x).reshape(B,L,a.n_kv_heads,-1).transpose(0,2,1,3)
        q=a.rope(q);k=a.rope(k);o=scaled_dot_product_attention(q,k,v,cache=None,scale=a.scale,mask=mask)
        mid=h+a.o_proj(o.transpose(0,2,1,3).reshape(B,L,-1));h=mid+b.mlp(b.post_attention_layernorm(mid))
    z=output_head(model,h[0,-1]).astype(mx.float32);mx.eval(z);return z

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--model',choices=['1.7b','4b'],default='1.7b');ap.add_argument('--limit',type=int,default=0);args=ap.parse_args()
    cases=[c for c in map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines()) if c['mechanism_capture'] and c['cohort']=='confirmation'];dest=ROOT/'runs'/('belief_v4_routes_'+args.model);dest.mkdir(parents=True,exist_ok=True)
    modeldir=MODEL if args.model=='1.7b' else ROOT.parent/'MedicalBeliefMechanisms/.models/Qwen3-4B-8bit'
    spec=dict(model=args.model,patients=len(cases),conditions_per_case=24,source_sha256=sha(__file__),core_sha256=sha(ROOT/'src/belief_v4_core.py'),protocol_sha256=sha(ROOT/'research_v4/ROUTE_PROTOCOL.md'),cases_sha256=sha(DATA/'cases.private.jsonl'),api_cost_usd=0)
    if (dest/'manifest.json').exists():assert json.loads((dest/'manifest.json').read_text())==spec
    else:write_json(dest/'manifest.json',spec)
    model,tok=load_model(modeldir);start=time.time();done=0
    for i,c in enumerate(cases):
        p=dest/(c['case_id']+'.json')
        if p.exists():continue
        records=[];T=len(c['sentences'])
        for cond in ['neutral','wrong','mention']:
            for rot in [0,2]:
                row=dict(condition=cond,mode='code',rotation=rot,round=T,last_round=T,order='base');e=render(c,row,tok);part=spans(e,tok);codes=[s[0] for s in e['suffix']];assert len(set(codes))==4
                for route in ROUTES:
                    z=forward(model,e,part,route);lp=log_softmax(z)[mx.array(codes)];q=mx.softmax(lp);mx.eval(lp,q);check=None
                    if route=='full' and (i==0 or i%16==0):
                        native=model(mx.array([e['ids']]))[0,-1].astype(mx.float32);mx.eval(native);check=dict(allclose=bool(np.allclose(np.array(native),np.array(z),atol=1e-3,rtol=1e-3)),same_argmax=int(mx.argmax(native).item())==int(mx.argmax(z).item()));assert check['allclose'] and check['same_argmax']
                    # The measured answer is the first code token. No later
                    # generated token can silently reopen the blocked pathway.
                    records.append(dict(condition=cond,rotation=rot,route=route,log_probability=np.array(lp).tolist(),q=np.array(q).tolist(),candidate_mass=float(np.exp(np.array(lp)).sum()),unrestricted_first_is_code=int(mx.argmax(z).item()) in codes,first_token_ids=codes,native_check=check,partition=part,prompt_sha256=hashlib.sha256(e['prompt'].encode()).hexdigest()))
                    del z;mx.clear_cache()
        assert len(records)==24
        write_json(p,dict(case_id=c['case_id'],dataset=c['dataset'],cohort=c['cohort'],candidate_diseases=c['candidates'],conditions=records));done+=1
        if i==0 or (i+1)%4==0:print(json.dumps(dict(case=i+1,total=len(cases),model=args.model,seconds=round(time.time()-start,1))),flush=True)
        if args.limit and done>=args.limit:break
    n=sum((dest/(c['case_id']+'.json')).exists() for c in cases)
    if n==len(cases):
        original=RUN if args.model=='1.7b' else ROOT/'runs/belief_v4_4b';hashes=json.loads((original/'manifest.json').read_text())['model_hashes'];assert {k:sha(modeldir/k) for k in hashes}==hashes
        write_json(dest/'completion.json',dict(complete=True,patients=n,conditions=24*n,model=args.model,weights_unchanged=True,api_cost_usd=0))

if __name__=='__main__':main()
