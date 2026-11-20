"""Natural anchor-state necessity on every external MedQA vignette."""
import hashlib,json,time
from pathlib import Path
import numpy as np
import mlx.core as mx
from phase6_measure import ROOT,MODEL,load_model,capture
from phase24_natural_intervene import prefill
from phase25_external_run import render
from phase9_names import score_names
from phase1_run_direct import output_head,sha,write_json
RUN=ROOT/'runs/belief_v3_medqa';DEST=RUN/'natural_interventions'
def main():
 assert (RUN/'completion.json').exists();DEST.mkdir(exist_ok=True);data=ROOT/'data/external_medqa';cases=list(map(json.loads,(data/'cases.private.jsonl').read_text().splitlines()));jobs={r['job_id']:r for r in map(json.loads,(data/'jobs.jsonl').read_text().splitlines())};spec={'patients':len(cases),'conditions':len(cases)*9,'layers':[14,21,28],'source_sha256':sha(__file__),'protocol_sha256':sha(ROOT/'research_v3/EXTERNAL_INTERNAL_PROTOCOL.md'),'input_sha256':sha(data/'jobs.jsonl'),'prefill_source_sha256':sha(ROOT/'src/phase24_natural_intervene.py'),'api_cost_usd':0}
 if (DEST/'manifest.json').exists():assert json.loads((DEST/'manifest.json').read_text())==spec
 else:write_json(DEST/'manifest.json',spec);(DEST/'source_snapshot.py').write_bytes(Path(__file__).read_bytes())
 model,tok=load_model();start=time.time()
 for i,c in enumerate(cases):
  cid=c['case_id'];path=DEST/(cid+'.json')
  if path.exists():continue
  t=max(2,len(c['evidence_sentences'])//2);newid=f'{cid}_base_t{t:02d}';oldid=f'{cid}_base_t{t-1:02d}';new=json.loads((RUN/'observations'/(newid+'.json')).read_text());old=json.loads((RUN/'observations'/(oldid+'.json')).read_text());g=c['candidate_diseases'].index(c['gold_disease']);co=max((j for j in range(4) if j!=g),key=lambda j:old['log_probability'][j]);e=render(jobs[newid],tok);assert hashlib.sha256(e['prompt'].encode()).hexdigest()==new['prompt_sha256'];a=np.load(RUN/new['state_file'])['residual_stages'][:,4].astype(float);b=np.load(RUN/old['state_file'])['residual_stages'][:,4].astype(float);base,z0,cache0=capture(model,e['ids'],keep_cache=True);records=[];states={}
  for l in [13,20,27]:
   delta=a[l]-b[l];magnitude=np.linalg.norm(delta);v=delta/max(magnitude,1e-12);seed=int(hashlib.sha256((cid+str(l)+':external-natural').encode()).hexdigest()[:8],16);random=np.random.default_rng(seed).normal(size=len(delta));random-=random@v*v;random/=np.linalg.norm(random);states[f'L{l+1}_new']=a[l];states[f'L{l+1}_old']=b[l];states[f'L{l+1}_random']=random
   for cond,dx in [('self',np.zeros_like(delta)),('replace_old',-delta),('random_matched',-magnitude*random)]:
    if l==27:
     before=np.array(base['residual_stages'][l,4]);ah=(mx.array(before).astype(mx.float32)+mx.array(dx,mx.float32)).astype(mx.float16);z=output_head(model,ah).astype(mx.float32);mx.eval(z,ah);cache=cache0;after=np.array(ah)
    else:z,cache,before,after=prefill(model,e['ids'],l,dx)
    score=score_names(model,z,cache,e);err=float(np.max(abs(np.array(score['log_probability'])-new['log_probability']))) if cond=='self' else None
    if cond=='self':assert err<.05,(cid,l,err)
    states[f'L{l+1}_{cond}_after']=after;records.append(dict(layer=l+1,condition=cond,requested_delta_norm=float(np.linalg.norm(dx)),actual_delta_norm=float(np.linalg.norm(after.astype(float)-before)),natural_delta_norm=float(magnitude),sham_max_logp_error=err,seed=seed,**score));del z,cache;mx.clear_cache()
  p=DEST/(cid+'.npz');np.savez_compressed(p,**states);write_json(path,dict(case_id=cid,round=t,gold=c['gold_disease'],competitor=c['candidate_diseases'][co],gold_index=g,competitor_index=co,candidate_diseases=c['candidate_diseases'],old_log_probability=old['log_probability'],new_log_probability=new['log_probability'],same_first_token=e['suffix'][g][0]==e['suffix'][co][0],conditions=records,state_file=p.name,state_sha256=sha(p)));del base,z0,cache0;mx.clear_cache()
  if i==0 or (i+1)%5==0:print(json.dumps({'case':i+1,'total':len(cases),'seconds':round(time.time()-start,1)}),flush=True)
 assert len(list(DEST.glob('medqa*.json')))==len(cases);hashes=json.loads((RUN/'manifest.json').read_text())['model_hashes'];assert {n:sha(MODEL/n) for n in hashes}==hashes;write_json(DEST/'completion.json',{'complete':True,'patients':len(cases),'conditions':len(cases)*9,'weights_unchanged':True,'api_cost_usd':0})
if __name__=='__main__':main()
