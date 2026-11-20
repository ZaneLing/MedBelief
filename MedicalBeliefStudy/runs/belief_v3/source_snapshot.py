"""Broad new-patient observations with frozen readouts and controlled history."""
import argparse,copy,hashlib,json,re,time
from pathlib import Path
import numpy as np
import mlx.core as mx
from phase6_measure import ROOT,SYSTEM,load_model,capture
from phase14_run import render as base_render
from phase9_names import score_names
from phase1_run_direct import sha,write_json,greedy_answer
from phase6_name_control import clone
NAMED=re.compile(r'diagnos|history of|treated.{0,45}for|anemia|anaemia|asthma|copd|lupus|hiv|diabet|cancer|tumou?r|neoplasm|pericard|embol|pneumo|angina|reflux|gerd|myasthen|guillain|migraine|dystoni|hernia|pharyng|otitis',re.I)
def encode_history(row,tok,prior):
 lines=[f"Patient: age {row['age']} years; sex {row['sex']}.",'Cumulative findings:']
 for i,g in enumerate(row['revealed_groups']):lines.append(f'[Evidence group {i}: {g["question_group_id"]}]');lines.extend(x['question_en']+' Answer: '+x['answer_en']+'.' for x in g['items'])
 lines+=['Candidate diagnoses:']+['- '+d for d in row['candidate_diseases']]
 lines+=['Select the best-supported candidate for the current presentation at this point. Choose one listed diagnosis even if evidence is incomplete. Complete the JSON object with exactly one candidate diagnosis copied verbatim from the list. Do not abbreviate or add an explanation. The output must have the form {"diagnosis":"exact candidate diagnosis"}.','The preceding assessment may be wrong. Reassess using only the current cumulative findings.']
 body='\n'.join(lines);old=json.dumps({'diagnosis':prior},separators=(',',':'));msgs=[{'role':'system','content':SYSTEM},{'role':'user','content':'An earlier partial record was assessed.'},{'role':'assistant','content':old},{'role':'user','content':body}]
 prompt=tok.apply_chat_template(msgs,tokenize=False,add_generation_prompt=True,enable_thinking=False)+'{"diagnosis":"';enc=tok._tokenizer(prompt,add_special_tokens=False,return_offsets_mapping=True);ids=enc['input_ids'];groups=np.zeros(len(ids),np.int16);start=prompt.index(body);cs=prompt.index('Candidate diagnoses:',start);ce=prompt.index('Select the best-supported',cs);hs=prompt.index(old);spans=[(start,start+len(lines[0]),2),(start+len(lines[0]),cs,3),(cs,ce,1),(hs,hs+len(old),4)]
 for a,b,k in spans:
  for j,(l,r) in enumerate(enc['offset_mapping']):
   if r>l and a<=(l+r)/2<b:groups[j]=k
 suffix=[]
 for d in row['candidate_diseases']:
  z=tok.encode(prompt+d+'"}',add_special_tokens=False);assert z[:len(ids)]==ids;suffix.append(z[len(ids):]+[tok.eos_token_id])
 return dict(prompt=prompt,ids=ids,token_groups=groups,group_labels=['format','candidates','demographics','known_facts','prior_diagnosis'],evidence_ends=[],suffix=suffix)
