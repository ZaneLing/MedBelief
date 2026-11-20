"""Same patient sequences on the locally available Qwen3-4B 8-bit model."""
import hashlib,json,time
from pathlib import Path
import numpy as np
import mlx.core as mx
from phase6_measure import ROOT,load_model,capture
from phase9_names import render,score_names
from phase14_run import render as panel_render
from phase6_name_control import clone
from phase1_run_direct import sha,write_json,greedy_answer
MODEL=ROOT.parent/'MedicalBeliefMechanisms/.models/Qwen3-4B-8bit';RUN=ROOT/'runs/belief_v2_4b'
def main():
    for sub in ['observations','states']:(RUN/sub).mkdir(parents=True,exist_ok=True)
    old=[json.loads(s) for s in (ROOT/'data/full49_v1/jobs.public.jsonl').read_text().splitlines()]
    train=[{**r,'cohort':'train','view':'append','job_id':f"{r['case_id']}_append_base_t{r['round']:02d}"} for r in old if r['order']=='base' and r['rotation']==0 and r['round']==r['last_round']]
    new=[json.loads(s) for s in (ROOT/'data/belief_v2/jobs.public.jsonl').read_text().splitlines()];test=[r for r in new if r['view']=='append' and r['order']=='base'];extra=[r for r in new if r['cohort']=='test' and r['deep_capture'] and r['view']=='panel' and r['order']=='base' and r['round']==r['last_round']];jobs=train+test+extra;assert len(jobs)==448
    panel=json.loads((ROOT/'data/belief_v2/panel.json').read_text())
    files=list(MODEL.glob('*.safetensors'))+[MODEL/'config.json',MODEL/'tokenizer.json',MODEL/'tokenizer_config.json']
    spec={'source_sha256':sha(__file__),'protocol_sha256':sha(ROOT/'protocol/MODEL_REPLICATION_V2.md'),'presentation_followup_sha256':sha(ROOT/'protocol/PRESENTATION_FOLLOWUP_V2.md'),'model':'Qwen3-4B-8bit','quantization':{'bits':8,'group_size':128},'layers':36,'hidden_dim':2560,'jobs':len(jobs),'candidate_diseases':jobs[0]['candidate_diseases'],'model_hashes':{p.name:sha(p) for p in files},'input_hashes':{v:sha(ROOT/f'data/{v}/jobs.public.jsonl') for v in ['full49_v1','belief_v2']},'helper_hashes':{v:sha(ROOT/'src'/v) for v in ['phase6_measure.py','phase9_names.py','phase14_run.py']},'api_cost_usd':0}
    if (RUN/'manifest.json').exists():assert json.loads((RUN/'manifest.json').read_text())==spec
    else:write_json(RUN/'manifest.json',spec);(RUN/'source_snapshot.py').write_bytes(Path(__file__).read_bytes())
    model,tok=load_model(MODEL);start=time.time();done=0
    for i,row in enumerate(jobs):
        p=RUN/'observations'/f"{row['job_id']}.json"
        if p.exists():continue
        e=render(row,tok) if row['view']=='append' else panel_render(row,tok,panel);a,z,cache=capture(model,e['ids'],e['token_groups'],keep_cache=True);assert a['residual_stages'].shape==(36,5,2560)
        score=score_names(model,z,cache,e,validate=done==0 or i%100==0)
        _,text,stop=greedy_answer(model,tok,z,clone(cache,len(e['ids'])),limit=48)
        try:generated=json.loads('{"diagnosis":"'+text)['diagnosis']
        except (ValueError,KeyError,TypeError):generated=None
        sp=RUN/'states'/f"{row['job_id']}.npz";np.savez_compressed(sp,**{k:np.array(v) for k,v in a.items()},input_ids=e['ids'],token_groups=e['token_groups'])
        rec={k:row[k] for k in ['job_id','case_id','cohort','view','order','round','last_round','family','deep_capture']};rec.update(score);rec.update(input_tokens=len(e['ids']),group_labels=e['group_labels'],suffix_ids=e['suffix'],generated_text=text,generated_disease=generated,free_stop=stop,state_file=str(sp.relative_to(RUN)),state_sha256=sha(sp),prompt_sha256=hashlib.sha256(e['prompt'].encode()).hexdigest())
        write_json(p,rec);del a,z,cache;mx.clear_cache();done+=1
        if done==1 or done%10==0:print(json.dumps({'job':i+1,'total':448,'elapsed':round(time.time()-start,1)}),flush=True)
    assert len(list((RUN/'observations').glob('*.json')))==448;assert {p.name:sha(p) for p in files}==spec['model_hashes'];write_json(RUN/'completion.json',dict(complete=True,observations=448,weights_unchanged=True,api_cost_usd=0))
if __name__=='__main__':main()
