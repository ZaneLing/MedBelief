"""Source-role metadata controls on all 72 preselected deep patients."""
import copy,hashlib,json,time
from pathlib import Path
import numpy as np
import mlx.core as mx
import phase9_names
from phase6_measure import ROOT,MODEL,load_model,capture,SYSTEM
from phase14_run import render
from phase9_names import score_names
from phase1_run_direct import sha,write_json
RUN=ROOT/'runs/belief_v3';DEST=RUN/'role_binding'
LEGEND=' Each evidence group may carry a source category. HISTORY means a prior condition or background risk. CURRENT means a symptom or finding in the current presentation. UNSPECIFIED leaves the category unlabelled. Select the diagnosis explaining the current presentation, considering the role of each fact.'
def main():
 assert (RUN/'completion.json').exists();DEST.mkdir(exist_ok=True);data=ROOT/'data/belief_v3';cases=[c for c in map(json.loads,(data/'cases.private.jsonl').read_text().splitlines()) if c['deep_capture']];jobs={r['job_id']:r for r in map(json.loads,(data/'jobs.jsonl').read_text().splitlines())};panel=json.loads((ROOT/'data/belief_v2/panel.json').read_text());spec={'cases':72,'observations':216,'conditions':['correct','neutral','swapped'],'legend':LEGEND,'source_sha256':sha(__file__),'protocol_sha256':sha(ROOT/'research_v3/ROLE_BINDING_PROTOCOL.md'),'input_sha256':sha(data/'jobs.jsonl'),'api_cost_usd':0}
 if (DEST/'manifest.json').exists():assert json.loads((DEST/'manifest.json').read_text())==spec
 else:write_json(DEST/'manifest.json',spec);(DEST/'source_snapshot.py').write_bytes(Path(__file__).read_bytes())
 phase9_names.SYSTEM=SYSTEM+LEGEND;model,tok=load_model();start=time.time();done=0
 for c in cases:
  cid=c['case_id'];base=jobs[f"{cid}_append_base_t{len(c['orders']['base']):02d}"]
  for cond in ['correct','neutral','swapped']:
   p=DEST/f'{cid}_{cond}.json'
   if p.exists():continue
   row=copy.deepcopy(base);mapping={}
   for group in row['revealed_groups']:
    flags={v['is_antecedent'] for v in group['items']};assert len(flags)==1;history=flags.pop();label='UNSPECIFIED' if cond=='neutral' else ('HISTORY' if (history if cond=='correct' else not history) else 'CURRENT');mapping[group['question_group_id']]=label;group['items'][0]['question_en']=f'[Source category: {label}]\n'+group['items'][0]['question_en']
   e=render(row,tok,panel);a,z,cache=capture(model,e['ids'],e['token_groups'],keep_cache=True);score=score_names(model,z,cache,e,validate=done==0);state=DEST/f'{cid}_{cond}.npz';np.savez_compressed(state,**{k:np.array(v) for k,v in a.items()});write_json(p,dict(case_id=cid,condition=cond,role_mapping=mapping,input_tokens=len(e['ids']),state_file=state.name,state_sha256=sha(state),prompt_sha256=hashlib.sha256(e['prompt'].encode()).hexdigest(),**score));del a,z,cache;mx.clear_cache();done+=1
   if done==1 or done%15==0:print(json.dumps({'observations':done,'total':216,'seconds':round(time.time()-start,1)}),flush=True)
 assert len(list(DEST.glob('ddx*.json')))==216;hashes=json.loads((RUN/'manifest.json').read_text())['model_hashes'];assert {n:sha(MODEL/n) for n in hashes}==hashes;write_json(DEST/'completion.json',{'complete':True,'patients':72,'observations':216,'weights_unchanged':True,'api_cost_usd':0})
if __name__=='__main__':main()
