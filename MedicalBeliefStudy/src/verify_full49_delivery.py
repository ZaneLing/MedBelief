"""Read-only integrity and numerical audit of the completed new-stage delivery."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,re
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check_record(args):
    run,path=args;r=json.loads(path.read_text());p=run/r['state_file'];assert sha(p)==r['state_sha256'],str(p)
    projection_error=0.;projection_top_diff=False
    with np.load(p) as a:
        h=a['residual_stages'];assert h.shape==(28,5,2048) and np.isfinite(h).all()
        assert np.array_equal((h[:,0]+h[:,1]).astype(h.dtype),h[:,2])
        assert np.array_equal((h[:,2]+h[:,3]).astype(h.dtype),h[:,4])
        att=a['attention_by_group'];assert att.shape[:2]==(28,16);assert np.allclose(att.sum(-1),1,atol=1e-5)
        if 'component_support' in a:
            q=a['component_support'];z=a['component_logits'].astype(float);expected=np.exp(z-z.max(-1,keepdims=True));expected/=expected.sum(-1,keepdims=True)
            assert q.shape==(28,3,49) and np.allclose(q,expected,atol=2e-6)
            # Batched layer projection and single-anchor projection may differ in FP16.
            # Apply the same logit tolerance frozen in the measurement protocol; report probability drift.
            assert np.allclose(a['component_logits'][-1,-1],r['z'],atol=1e-3,rtol=1e-3)
            rz=np.array(r['z']);rq=np.exp(rz-rz.max());rq/=rq.sum();assert np.allclose(rq,r['q'],atol=2e-6)
            projection_error=float(np.max(np.abs(q[-1,-1]-r['q'])));projection_top_diff=bool(np.argmax(q[-1,-1])!=np.argmax(r['q']))
        if r['deep_capture']:
            assert a['attention_by_token'].shape==(28,16,len(a['input_ids']))
            assert a['head_outputs'].shape==(28,16,128)
            assert a['evidence_end_states'].shape==(28,len(a['evidence_end_positions']),2048)
    q=np.asarray(r.get('q',r.get('q_sequence')));assert q.shape==(49,) and np.isfinite(q).all() and np.isclose(q.sum(),1,atol=1e-6)
    if 'q_sequence' in r:
        z=np.asarray(r['log_probability']);eq=np.exp(z-z.max());eq/=eq.sum();assert np.allclose(eq,q,atol=1e-8)
        assert 0<=r['sequence_probability_mass']<=1.00001
    return {'deep':r['deep_capture'],'bytes':p.stat().st_size,'final_projection_max_support_error':projection_error,'final_projection_top_diff':projection_top_diff}
def main():
    results={}
    cohort=json.loads((ROOT/'protocol/FULL49_COHORT.json').read_text())
    for name,expected in cohort['input_hashes'].items():assert sha(ROOT/'data/full49_v1'/name)==expected
    for name,n in [('full49_v1',5040),('structured_names_v1',538)]:
        run=ROOT/'runs'/name;assert (run/'completion.json').exists();m=json.loads((run/'manifest.json').read_text())
        source=ROOT/'src'/('phase6_measure.py' if name=='full49_v1' else 'phase9_names.py');assert sha(source)==m['source_sha256']
        files=sorted((run/'observations').glob('ddx*.json'));assert len(files)==n
        with ThreadPoolExecutor(max_workers=4) as pool:checks=list(pool.map(check_record,[(run,p) for p in files]))
        results[name]={'observations_checked':n,'deep_states':sum(c['deep'] for c in checks),'state_bytes':sum(c['bytes'] for c in checks),
                       'max_final_batched_projection_support_difference':max(c['final_projection_max_support_error'] for c in checks),
                       'final_batched_projection_argmax_differences':sum(c['final_projection_top_diff'] for c in checks)}
    missing=[];png=pdf=0
    for dirname in ['06_full_candidate_trajectories','07_attention_and_layers','08_causal_confirmation','09_disease_name_trajectories','10_name_causal_mechanism','11_disease_information','12_current_synthesis']:
        dest=ROOT/'results'/dirname;assert (dest/'RESULTS.md').exists();assert (dest/'summary.json').exists()
        png+=len(list(dest.rglob('*.png')));pdf+=len(list(dest.rglob('*.pdf')))
        for p in dest.rglob('*.md'):
            for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
                if target.startswith(('http:','https:','#')):continue
                f=(p.parent/target.split('#')[0]).resolve()
                if not f.exists():missing.append({'source':str(p),'target':target})
    for p in [ROOT/'README.md']+list((ROOT/'acl_paper').glob('*.md')):
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
            if target.startswith(('http:','https:','#')):continue
            if not (p.parent/target.split('#')[0]).resolve().exists():missing.append({'source':str(p),'target':target})
    assert not missing,missing
    assert len(list((ROOT/'results/06_full_candidate_trajectories/cases').glob('*.md')))==120
    assert len(list((ROOT/'results/09_disease_name_trajectories/cases').glob('*.md')))==24
    probe=ROOT/'results/11_disease_information'
    with np.load(probe/'heldout_predictions.npz') as a:
        for f in range(5):assert sorted(a['gold'][a['fold']==f].tolist())==list(range(24))
        assert np.array_equal(a['0.1_name_to_name'],a['0.1_name_to_name'].astype(int))
    with np.load(probe/'heldout_name_readouts.npz') as heads,np.load(probe/'heldout_prefix_class_scores.npz') as scores:
        for cid in scores.files:
            if cid=='classes':continue
            i=list(heads['case_ids']).index(cid);f=int(heads['fold'][i]);r=json.loads((ROOT/'runs/structured_names_v1/observations'/f'{cid}_base_t00_m0.json').read_text())
            with np.load(ROOT/'runs/structured_names_v1'/r['state_file']) as a:h=a['residual_stages'][:,4].astype(float)
            h=h/np.linalg.norm(h,axis=-1,keepdims=True);out=np.einsum('ld,ldk->lk',h-heads['train_centers'][f],heads['weights'][f])+heads['bias']
            assert np.allclose(out,scores[cid][0],atol=1e-9)
    results['heldout_probe_checks']={'stratified_folds':5,'independent_prefix_reconstructions':24}
    results.update(png_figures=png,pdf_figures=pdf,broken_links=missing,passed=True,api_cost_usd=0)
    p=ROOT/'protocol/FULL49_DELIVERY_VERIFICATION.json';p.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n');print(json.dumps(results,ensure_ascii=False))

if __name__=='__main__':main()