def prepare(row,tok,panel,run):
 row=copy.deepcopy(row);cond=row.get('condition','natural');removed=[];prior=None
 if cond=='repeat_middle':row['revealed_groups'].append(copy.deepcopy(next(g for g in row['revealed_groups'] if g['question_group_id']==row['intervention_group'])))
 if cond=='remove_middle':row['revealed_groups']=[g for g in row['revealed_groups'] if g['question_group_id']!=row['intervention_group']]
 if cond=='omit_named_history':
  out=[]
  for g in row['revealed_groups']:
   if any(v['is_antecedent'] and NAMED.search(v['question_en']+' '+v['answer_en']) for v in g['items']):removed.append(g['question_group_id'])
   else:out.append(g)
  row['revealed_groups']=out
 if cond.startswith('history_'):
  if cond=='history_actual':
   p=run/'observations'/f"{row['case_id']}_append_base_t{row['previous_round']:02d}.json";z=json.loads(p.read_text());prior=row['candidate_diseases'][np.argmax(z['q_sequence'])]
  else:prior=row['source_label'] if cond=='history_gold' else row['wrong_disease']
  e=encode_history(row,tok,prior)
 else:e=base_render(row,tok,panel)
 return e,{'condition':cond,'removed_groups':removed,'prior_disease':prior,'prior_actual_definition':'previous-round native49 argmax' if cond=='history_actual' else None}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--model',choices=['1.7b','4b'],default='1.7b');ap.add_argument('--limit',type=int,default=0);args=ap.parse_args();data=ROOT/'data/belief_v3';run=ROOT/'runs'/('belief_v3' if args.model=='1.7b' else 'belief_v3_4b');modeldir=ROOT.parent/'MedicalBeliefMechanisms/.models'/('Qwen3-1.7B' if args.model=='1.7b' else 'Qwen3-4B-8bit')
 for sub in ['observations','states']: (run/sub).mkdir(parents=True,exist_ok=True)
 file=data/('jobs.jsonl' if args.model=='1.7b' else 'jobs4b.jsonl');jobs=list(map(json.loads,file.read_text().splitlines()));panel=json.loads((ROOT/'data/belief_v2/panel.json').read_text());weights=list(modeldir.glob('*.safetensors'))+[modeldir/'config.json',modeldir/'tokenizer.json',modeldir/'tokenizer_config.json']
 spec={'source_sha256':sha(__file__),'input_sha256':sha(file),'protocol_sha256':sha(ROOT/'research_v3/BUILDING_PLAN.md'),'model':args.model,'jobs':len(jobs),'model_hashes':{p.name:sha(p) for p in weights},'helper_hashes':{n:sha(ROOT/'src'/n) for n in ['phase6_measure.py','phase14_run.py','phase9_names.py','phase1_run_direct.py']},'api_cost_usd':0}
 if (run/'manifest.json').exists():assert json.loads((run/'manifest.json').read_text())==spec
 else:write_json(run/'manifest.json',spec);(run/'source_snapshot.py').write_bytes(Path(__file__).read_bytes())
 model,tok=load_model(modeldir);start=time.time();done=0
 for i,row in enumerate(jobs):
  path=run/'observations'/f"{row['job_id']}.json"
  if path.exists():continue
  e,meta=prepare(row,tok,panel,run);deep=row['deep_capture'] and row['view']=='append' and row['order']=='base' and not row.get('condition') and bool(e['evidence_ends']);a,z,cache=capture(model,e['ids'],e['token_groups'],e['evidence_ends'],deep,keep_cache=True);err=np.array(a['attention_reconstruction_relative_rms']);assert np.isfinite(err).all() and err.max()<.02
  score=score_names(model,z,cache,e,validate=done==0 or i%200==0);_,txt,stop=greedy_answer(model,tok,z,clone(cache,len(e['ids'])),limit=48)
  try:generated=json.loads('{"diagnosis":"'+txt)['diagnosis']
  except (ValueError,TypeError,KeyError):generated=None
  state=run/'states'/f"{row['job_id']}.npz";np.savez_compressed(state,**{k:np.array(v) for k,v in a.items()},input_ids=np.array(e['ids']),token_groups=e['token_groups']);rec={k:row[k] for k in ['job_id','case_id','view','order','round','last_round','family','deep_capture']};rec.update(meta);rec.update(score);rec.update(input_tokens=len(e['ids']),state_file=str(state.relative_to(run)),state_sha256=sha(state),prompt_sha256=hashlib.sha256(e['prompt'].encode()).hexdigest(),generated_disease=generated,generated_text=txt,attention_max_error=float(err.max()),group_labels=e['group_labels'],suffix_ids=e['suffix'],deep_token_capture=deep)
  write_json(path,rec);del a,z,cache;mx.clear_cache();done+=1
  if done==1 or done%20==0:print(json.dumps({'job':i+1,'total':len(jobs),'condition':meta['condition'],'model':args.model,'elapsed_seconds':round(time.time()-start,1)}),flush=True)
  if args.limit and done>=args.limit:break
 if len(list((run/'observations').glob('*.json')))==len(jobs):
  assert {p.name:sha(p) for p in weights}==spec['model_hashes'];write_json(run/'completion.json',{'complete':True,'observations':len(jobs),'new_patients':240,'weights_unchanged':True,'api_cost_usd':0})
if __name__=='__main__':main()
