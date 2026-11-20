"""Complete per-round, per-layer candidate-code readouts on frozen cases."""
import json,time
import numpy as np
import mlx.core as mx
from belief_v4_core import *
from phase6_name_control import log_softmax

def main():
    cases=[c for c in map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines()) if c['mechanism_capture']]
    dest=ROOT/'runs/belief_v4_layer_trajectories';dest.mkdir(parents=True,exist_ok=True)
    jobs=[]
    for c in cases:
        T=len(c['sentences'])
        for t in range(1,T):
            for cond in ['neutral','wrong']:
                for rot in [0,2]:jobs.append((c,dict(job_id=f'{c["case_id"]}_{cond}_code_r{rot}_base_t{t:02d}',case_id=c['case_id'],round=t,last_round=T,condition=cond,mode='code',rotation=rot,order='base')))
        # Added after development-set inspection; the confirmation subset remains
        # separately identifiable. This is an explicit follow-up, not a primary test.
        for rot in [0,2]:jobs.append((c,dict(job_id=f'{c["case_id"]}_mention_code_r{rot}_base_t{T:02d}',case_id=c['case_id'],round=T,last_round=T,condition='mention',mode='code',rotation=rot,order='base')))
    spec=dict(patients=len(cases),new_jobs=len(jobs),reused_endpoint_jobs=4*len(cases),additional_mention_endpoint_jobs=2*len(cases),source_sha256=sha(__file__),core_sha256=sha(ROOT/'src/belief_v4_core.py'),cases_sha256=sha(DATA/'cases.private.jsonl'),api_cost_usd=0)
    if (dest/'manifest.json').exists():assert json.loads((dest/'manifest.json').read_text())==spec
    else:write_json(dest/'manifest.json',spec)
    model,tok=load_model();start=time.time()
    for i,(c,row) in enumerate(jobs):
        p=dest/(row['job_id']+'.json')
        if p.exists():continue
        e=render(c,row,tok);a,z,cache=capture(model,e,False);score=score_names(model,z,cache,e,validate=i==0 or i%400==0)
        code_ids=mx.array([s[0] for s in e['suffix']]);assert len(set(np.array(code_ids).tolist()))==4
        lp=log_softmax(output_head(model,a['residual_stages'][:,4]).astype(mx.float32))[:,code_ids];qq=mx.softmax(lp,axis=-1);mx.eval(lp,qq)
        write_json(p,dict(**row,dataset=c['dataset'],cohort=c['cohort'],candidate_diseases=c['candidates'],**score,layer_code_support=np.array(qq).tolist(),layer_code_candidate_mass=np.exp(np.array(lp)).sum(-1).tolist(),prompt_sha256=hashlib.sha256(e['prompt'].encode()).hexdigest(),layer_code_definition='Untrained final-head projection; two mappings reported separately; not a clinical posterior'))
        del a,z,cache;mx.clear_cache()
        if i==0 or (i+1)%40==0:print(json.dumps(dict(job=i+1,total=len(jobs),seconds=round(time.time()-start,1))),flush=True)
    assert len(list(dest.glob('*_code_*.json')))==len(jobs)
    hashes=json.loads((RUN/'manifest.json').read_text())['model_hashes'];assert {n:sha(MODEL/n) for n in hashes}==hashes
    write_json(dest/'completion.json',dict(complete=True,new_observations=len(jobs),reused_endpoint_observations=4*len(cases),mention_endpoint_observations=2*len(cases),patients=len(cases),weights_unchanged=True,api_cost_usd=0))

if __name__=='__main__':main()
