"""Matched gold-vs-wrong history at the full-evidence endpoint."""
import copy,json,time,hashlib
from pathlib import Path
import numpy as np
import mlx.core as mx
from phase6_measure import ROOT,MODEL,load_model,capture
from phase23_run import prepare
from phase9_names import score_names
from phase1_run_direct import sha,write_json
RUN=ROOT/'runs/belief_v3';DEST=RUN/'history_matched'
def main():
 assert (RUN/'completion.json').exists();DEST.mkdir(exist_ok=True);data=ROOT/'data/belief_v3';cases={c['case_id']:c for c in map(json.loads,(data/'cases.private.jsonl').read_text().splitlines())};base=[r for r in map(json.loads,(data/'jobs.jsonl').read_text().splitlines()) if r.get('condition')=='history_wrong_final'];panel=json.loads((ROOT/'data/belief_v2/panel.json').read_text());spec={'source_sha256':sha(__file__),'protocol_sha256':sha(ROOT/'research_v3/HISTORY_MATCHED_PROTOCOL.md'),'input_sha256':sha(data/'jobs.jsonl'),'helper_source_sha256':sha(ROOT/'src/phase23_run.py'),'patients':24,'api_cost_usd':0}
 if (DEST/'manifest.json').exists():assert json.loads((DEST/'manifest.json').read_text())==spec
 else:write_json(DEST/'manifest.json',spec);(DEST/'source_snapshot.py').write_bytes(Path(__file__).read_bytes())
 model,tok=load_model();start=time.time()
 for i,original in enumerate(base):
  c=cases[original['case_id']];path=DEST/(c['case_id']+'.json')
  if path.exists():continue
  row=copy.deepcopy(original);row.update(condition='history_gold',source_label=c['gold_disease'],job_id=c['case_id']+'_history_gold_final');e,meta=prepare(row,tok,panel,RUN);a,z,cache=capture(model,e['ids'],e['token_groups'],keep_cache=True);score=score_names(model,z,cache,e,validate=i==0);state=DEST/(c['case_id']+'.npz');np.savez_compressed(state,**{k:np.array(v) for k,v in a.items()},input_ids=e['ids'],token_groups=e['token_groups']);write_json(path,dict(case_id=c['case_id'],job_id=row['job_id'],round=row['round'],condition='history_gold_final',prior_disease=c['gold_disease'],input_tokens=len(e['ids']),state_file=state.name,state_sha256=sha(state),prompt_sha256=hashlib.sha256(e['prompt'].encode()).hexdigest(),group_labels=e['group_labels'],**score));del a,z,cache;mx.clear_cache();print(json.dumps({'case':i+1,'total':24,'seconds':round(time.time()-start,1)}),flush=True)
 assert len(list(DEST.glob('ddx*.json')))==24;hashes=json.loads((RUN/'manifest.json').read_text())['model_hashes'];assert {n:sha(MODEL/n) for n in hashes}==hashes;write_json(DEST/'completion.json',{'complete':True,'patients':24,'weights_unchanged':True,'api_cost_usd':0})
if __name__=='__main__':main()
