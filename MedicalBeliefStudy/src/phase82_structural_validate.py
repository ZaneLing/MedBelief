"""Independent cardinality, cohort, numerical and frozen-source audit."""
import hashlib,json
from pathlib import Path
import numpy as np
from structural_v1_analysis import ROOT,DATA,RUN,read,write

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()

def probability(q):
    a=np.asarray(q,float)
    assert a.shape[-1]==4 and np.isfinite(a).all() and (a>=0).all() and (a<=1.000001).all()
    assert np.allclose(a.sum(-1),1,atol=1e-6)
    return a

def main():
    cases={c['case_id']:c for c in map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines())}
    screen=read(RUN/'screen/manifest.json');selected=read(RUN/'selected.json');selection_hash=sha(RUN/'selected.json');checks={}
    ids=[set(screen[s]) for s in ['screen','tune','test']]
    assert list(map(len,ids))==[18,27,345] and all(not(ids[i]&ids[j]) for i in range(3) for j in range(i))
    assert screen['cases_sha256']==sha(DATA/'cases.private.jsonl')
    for key,path in [('source_sha256',ROOT/'src/phase70_structural_screen.py'),('core_sha256',ROOT/'src/structural_v1_core.py'),('protocol_sha256',ROOT/'research_v5_structural/PROTOCOL.md')]:assert screen[key]==sha(path)
    mxnative=mxsham=0.;sham_flips=0;global_n=local_n=sham_n=0
    for cid in screen['screen']:
        for cond in ['neutral','wrong']:
            for rot in [0,2]:
                p=RUN/'screen'/f'{cid}_{cond}_r{rot}.json';z=read(p);assert len(z['global_deletions'])==84 and len(z['anchor_deletions'])==560
                probability(z['baseline']['q']);probability(z['layer_q'])
                mxnative=max(mxnative,z['native_q_error']);mxsham=max(mxsham,z['sham_q_error']);sham_flips+=z['sham_top_changes']
                for r in z['global_deletions']+z['anchor_deletions']:probability(r['q']);assert np.isfinite(r['candidate_logits']).all()
                global_n+=len(z['global_deletions']);sham_n+=28;local_n+=len(z['anchor_deletions'])-28
                with np.load(p.with_suffix('.npz')) as a:assert a['x'].shape==a['y'].shape==(28,32,2048) and np.isfinite(a['x']).all() and np.isfinite(a['y']).all()
    assert mxnative<.01 and mxsham<.02 and sham_flips==0
    checks['screen']=dict(cases=18,prompts=72,global_deletions=global_n,anchor_deletions=local_n,anchor_shams=sham_n,native_q_error=mxnative,sham_q_error=mxsham,sham_choice_changes=sham_flips)
    for split,n,configs,selection in [('tune',27,16,'development_candidates.json'),('test',345,9,'selected.json')]:
        src=RUN/split;sp=read(src/'manifest.json');done=read(src/'completion.json');assert done['complete'] and done['conditions']==n*configs*4
        assert len(sp['cases'])==n and len(sp['candidates'])==configs and sp['selection_sha256']==sha(RUN/selection)
        assert sp['source_sha256']==sha(ROOT/'src/phase74_structural_evaluate.py') and sp['variants_sha256']==sha(ROOT/'src/structural_v1_variants.py')
        native=[];stats={}
        for cid in sp['cases']:
            base=read(src/(cid+'_baseline.json'));prompts={(r['condition'],r['rotation']):r['prompt_sha256'] for r in base['conditions']}
            for cfg in sp['candidates']:
                z=read(src/(cid+'_'+cfg['name']+'.json'));assert z['configuration']==cfg and len(z['conditions'])==4
                assert {(r['condition'],r['rotation']) for r in z['conditions']}=={(c,r) for c in ['neutral','wrong'] for r in [0,2]}
                assert stats.setdefault(cfg['name'],z['parameter_stats'])==z['parameter_stats']
                for r in z['conditions']:
                    # FP32 exp(logit - logsumexp) can exceed unit mass by a few ulps.
                    q=probability(r['q']);lp=np.array(r['candidate_logits']);assert np.isfinite(lp).all() and 0<=r['candidate_mass']<=1.00001
                    soft=np.exp(lp-lp.max());soft/=soft.sum();assert np.allclose(q,soft,atol=1e-6)
                    assert r['prompt_sha256']==prompts[r['condition'],r['rotation']]
                    if 'native_q_error' in r:native.append(r['native_q_error'])
        assert len(native)==4*configs and max(native)<.01
        checks[split]=dict(cases=n,configurations=configs,conditions=n*configs*4,native_checks=len(native),max_native_q_error=max(native),parameter_stats=stats)
    sp=read(RUN/'generation/manifest.json');done=read(RUN/'generation/completion.json');assert done['complete'] and done['actual_generations']==1080 and sp['selection_sha256']==selection_hash
    assert set(sp['cases'])<=ids[2] and len(sp['cases'])==60
    for cid in sp['cases']:
        for cfg in sp['candidates']:
            z=read(RUN/'generation'/(cid+'_'+cfg['name']+'.json'));assert len(z['conditions'])==2
            for r in z['conditions']:
                try:d=json.loads('{"diagnosis":"'+r['text'])['diagnosis']
                except (ValueError,TypeError,KeyError):d=None
                assert d==r['generated_disease'] and r['correct']==(d==cases[cid]['gold_disease']) and r['listed']==(d in cases[cid]['candidates'])
    checks['generation']=done
    timing=read(RUN/'timing/completion.json');assert timing['complete'] and timing['paired_trials']==288
    for cfg in selected['candidates']:
        if cfg['name']=='baseline':continue
        z=read(RUN/'timing'/(cfg['name']+'.json'));assert len(z['trials'])==36
        for r in z['trials']:assert r['baseline_seconds']>0 and r['variant_seconds']>0 and np.isclose(r['ratio'],r['variant_seconds']/r['baseline_seconds'])
    checks['timing']=timing
    src=RUN/'trajectories';sp=read(src/'manifest.json');done=read(src/'completion.json');assert done['complete'] and len(sp['cases'])==47 and sp['selection_sha256']==selection_hash and set(sp['cases'])<=ids[2]
    errors=[];flips=0;endpoints=0;counts=0
    for cid in sp['cases']:
        T=len(cases[cid]['sentences'])
        for cfg in sp['candidates']:
            z=read(src/(cid+'_'+cfg['name']+'.json'));assert len(z['conditions'])==4*T
            assert {(r['condition'],r['rotation'],r['round']) for r in z['conditions']}=={(c,r,t) for c in ['neutral','wrong'] for r in [0,2] for t in range(1,T+1)}
            base=read(RUN/'test'/(cid+'_'+cfg['name']+'.json'));bb={(r['condition'],r['rotation']):r for r in base['conditions']}
            for r in z['conditions']:
                q=probability(r['layer_q']);assert q.shape==(28,4);m=np.array(r['layer_mass']);assert m.shape==(28,) and np.isfinite(m).all() and (m>=0).all() and (m<=1.00001).all()
                if cfg['name']=='baseline':
                    a=np.array(r['attention_by_group']);assert a.shape==(28,16,5) and np.isfinite(a).all() and np.allclose(a.sum(-1),1,atol=1e-5)
                if r['round']==T:
                    b=bb[r['condition'],r['rotation']];errors.append(float(np.max(np.abs(q[-1]-b['q']))));flips+=int(q[-1].argmax()!=np.argmax(b['q']));endpoints+=1
                counts+=1
        for ending in ['.md','.png','.pdf','_layers.png','_layers.pdf']:assert (ROOT/'results/45_structural_synthesis/cases'/(cid+ending)).exists()
    assert counts==done['conditions'] and max(errors)<.02
    checks['trajectories']=dict(**done,endpoint_comparisons=endpoints,endpoint_max_q_error=max(errors),endpoint_choice_changes=flips)
    for folder in ['42_structural_localization','43_structural_development','44_structural_holdout']:assert (ROOT/'results'/folder/'summary.json').exists() and (ROOT/'results'/folder/'RESULTS.md').exists()
    previous=read(ROOT/'runs/belief_v4/manifest.json')
    for name,h in previous['model_hashes'].items():assert sha(ROOT.parent/'MedicalBeliefMechanisms/.models/Qwen3-1.7B'/name)==h
    result=dict(complete=True,model='Qwen3-1.7B',model_weights_unchanged=True,cases_sha256=sha(DATA/'cases.private.jsonl'),selection_sha256=selection_hash,development_and_test_disjoint=True,stages=checks,api_cost_usd=0)
    write(ROOT/'research_v5_structural/FINAL_VALIDATION.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
