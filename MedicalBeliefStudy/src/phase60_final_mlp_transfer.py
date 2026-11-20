"""Exact final-block MLP state transfer at first answer-code position."""
import json,hashlib,time
import numpy as np
import mlx.core as mx
from belief_v4_core import *

def main():
 dest=ROOT/'runs/belief_v4_final_mlp';dest.mkdir(parents=True,exist_ok=True);cases=[c for c in map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines()) if c['mechanism_capture']]
 spec=dict(patients=len(cases),source_sha256=sha(__file__),cases_sha256=sha(DATA/'cases.private.jsonl'),new_model_prefills=0,conditions_per_patient=10,layer=28,site='answer_anchor_MLP',outcome='first_code_token',status='post_observation_followup',api_cost_usd=0)
 if (dest/'manifest.json').exists():assert json.loads((dest/'manifest.json').read_text())==spec
 else:write_json(dest/'manifest.json',spec)
 model,tok=load_model();start=time.time()
 for i,c in enumerate(cases):
  p=dest/(c['case_id']+'.json')
  if p.exists():continue
  rr=[]
  for rot in [0,2]:
   T=len(c['sentences']);states={};obs={}
   for cond in ['neutral','wrong']:
    z=json.loads((RUN/'observations'/f'{c["case_id"]}_{cond}_code_r{rot}_base_t{T:02d}.json').read_text());obs[cond]=z
    with np.load(RUN/z['state_file']) as a:states[cond]=a['residual_stages'][-1].astype(np.float32)
   row=dict(condition='wrong',mode='code',rotation=rot,round=T,last_round=T,order='base');e=render(c,row,tok);codes=[s[0] for s in e['suffix']]
   delta=states['neutral'][3]-states['wrong'][3];norm=float(np.linalg.norm(delta));seed=int(hashlib.sha256((c['case_id']+f':MLP28:{rot}').encode()).hexdigest()[:8],16)
   trials=[('neutral_mlp_to_wrong','wrong',delta),('wrong_mlp_to_neutral','neutral',-delta),('self','wrong',np.zeros_like(delta))]
   for draw in [0,1]:
    dx=np.random.default_rng(seed+draw).normal(size=delta.shape).astype(np.float32);dx*=norm/max(float(np.linalg.norm(dx)),1e-12);trials.append((f'random_{draw}','wrong',dx))
   # This is the final block at the answer position: only the unchanged final
   # norm/head remain. No omitted downstream attention or token generation.
   hs=mx.array(np.stack([(states[recip][4]+dx).astype(np.float16) for _,recip,dx in trials]));z=output_head(model,hs).astype(mx.float32);mx.eval(z);lp=z-mx.logsumexp(z,axis=-1,keepdims=True);code_lp=lp[:,mx.array(codes)];q=mx.softmax(code_lp,axis=-1);mx.eval(code_lp,q)
   for j,(cond,recipient,dx) in enumerate(trials):
    if cond=='self':assert np.max(np.abs(np.array(q[j])-np.array(obs['wrong']['layer_code_support'][-1])))<.01
    rr.append(dict(rotation=rot,condition=cond,recipient=recipient,delta_norm=norm,requested_norm=float(np.linalg.norm(dx)),q=np.array(q[j]).tolist(),log_probability=np.array(code_lp[j]).tolist(),candidate_mass=float(np.exp(np.array(code_lp[j])).sum()),unrestricted_first_is_code=int(mx.argmax(z[j]).item()) in codes))
   for cond in ['neutral','wrong']:rr.append(dict(rotation=rot,condition=cond+'_baseline',q=obs[cond]['layer_code_support'][-1],candidate_mass=obs[cond]['layer_code_candidate_mass'][-1]))
   del hs,z,lp,code_lp,q;mx.clear_cache()
  write_json(p,dict(case_id=c['case_id'],dataset=c['dataset'],cohort=c['cohort'],candidate_diseases=c['candidates'],conditions=rr))
  if i==0 or (i+1)%20==0:print(json.dumps(dict(case=i+1,total=len(cases),seconds=round(time.time()-start,1))),flush=True)
 write_json(dest/'completion.json',dict(complete=True,patients=len(cases),intervention_conditions=10*len(cases),reused_baseline_readouts=4*len(cases),new_model_prefills=0,api_cost_usd=0))
if __name__=='__main__':main()
