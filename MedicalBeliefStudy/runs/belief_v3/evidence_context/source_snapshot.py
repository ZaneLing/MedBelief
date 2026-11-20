"""Leave every source evidence group out, on each preselected mechanism patient."""
import copy,json,time,hashlib
from pathlib import Path
import numpy as np
import mlx.core as mx
from phase6_measure import ROOT,MODEL,load_model,capture
from phase14_run import render
from phase9_names import score_names
from phase1_run_direct import sha,write_json
RUN=ROOT/'runs/belief_v3';DEST=RUN/'evidence_context'
def main():
 assert (RUN/'completion.json').exists();DEST.mkdir(exist_ok=True);data=ROOT/'data/belief_v3';cases=[c for c in map(json.loads,(data/'cases.private.jsonl').read_text().splitlines()) if c['mechanism_capture']];jobs={r['job_id']:r for r in map(json.loads,(data/'jobs.jsonl').read_text().splitlines())};panel=json.loads((ROOT/'data/belief_v2/panel.json').read_text());tasks=[]
 for c in cases:
  base=jobs[f"{c['case_id']}_append_base_t{len(c['orders']['base']):02d}"]
  for t,g in enumerate([c['initial_question_group']]+c['orders']['base']):tasks.append((c,t,g,base))
 spec={'patients':24,'jobs':len(tasks),'source_sha256':sha(__file__),'protocol_sha256':sha(ROOT/'research_v3/EVIDENCE_CONTEXT_PROTOCOL.md'),'input_sha256':sha(data/'jobs.jsonl'),'api_cost_usd':0}
 if (DEST/'manifest.json').exists():assert json.loads((DEST/'manifest.json').read_text())==spec
 else:write_json(DEST/'manifest.json',spec);(DEST/'source_snapshot.py').write_bytes(Path(__file__).read_bytes())
 model,tok=load_model();start=time.time();done=0
 for i,(c,t,g,base) in enumerate(tasks):
  path=DEST/f"{c['case_id']}_omit{t:02d}.json"
  if path.exists():continue
  row=copy.deepcopy(base);row['revealed_groups']=[x for x in row['revealed_groups'] if x['question_group_id']!=g];e=render(row,tok,panel);a,z,cache=capture(model,e['ids'],e['token_groups'],keep_cache=True);score=score_names(model,z,cache,e,validate=done==0);state=DEST/f"{c['case_id']}_omit{t:02d}.npz";np.savez_compressed(state,**{k:np.array(v) for k,v in a.items()});write_json(path,dict(case_id=c['case_id'],omitted_group=g,source_round=t,input_tokens=len(e['ids']),state_file=state.name,state_sha256=sha(state),prompt_sha256=hashlib.sha256(e['prompt'].encode()).hexdigest(),**score));del a,z,cache;mx.clear_cache();done+=1
  if done==1 or done%20==0:print(json.dumps({'job':i+1,'total':len(tasks),'elapsed_seconds':round(time.time()-start,1)}),flush=True)
 assert len(list(DEST.glob('ddx*.json')))==len(tasks);hashes=json.loads((RUN/'manifest.json').read_text())['model_hashes'];assert {n:sha(MODEL/n) for n in hashes}==hashes;write_json(DEST/'completion.json',{'complete':True,'patients':24,'observations':len(tasks),'weights_unchanged':True,'api_cost_usd':0})
if __name__=='__main__':main()
