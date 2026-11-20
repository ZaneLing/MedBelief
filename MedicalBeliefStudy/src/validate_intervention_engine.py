"""Compare optimized anchor replay with a complete patched forward."""
from pathlib import Path
import json,os
os.environ['TOKENIZERS_PARALLELISM']='false'
import numpy as np
import mlx.core as mx
from mlx_lm import load
from mlx.utils import tree_map
from mlx_lm.models.base import create_attention_mask
from phase1_run_direct import capture_forward,output_head,scores,write_json,sha
from content_and_depth import replay_anchor
ROOT=Path(__file__).resolve().parents[1]
def full_patch(model,ids,l,component,replacement):
 h=model.model.embed_tokens(mx.array([ids]));mask=create_attention_mask(h,None)
 for j,b in enumerate(model.model.layers):
  a=b.self_attn(b.input_layernorm(h),mask,None)
  if j==l and component=='attention':a=mx.concatenate([a[:,:-1],replacement[None,None]],axis=1)
  mid=h+a;m=b.mlp(b.post_attention_layernorm(mid))
  if j==l and component=='mlp':m=mx.concatenate([m[:,:-1],replacement[None,None]],axis=1)
  h=mid+m
 out=output_head(model,h[:,-1:])[0,0].astype(mx.float32);mx.eval(out);return out
def main():
 run=ROOT/'runs/expanded_v1';jobs=list(map(json.loads,(ROOT/'data/jobs.public.jsonl').read_text().splitlines()))
 candidates=[r for r in jobs if r['cohort']=='replication' and r['order']=='base' and r['rotation']==0 and r['round']==r['last_round']//2 and (run/'observations'/f'{r["job_id"]}.json').exists()][:2]
 assert len(candidates)==2
 model,tok=load(str(ROOT.parent/'MedicalBeliefMechanisms/.models/Qwen3-1.7B'));model.update(tree_map(lambda a:a.astype(mx.float16) if mx.issubdtype(a.dtype,mx.floating) else a,model.parameters()));model.eval();mx.eval(model.parameters());checks=[]
 for job in candidates:
  r=json.loads((run/'observations'/f'{job["job_id"]}.json').read_text());prior=f'{job["case_id"]}_base_t{job["round"]-1:02d}_m0';old=json.loads((run/'observations'/f'{prior}.json').read_text())
  with np.load(run/r['state_file']) as a:ids=a['input_ids'].tolist();cids=a['candidate_ids'].tolist()
  with np.load(run/old['state_file']) as a:previous=mx.array(a['residual_stages'])
  current,terminal,cache=capture_forward(model,ids)
  for l in [23,25,27]:
   b=model.model.layers[l]
   for component in ['attention','mlp']:
    repl=previous[l,1 if component=='attention' else 3]
    if component=='attention':mid=current[l,0]+repl;post=mid+b.mlp(b.post_attention_layernorm(mid))
    else:post=current[l,2]+repl
    fast=replay_anchor(model,mx.stack([current[l,4],post,post,post,post]),l,cache,len(ids))[1]
    full=full_patch(model,ids,l,component,repl)
    fz,fp,fq=scores(fast,cids);zz,pp,qq=scores(full,cids)
    ok=bool(np.allclose(fz,zz,atol=1e-3,rtol=1e-3))
    check={'job_id':job['job_id'],'layer':l+1,'component':component,'max_abs_candidate_logit_error':float(np.abs(fz-zz).max()),'max_abs_support_error':float(np.abs(fq-qq).max()),'allclose':ok,'top_same':bool(fq.argmax()==qq.argmax())}
    checks.append(check);print(json.dumps(check),flush=True)
 write_json(ROOT/'protocol/intervention_engine_validation.json',{'checks':checks,'source_sha256':sha(__file__),'all_pass':all(c['allclose'] and c['top_same'] for c in checks)})
 assert all(c['allclose'] and c['top_same'] for c in checks)
if __name__=='__main__':main()
