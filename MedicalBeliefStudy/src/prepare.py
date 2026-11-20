from pathlib import Path
import ast,csv,hashlib,json,collections
import numpy as np
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT.parent
SEED=20261119
DISEASES=['Pneumonia','Bronchitis','Bronchosp / placeholder','Pulmonary embolism','Spontaneous pneumothorax','Acute pulmonary edema']
DISEASES[2]='Bronchospasm / acute asthma exacerbation'
def rank(s):return hashlib.sha256(f'{SEED}:{s}'.encode()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def jsonl(p,rows):p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
def main():
 raw=WORK/'ClinicalBelief/data/raw';ev=json.loads((raw/'release_evidences.json').read_text())
 pilot=list(map(json.loads,(WORK/'MedicalBelief1_7B/data/pilot_cases.private.jsonl').read_text().splitlines()))
 pilot_ids={r['case_id'] for r in pilot};lookup={};pools={s:{d:[] for d in DISEASES} for s in ['fit','discovery']}
 for split in pools:
  z=np.load(WORK/f'ClinicalBelief/data/processed/{split}.npz',allow_pickle=True)
  for cid in map(str,z['case_ids']):lookup[int(cid.rsplit('_',1)[1])]=(cid,split)
 bad=[];last_row=max(lookup)
 with (raw/'train.csv').open(newline='') as f:
  for i,r in enumerate(csv.DictReader(f)):
   if i>last_row:break
   if i not in lookup or r['PATHOLOGY'] not in DISEASES:continue
   cid,split=lookup[i]
   if cid in pilot_ids or not 18<=int(float(r['AGE']))<=90:continue
   try:
    explicit={}
    for token in ast.literal_eval(r['EVIDENCES']):
     e,sep,val=token.partition('_@_');explicit.setdefault(e,[]).append(val if sep else '1')
    groups={}
    for e,vals in explicit.items():
     meta=ev[e];rendered=[]
     for v in vals:
      if meta['data_type']=='B':assert v=='1';rendered.append('Yes')
      elif v in meta.get('value_meaning',{}):
       meaning=meta['value_meaning'][v]['en'];rendered.append({'Y':'Yes','N':'No'}.get(meaning,meaning))
      else:assert meta['data_type']=='C' and v in map(str,meta['possible-values']);rendered.append('dataset scale value '+v)
     groups.setdefault(meta['code_question'],[]).append({'evidence_id':e,'question_en':meta['question_en'],'answer_en':'; '.join(rendered),'data_type':meta['data_type'],'values':vals,'is_antecedent':meta.get('is_antecedent',False),'source':'explicit_raw_token'})
    for g in groups.values():g.sort(key=lambda x:int(x['evidence_id'].split('_')[1]))
    initial=r['INITIAL_EVIDENCE'].split('_@_')[0];assert initial in explicit
    ig=ev[initial]['code_question'];new=[g for g in groups if g!=ig]
    if len(new)<4:continue
    pools[split][r['PATHOLOGY']].append({'case_id':cid,'source_row_zero_based':i,'source_split':'train','secondary_split':split,
      'gold_disease':r['PATHOLOGY'],'age':int(float(r['AGE'])),'sex':r['SEX'],'initial_question_group':ig,
      'explicit_evidence_groups':groups,'new_group_order':sorted(new,key=lambda g:rank(cid+':order:'+g))})
   except (ValueError,AssertionError,KeyError,SyntaxError) as e:bad.append({'case_id':cid,'error':type(e).__name__})
 selected=[]
 for d in DISEASES:
  dis=sorted(pools['discovery'][d],key=lambda r:rank(r['case_id']+':select'));fit=sorted(pools['fit'][d],key=lambda r:rank(r['case_id']+':select'))
  assert len(dis)>=10 and len(fit)>=30,(d,len(dis),len(fit))
  selected.extend([{**r,'cohort':'replication'} for r in dis[:10]])
  selected.extend([{**r,'cohort':'readout_train'} for r in fit[:20]])
  selected.extend([{**r,'cohort':'readout_dev'} for r in fit[20:30]])
 selected.extend([{**r,'cohort':'pilot'} for r in pilot])
 assert len({r['case_id'] for r in selected})==252
 jobs=[];full_cases=[]
 for case in selected:
  cid=case['case_id'];base=case['new_group_order'];T=len(base)
  offset=(next(i for i,r in enumerate(pilot) if r['case_id']==cid)%6) if case['cohort']=='pilot' else int(rank(cid+':mapping')[:8],16)%6
  orders={'base':base,'reverse':list(reversed(base)),'shuffle':sorted(base,key=lambda g:rank(cid+':alternative:'+g))}
  if case['cohort'].startswith('readout'):orders={'base':base}
  case['orders']=orders;case['mapping_offset']=offset;full_cases.append(case)
  for order,seq in orders.items():
   rounds=[0,T//2,T] if case['cohort'].startswith('readout') else range(T+1)
   for t in rounds:
    groups=[case['initial_question_group']]+seq[:t]
    assert len(groups)==len(set(groups))
    mappings=[0] if case['cohort'].startswith('readout') else [0,3]
    if not case['cohort'].startswith('readout') and ((order=='base' and t in [0,T//2,T]) or t==T):mappings=list(range(6))
    for rotation in mappings:
     jobs.append({'job_id':f'{cid}_{order}_t{t:02d}_m{rotation}','case_id':cid,'cohort':case['cohort'],'order':order,'round':t,'last_round':T,
      'age':case['age'],'sex':case['sex'],'new_question_group':seq[t-1] if t else None,
      'revealed_groups':[{'question_group_id':g,'items':case['explicit_evidence_groups'][g]} for g in groups],
      'candidate_diseases':DISEASES,'mapping_offset':offset,'rotation':rotation,'reasoning_history':[]})
 # Run independent readout data first; stages2/3 share one frozen forward dataset.
 priority={'readout_train':0,'readout_dev':1,'replication':2,'pilot':3}
 jobs.sort(key=lambda r:(priority[r['cohort']],r['case_id'],['base','reverse','shuffle'].index(r['order']),r['round'],r['rotation']))
 jsonl(ROOT/'data/cases.private.jsonl',full_cases);jsonl(ROOT/'data/jobs.public.jsonl',jobs)
 meta={'seed':SEED,'cohorts':dict(collections.Counter(r['cohort'] for r in full_cases)),'jobs':len(jobs),
  'jobs_by_cohort':dict(collections.Counter(r['cohort'] for r in jobs)),'eligible':{s:{d:len(v) for d,v in pool.items()} for s,pool in pools.items()},'invalid_records':bad,
  'source_hashes':{str(p.relative_to(WORK)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [raw/'train.csv',raw/'release_evidences.json',WORK/'ClinicalBelief/data/processed/fit.npz',WORK/'ClinicalBelief/data/processed/discovery.npz']},
  'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 dump(ROOT/'protocol/cohort_manifest.json',meta);print(json.dumps(meta,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
