"""Post-observation counterbalance of all four unendorsed candidate names."""
import argparse,json,time,copy,hashlib
import numpy as np
import mlx.core as mx
from belief_v4_core import *
from phase6_name_control import log_softmax

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--model',choices=['1.7b','4b'],default='1.7b');args=ap.parse_args();dest=ROOT/'runs'/('belief_v4_names_'+args.model);dest.mkdir(parents=True,exist_ok=True)
 cs=[c for c in map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines()) if c['mechanism_capture'] and c['cohort']=='confirmation'];modeldir=MODEL if args.model=='1.7b' else ROOT.parent/'MedicalBeliefMechanisms/.models/Qwen3-4B-8bit'
 spec=dict(patients=len(cs),conditions_per_patient=10,source_sha256=sha(__file__),core_sha256=sha(ROOT/'src/belief_v4_core.py'),cases_sha256=sha(DATA/'cases.private.jsonl'),model=args.model,status='post_observation_counterbalance',api_cost_usd=0)
 if (dest/'manifest.json').exists():assert read_json(dest/'manifest.json')==spec
 else:write_json(dest/'manifest.json',spec)
 model,tok=load_model(modeldir);start=time.time()
 for i,c in enumerate(cs):
  p=dest/(c['case_id']+'.json')
  if p.exists():continue
  rr=[]
  for named in [-1,0,1,2,3]:
   modified=copy.deepcopy(c);modified['wrong_disease']='Undetermined' if named==-1 else c['candidates'][named]
   for rot in [0,2]:
    T=len(c['sentences']);e=render(modified,dict(condition='mention',mode='code',rotation=rot,round=T,last_round=T,order='base'),tok);z=model(mx.array([e['ids']]))[0,-1].astype(mx.float32);ids=[s[0] for s in e['suffix']];lp=log_softmax(z)[mx.array(ids)];q=mx.softmax(lp);mx.eval(lp,q)
    rr.append(dict(named_index=named,named_disease=modified['wrong_disease'],rotation=rot,q=np.array(q).tolist(),log_probability=np.array(lp).tolist(),candidate_mass=float(np.exp(np.array(lp)).sum()),unrestricted_first_is_code=int(mx.argmax(z).item()) in ids,prompt_sha256=hashlib.sha256(e['prompt'].encode()).hexdigest()))
    del z,lp,q;mx.clear_cache()
  write_json(p,dict(case_id=c['case_id'],dataset=c['dataset'],cohort=c['cohort'],candidate_diseases=c['candidates'],conditions=rr))
  if i==0 or (i+1)%8==0:print(json.dumps(dict(case=i+1,total=len(cs),model=args.model,seconds=round(time.time()-start,1))),flush=True)
 original=RUN if args.model=='1.7b' else ROOT/'runs/belief_v4_4b';hashes=json.loads((original/'manifest.json').read_text())['model_hashes'];assert {k:sha(modeldir/k) for k in hashes}==hashes
 write_json(dest/'completion.json',dict(complete=True,patients=48,conditions=480,model=args.model,weights_unchanged=True,api_cost_usd=0))

def read_json(p):return json.loads(p.read_text())
if __name__=='__main__':main()
