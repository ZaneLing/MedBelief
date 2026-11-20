"""Remove natural disease-direction updates on 24 fresh, preselected patients."""
import argparse,json,hashlib,time
from pathlib import Path
import numpy as np
import mlx.core as mx
from mlx_lm.models.cache import KVCache
from mlx_lm.models.base import create_attention_mask
from phase6_measure import ROOT,MODEL,load_model,capture
from phase14_run import render
from phase9_names import score_names
from phase1_run_direct import output_head,sha,write_json
RUN=ROOT/'runs/belief_v3'
def prefill(model,ids,layer,delta):
 h=model.model.embed_tokens(mx.array([ids]));mask=create_attention_mask(h,None);cache=[];before=None;after=None
 for l,b in enumerate(model.model.layers):
  c=KVCache();h=b(h,mask=mask,cache=c)
  if l==layer:
   before=h[0,-1];hh=(h[:,-1:].astype(mx.float32)+mx.array(delta,mx.float32)[None,None,:]).astype(h.dtype);h=mx.concatenate([h[:,:-1],hh],axis=1);after=h[0,-1]
  cache.append(c)
 z=output_head(model,h[0,-1]).astype(mx.float32);mx.eval(z,before,after);return z,cache,np.array(before),np.array(after)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--replication',action='store_true');args=ap.parse_args();assert (RUN/'completion.json').exists();dest=RUN/('natural_interventions_replication' if args.replication else 'natural_interventions');dest.mkdir(exist_ok=True);data=ROOT/'data/belief_v3';cases=[c for c in map(json.loads,(data/'cases.private.jsonl').read_text().splitlines()) if (c['deep_capture'] and not c['mechanism_capture'] if args.replication else c['mechanism_capture'])];jobs={r['job_id']:r for r in map(json.loads,(data/'jobs.jsonl').read_text().splitlines())};panel=json.loads((ROOT/'data/belief_v2/panel.json').read_text());headsfile=ROOT/'results/14_fixed_panel/training_heads.npz';heads=np.load(headsfile);cl=heads['classes'].tolist();ds=next(iter(jobs.values()))['candidate_diseases'];sub=[ds.index(x) for x in cl]
 spec={'cases':len(cases),'replication':args.replication,'layers':[14,21,28],'conditions':['self','remove_target','random_matched','replace_old'],'conditions_total':12*len(cases),'source_sha256':sha(__file__),'protocol_sha256':sha(ROOT/'research_v3/NATURAL_UPDATE_PROTOCOL.md'),'replication_protocol_sha256':sha(ROOT/'research_v3/NATURAL_REPLICATION_PROTOCOL.md'),'heads_sha256':sha(headsfile),'input_manifest_sha256':sha(data/'manifest.json'),'api_cost_usd':0}
 if (dest/'manifest.json').exists():assert json.loads((dest/'manifest.json').read_text())==spec
 else:write_json(dest/'manifest.json',spec);(dest/'source_snapshot.py').write_bytes(Path(__file__).read_bytes())
 model,tok=load_model();start=time.time()
 for i,c in enumerate(cases):
  path=dest/f"{c['case_id']}.json"
  if path.exists():continue
  cid=c['case_id'];t=c['fixed_middle_round'];newid=f'{cid}_append_base_t{t:02d}';oldid=f'{cid}_append_base_t{t-1:02d}';new=json.loads((RUN/'observations'/f'{newid}.json').read_text());old=json.loads((RUN/'observations'/f'{oldid}.json').read_text());a=np.load(RUN/new['state_file'])['residual_stages'][:,4].astype(float);b=np.load(RUN/old['state_file'])['residual_stages'][:,4].astype(float);yi=cl.index(c['gold_disease']);co=max((k for k in range(24) if k!=yi),key=lambda k:old['log_probability'][sub[k]]);e=render(jobs[newid],tok,panel);assert hashlib.sha256(e['prompt'].encode()).hexdigest()==new['prompt_sha256'];base_arrays,base_z,base_cache=capture(model,e['ids'],keep_cache=True);records=[];arrays={}
  for l in [13,20,27]:
   W=heads['weights_append_0.1'][l];v=W[:,yi]-W[:,co];v/=np.linalg.norm(v);delta=a[l]-b[l];coef=float(delta@v);project=coef*v;seed=int(hashlib.sha256((cid+str(l)+':natural-removal').encode()).hexdigest()[:8],16);rd=np.random.default_rng(seed).normal(size=len(v));rd-=rd@v*v;rd/=np.linalg.norm(rd);arrays[f'L{l+1}_new']=a[l];arrays[f'L{l+1}_old']=b[l];arrays[f'L{l+1}_direction']=v;arrays[f'L{l+1}_random']=rd
   for cond,dx in [('self',np.zeros_like(v)),('remove_target',-project),('random_matched',-coef*rd),('replace_old',-delta)]:
    if l==27:
     before=np.array(base_arrays['residual_stages'][l,4]);ah=(mx.array(before).astype(mx.float32)+mx.array(dx,mx.float32)).astype(mx.float16);z=output_head(model,ah).astype(mx.float32);mx.eval(z,ah);cache=base_cache;after=np.array(ah)
    else:z,cache,before,after=prefill(model,e['ids'],l,dx)
    score=score_names(model,z,cache,e);err=float(np.max(abs(np.array(score['log_probability'])-np.array(new['log_probability'])))) if cond=='self' else None
    if cond=='self':assert err<.05,(cid,l,err)
    arrays[f'L{l+1}_{cond}_after']=after;records.append(dict(layer=l+1,condition=cond,requested_delta_norm=float(np.linalg.norm(dx)),actual_delta_norm=float(np.linalg.norm(after.astype(float)-before)),natural_delta_norm=float(np.linalg.norm(delta)),projection_fraction=float(np.linalg.norm(project)/max(np.linalg.norm(delta),1e-12)),sham_max_logp_error=err,seed=seed,**score));del z,cache;mx.clear_cache()
  state=dest/f'{cid}.npz';np.savez_compressed(state,**arrays);write_json(path,dict(case_id=cid,gold=c['gold_disease'],competitor=cl[co],gold_index=ds.index(c['gold_disease']),competitor_index=sub[co],round=t,old_job=oldid,new_job=newid,old_log_probability=old['log_probability'],new_log_probability=new['log_probability'],same_first_token=e['suffix'][ds.index(c['gold_disease'])][0]==e['suffix'][sub[co]][0],conditions=records,state_file=state.name,state_sha256=sha(state)));del base_arrays,base_z,base_cache;mx.clear_cache();print(json.dumps({'case':i+1,'total':len(cases),'elapsed_seconds':round(time.time()-start,1)}),flush=True)
 assert len(list(dest.glob('ddx*.json')))==len(cases);hashes=json.loads((RUN/'manifest.json').read_text())['model_hashes'];assert {n:sha(MODEL/n) for n in hashes}==hashes;write_json(dest/'completion.json',{'complete':True,'patients':len(cases),'conditions':12*len(cases),'weights_unchanged':True,'api_cost_usd':0})
if __name__=='__main__':main()
