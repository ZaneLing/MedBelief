"""Validate completed inference, cohort isolation, probabilities and immutable inputs."""
import hashlib
import numpy as np
from phase90_structure2_prepare import *
from structure2_scoring import normalize_name,surface_choice

def filehash(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()

def main():
    cs=cases();lookup={c['case_id']:c for c in cs};assert len(cs)==len(lookup)==880;dm=read(DATA/'manifest.json');assert sha(DATA/'cases.private.jsonl')==dm['cases_sha256'];assert sha(ROOT/'data/belief_v4/cases.private.jsonl')==dm['old_cases_sha256'];assert sha(ROOT/'data/belief_v4/eligible.unique.jsonl')==dm['source_unique_sha256'];assert sha(ROOT/'src/phase90_structure2_prepare.py')==dm['source_sha256'];old={c['case_id'] for c in map(json.loads,(ROOT/'data/belief_v4/cases.private.jsonl').read_text().splitlines())};assert not set(lookup)&old
    counts=collections.Counter(c['cohort'] for c in cs);assert counts==dict(train=400,development=80,confirmation=400);assert all(sum(c['dataset']==ds and c['cohort']==co for c in cs)==n//2 for co,n in counts.items() for ds in ['MedQA','MedMCQA']);assert set(dm['calibration'])<={c['case_id'] for c in cs if c['cohort']=='train'}
    spec=read(RUN/'confirmation_selection.json');assert spec['cases_sha256']==sha(DATA/'cases.private.jsonl');assert spec['core_sha256']==sha(ROOT/'src/structure2_core.py');assert spec['decoder_sha256']==sha(ROOT/'src/structure2_decode.py');assert spec['ranking_sha256']==sha(RUN/'calibration/ranking.json');assert spec['source_sha256']==sha(ROOT/'src/phase98_structure2_freeze.py')
    amendment=read(DOC/'TOKENIZATION_AMENDMENT.json');assert amendment==read(RUN/'confirmation/execution_amendment.json');assert amendment['compat_sha256']==sha(ROOT/'src/structure2_compat.py') and amendment['selection_sha256']==sha(RUN/'confirmation_selection.json');assert amendment['original_renderer_sha256']==sha(ROOT/'src/belief_v4_core.py');assert amendment['all_cases_checked']==880 and amendment['previous_generated_conditions_unchanged']==258
    audit=read(DATA/'source_sensitivity_audit.json');assert audit['cases_sha256']==sha(DATA/'cases.private.jsonl') and audit['source_sha256']==sha(ROOT/'src/structure2_source_audit.py');assert audit['counts']['confirmation']==dict(total=400,source_kept=386,source_and_similarity_kept=366)
    generation_counts={};selection_mtime=(RUN/'confirmation_selection.json').stat().st_mtime
    for folder,configs,cohort,conds in [('structure_development',read(RUN/'structural_candidates.json'),'development',['neutral','wrong']),('adapter_development',read(RUN/'added_candidates.json'),'development',['neutral','wrong']),('confirmation',spec['configurations'],'confirmation',['neutral','wrong']),('confirmation',[dict(name='baseline_no_history')],'confirmation',['none'])]:
        count=0;cohort_ids={c['case_id'] for c in cs if c['cohort']==cohort}
        for cfg in configs:
            dest=RUN/folder/cfg['name'];manifest=read(dest/'manifest.json');assert set(manifest['cases'])==cohort_ids and manifest['configuration']==cfg;assert manifest['core_sha256']==spec['core_sha256'];assert manifest['cases_sha256']==spec['cases_sha256']
            if cfg.get('constrained'):assert manifest['decoder_sha256']==spec['decoder_sha256']
            expected_sizes=None
            for cid in cohort_ids:
                p=dest/(cid+'.json');z=read(p);c=lookup[cid];assert z['case_id']==cid and z['configuration']==cfg and z['dataset']==c['dataset'];assert sorted(r['condition'] for r in z['conditions'])==sorted(conds)
                if cohort=='confirmation':assert p.stat().st_mtime>=selection_mtime
                if expected_sizes is None:expected_sizes=z['parameter_stats']
                assert z['parameter_stats']==expected_sizes
                for r in z['conditions']:
                    try:parsed=json.loads('{"diagnosis":"'+r['text'])['diagnosis']
                    except (ValueError,KeyError,TypeError):parsed=None
                    assert parsed==r['generated_disease'];assert r['correct']==(parsed==c['gold_disease']);assert r['listed']==(parsed in c['candidates']);assert 0<=r['tokens']<=64;count+=1
                    if cfg.get('constrained'):assert r['listed']
        generation_counts[folder+':'+','.join(conds)]=generation_counts.get(folder+':'+','.join(conds),0)+count
    assert generation_counts=={'structure_development:neutral,wrong':2080,'adapter_development:neutral,wrong':1440,'confirmation:neutral,wrong':5600,'confirmation:none':400}
    control_amend=read(DOC/'MATCHED_OUTPUT_CONTROL.json');assert control_amend['source_sha256']==sha(ROOT/'src/phase107_structure2_matched_output.py') and control_amend['selection_sha256']==sha(RUN/'confirmation_selection.json');control=control_amend['control'];folder=RUN/'output_matched_control'/control['name'];m=read(folder/'manifest.json');assert m['core_sha256']==spec['core_sha256'] and m['decoder_sha256']==spec['decoder_sha256'] and m['cases_sha256']==spec['cases_sha256'];cc=0
    for c in cs:
        if c['cohort']!='confirmation':continue
        z=read(folder/(c['case_id']+'.json'));assert z['configuration']==control and len(z['conditions'])==2
        for r in z['conditions']:
            assert json.loads('{"diagnosis":"'+r['text'])['diagnosis']==r['generated_disease'];assert r['listed'] and r['correct']==(r['generated_disease']==c['gold_disease']);cc+=1
    assert cc==800;ct=read(RUN/'output_matched_control/timing.json');assert len(ct['trials'])==24
    scoring=read(DOC/'SCORING_AMENDMENT.json');assert scoring['source_sha256']==sha(ROOT/'src/structure2_scoring.py') and scoring['cases_sha256']==sha(DATA/'cases.private.jsonl') and scoring['selection_sha256']==sha(RUN/'confirmation_selection.json');assert not scoring['ambiguous_case_ids'];assert all(len({normalize_name(x) for x in c['candidates']})==4 for c in cs)
    analyzed=read(ROOT/'results/49_structure_confirmation/summary.json')['normalized_scoring'];assert analyzed['rule_sha256']==scoring['source_sha256'];assert analyzed['constraint_repairs']==28 and analyzed['constraint_repairs_already_correct']==18
    for row in analyzed['per_method']:
        n=row['candidate'];folder='output_matched_control' if n==control['name'] else 'confirmation';totals=collections.Counter()
        for c in cs:
            if c['cohort']!='confirmation':continue
            for r in read(RUN/folder/n/(c['case_id']+'.json'))['conditions']:
                choice=surface_choice(c,r);totals[r['condition']]+=int(choice==c['gold_index'])
                if r['correct']:assert choice==c['gold_index']
        assert totals['neutral']==row['neutral_correct'] and totals['wrong']==row['wrong_correct']
    assert sum(r['normalized_correct'] for r in scoring['repairs'])==18
    scope=read(DOC/'ANSWER_SCOPE_AUDIT.json');assert scope['cases_sha256']==sha(DATA/'cases.private.jsonl');scope_ids={r['case_id'] for r in scope['rows']};assert len(scope_ids)==9
    strict_ids={r['case_id'] for r in audit['rows'] if r['cohort']=='confirmation' and r['strict_source_and_similarity_keep']};assert analyzed['answer_scope_sensitivity']['n']==len(strict_ids-scope_ids)
    for r in ct['trials']:
        for f in ['prefill_seconds','fixed12_decode_seconds','actual_answer_seconds']:assert r['baseline'][f]>0 and r['variant'][f]>0 and np.isclose(r['ratios'][f],r['variant'][f]/r['baseline'][f])
    feature_ids={c['case_id'] for c in cs if c['cohort'] in ['train','development']}
    for folder in ['base','pruned']:
        manifest=read(RUN/'features'/folder/'manifest.json');assert set(manifest['cases'])==feature_ids;assert {p.stem for p in (RUN/'features'/folder).glob('*.npz')}==feature_ids
    for cid in feature_ids:
        with np.load(RUN/'features/base'/(cid+'.npz')) as a,np.load(RUN/'features/pruned'/(cid+'.npz')) as b:
            assert np.array_equal(a['y'],b['y']) and np.array_equal(a['weight'],b['weight']);assert np.isclose(a['weight'].sum(),2)
            for key in a.files:assert np.isfinite(a[key]).all()
            for key in b.files:assert np.isfinite(b[key]).all()
    for cfg in read(RUN/'trained_adapters.json'):
        p=RUN/'adapters'/cfg['name'];z=read(p/'completion.json');assert z['train_cases']==400 and z['development_cases']==80 and z['full_vocabulary_size']==151936;assert z['weights_sha256']==sha(p/'best.safetensors');assert z['best_development_loss']==min(r['development_loss'] for r in z['history']);assert z['best_step'] in [0,100,300,600];assert z['trainable_parameters'] in [4096,67600,264256];assert read(p/'manifest.json')['core_sha256']==spec['core_sha256']
    bridge=read(RUN/'bridge/completion.json');assert bridge['weights_sha256']==sha(RUN/'bridge/rank64.npz') and bridge['parameters']==266240
    td=read(RUN/'timing/completion.json');assert td['paired_trials']==144
    for cfg in spec['configurations'][1:]:
        z=read(RUN/'timing'/(cfg['name']+'.json'));assert len(z['trials'])==24
        for r in z['trials']:
            for f in ['prefill_seconds','fixed12_decode_seconds','actual_answer_seconds']:assert r['baseline'][f]>0 and r['variant'][f]>0 and np.isclose(r['ratios'][f],r['variant'][f]/r['baseline'][f])
    trajectory_count=0;prefixes=sum(len(lookup[cid]['sentences']) for cid in spec['trajectory_cases']);assert len(set(spec['trajectory_cases']))==24
    for cid in spec['trajectory_cases']:
        c=lookup[cid];assert c['cohort']=='confirmation';T=len(c['sentences'])
        for cfg in spec['trajectory_configurations']:
            p=RUN/'trajectories'/(cid+'_'+cfg['name']+'.json');z=read(p);assert z['state_sha256']==sha(p.with_suffix('.npz'));assert len(z['conditions'])==2*T;assert {(r['condition'],r['round']) for r in z['conditions']}=={(co,t) for co in ['neutral','wrong'] for t in range(1,T+1)};final={r['condition']:r for r in read(RUN/'confirmation'/cfg['name']/(cid+'.json'))['conditions']}
            with np.load(p.with_suffix('.npz')) as a:
                assert len(a.files)==4*T
                for r in z['conditions']:
                    for field in ['q_sequence','q_token_mean']:
                        q=np.array(r[field]);assert q.shape==(4,) and np.isfinite(q).all() and np.all(q>=0) and np.isclose(q.sum(),1)
                    log=np.array(r['log_probability']);assert np.isfinite(log).all();q=np.exp(log-log.max());q/=q.sum();assert np.allclose(q,r['q_sequence']);assert r['correct']==(r['generated_disease']==c['gold_disease']);assert r['listed']==(r['generated_disease'] in c['candidates']);assert np.isfinite(r['adapter_relative_change']);key=f'{r["condition"]}_t{r["round"]}';assert a[key+'_layers'].shape[-1]==2048 and np.isfinite(a[key+'_layers']).all();assert a[key+'_readout'].shape==(2,2048) and np.isfinite(a[key+'_readout']).all()
                    if r['round']==T:assert r['generated_disease']==final[r['condition']]['generated_disease'] and r['text']==final[r['condition']]['text'] and r['prompt_sha256']==final[r['condition']]['prompt_sha256']
                    trajectory_count+=1
    assert trajectory_count==prefixes*2*len(spec['trajectory_configurations']);base=read(ROOT/'runs/belief_v4/manifest.json');model=ROOT.parent/'MedicalBeliefMechanisms/.models/Qwen3-1.7B';hashes={n:filehash(model/n) for n in base['model_hashes']};assert hashes==base['model_hashes']
    result=dict(complete=True,cohort_cases=880,splits=counts,new_cases_disjoint_from_old540=True,source_and_data_hashes_verified=True,confirmation_selection_precedes_every_confirmation_output=True,all_core_and_decoder_hashes_match=True,actual_generations=generation_counts,development_and_confirmation_generations=sum(generation_counts.values()),trained_adapters=5,bridge_parameters=266240,timing_pairs=144,trajectory_cases=24,trajectory_prefixes=prefixes,trajectory_observations=trajectory_count,all_final_trajectories_match_confirmation=True,all_probabilities_finite_and_normalized=True,original_model_files_unchanged=hashes,api_cost_usd=0)
    result.update(matched_output_control_generations=800,matched_output_timing_pairs=24,post_primary_control_registered=True,normalized_scores_independently_recomputed=True,scoring_amendment_hash_verified=True,surface_normalization_preserves_all_strict_correct=True);write(DOC/'FINAL_VALIDATION.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
