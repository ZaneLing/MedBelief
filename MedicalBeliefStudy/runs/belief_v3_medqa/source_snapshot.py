"""External MedQA source sentence prefixes, order controls, and prior judgment."""
import json,time,hashlib
from pathlib import Path
import numpy as np
import mlx.core as mx
from phase6_measure import ROOT,MODEL,load_model,capture
from phase9_names import score_names
from phase1_run_direct import sha,write_json,greedy_answer
from phase6_name_control import clone
RUN=ROOT/'runs/belief_v3_medqa'
def render(row,tok):
 system='You are analyzing a medical examination vignette for research. Compare the listed diagnoses using only the available vignette evidence. Missing information is unknown. Do not invent additional patient findings.'
 evidence='\n'.join(row['sentences']);body='Current vignette evidence:\n'+evidence+'\n\n'+row['question']+'\nCandidate diagnoses:\n'+'\n'.join('- '+d for d in row['candidate_diseases'])+'\nSelect the best-supported listed diagnosis using the currently available evidence, even if incomplete. Any preceding assessment may be wrong; reassess using the current facts. Complete the JSON object with one exact candidate diagnosis. Do not abbreviate or explain.'
 msgs=[{'role':'system','content':system}];old=None
 if row.get('prior_disease'):
  old=json.dumps({'diagnosis':row['prior_disease']},separators=(',',':'));msgs.extend([{'role':'user','content':'An earlier partial record was assessed.'},{'role':'assistant','content':old}])
 msgs.append({'role':'user','content':body});prompt=tok.apply_chat_template(msgs,tokenize=False,add_generation_prompt=True,enable_thinking=False)+'{"diagnosis":"';enc=tok._tokenizer(prompt,add_special_tokens=False,return_offsets_mapping=True);ids=enc['input_ids'];groups=np.zeros(len(ids),np.int16);start=prompt.index(evidence,prompt.index(body));end=start+len(evidence);cs=prompt.index('Candidate diagnoses:',end);ce=prompt.index('Select the best-supported',cs);spans=[(start,end,1),(cs,ce,2)]
 if old:hs=prompt.index(old);spans.append((hs,hs+len(old),3))
 for l,r,g in spans:
  for i,(a,b) in enumerate(enc['offset_mapping']):
   if b>a and l<=(a+b)/2<r:groups[i]=g
 suffix=[]
 for d in row['candidate_diseases']:
  z=tok.encode(prompt+d+'"}',add_special_tokens=False);assert z[:len(ids)]==ids;suffix.append(z[len(ids):]+[tok.eos_token_id])
 return dict(prompt=prompt,ids=ids,token_groups=groups,suffix=suffix)
def main():
 data=ROOT/'data/external_medqa';jobs=list(map(json.loads,(data/'jobs.jsonl').read_text().splitlines()))
 for sub in ['observations','states']:(RUN/sub).mkdir(parents=True,exist_ok=True)
 hashes=json.loads((ROOT/'runs/belief_v3/manifest.json').read_text())['model_hashes'];spec={'source_sha256':sha(__file__),'input_sha256':sha(data/'jobs.jsonl'),'data_manifest_sha256':sha(data/'manifest.json'),'model_hashes':hashes,'jobs':len(jobs),'api_cost_usd':0}
 if (RUN/'manifest.json').exists():assert json.loads((RUN/'manifest.json').read_text())==spec
 else:write_json(RUN/'manifest.json',spec);(RUN/'source_snapshot.py').write_bytes(Path(__file__).read_bytes())
 model,tok=load_model();start=time.time();done=0
 for i,row in enumerate(jobs):
  p=RUN/'observations'/f"{row['job_id']}.json"
  if p.exists():continue
  e=render(row,tok);a,z,cache=capture(model,e['ids'],e['token_groups'],keep_cache=True);score=score_names(model,z,cache,e,validate=done==0 or i%200==0);_,txt,stop=greedy_answer(model,tok,z,clone(cache,len(e['ids'])),limit=48)
  try:generated=json.loads('{"diagnosis":"'+txt)['diagnosis']
  except (ValueError,KeyError,TypeError):generated=None
  state=RUN/'states'/f"{row['job_id']}.npz";np.savez_compressed(state,**{k:np.array(v) for k,v in a.items()},input_ids=e['ids'],token_groups=e['token_groups']);write_json(p,dict(**{k:row[k] for k in ['job_id','case_id','round','last_round','condition']},**score,input_tokens=len(e['ids']),prompt_sha256=hashlib.sha256(e['prompt'].encode()).hexdigest(),state_file=str(state.relative_to(RUN)),state_sha256=sha(state),generated_disease=generated,generated_text=txt,candidate_diseases=row['candidate_diseases'],prior_disease=row.get('prior_disease'),attention_max_error=float(np.array(a['attention_reconstruction_relative_rms']).max())));del a,z,cache;mx.clear_cache();done+=1
  if done==1 or done%30==0:print(json.dumps({'job':i+1,'total':len(jobs),'elapsed_seconds':round(time.time()-start,1)}),flush=True)
 assert len(list((RUN/'observations').glob('*.json')))==len(jobs);assert {n:sha(MODEL/n) for n in hashes}==hashes;write_json(RUN/'completion.json',{'complete':True,'observations':len(jobs),'weights_unchanged':True,'api_cost_usd':0})
if __name__=='__main__':main()
