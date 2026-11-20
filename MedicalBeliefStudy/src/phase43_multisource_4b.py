"""Matched larger-configuration replication on the frozen mechanistic cohort."""
import json,time
import numpy as np
import mlx.core as mx
from belief_v4_core import *
from phase6_name_control import log_softmax

def main():
    cases=[c for c in map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines()) if c['mechanism_capture']];cases.sort(key=lambda c:c['cohort']!='development')
    dest=ROOT/'runs/belief_v4_4b';modeldir=ROOT.parent/'MedicalBeliefMechanisms/.models/Qwen3-4B-8bit'
    for s in ['observations','states']:(dest/s).mkdir(parents=True,exist_ok=True)
    jobs=[]
    for c in cases:
        for j in jobs_for(c):
            if j['order']!='base':continue
            if j['mode']=='code' or (j['round']==j['last_round']) or (j['round']==j['last_round']-1 and j['condition'] in ['neutral','wrong']):jobs.append((c,j))
    files=list(modeldir.glob('*.safetensors'))+[modeldir/'config.json',modeldir/'tokenizer.json',modeldir/'tokenizer_config.json']
    spec=dict(patients=len(cases),jobs=len(jobs),model='Qwen3-4B-8bit',source_sha256=sha(__file__),core_sha256=sha(ROOT/'src/belief_v4_core.py'),cases_sha256=sha(DATA/'cases.private.jsonl'),model_hashes={p.name:sha(p) for p in files},api_cost_usd=0)
    if (dest/'manifest.json').exists():assert json.loads((dest/'manifest.json').read_text())==spec
    else:write_json(dest/'manifest.json',spec)
    model,tok=load_model(modeldir);start=time.time();done=0
    for i,(c,row) in enumerate(jobs):
        path=dest/'observations'/(row['job_id']+'.json')
        if path.exists():continue
        e=render(c,row,tok);a,z,cache=capture(model,e,False);score=score_names(model,z,cache,e,validate=done==0 or i%250==0)
        gen={}
        if row['round']==row['last_round'] and row['mode']=='name' and row['condition'] in ['none','neutral','wrong']:gen=decoded(model,tok,z,cache,e)
        if row['mode']=='code':
            codes=mx.array([s[0] for s in e['suffix']]);assert len(set(np.array(codes).tolist()))==4
            lp=log_softmax(output_head(model,a['residual_stages'][:,4]).astype(mx.float32))[:,codes];qq=mx.softmax(lp,axis=-1);mx.eval(lp,qq);score['layer_code_support']=np.array(qq).tolist();score['layer_code_candidate_mass']=np.exp(np.array(lp)).sum(-1).tolist()
        state=dest/'states'/(row['job_id']+'.npz');np.savez_compressed(state,residual_anchor=np.array(a['residual_stages'][:,4]),evidence_means=np.array(a['evidence_means']),attention_by_group=np.array(a['attention_by_group']))
        write_json(path,dict(**row,dataset=c['dataset'],cohort=c['cohort'],candidate_diseases=c['candidates'],**score,**gen,input_tokens=len(e['ids']),state_file=str(state.relative_to(dest)),state_sha256=sha(state),attention_max_error=float(np.array(a['attention_reconstruction_relative_rms']).max())))
        del a,z,cache;mx.clear_cache();done+=1
        if done==1 or done%25==0:print(json.dumps(dict(job=i+1,total=len(jobs),dataset=c['dataset'],seconds=round(time.time()-start,1))),flush=True)
    assert len(list((dest/'observations').glob('*.json')))==len(jobs)
    assert {p.name:sha(p) for p in files}==spec['model_hashes']
    write_json(dest/'completion.json',dict(complete=True,patients=len(cases),observations=len(jobs),weights_unchanged=True,api_cost_usd=0))

if __name__=='__main__':main()
