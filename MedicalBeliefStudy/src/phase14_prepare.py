"""Frozen test-split cohort and matched fixed-panel / append observations."""
import ast, collections, csv, hashlib, json
from pathlib import Path
from phase6_prepare import ROOT, FAMILIES, groups_from_raw, signature, sha, write

DEST=ROOT/'data/belief_v2'
SEED='belief-v2-test-panel-20261118'
def rank(s): return hashlib.sha256((SEED+':'+s).encode()).hexdigest()
def factsig(groups):
    facts=sorted((x['evidence_id'],tuple(sorted(x['values']))) for g in groups.values() for x in g)
    return hashlib.sha256(json.dumps(facts).encode()).hexdigest()
def main():
    raw=ROOT.parent/'ClinicalBelief/data/raw'
    ev=json.loads((raw/'release_evidences.json').read_text())
    old=[json.loads(s) for s in (ROOT/'data/full49_v1/cases.private.jsonl').read_text().splitlines()]
    prior=old+[json.loads(s) for s in (ROOT/'data/cases.private.jsonl').read_text().splitlines()]
    excluded={factsig(c['explicit_evidence_groups']) for c in prior}
    diseases=json.loads((ROOT/'runs/structured_names_v1/manifest.json').read_text())['candidate_diseases']
    targets={d:f for f,ds in FAMILIES.items() for d in ds};pools=collections.defaultdict(list);duplicates=0
    with (raw/'test.csv').open() as f:
        for i,row in enumerate(csv.DictReader(f)):
            if row['PATHOLOGY'] not in targets or not 18<=int(float(row['AGE']))<=90:continue
            groups,initial=groups_from_raw(row,ev)
            if len(groups)<5:continue
            sig=factsig(groups)
            if sig in excluded:duplicates+=1;continue
            diff=dict(ast.literal_eval(row['DIFFERENTIAL_DIAGNOSIS']))
            assert set(diff)<=set(diseases) and abs(sum(diff.values())-1)<1e-6
            pools[row['PATHOLOGY']].append(dict(case_id=f'ddx_test_{i:07d}',source_row_zero_based=i,source_split='test',
                family=targets[row['PATHOLOGY']],gold_disease=row['PATHOLOGY'],age=int(float(row['AGE'])),sex=row['SEX'],
                initial_question_group=initial,explicit_evidence_groups=groups,reference_differential=diff,fact_signature=sig))
    chosen=[];used=set(excluded)
    for d in sorted(targets):
        take=[]
        for c in sorted(pools[d],key=lambda c:rank(c['case_id']+':select')):
            if c['fact_signature'] in used:continue
            take.append(c);used.add(c['fact_signature'])
            if len(take)==5:break
        assert len(take)==5;chosen+=take
    chosen.sort(key=lambda c:rank(c['case_id']+':deep'))
    for i,c in enumerate(chosen):
        seq=sorted((g for g in c['explicit_evidence_groups'] if g!=c['initial_question_group']),key=lambda g:rank(c['case_id']+':base:'+g))
        c.update(orders={'base':seq,'reverse':list(reversed(seq)),'shuffle':sorted(seq,key=lambda g:rank(c['case_id']+':shuffle:'+g))},deep_capture=i<24,fixed_middle_round=len(seq)//2)
    jobs=[]
    for cohort,cases in [('train',old),('test',chosen)]:
        for c in cases:
            T=len(c['orders']['base'])
            for view in (['panel'] if cohort=='train' else ['append','panel']):
                rounds=range(T+1) if cohort=='test' and c['deep_capture'] else [T]
                for t in rounds:jobs.append(job(c,cohort,view,'base',t,diseases))
            if cohort=='test' and c['deep_capture']:
                jobs.append(job(c,cohort,'presence','base',T,diseases))
                for order in ['reverse','shuffle']:jobs.append(job(c,cohort,'append',order,T,diseases))
    DEST.mkdir(parents=True,exist_ok=True)
    for name,rows in [('cases.private.jsonl',chosen),('jobs.public.jsonl',jobs)]:
        content=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows);p=DEST/name
        if p.exists():assert p.read_text()==content
        else:p.write_text(content)
    write(DEST/'panel.json',[{'evidence_id':k,'question_en':v['question_en'],'is_antecedent':v['is_antecedent'],'data_type':v['data_type']} for k,v in sorted(ev.items(),key=lambda kv:int(kv[0][2:]))])
    manifest={'seed':SEED,'test_cases':120,'training_cases':120,'deep_test_cases':[c['case_id'] for c in chosen if c['deep_capture']],
        'jobs':len(jobs),'jobs_by_view':dict(collections.Counter(r['view'] for r in jobs)),'fields':len(ev),
        'source_hashes':{p.name:sha(p) for p in [raw/'test.csv',raw/'release_evidences.json']},'excluded_prior_fact_duplicates':duplicates,
        'prior_unique_fact_sets':len(excluded),'source_sha256':sha(__file__),'protocol_sha256':sha(ROOT/'protocol/MECHANISM_CONTINUATION_V2.md'),
        'input_hashes':{p.name:sha(p) for p in DEST.glob('*.json*') if p.name!='manifest.json'}}
    write(DEST/'manifest.json',manifest);print(json.dumps(manifest,ensure_ascii=False),flush=True)
def job(c,cohort,view,order,t,diseases):
    return dict(job_id=f"{c['case_id']}_{view}_{order}_t{t:02d}",case_id=c['case_id'],cohort=cohort,view=view,order=order,round=t,last_round=len(c['orders']['base']),
        age=c['age'],sex=c['sex'],family=c['family'],candidate_diseases=diseases,deep_capture=c['deep_capture'],
        revealed_groups=[{'question_group_id':g,'items':c['explicit_evidence_groups'][g]} for g in [c['initial_question_group']]+c['orders'][order][:t]])
if __name__=='__main__':main()
