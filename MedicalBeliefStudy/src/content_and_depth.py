from pathlib import Path
import argparse,hashlib,json,os,time
os.environ['TOKENIZERS_PARALLELISM']='false'
import numpy as np
import mlx.core as mx
from mlx.utils import tree_map
from mlx_lm import load
from mlx_lm.models.cache import KVCache
from phase1_run_direct import render,output_head,scores,write_json,sha,capture_forward
from run_observations import forward
ROOT=Path(__file__).resolve().parents[1]

def replay_anchor(model,hs,layer,cache,N):
 h=hs[:,None,:];batch=h.shape[0]
 for l in range(layer+1,len(model.model.layers)):
  source=cache[l];c=KVCache()
  k=source.keys[...,:N-1,:];v=source.values[...,:N-1,:]
  c.state=(mx.broadcast_to(k,(batch,)+k.shape[1:]),mx.broadcast_to(v,(batch,)+v.shape[1:]),N-1)
  h=model.model.layers[l](h,None,c)
 return output_head(model,h[:,0]).astype(mx.float32)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run-id',default='expanded_v1');ap.add_argument('--model-dir',default=str(ROOT.parent/'MedicalBeliefMechanisms/.models/Qwen3-1.7B'));args=ap.parse_args()
 run=ROOT/'runs'/args.run_id;assert (run/'completion.json').exists()
 content=run/'content_controls';depth=run/'depth_interventions'
 for d in [content,depth]:d.mkdir(exist_ok=True)
 jobs=list(map(json.loads,(ROOT/'data/jobs.public.jsonl').read_text().splitlines()));js={r['job_id']:r for r in jobs}
 selected=[r for r in jobs if r['cohort'] in ['replication','pilot'] and r['order']=='base' and r['round']==r['last_round']//2 and r['rotation'] in [0,3]];assert len(selected)==144
 model,tok=load(args.model_dir);model.update(tree_map(lambda a:a.astype(mx.float16) if mx.issubdtype(a.dtype,mx.floating) else a,model.parameters()));model.eval();mx.eval(model.parameters())
 spec={'source_sha256':sha(__file__),'protocol_sha256':sha(ROOT/'protocol/CONTENT_AND_DEPTH_CONTROLS.md'),'observations_manifest_sha256':sha(run/'manifest.json'),'prefixes':144,'layers':[24,25,26,27,28]}
 for dest in [content,depth]:
  if (dest/'manifest.json').exists():assert json.loads((dest/'manifest.json').read_text())==spec
  else:write_json(dest/'manifest.json',spec)
 start=time.time()
 for i,row in enumerate(selected):
  oid=row['job_id'];cur=json.loads((run/'observations'/f'{oid}.json').read_text());previous_id=f"{row['case_id']}_base_t{row['round']-1:02d}_m{row['rotation']}";old=json.loads((run/'observations'/f'{previous_id}.json').read_text())
  with np.load(run/cur['state_file']) as a:ids=a['input_ids'].tolist();cids=a['candidate_ids'].tolist()
  with np.load(run/old['state_file']) as a:oldids=a['input_ids'].tolist()
  if not (content/f'{oid}.json').exists():
   messages,mapping=render(row,row['rotation']);prompt=tok.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)+'Diagnosis code:'
   enc=tok._tokenizer(prompt,add_special_tokens=False,return_offsets_mapping=True);assert enc['input_ids']==ids
   marker=f"[Evidence group {row['round']}]";startchar=prompt.index(marker)+len(marker);endchar=prompt.index('Candidate diagnoses:',startchar)
   edit=[j for j,(a,b) in enumerate(enc['offset_mapping']) if a>=startchar and b<=endchar and b>a];assert edit and edit==list(range(edit[0],edit[-1]+1))
   pool=tok.encode(' Administrative placeholder; no new clinical information.'*(len(edit)+1),add_special_tokens=False)
   neutral=ids.copy();neutral[edit[0]:edit[-1]+1]=pool[:len(edit)];assert len(neutral)==len(ids)
   assert neutral[:edit[0]]==ids[:edit[0]] and neutral[edit[-1]+1:]==ids[edit[-1]+1:]
   states=forward(model,neutral);logits=output_head(model,states[:,4]).astype(mx.float32);z,p,q=scores(logits,cids)
   np.savez_compressed(content/f'{oid}.npz',input_ids=np.array(neutral),residual_stages=np.array(states),layer_q=q,layer_z=z,layer_p=p)
   write_json(content/f'{oid}.json',{'job_id':oid,'case_id':row['case_id'],'cohort':row['cohort'],'rotation':row['rotation'],'round':row['round'],
    'replaced_tokens':len(edit),'input_tokens':len(ids),'span':[edit[0],edit[-1]+1],'previous_q':old['q'],'real_q':cur['q'],'neutral_q':q[-1].tolist(),
    'neutral_layer_q':q.tolist(),'neutral_mass':float(p[-1].sum()),'real_mass':cur['candidate_mass'],'neutral_text':tok.decode(neutral)})
  paths=[depth/f'{oid}_l{l+1}.json' for l in range(23,28)]
  if not all(p.exists() for p in paths):
   current,logits,cache=capture_forward(model,ids);oldstates,_,unused=capture_forward(model,oldids);del unused
   basez,basep,baseq=scores(logits,cids)
   for layer,path in zip(range(23,28),paths):
    if path.exists():continue
    pre,att,mid,mlp,post=[current[layer,j] for j in range(5)];oa=oldstates[layer,1];om=oldstates[layer,3];b=model.model.layers[layer]
    mids=mx.stack([pre+oa,pre+att+mx.roll(oa-att,257)])
    posts=mids+b.mlp(b.post_attention_layernorm(mids))
    hs=mx.stack([post,posts[0],mid+om,posts[1],mid+mlp+mx.roll(om-mlp,257)])
    endlogits=replay_anchor(model,hs,layer,cache,len(ids));z,p,q=scores(endlogits,cids)
    valid=bool(np.allclose(z[0],basez,atol=1e-3,rtol=1e-3) and q[0].argmax()==baseq.argmax())
    write_json(path,{'job_id':oid,'case_id':row['case_id'],'cohort':row['cohort'],'rotation':row['rotation'],'round':row['round'],'layer':layer+1,
     'components':['sham','previous_attention','previous_mlp','shifted_attention_difference','shifted_mlp_difference'],
     'previous_q':old['q'],'current_q':baseq.tolist(),'q':q.tolist(),'candidate_mass':p.sum(-1).tolist(),
     'sham_max_candidate_logit_error':float(np.abs(z[0]-basez).max()),'numerically_stable':valid})
  mx.clear_cache()
  if (i+1)%12==0:print(json.dumps({'content_and_depth_prefixes':i+1,'total':144,'elapsed':time.time()-start}),flush=True)
 for dest,n in [(content,144),(depth,720)]:
  assert len(list(dest.glob('ddx*.json')))==n
  write_json(dest/'completion.json',{'complete':True,'observations':n,'api_cost_usd':0})
 meta=json.loads((run/'manifest.json').read_text());assert {f:sha(Path(args.model_dir)/f) for f in meta['model_hashes']}==meta['model_hashes']
if __name__=='__main__':main()
