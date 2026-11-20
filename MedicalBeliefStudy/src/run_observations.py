"""Frozen GPU observations: no gold labels, no previous answers, no text generation."""
from pathlib import Path
import argparse,hashlib,json,time,importlib.metadata,os
os.environ['TOKENIZERS_PARALLELISM']='false'
import numpy as np
import mlx.core as mx
from mlx_lm import load
from mlx.utils import tree_map
from mlx_lm.models.base import create_attention_mask
from phase1_run_direct import render,output_head,scores,sha,write_json
ROOT=Path(__file__).resolve().parents[1]

def forward(model,ids):
 h=model.model.embed_tokens(mx.array([ids]));mask=create_attention_mask(h,None);states=[]
 for block in model.model.layers:
  pre=h;att=block.self_attn(block.input_layernorm(pre),mask,None);mid=pre+att
  mlp=block.mlp(block.post_attention_layernorm(mid));h=mid+mlp
  states.append(mx.stack([x[0,-1] for x in [pre,att,mid,mlp,h]]))
 states=mx.stack(states);mx.eval(states)
 return states

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run-id',default='expanded_v1');ap.add_argument('--limit',type=int,default=0)
 ap.add_argument('--model-dir',default=str(ROOT.parent/'MedicalBeliefMechanisms/.models/Qwen3-1.7B'))
 args=ap.parse_args();run=ROOT/'runs'/args.run_id;run.mkdir(exist_ok=True)
 for d in ['observations','states']:(run/d).mkdir(exist_ok=True)
 jobs=list(map(json.loads,(ROOT/'data/jobs.public.jsonl').read_text().splitlines()))
 model_dir=Path(args.model_dir);hashes={f.name:sha(f) for f in list(model_dir.glob('*.safetensors'))+[model_dir/'config.json',model_dir/'tokenizer.json',model_dir/'tokenizer_config.json']}
 manifest={'run_id':args.run_id,'jobs':len(jobs),'model_dir':str(model_dir),'model_hashes':hashes,'model_config':json.loads((model_dir/'config.json').read_text()),
 'source_hashes':{f.name:sha(f) for f in [Path(__file__),ROOT/'src/phase1_run_direct.py',ROOT/'data/jobs.public.jsonl',ROOT/'protocol/STAGES_2_4.md']},
 'dtype':'FP16 from BF16; no training; no quantization','device':mx.device_info(),'diseases':jobs[0]['candidate_diseases'],
 'packages':{p:importlib.metadata.version(p) for p in ['mlx','mlx-lm','numpy','transformers']},'api_cost_usd':0,
 'measurement':'D next-code scores; full-vocabulary greedy first token recorded; no continuation generated'}
 if (run/'manifest.json').exists():assert json.loads((run/'manifest.json').read_text())==manifest,'Use new run ID'
 else:write_json(run/'manifest.json',manifest);(run/'source_snapshot.py').write_bytes(Path(__file__).read_bytes())
 print(json.dumps({'loading':str(model_dir),'jobs':len(jobs)}),flush=True)
 model,tok=load(str(model_dir));model.update(tree_map(lambda a:a.astype(mx.float16) if mx.issubdtype(a.dtype,mx.floating) else a,model.parameters()));model.eval();mx.eval(model.parameters())
 code_ids={c:tok.encode(' '+c,add_special_tokens=False) for c in 'ABCDEF'};assert all(len(x)==1 for x in code_ids.values())
 start=time.time();done=0
 for ji,row in enumerate(jobs):
  path=run/'observations'/(row['job_id']+'.json')
  if path.exists():continue
  tick=time.time();messages,mapping=render(row,row['rotation'])
  prompt=tok.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)+'Diagnosis code:'
  ids=tok.encode(prompt,add_special_tokens=False)
  for c in 'ABCDEF':assert tok.encode(prompt+' '+c,add_special_tokens=False)==ids+code_ids[c]
  inv={d:c for c,d in mapping.items()};cids=[code_ids[inv[d]][0] for d in row['candidate_diseases']]
  states=forward(model,ids)
  # Decode all layer exits plus the final layer's entry and post-attention positions.
  readouts=mx.concatenate([states[:,4],states[-1,[0,2]]],axis=0)
  all_logits=output_head(model,readouts).astype(mx.float32)
  z,p,q=scores(all_logits,cids);terminal=all_logits[27];mx.eval(terminal)
  arr=np.array(states);assert np.isfinite(arr).all()
  assert np.array_equal((arr[:,0]+arr[:,1]).astype(arr.dtype),arr[:,2])
  assert np.array_equal((arr[:,2]+arr[:,3]).astype(arr.dtype),arr[:,4])
  check=None
  if ji%250==0:
   native=model(mx.array([ids]))[0,-1].astype(mx.float32);mx.eval(native)
   a,b=np.array(native),np.array(terminal)
   check={'max_abs':float(np.abs(a-b).max()),'allclose':bool(np.allclose(a,b,atol=1e-3,rtol=1e-3)),'argmax_equal':bool(a.argmax()==b.argmax())}
   assert check['allclose'] and check['argmax_equal'],check
  arrays={'residual_stages':arr,'layer_candidate_logits':z[:28],'layer_code_probabilities':p[:28],
          'layer_support':q[:28],'last_stage_logits':z[[28,29,27]],'last_stage_support':q[[28,29,27]],
          'last_stage_mass':p[[28,29,27]].sum(-1),'input_ids':np.array(ids,dtype=np.int32),'candidate_ids':np.array(cids,dtype=np.int32)}
  if row['order']=='base' and row['rotation']==0 and not row['cohort'].startswith('readout'):arrays['terminal_logits']=np.array(terminal)
  state_path=run/'states'/(row['job_id']+'.npz');temp=state_path.with_suffix('.tmp.npz');np.savez_compressed(temp,**arrays);temp.replace(state_path)
  first=int(mx.argmax(terminal).item());firstcode=next((c for c,v in code_ids.items() if v[0]==first),None)
  record={k:row[k] for k in ['job_id','case_id','cohort','order','round','last_round','rotation','mapping_offset','new_question_group']}
  record.update({'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'input_tokens':len(ids),'code_to_disease':mapping,
   'q':q[27].tolist(),'z':z[27].tolist(),'p':p[27].tolist(),'candidate_mass':float(p[27].sum()),
   'layer_q':q[:28].tolist(),'layer_mass':p[:28].sum(-1).tolist(),'top_disease':row['candidate_diseases'][int(q[27].argmax())],
   'greedy_first_token':first,'greedy_first_text':tok.decode([first]),'greedy_first_disease':mapping.get(firstcode),
   'native_check':check,'state_file':str(state_path.relative_to(run)),'state_sha256':sha(state_path),'elapsed_sec':time.time()-tick})
  write_json(path,record);done+=1
  if done%25==0 or done==1:print(json.dumps({'job':ji+1,'total':len(jobs),'cohort':row['cohort'],'sec_per_job':round((time.time()-start)/done,3),'elapsed':round(time.time()-start,1)}),flush=True)
  del states,all_logits,terminal,readouts,arrays
  if done%25==0:mx.clear_cache()
  if args.limit and done>=args.limit:break
 complete=len(list((run/'observations').glob('*.json')))
 if complete==len(jobs):
  assert {f:sha(model_dir/f) for f in hashes}==hashes
  write_json(run/'completion.json',{'complete':True,'observations':complete,'weights_unchanged':True,'elapsed_this_invocation':time.time()-start,'api_cost_usd':0})
 print(json.dumps({'saved':complete,'expected':len(jobs),'elapsed':time.time()-start}),flush=True)
if __name__=='__main__':main()
