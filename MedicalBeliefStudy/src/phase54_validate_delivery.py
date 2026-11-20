"""Audit frozen records, source hashes, probability arithmetic and interventions."""
from pathlib import Path
import json,hashlib,collections
import numpy as np
from phase41_multisource_analyze import ROOT,DATA,RUN,read,write

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    manifest=read(RUN/'manifest.json');cases=list(map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines()));cm={c['case_id']:c for c in cases};assert sha(DATA/'cases.private.jsonl')==manifest['cases_sha256']
    for name,value in manifest['helpers'].items():assert sha(ROOT/'src'/name)==value
    assert sha(ROOT/'src/phase39_multisource_run.py')==manifest['source_sha256']
    totals=collections.Counter();nonfinite_means=0;max_att=0.;max_native=0.;max_cache=0.;mean_examples=[]
    for i,p in enumerate(sorted((RUN/'observations').glob('*.json'))):
        z=read(p);c=cm[z['case_id']];assert z['candidate_diseases']==c['candidates'];assert z['cohort']==c['cohort'] and z['dataset']==c['dataset'];assert p.stem==z['job_id']
        lp=np.array(z['log_probability']);qq=np.array(z['q_sequence']);assert np.isfinite(lp).all() and np.isfinite(qq).all();assert np.allclose(qq,np.exp(lp-lp.max())/np.exp(lp-lp.max()).sum(),atol=1e-7)
        assert np.allclose(lp,[np.sum(t) for t in z['token_log_probability']],atol=1e-6)
        st=RUN/z['state_file'];assert sha(st)==z['state_sha256']
        with np.load(st) as a:
            for k in a.files:
                if k=='evidence_means':
                    if not np.isfinite(a[k]).all():nonfinite_means+=1
                    continue
                assert np.isfinite(a[k]).all(),(p.name,k)
            assert a['residual_stages'].shape[0]==28
            assert np.allclose(a['attention_by_group'].sum(-1),1,atol=2e-3)
        if z['native_validation']:
            assert z['native_validation']['allclose'] and z['native_validation']['same_argmax'];totals['native_checks']+=1;max_native=max(max_native,z['native_validation']['max_error'])
        max_att=max(max_att,z['attention_max_error']);totals['observations']+=1
        if z['mode']=='code':
            q=np.array(z['layer_code_support']);assert q.shape==(28,4) and np.isfinite(q).all() and np.allclose(q.sum(-1),1,atol=1e-6);totals['code_observations']+=1
        if 'generated_disease' in z:totals['generated_answers']+=1
        if (i+1)%500==0:print('validated',i+1,flush=True)
    assert totals['observations']==manifest['jobs']==6823
    write(ROOT/'research_v4/main_validation.json',dict(complete=True,patients=len(cases),counts=dict(totals),all_hashes_match=True,all_primary_arrays_finite=True,all_primary_probabilities_recompute=True,all_attention_rows_normalized=True,max_attention_reconstruction_error=max_att,max_native_logit_error=max_native,deprecated_fp16_mean_records_with_nonfinite=nonfinite_means,note='Only auxiliary evidence_means exempted from finiteness, formally deprecated. All 1080 endpoint means used in final analysis require phase51 FP32 sidecars.'))
    print('main observation validation complete',flush=True)

if __name__=='__main__':main()
