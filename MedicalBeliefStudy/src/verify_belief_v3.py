"""Verify all completed v3 inputs, observations, intervention controls and results."""
import collections,csv,hashlib,json,re
from pathlib import Path
import numpy as np
from belief_v3_analysis import ROOT,read,rows,sha,dump
def validate_score(r,K):
 lp=np.asarray(r['log_probability']);q=np.asarray(r['q_sequence']);assert lp.shape==q.shape==(K,) and np.isfinite(lp).all() and np.isfinite(q).all()
 exp=np.exp(lp-lp.max());assert np.allclose(q,exp/exp.sum(),rtol=1e-9,atol=1e-12)
 assert np.isclose(sum(np.exp(lp)),r['sequence_probability_mass'],rtol=1e-7)
 tlp=r['token_log_probability'];assert len(tlp)==K
 assert np.allclose([sum(v) for v in tlp],lp,atol=1e-8)
 if r.get('cache_validation'):assert r['cache_validation']['absolute_error']<.15
def main():
 dest=ROOT/'results/27_building_synthesis';dest.mkdir(parents=True,exist_ok=True);audit={'api_cost_usd':0,'observations':{},'interventions':{}};cases=rows(ROOT/'data/belief_v3/cases.private.jsonl');cids={c['case_id'] for c in cases};assert len(cids)==240 and len({c['fact_signature'] for c in cases})==240;old=[]
 from phase14_prepare import factsig
 for n in ['cases.private.jsonl','full49_v1/cases.private.jsonl','belief_v2/cases.private.jsonl']:old+=rows(ROOT/'data'/n)
 assert not {factsig(c['explicit_evidence_groups']) for c in old}&{c['fact_signature'] for c in cases}
 for p in [ROOT/'results/14_fixed_panel/training_heads.npz',ROOT/'results/18_model_replication/training_heads.npz']:
  with np.load(p) as a:assert not set(a['training_ids'].tolist())&cids
 audit['new_ddx_patients']=240;audit['new_ddx_deep']=sum(c['deep_capture'] for c in cases);audit['new_ddx_fact_overlap']=0
 for name,jobfile,K,L in [('belief_v3','belief_v3/jobs.jsonl',49,28),('belief_v3_4b','belief_v3/jobs4b.jsonl',49,36),('belief_v3_medqa','external_medqa/jobs.jsonl',4,28)]:
  run=ROOT/'runs'/name;complete=read(run/'completion.json');assert complete['complete'] and complete['weights_unchanged'];jobs=rows(ROOT/'data'/jobfile);expected={r['job_id'] for r in jobs};actual={p.stem for p in (run/'observations').glob('*.json')};assert expected==actual;manifest=read(run/'manifest.json');assert sha(ROOT/'data'/jobfile)==manifest['input_sha256'];assert manifest['source_sha256']==sha(run/'source_snapshot.py');attention_error=0.;cache_errors=[]
  for i,job in enumerate(jobs):
   r=read(run/'observations'/(job['job_id']+'.json'));validate_score(r,K);assert sha(run/r['state_file'])==r['state_sha256']
   with np.load(run/r['state_file']) as a:assert a['residual_stages'].shape[:2]==(L,5);assert np.isfinite(a['residual_stages']).all();assert np.allclose(a['attention_by_group'].sum(-1),1,atol=1e-5);assert np.isfinite(a['attention_reconstruction_relative_rms']).all();attention_error=max(attention_error,float(a['attention_reconstruction_relative_rms'].max()))
   if r.get('cache_validation'):cache_errors.append(r['cache_validation']['absolute_error'])
  assert attention_error<.02;audit['observations'][name]={'records':len(jobs),'all_state_hashes_match':True,'attention_max_error':attention_error,'cache_validation_count':len(cache_errors),'cache_validation_max_error':max(cache_errors)};print('Verified',name,len(jobs),flush=True)
  model=ROOT.parent/'MedicalBeliefMechanisms/.models'/('Qwen3-4B-8bit' if name.endswith('4b') else 'Qwen3-1.7B');assert {n:sha(model/n) for n in manifest['model_hashes']}==manifest['model_hashes']
 for name,N in [('natural_interventions',24),('natural_interventions_replication',48)]:
  run=ROOT/'runs/belief_v3'/name;done=read(run/'completion.json');assert done['patients']==N and done['conditions']==N*12 and done['weights_unchanged'];records=[read(p) for p in run.glob('ddx*.json')];assert len(records)==N;expected={c['case_id'] for c in cases if (c['mechanism_capture'] if N==24 else c['deep_capture'] and not c['mechanism_capture'])};assert {r['case_id'] for r in records}==expected;errors=[]
  for r in records:
   assert sha(run/r['state_file'])==r['state_sha256'];assert len(r['conditions'])==12
   for z in r['conditions']:
    validate_score(z,49)
    if z['condition']=='self':errors.append(z['sham_max_logp_error']);assert z['requested_delta_norm']==0 and z['actual_delta_norm']==0
   for l in [14,21,28]:
    z={z['condition']:z for z in r['conditions'] if z['layer']==l};assert np.isclose(z['remove_target']['requested_delta_norm'],z['random_matched']['requested_delta_norm'],rtol=1e-8)
  assert max(errors)<.05;audit['interventions'][name]={'patients':N,'conditions':N*12,'sham_max_logp_error':max(errors),'equal_requested_norm_target_random':True};print('Verified',name,N,flush=True)
 for name,N in [('evidence_context',208),('history_matched',24),('role_binding',216)]:
  run=ROOT/'runs/belief_v3'/name;done=read(run/'completion.json');assert done['complete'] and done['weights_unchanged'];records=[read(p) for p in run.glob('ddx*.json')];assert len(records)==N
  for r in records:validate_score(r,49);assert sha(run/r['state_file'])==r['state_sha256']
  if name=='role_binding':
   lookup={c['case_id']:c for c in cases}
   for r in records:
    c=lookup[r['case_id']];assert set(r['role_mapping'])==set(c['explicit_evidence_groups'])
    for group,label in r['role_mapping'].items():
     flags={v['is_antecedent'] for v in c['explicit_evidence_groups'][group]};assert len(flags)==1;history=flags.pop();expected='UNSPECIFIED' if r['condition']=='neutral' else ('HISTORY' if (history if r['condition']=='correct' else not history) else 'CURRENT');assert label==expected
  audit['observations'][name]={'records':N,'all_state_hashes_match':True};print('Verified',name,N,flush=True)
 ext=rows(ROOT/'data/external_medqa/cases.private.jsonl');assert len(ext)==87
 for c in ext:assert c['source_options'][c['answer_idx']]==c['gold_disease'];assert re.sub(r'\s+',' ',' '.join(c['evidence_sentences'])+' '+c['diagnostic_question'])==re.sub(r'\s+',' ',c['question'].strip());assert '.' not in c['diagnostic_question']
 run=ROOT/'runs/belief_v3_medqa/natural_interventions';complete=read(run/'completion.json');assert complete['complete'] and complete['weights_unchanged'];external_interventions=[read(p) for p in run.glob('medqa*.json')];assert len(external_interventions)==87;errors=[]
 for r in external_interventions:
  assert sha(run/r['state_file'])==r['state_sha256'] and len(r['conditions'])==9
  for z in r['conditions']:
   validate_score(z,4)
   if z['condition']=='self':errors.append(z['sham_max_logp_error']);assert z['actual_delta_norm']==0
  for l in [14,21,28]:
   z={v['condition']:v for v in r['conditions'] if v['layer']==l};assert np.isclose(z['replace_old']['requested_delta_norm'],z['random_matched']['requested_delta_norm'],rtol=1e-8)
 assert max(errors)<.05;audit['interventions']['external_medqa']={'patients':87,'conditions':783,'sham_max_logp_error':max(errors),'equal_requested_norm_old_random':True}
 for subrun in ['belief_v3/natural_interventions','belief_v3/natural_interventions_replication','belief_v3/evidence_context','belief_v3/history_matched','belief_v3/role_binding','belief_v3_medqa/natural_interventions']:
  run=ROOT/'runs'/subrun;manifest=read(run/'manifest.json');assert manifest['source_sha256']==sha(run/'source_snapshot.py')
 audit['external_cases']=87;audit['total_new_patients_or_vignettes']=327;audit['total_observation_conditions']=sum(v['records'] for v in audit['observations'].values())+sum(v['conditions'] for v in audit['interventions'].values());assert audit['total_observation_conditions']==4832
 for name,N in [('23_new_patients',72),('26_external_medqa',87),('28_new_4b_replication',24)]:
  d=ROOT/'results'/name;summary=read(d/'summary.json');assert len(list((d/'cases').glob('*.md')))==N
  for p in (d/'cases').glob('*.md'):assert p.with_suffix('.png').exists() and p.with_suffix('.pdf').exists()
  if name!='26_external_medqa':
   with (d/'endpoint_cases.csv').open() as f:ep=list(csv.DictReader(f))
   for v in summary['endpoints']:
    e=[r for r in ep if r['view']==v];assert len(e)==240;assert np.isclose(np.mean([r['native24']==r['gold'] for r in e]),summary['endpoints'][v]['native24']['mean']);assert np.isclose(np.mean([r['probe_last']==r['gold'] for r in e]),summary['endpoints'][v]['layers'][str(36 if '4b' in name else 28)]['mean'])
 audit['verified']=True;audit['analysis_source_hashes']={p.name:sha(p) for p in (ROOT/'src').glob('*v3*.py')};audit['analysis_source_hashes'].update({p.name:sha(p) for p in (ROOT/'src').glob('phase*.py') if re.match(r'phase(2[3-9]|3[0-9])',p.name)});dump(dest/'validation.json',audit);print(json.dumps(audit,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
