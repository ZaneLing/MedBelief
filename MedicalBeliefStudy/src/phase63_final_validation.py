"""Final multi-stage consistency audit, separate from exploratory analysis."""
from pathlib import Path
import json,hashlib,collections
import numpy as np
from phase41_multisource_analyze import ROOT,DATA,RUN,read,write

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 cases=list(map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines()));mech={c['case_id']:c for c in cases if c['mechanism_capture']};conf={k:c for k,c in mech.items() if c['cohort']=='confirmation'};ch=sha(DATA/'cases.private.jsonl');checks={};max_sham=0.;max_state=0.
 assert read(ROOT/'research_v4/main_validation.json')['complete']
 for folder,patients,conditions,key in [('belief_v4',540,6823,'observations'),('belief_v4_4b',94,1034,'observations'),('belief_v4_layer_trajectories',94,1960,'new_observations'),('belief_v4_routes_1.7b',48,1152,'conditions'),('belief_v4_routes_4b',48,1152,'conditions'),('belief_v4_module_readout',94,376,'endpoint_state_readouts'),('belief_v4_final_mlp',94,940,'intervention_conditions'),('belief_v4_names_1.7b',48,480,'conditions'),('belief_v4_names_4b',48,480,'conditions')]:
  path=ROOT/'runs'/folder;done=read(path/'completion.json');spec=read(path/'manifest.json');assert done['complete'] and done['patients']==patients and done[key]==conditions;assert spec['cases_sha256']==ch;checks[folder]=dict(patients=patients,conditions=conditions)
 for folder,n,trials in [('patches',94,26),('mention_patches',48,20)]:
  path=RUN/folder;done=read(path/'completion.json');assert done['complete'] and done['conditions']==n*trials
  cc=mech if n==94 else conf
  for cid in cc:
   z=read(path/(cid+'.json'));assert len(z['conditions'])==trials
   for r in z['conditions']:
    assert np.isfinite(r['log_probability']).all() and np.isfinite(r['q_sequence']).all();assert abs(sum(r['q_sequence'])-1)<1e-6
    if r.get('sham_max_logp_error') is not None:max_sham=max(max_sham,r['sham_max_logp_error'])
    if 'state_error' in r:max_state=max(max_state,r['state_error'])
    if r['condition'].startswith('random'):assert np.isclose(r['requested_norm'],r['delta_norm'],rtol=1e-5,atol=1e-4)
  checks[folder]=dict(patients=n,conditions=n*trials)
 assert max_sham<.05 and max_state<.02
 for folder in ['belief_v4_routes_1.7b','belief_v4_routes_4b']:
  n=0
  for cid in conf:
   z=read(ROOT/'runs'/folder/(cid+'.json'));assert len(z['conditions'])==24
   identities={(r['condition'],r['rotation'],r['route']) for r in z['conditions']};assert len(identities)==24
   for r in z['conditions']:
    q=np.array(r['q']);lp=np.array(r['log_probability']);assert np.isfinite(q).all() and np.isfinite(lp).all() and abs(q.sum()-1)<1e-6;assert np.allclose(q,np.exp(lp-lp.max())/np.exp(lp-lp.max()).sum(),atol=1e-6);assert np.isclose(np.exp(lp).sum(),r['candidate_mass'],atol=1e-6)
    p=r['partition'];assert p['history_start']<p['facts_start']<p['facts_end']<p['total'];assert p['facts_end']==p['decision_start']
    if r['native_check']:assert r['native_check']['allclose'] and r['native_check']['same_argmax'];n+=1
  checks[folder]['native_checks']=n
 name_check_error=0.
 for model in ['1.7b','4b']:
  for cid,c in conf.items():
   names=read(ROOT/'runs'/('belief_v4_names_'+model)/(cid+'.json'))['conditions'];assert len(names)==10
   assert {(r['named_index'],r['rotation']) for r in names}=={(j,rot) for j in [-1,0,1,2,3] for rot in [0,2]}
   routes=read(ROOT/'runs'/('belief_v4_routes_'+model)/(cid+'.json'))['conditions']
   for r in names:
    assert np.isfinite(r['q']).all() and abs(sum(r['q'])-1)<1e-6
    if r['named_index']==c['wrong_index']:
     original=next(z for z in routes if z['condition']=='mention' and z['route']=='full' and z['rotation']==r['rotation']);assert r['prompt_sha256']==original['prompt_sha256'];name_check_error=max(name_check_error,float(np.max(np.abs(np.array(r['q'])-original['q']))))
 assert name_check_error<.02
 # Extra trajectory readouts are finite and agree with their frozen case metadata.
 extra=ROOT/'runs/belief_v4_layer_trajectories';records=list(extra.glob('*_code_*.json'));assert len(records)==1960
 for p in records:
  z=read(p);c=mech[z['case_id']];assert z['candidate_diseases']==c['candidates'];q=np.array(z['layer_code_support']);assert q.shape==(28,4) and np.isfinite(q).all() and np.allclose(q.sum(1),1,atol=1e-6)
 # Verify each larger-model state artifact. Auxiliary original means are deprecated.
 r4=ROOT/'runs/belief_v4_4b';nonfinite4=0
 for p in (r4/'observations').glob('*.json'):
  z=read(p);assert sha(r4/z['state_file'])==z['state_sha256'];assert np.isfinite(z['log_probability']).all()
  with np.load(r4/z['state_file']) as a:
   assert np.isfinite(a['residual_anchor']).all() and np.isfinite(a['attention_by_group']).all();assert a['residual_anchor'].shape[0]==36
   nonfinite4+=int(not np.isfinite(a['evidence_means']).all())
 repair=RUN/'mean_repair';assert read(repair/'completion.json')['complete'];files=list(repair.glob('*.npz'));assert len(files)==1080;err=0.
 for p in files:
  with np.load(p) as a:assert a['evidence_means'].shape[0]==28 and np.isfinite(a['evidence_means']).all();err=max(err,float(a['anchor_error']))
 assert err<.02
 # Models and immutable sources still match their original run manifests.
 for folder,modeldir in [('belief_v4','Qwen3-1.7B'),('belief_v4_4b','Qwen3-4B-8bit')]:
  sp=read(ROOT/'runs'/folder/'manifest.json')
  for name,h in sp['model_hashes'].items():assert sha(ROOT.parent/'MedicalBeliefMechanisms/.models'/modeldir/name)==h
 # Full code-layer export cardinality and per-case atlases.
 import gzip,csv
 atlas=ROOT/'results/34_multisource_depth';nrows=sum(1 for _ in gzip.open(atlas/'all_round_layer_candidates.csv.gz','rt'))-1;assert nrows==240576
 for cid in mech:
  for ext in ['md','png','pdf']:assert (atlas/'cases'/(cid+'.'+ext)).is_file()
  for ext in ['png','pdf']:assert (atlas/'cases'/(cid+'_all_candidates.'+ext)).is_file()
 summaries=['32_multisource_belief','33_multisource_causality','34_multisource_depth','35_unendorsed_name','36_history_routes','37_behavior_checks','38_text_quality','39_module_readout','40_final_mlp','41_name_counterbalance']
 for d in summaries:assert (ROOT/'results'/d/'RESULTS.md').exists() and (ROOT/'results'/d/'summary.json').exists()
 result=dict(complete=True,api_cost_usd=0,cases=540,strict_text_cases=520,full_trajectory_cases=94,strict_full_trajectory_cases=92,confirmation_mechanism_cases=48,strict_confirmation_mechanism_cases=47,stages=checks,total_prompt_or_transfer_conditions=15525,additional_final_mlp_transfers=940,additional_name_counterbalance_evaluations=960,max_counterbalance_native_repeat_error=name_check_error,additional_endpoint_state_readouts=376,baseline_recaptures=48,fp32_mean_recaptures=1080,all_case_hashes_match=True,model_weights_unchanged=True,max_sham_logp_error=max_sham,max_patch_reference_state_error=max_state,max_fp32_repair_anchor_error=err,deprecated_4b_auxiliary_mean_arrays_nonfinite=nonfinite4,atlas_patients=94,layer_candidate_export_rows=nrows,all_required_results_present=True)
 write(ROOT/'research_v4/FINAL_VALIDATION.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
