"""Resumable multi-source observations; no model training or paid API calls."""
import argparse,json,time,hashlib
from pathlib import Path
import numpy as np
import mlx.core as mx
from belief_v4_core import *

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--limit',type=int,default=0);args=ap.parse_args()
    cases=list(map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines()))
    cases.sort(key=lambda c:c['cohort']!='development')
    for sub in ['observations','states']:(RUN/sub).mkdir(parents=True,exist_ok=True)
    jobs=[(c,j) for c in cases for j in jobs_for(c)]
    helpers=['belief_v4_core.py','phase9_names.py','phase6_measure.py','phase1_run_direct.py','phase6_name_control.py']
    files=list(MODEL.glob('*.safetensors'))+[MODEL/'config.json',MODEL/'tokenizer.json',MODEL/'tokenizer_config.json']
    spec=dict(patients=len(cases),jobs=len(jobs),model='Qwen3-1.7B',device=mx.device_info(),source_sha256=sha(__file__),helpers={n:sha(ROOT/'src'/n) for n in helpers},cases_sha256=sha(DATA/'cases.private.jsonl'),protocol_sha256=sha(ROOT/'research_v4/PROTOCOL.md'),model_hashes={p.name:sha(p) for p in files},api_cost_usd=0)
    if (RUN/'manifest.json').exists():assert json.loads((RUN/'manifest.json').read_text())==spec
    else:
        write_json(RUN/'manifest.json',spec)
        (RUN/'source_snapshot.py').write_bytes(Path(__file__).read_bytes())
        (RUN/'core_snapshot.py').write_bytes((ROOT/'src/belief_v4_core.py').read_bytes())
    model,tok=load_model();start=time.time();done=0
    for i,(c,row) in enumerate(jobs):
        p=RUN/'observations'/(row['job_id']+'.json')
        if p.exists():continue
        tick=time.time();e=render(c,row,tok)
        keep_patch=c['mechanism_capture'] and row['mode']=='name' and row['condition'] in ['neutral','wrong'] and row['order']=='base' and row['round']==row['last_round']
        a,z,cache=capture(model,e,keep_patch)
        err=float(np.array(a['attention_reconstruction_relative_rms']).max());assert err<.02
        check=None
        if done==0 or i%400==0:
            native=model(mx.array([e['ids']]))[0,-1].astype(mx.float32);mx.eval(native)
            check=dict(max_error=float(mx.max(mx.abs(native-z)).item()),same_argmax=bool(mx.argmax(native).item()==mx.argmax(z).item()),allclose=bool(np.allclose(np.array(native),np.array(z),atol=1e-3,rtol=1e-3)))
            assert check['allclose'] and check['same_argmax'],check
        score=score_names(model,z,cache,e,validate=done==0 or i%400==0)
        if row['mode']=='code':
            from phase6_name_control import log_softmax
            readout=output_head(model,a['residual_stages'][:,4]).astype(mx.float32)
            code_ids=mx.array([s[0] for s in e['suffix']]);assert len(set(np.array(code_ids).tolist()))==4
            lp=log_softmax(readout)[:,code_ids];qq=mx.softmax(lp,axis=-1);mx.eval(lp,qq)
            a['layer_code_log_probability']=lp;a['layer_code_support']=qq
            score['layer_code_support']=np.array(qq).tolist()
            score['layer_code_candidate_mass']=np.exp(np.array(lp)).sum(-1).tolist()
            score['layer_code_definition']='Untrained final-head projection at each layer; first code token, not a calibrated disease posterior'
        gen={}
        if row['round']==row['last_round'] and row['order']=='base' and row['mode']=='name' and row['condition'] in ['none','neutral','wrong']:gen=decoded(model,tok,z,cache,e)
        state=RUN/'states'/(row['job_id']+'.npz');temp=state.with_suffix('.tmp.npz')
        # Full stage decomposition for mechanistic/trajectory cases, compact all-layer
        # states for the remaining population. No supervised external disease probe.
        saved={k:np.array(v) for k,v in a.items()}
        if not c['mechanism_capture']:saved['residual_stages']=saved['residual_stages'][:,4:5]
        np.savez_compressed(temp,**saved,input_ids=np.array(e['ids'],np.int32),token_groups=e['token_groups'],new_positions=e['new_positions'],evidence_ends=e['evidence_ends']);temp.replace(state)
        record=dict(**row,dataset=c['dataset'],cohort=c['cohort'],candidate_diseases=c['candidates'],**score,**gen,input_tokens=len(e['ids']),prompt_sha256=hashlib.sha256(e['prompt'].encode()).hexdigest(),state_file=str(state.relative_to(RUN)),state_sha256=sha(state),native_validation=check,attention_max_error=err,code_to_disease=e['code_to_disease'] if row['mode']=='code' else None,seconds=time.time()-tick)
        write_json(p,record);del a,z,cache,saved;mx.clear_cache();done+=1
        if done==1 or done%20==0:print(json.dumps(dict(done_this_run=done,job=i+1,total=len(jobs),dataset=c['dataset'],cohort=c['cohort'],elapsed=round(time.time()-start,1),seconds_per_job=round((time.time()-start)/done,2))),flush=True)
        if args.limit and done>=args.limit:break
    n=len(list((RUN/'observations').glob('*.json')))
    if n==len(jobs):
        assert {p.name:sha(p) for p in files}==spec['model_hashes']
        write_json(RUN/'completion.json',dict(complete=True,patients=len(cases),observations=n,weights_unchanged=True,api_cost_usd=0))
    print(json.dumps(dict(saved=n,expected=len(jobs),complete=n==len(jobs))),flush=True)

if __name__=='__main__':main()
