"""Last-block previous-state interventions and literal disease-name likelihoods."""
from pathlib import Path
import argparse,copy,json,time,hashlib,os
os.environ['TOKENIZERS_PARALLELISM']='false'
import numpy as np
import mlx.core as mx
from mlx.utils import tree_map
from mlx_lm import load
from mlx_lm.models.base import create_attention_mask
from mlx_lm.models.cache import make_prompt_cache
from phase1_run_direct import render,output_head,scores,write_json,sha,SYSTEM
ROOT=Path(__file__).resolve().parents[1]
def prompt_forward(model,ids):
 cache=make_prompt_cache(model);h=model.model.embed_tokens(mx.array([ids]));mask=create_attention_mask(h,cache[0])
 for b,c in zip(model.model.layers,cache):h=b(h,mask,c)
 logits=output_head(model,h[:,-1:])[0,0].astype(mx.float32);mx.eval(logits)
 return logits,cache
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run-id',default='expanded_v1');ap.add_argument('--model-dir',default=str(ROOT.parent/'MedicalBeliefMechanisms/.models/Qwen3-1.7B'));args=ap.parse_args()
 run=ROOT/'runs'/args.run_id;assert (run/'completion.json').exists()
 dest=run/'interventions';dest.mkdir(exist_ok=True);names=run/'name_scores';names.mkdir(exist_ok=True)
 rows=[json.loads(p.read_text()) for p in sorted((run/'observations').glob('*.json'))]
 lookup={(r['case_id'],r['order'],r['round'],r['rotation']):r for r in rows}
 jobs=list(map(json.loads,(ROOT/'data/jobs.public.jsonl').read_text().splitlines()));jobmap={r['job_id']:r for r in jobs}
 meta=json.loads((run/'manifest.json').read_text());assert {f:sha(Path(args.model_dir)/f) for f in meta['model_hashes']}==meta['model_hashes']
 model,tok=load(args.model_dir);model.update(tree_map(lambda a:a.astype(mx.float16) if mx.issubdtype(a.dtype,mx.floating) else a,model.parameters()));model.eval();mx.eval(model.parameters());block=model.model.layers[-1]
 spec={'source_sha256':sha(__file__),'protocol_sha256':sha(ROOT/'protocol/ANALYSIS_SUPPLEMENT.md'),'base_manifest_sha256':sha(run/'manifest.json'),'components':['sham','previous_attention','previous_mlp','shifted_attention_difference','shifted_mlp_difference'],'shift':257}
 if (dest/'manifest.json').exists():assert json.loads((dest/'manifest.json').read_text())==spec
 else:write_json(dest/'manifest.json',spec)
 todo=[r for r in rows if r['cohort'] in ['replication','pilot'] and r['order']=='base' and r['rotation'] in [0,3] and r['round']>0]
 start=time.time()
 for i,r in enumerate(todo):
  path=dest/(r['job_id']+'.json')
  if path.exists():continue
  previous=lookup[r['case_id'],'base',r['round']-1,r['rotation']]
  with np.load(run/r['state_file']) as a:cur=mx.array(a['residual_stages'][-1]);cids=a['candidate_ids'].tolist()
  with np.load(run/previous['state_file']) as a:old=mx.array(a['residual_stages'][-1])
  pre,att,mid,mlp,post=[cur[j] for j in range(5)]
  shifted_att=att+mx.roll(old[1]-att,257);shifted_mlp=mlp+mx.roll(old[3]-mlp,257)
  att_mids=mx.stack([pre+att,pre+old[1],pre+shifted_att]);att_posts=att_mids+block.mlp(block.post_attention_layernorm(att_mids))
  hs=mx.stack([att_posts[0],att_posts[1],mid+old[3],att_posts[2],mid+shifted_mlp])
  logits=output_head(model,hs).astype(mx.float32);z,p,q=scores(logits,cids)
  assert np.allclose(z[0],r['z'],atol=1e-3,rtol=1e-3)
  assert int(q[0].argmax())==int(np.argmax(r['q']))
  record={k:r[k] for k in ['job_id','case_id','cohort','round','rotation']}
  record.update({'previous_q':previous['q'],'current_q':r['q'],'components':spec['components'],'q':q.tolist(),'z':z.tolist(),
   'candidate_mass':p.sum(-1).tolist(),'sham_max_abs_candidate_logit_error':float(np.abs(z[0]-np.array(r['z'])).max())})
  write_json(path,record)
  if (i+1)%100==0:print(json.dumps({'interventions':i+1,'total':len(todo),'sec':time.time()-start}),flush=True)
  if (i+1)%50==0:mx.clear_cache()
 write_json(dest/'completion.json',{'complete':True,'pairs':len(todo),'variants_per_pair':5,'api_cost_usd':0})
 # Literal disease names: teacher force all tokens including end-of-turn.
 endpoints=[r for r in rows if r['cohort'] in ['replication','pilot'] and r['round']==r['last_round'] and r['rotation']==0]
 for i,r in enumerate(endpoints):
  path=names/(r['job_id']+'.json')
  if path.exists():continue
  row=jobmap[r['job_id']];messages,_=render(row,0);body=messages[1]['content'].split('Candidate diagnoses:')[0]
  diseases=row['candidate_diseases'];listed=[diseases[(j+row['mapping_offset'])%6] for j in range(6)]
  body+='Candidate diagnoses:\n'+'\n'.join(listed)+'\nSelect the best-supported candidate for the current presentation. After "Diagnosis:", output one space and exactly one of the disease names listed above, then end your answer.'
  messages=[{'role':'system','content':SYSTEM},{'role':'user','content':body}]
  prompt=tok.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)+'Diagnosis:';ids=tok.encode(prompt,add_special_tokens=False)
  initial,cache=prompt_forward(model,ids);sums=[];avgs=[];token_scores=[];sequence_ids=[]
  eos=tok.convert_tokens_to_ids('<|im_end|>');assert eos in tok.eos_token_ids
  for disease in diseases:
   suffix=tok.encode(' '+disease,add_special_tokens=False)+[eos]
   assert tok.encode(prompt+' '+disease,add_special_tokens=False)==ids+suffix[:-1]
   c=copy.deepcopy(cache);continuation=model(mx.array([suffix[:-1]]),cache=c)[0].astype(mx.float32)
   allz=mx.concatenate([initial[None],continuation],axis=0);lp=allz-mx.logsumexp(allz,axis=-1,keepdims=True)
   chosen=lp[mx.arange(len(suffix)),mx.array(suffix)];mx.eval(chosen);values=np.array(chosen).astype(float)
   token_scores.append(values.tolist());sequence_ids.append(suffix);sums.append(float(values.sum()));avgs.append(float(values.mean()))
  def norm(x):a=np.array(x);e=np.exp(a-a.max());return (e/e.sum()).tolist()
  record={k:r[k] for k in ['job_id','case_id','cohort','order','round']};record.update({'name_log_probability':sums,'token_mean_log_probability':avgs,'sequence_support':norm(sums),
   'length_normalized_score_support':norm(avgs),'candidate_sequence_mass':float(np.exp(np.array(sums)).sum()),'sequence_ids':sequence_ids,'token_log_probabilities':token_scores,'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'prompt':prompt})
  write_json(path,record)
  if (i+1)%12==0:print(json.dumps({'name_endpoints':i+1,'total':len(endpoints)}),flush=True)
  mx.clear_cache()
 write_json(names/'manifest.json',spec);write_json(names/'completion.json',{'complete':True,'endpoints':len(endpoints),'sequences_scored':6*len(endpoints),'api_cost_usd':0})
 assert {f:sha(Path(args.model_dir)/f) for f in meta['model_hashes']}==meta['model_hashes']
if __name__=='__main__':main()
