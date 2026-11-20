"""Descriptive attention/MLP increments of the same untrained code readout."""
import json,time
import numpy as np
import mlx.core as mx
from belief_v4_core import *

def main():
 dest=ROOT/'runs/belief_v4_module_readout';dest.mkdir(parents=True,exist_ok=True);cases=[c for c in map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines()) if c['mechanism_capture']]
 spec=dict(patients=len(cases),source_sha256=sha(__file__),cases_sha256=sha(DATA/'cases.private.jsonl'),new_model_prefills=0,method='Frozen state readout at block input, after attention, after MLP; not a causal module ablation',api_cost_usd=0)
 if (dest/'manifest.json').exists():assert json.loads((dest/'manifest.json').read_text())==spec
 else:write_json(dest/'manifest.json',spec)
 model,tok=load_model();start=time.time();checks=[]
 for i,c in enumerate(cases):
  p=dest/(c['case_id']+'.json')
  if p.exists():continue
  rr=[]
  for cond in ['neutral','wrong']:
   for rot in [0,2]:
    T=len(c['sentences']);row=dict(condition=cond,mode='code',rotation=rot,round=T,last_round=T,order='base');e=render(c,row,tok);codes=[s[0] for s in e['suffix']]
    old=json.loads((RUN/'observations'/f'{c["case_id"]}_{cond}_code_r{rot}_base_t{T:02d}.json').read_text())
    with np.load(RUN/old['state_file']) as a:states=mx.array(a['residual_stages'][:,[0,2,4]])
    head=model.model.embed_tokens if model.args.tie_word_embeddings else model.lm_head
    v=model.model.norm(states);selected=v@head.weight[mx.array(codes)].T;mx.eval(selected);err=None
    if i==0:
     direct=output_head(model,states)[:,:,mx.array(codes)];mx.eval(direct);err=float(mx.max(mx.abs(direct-selected)).item());assert err<.05;checks.append(err)
    q=mx.softmax(selected.astype(mx.float32),axis=-1);mx.eval(q);assert np.max(np.abs(np.array(q)[:,2]-np.array(old['layer_code_support'])))<.01
    rr.append(dict(condition=cond,rotation=rot,stage_code_logits=np.array(selected.astype(mx.float32)).tolist(),stage_code_support=np.array(q).tolist(),selected_head_max_error=err));del states,v,selected,q;mx.clear_cache()
  write_json(p,dict(case_id=c['case_id'],dataset=c['dataset'],cohort=c['cohort'],candidate_diseases=c['candidates'],stages=['block_input','after_attention','after_MLP'],conditions=rr))
  if i==0 or (i+1)%20==0:print(json.dumps(dict(case=i+1,total=len(cases),seconds=round(time.time()-start,1))),flush=True)
 write_json(dest/'completion.json',dict(complete=True,patients=len(cases),endpoint_state_readouts=4*len(cases),new_model_prefills=0,api_cost_usd=0))
if __name__=='__main__':main()
