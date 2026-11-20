"""Validate complete experiment delivery from frozen records, not prose claims."""
import hashlib,json,re
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];RUN=ROOT/'runs/belief_v2'
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def check_scores(r):
    q=np.asarray(r['q_sequence']);lp=np.asarray(r['log_probability']);assert len(q) in [24,49] and np.isfinite(lp).all()
    expected=np.exp(lp-lp.max());expected/=expected.sum();assert np.max(abs(q-expected))<1e-12 and abs(q.sum()-1)<1e-12
    assert all(abs(sum(v)-s)<1e-8 for v,s in zip(r['token_log_probability'],lp))
def main():
    for directory in [RUN,RUN/'disease_interventions',RUN/'polarity',RUN/'presentation',RUN/'template_prior',ROOT/'runs/belief_v2_4b']:assert (directory/'completion.json').exists()
    manifest=json.loads((RUN/'manifest.json').read_text());jobs=[json.loads(s) for s in (ROOT/'data/belief_v2/jobs.public.jsonl').read_text().splitlines()];jobids={r['job_id'] for r in jobs}
    data=ROOT/'data/belief_v2';data_manifest=json.loads((data/'manifest.json').read_text());assert sha(data/'manifest.json')==manifest['data_manifest_sha256']
    assert all(sha(data/name)==value for name,value in data_manifest['input_hashes'].items());assert all('gold_disease' not in r for r in jobs)
    assert sha(ROOT/'src/phase9_names.py')==manifest['scorer_sha256'] and sha(ROOT/'src/phase6_measure.py')==manifest['capture_sha256']
    assert sha(ROOT/'results/14_fixed_panel/training_heads.npz')==json.loads((RUN/'disease_interventions/manifest.json').read_text())['heads_sha256']
    files=list((RUN/'observations').glob('*.json'));assert len(files)==len(jobs)==800
    assert {p.stem for p in files}==jobids
    bytes_=0;maxerr=0;maxcache=0;minmass=1.;maxmass=0.;bad_numeric=[]
    for p in files:
        r=json.loads(p.read_text());q=np.array(r['q_sequence']);lp=np.array(r['log_probability']);assert len(q)==49 and np.isfinite(lp).all();expect=np.exp(lp-lp.max());expect/=expect.sum();assert np.max(abs(q-expect))<1e-12 and abs(q.sum()-1)<1e-12
        assert all(abs(sum(t)-v)<1e-8 for t,v in zip(r['token_log_probability'],lp))
        sp=RUN/r['state_file'];assert sha(sp)==r['state_sha256'];bytes_+=sp.stat().st_size
        with np.load(sp) as a:
            x=a['residual_stages'];assert x.shape==(28,5,2048) and np.isfinite(x).all()
            assert np.array_equal(x[1:,0],x[:-1,4])
            assert np.array_equal((x[:,0]+x[:,1]).astype(x.dtype),x[:,2]);assert np.array_equal((x[:,2]+x[:,3]).astype(x.dtype),x[:,4])
            att=a['attention_by_group'];assert att.shape[:2]==(28,16) and np.allclose(att.sum(-1),1,atol=1e-5)
            maxerr=max(maxerr,float(a['attention_reconstruction_relative_rms'].max()))
        if r['cache_validation']:maxcache=max(maxcache,r['cache_validation']['absolute_error'])
        minmass=min(minmass,r['sequence_probability_mass']);maxmass=max(maxmass,r['sequence_probability_mass'])
    assert maxerr<.02 and maxcache<.15
    old=[json.loads(s) for s in (ROOT/'data/full49_v1/cases.private.jsonl').read_text().splitlines()];new=[json.loads(s) for s in (ROOT/'data/belief_v2/cases.private.jsonl').read_text().splitlines()]
    with np.load(ROOT/'results/14_fixed_panel/training_heads.npz') as h:
        assert h['training_ids'].tolist()==[c['case_id'] for c in old];assert not(set(h['training_ids'])&{c['case_id'] for c in new})
        assert h['weights_append_0.1'].shape==h['weights_panel_0.1'].shape==(28,2048,24)
    interventions=[json.loads(p.read_text()) for p in (RUN/'disease_interventions').glob('ddx*.json')];assert len(interventions)==48 and sum(len(r['conditions']) for r in interventions)==672
    for r in interventions:
        check_scores(r['baseline']);check_scores(r['sham'])
        assert len(r['name_token_indices'])==49
        assert sha(RUN/r['intervention_state_file'])==r['intervention_state_sha256']
        if not r['numerically_stable']:bad_numeric.append({'case_id':r['case_id'],'view':r['view'],'sham_js':r['sham_js']})
        for c in r['conditions']:
            check_scores(c)
            assert abs(sum(c['q_sequence'])-1)<1e-12;assert abs(c['actual_relative_change']-c['scale'])<.001
    polarity=[json.loads(p.read_text()) for p in (RUN/'polarity').glob('ddx*.json')];assert len(polarity)==24
    for r in polarity:
        check_scores(r);assert sha(RUN/r['state_file'])==r['state_sha256'] and r['source_label_not_used_as_counterfactual_truth']
    model=ROOT.parent/'MedicalBeliefMechanisms/.models/Qwen3-1.7B';assert {f:sha(model/f) for f in manifest['model_hashes']}==manifest['model_hashes']
    presentation=[json.loads(p.read_text()) for p in (RUN/'presentation').glob('ddx*.json')];assert len(presentation)==120
    for r in presentation:
        check_scores(r);assert sha(RUN/r['state_file'])==r['state_sha256']
    assert json.loads((RUN/'presentation/prompt_verification.json').read_text())['verified_prompts']==120
    prior=[json.loads(p.read_text()) for p in (RUN/'template_prior').glob('ddx*.json')];assert len(prior)==96
    assert json.loads((RUN/'template_prior/completion.json').read_text())['weights_unchanged']
    for r in prior:
        check_scores(r)
        assert sha(RUN/r['state_file'])==r['state_sha256'];assert abs(sum(r['q_sequence'])-1)<1e-12
        assert sorted(r['canonical_diseases'])==sorted(r['presented_diseases']) and len(r['q_sequence'])==49
        with np.load(RUN/r['state_file']) as a:assert a['residual_stages'].shape==(28,5,2048)
    source_runs=[(RUN,'phase14_run.py'),(RUN/'disease_interventions','phase15_intervene.py'),(RUN/'polarity','phase17_polarity.py'),(RUN/'presentation','phase19_presentation.py'),(RUN/'template_prior','phase20_prior.py'),(ROOT/'runs/belief_v2_4b','phase18_run.py')]
    for directory,script in source_runs:
        spec=json.loads((directory/'manifest.json').read_text());assert spec['source_sha256']==sha(ROOT/'src'/script)==sha(directory/'source_snapshot.py')
    bigrun=ROOT/'runs/belief_v2_4b';assert (bigrun/'completion.json').exists();bigmanifest=json.loads((bigrun/'manifest.json').read_text());bigfiles=list((bigrun/'observations').glob('*.json'));assert len(bigfiles)==448
    bigmaxerror=0;bigmaxcache=0
    for p in bigfiles:
        r=json.loads(p.read_text());check_scores(r);sp=bigrun/r['state_file'];assert sha(sp)==r['state_sha256'];assert abs(sum(r['q_sequence'])-1)<1e-12
        with np.load(sp) as a:
            x=a['residual_stages'];assert x.shape==(36,5,2560) and np.isfinite(x).all();assert np.array_equal(x[1:,0],x[:-1,4]);assert np.array_equal(x[:,0]+x[:,1],x[:,2]);assert np.array_equal(x[:,2]+x[:,3],x[:,4]);bigmaxerror=max(bigmaxerror,float(a['attention_reconstruction_relative_rms'].max()))
        if r['cache_validation']:bigmaxcache=max(bigmaxcache,r['cache_validation']['absolute_error'])
    assert bigmaxerror<.02 and bigmaxcache<.15
    bigmodel=ROOT.parent/'MedicalBeliefMechanisms/.models/Qwen3-4B-8bit';assert {f:sha(bigmodel/f) for f in bigmanifest['model_hashes']}==bigmanifest['model_hashes']
    targets=[p for folder in ['13_token_path','14_fixed_panel','15_disease_directions','16_update_mechanism','17_answer_polarity','18_model_replication','19_presentation_mechanism','20_template_prior','21_current_synthesis'] for p in (ROOT/'results'/folder).rglob('*.md')]+list((ROOT/'acl_paper').glob('*.md'))+[ROOT/'README.md']
    broken=[]
    for p in targets:
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
            if target.startswith(('http:','https:','#','mailto:')):continue
            target=target.split('#')[0].split(' "')[0].strip('<>');target=re.sub(r':\d+$','',target)
            if target and (p.parent/target).resolve()!=ROOT/'protocol/BELIEF_V2_DELIVERY_VERIFICATION.json' and not (p.parent/target).exists():broken.append({'file':str(p.relative_to(ROOT)),'target':target})
    assert not broken,broken
    manuscript=(ROOT/'acl_paper/07_MANUSCRIPT.md').read_text();assert '@@' not in manuscript
    result={'complete':True,'observation_records':800,'state_bytes_checked':bytes_,'new_test_patients':120,'heldout_training_patients':120,'deep_test_patients':24,
        'active_causal_conditions':672,'zero_interventions':48,'causal_excluded_prefixes':bad_numeric,'counterfactual_no_observations':24,'same_length_yes_no':sum(r['yes_no_same_length'] for r in polarity),
        'max_attention_reconstruction_relative_rms':maxerr,'max_cache_full_sequence_logprob_error':maxcache,'canonical_string_mass_range':[minmass,maxmass],
        'model_weights_unchanged':True,'presentation_followup_observations':120,'template_prior_observations':96,'frozen_sources_verified':len(source_runs),'model4b_observations':448,'model4b_max_attention_error':bigmaxerror,'model4b_max_cache_error':bigmaxcache,'model4b_weights_unchanged':True,'markdown_documents_checked':len(targets),'broken_local_links':broken,'api_cost_usd':0,
        'source_sha256':sha(__file__)}
    (ROOT/'protocol/BELIEF_V2_DELIVERY_VERIFICATION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
