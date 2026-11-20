"""Development-motivated confirmation: unendorsed candidate-state transfer."""
import json,time,hashlib
import numpy as np
import mlx.core as mx
from belief_v4_core import *
from phase40_multisource_patch import transfer_forward

def main():
    cases=[c for c in map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines()) if c['mechanism_capture'] and c['cohort']=='confirmation'];dest=RUN/'mention_patches';dest.mkdir(parents=True,exist_ok=True)
    spec=dict(patients=len(cases),cohort='confirmation',recipient='unendorsed_candidate',conditions_per_case=20,source_sha256=sha(__file__),transfer_source_sha256=sha(ROOT/'src/phase40_multisource_patch.py'),core_sha256=sha(ROOT/'src/belief_v4_core.py'),cases_sha256=sha(DATA/'cases.private.jsonl'),status='development_motivated_followup',api_cost_usd=0)
    if (dest/'manifest.json').exists():assert json.loads((dest/'manifest.json').read_text())==spec
    else:write_json(dest/'manifest.json',spec)
    model,tok=load_model();start=time.time()
    for i,c in enumerate(cases):
        p=dest/(c['case_id']+'.json')
        if p.exists():continue
        jj={r['condition']:r for r in jobs_for(c) if r['round']==r['last_round'] and r['mode']=='name' and r['order']=='base' and r['condition'] in ['neutral','mention']}
        ob={k:json.loads((RUN/'observations'/(r['job_id']+'.json')).read_text()) for k,r in jj.items()};e={k:render(c,r,tok) for k,r in jj.items()};neutral=np.load(RUN/ob['neutral']['state_file'])
        a,z,cache=capture(model,e['mention'],True);baseline=score_names(model,z,cache,e['mention']);base_error=float(np.max(np.abs(np.asarray(baseline['log_probability'])-ob['mention']['log_probability'])));assert base_error<.05
        mention={k:np.array(v) for k,v in a.items()};del a,z,cache;mx.clear_cache();records=[]
        for layer in [14,21]:
            for site in ['new','old','anchor']:
                pos={k:np.array([len(x['ids'])-1]) if site=='anchor' else x[site+'_positions'] for k,x in e.items()}
                assert [e['neutral']['ids'][j] for j in pos['neutral']]==[e['mention']['ids'][j] for j in pos['mention']]
                delta=neutral[f'{site}_L{layer}'].astype(np.float32)-mention[f'{site}_L{layer}'].astype(np.float32);mag=float(np.linalg.norm(delta));seed=int(hashlib.sha256((c['case_id']+f':mention:{layer}:{site}').encode()).hexdigest()[:8],16)
                trials=[('target',delta)]
                for draw in [0,1]:
                    rd=np.random.default_rng(seed+draw).normal(size=delta.shape).astype(np.float32);rd*=mag/max(float(np.linalg.norm(rd)),1e-12);trials.append((f'random_{draw}',rd))
                if site=='anchor':trials.append(('self',np.zeros_like(delta)))
                for condition,dx in trials:
                    zz,cc,before,after=transfer_forward(model,e['mention'],layer,pos['mention'],dx);score=score_names(model,zz,cc,e['mention']);sham=None
                    if condition=='self':sham=float(np.max(np.abs(np.array(score['log_probability'])-ob['mention']['log_probability'])));assert sham<.05
                    assert np.max(np.abs(before-mention[f'{site}_L{layer}']))<.02
                    gen=decoded(model,tok,zz,cc,e['mention']) if condition=='target' and site in ['new','anchor'] else {}
                    records.append(dict(layer=layer,site=site,condition=condition,token_count=len(pos['mention']),position_offset=int(pos['mention'][0]-pos['neutral'][0]),delta_norm=mag,requested_norm=float(np.linalg.norm(dx)),sham_max_logp_error=sham,**score,**gen));del zz,cc;mx.clear_cache()
        assert len(records)==20
        write_json(p,dict(case_id=c['case_id'],dataset=c['dataset'],cohort=c['cohort'],candidate_diseases=c['candidates'],neutral_log_probability=ob['neutral']['log_probability'],mention_log_probability=ob['mention']['log_probability'],recapture_error=base_error,conditions=records))
        print(json.dumps(dict(case=i+1,total=len(cases),elapsed=round(time.time()-start,1))),flush=True)
    hashes=json.loads((RUN/'manifest.json').read_text())['model_hashes'];assert {n:sha(MODEL/n) for n in hashes}==hashes
    write_json(dest/'completion.json',dict(complete=True,patients=len(cases),conditions=20*len(cases),additional_baseline_recaptures=len(cases),weights_unchanged=True,api_cost_usd=0))

if __name__=='__main__':main()
