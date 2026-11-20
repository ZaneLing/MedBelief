"""Freeze new patients and a broad, finite set of medical-belief experiments."""
import ast,csv,collections,hashlib,json,re
from pathlib import Path
from phase6_prepare import ROOT,FAMILIES,groups_from_raw,sha,write
from phase14_prepare import factsig,job
DEST=ROOT/'data/belief_v3';SEED='medical-belief-building-v3-20261119'
def rank(s):return hashlib.sha256((SEED+':'+s).encode()).hexdigest()
def dumpjsonl(path,rows):
 text=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows)
 if path.exists():assert path.read_text()==text
 else:path.write_text(text)
def main():
 DEST.mkdir(exist_ok=True);raw=ROOT.parent/'ClinicalBelief/data/raw';ev=json.loads((raw/'release_evidences.json').read_text());diseases=json.loads((ROOT/'runs/belief_v2/manifest.json').read_text())['candidate_diseases'];target={d:f for f,dd in FAMILIES.items() for d in dd};old=[]
 for file in [ROOT/'data/cases.private.jsonl',ROOT/'data/full49_v1/cases.private.jsonl',ROOT/'data/belief_v2/cases.private.jsonl']:old.extend(map(json.loads,file.read_text().splitlines()))
 excluded={factsig(c['explicit_evidence_groups']) for c in old};pools=collections.defaultdict(list)
 with (raw/'test.csv').open() as f:
  for i,r in enumerate(csv.DictReader(f)):
   if r['PATHOLOGY'] not in target or not 18<=int(float(r['AGE']))<=90:continue
   groups,initial=groups_from_raw(r,ev)
   if len(groups)<5:continue
   sig=factsig(groups)
   if sig in excluded:continue
   c=dict(case_id=f'ddx_test_{i:07d}',source_row_zero_based=i,source_split='test',gold_disease=r['PATHOLOGY'],family=target[r['PATHOLOGY']],age=int(float(r['AGE'])),sex=r['SEX'],initial_question_group=initial,explicit_evidence_groups=groups,fact_signature=sig,reference_differential=dict(ast.literal_eval(r['DIFFERENTIAL_DIAGNOSIS'])))
   pools[r['PATHOLOGY']].append(c)
 chosen=[];used=set(excluded)
 for d in sorted(target):
  take=[]
  for c in sorted(pools[d],key=lambda c:rank(c['case_id'])):
   if c['fact_signature'] in used:continue
   used.add(c['fact_signature']);take.append(c)
   if len(take)==10:break
  assert len(take)==10
  take.sort(key=lambda c:rank(c['case_id']+':deep'))
  for i,c in enumerate(take):
   seq=sorted((g for g in c['explicit_evidence_groups'] if g!=c['initial_question_group']),key=lambda g:rank(c['case_id']+':order:'+g));c.update(deep_capture=i<3,mechanism_capture=i==0,orders=dict(base=seq,reverse=list(reversed(seq)),shuffle=sorted(seq,key=lambda g:rank(c['case_id']+':shuffle:'+g))),fixed_middle_round=max(1,len(seq)//2));chosen.append(c)
 jobs=[];jobs4=[]
 for c in chosen:
  T=len(c['orders']['base']);middle=c['fixed_middle_round']
  for t in (range(T+1) if c['deep_capture'] else [T]):jobs.append(job(c,'new_test','append','base',t,diseases))
  jobs.append(job(c,'new_test','panel','base',T,diseases))
  for t in (range(T+1) if c['mechanism_capture'] else [T]):jobs4.append(job(c,'new_test','append','base',t,diseases))
  if c['deep_capture']:
   for order in ['reverse','shuffle']:jobs.append(job(c,'new_test','append',order,T,diseases))
  if c['mechanism_capture']:
   for cond in ['repeat_middle','remove_middle','omit_named_history']:
    row=job(c,'new_test','append','base',T,diseases);row.update(condition=cond,job_id=c['case_id']+'_'+cond,intervention_group=c['orders']['base'][middle-1]);jobs.append(row)
   for cond in ['history_actual','history_gold','history_wrong','history_wrong_final']:
    t=T if cond.endswith('_final') else middle;row=job(c,'new_test','append','base',t,diseases);row.update(condition=cond,job_id=c['case_id']+'_'+cond,previous_round=middle-1,source_label=c['gold_disease'] if cond=='history_gold' else None,wrong_disease=next(d for d in sorted(diseases,key=lambda d:rank(c['case_id']+':wrong:'+d)) if d!=c['gold_disease']));jobs.append(row)
 # Public jobs contain source_label only in explicitly oracle-labelled historical control.
 dumpjsonl(DEST/'cases.private.jsonl',chosen);dumpjsonl(DEST/'jobs.jsonl',jobs);dumpjsonl(DEST/'jobs4b.jsonl',jobs4)
 manifest={'seed':SEED,'new_patients':len(chosen),'classes':len(target),'deep_patients':sum(c['deep_capture'] for c in chosen),'mechanism_patients':sum(c['mechanism_capture'] for c in chosen),'complete_trajectory_updates':sum(len(c['orders']['base']) for c in chosen if c['deep_capture']),'jobs_1_7b':len(jobs),'jobs_4b':len(jobs4),'jobs_by_condition':dict(collections.Counter(r.get('condition',r['view']+'_'+r['order']) for r in jobs)),'excluded_prior_fact_sets':len(excluded),'new_fact_sets_unique':len({c['fact_signature'] for c in chosen}),'prior_overlap':0,'source_hashes':{n:sha(raw/n) for n in ['test.csv','release_evidences.json']},'protocol_sha256':sha(ROOT/'research_v3/BUILDING_PLAN.md'),'script_sha256':sha(__file__),'api_cost_usd':0}
 write(DEST/'manifest.json',manifest);print(json.dumps(manifest),flush=True)
if __name__=='__main__':main()
