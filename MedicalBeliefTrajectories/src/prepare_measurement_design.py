"""Read-only source audit and deterministic case preparation; no LLM inference."""
from pathlib import Path
import ast,csv,hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT.parent
SEED=20261118
DISEASES=['Pneumonia','Bronchitis','Bronchospasm / acute asthma exacerbation','Pulmonary embolism','Spontaneous pneumothorax','Acute pulmonary edema']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def priority(s):return hashlib.sha256(f'{SEED}:{s}'.encode()).hexdigest()
def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    assert not path.exists(),path
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def main():
    raw=WORK/'ClinicalBelief/data/raw';schema_path=WORK/'ClinicalBelief/data/processed/schema.json'
    schema=json.loads(schema_path.read_text());ev=json.loads((raw/'release_evidences.json').read_text());eids=sorted(ev,key=lambda e:int(e.split('_')[1]))
    discovery=WORK/'ClinicalBelief/data/processed/discovery.npz'
    z=np.load(discovery,allow_pickle=True);ids=list(map(str,z['case_ids']));row_map={int(cid.rsplit('_',1)[1]):j for j,cid in enumerate(ids)}
    mismatches=[]
    for j,cid in enumerate(ids):
        ix=int(z['initial_evidence_idx'][j]);correct=eids[ix] if ix>=0 else None
        legacy=next((e for e,v in schema['encodings'].items() if v['start']<=ix<v['start']+v['count']),None)
        if correct!=legacy:mismatches.append({'case_id':cid,'ordinal':ix,'correct_evidence_id':correct,'legacy_decoded_evidence_id':legacy})
    pools={d:[] for d in DISEASES};counts={d:{'all':0,'age_18_to_90':0,'valid_record':0,'at_least_8_new_groups':0} for d in DISEASES};bad=[]
    with (raw/'train.csv').open(newline='') as f:
        reader=csv.DictReader(f)
        for i,r in enumerate(reader):
            if i>max(row_map):break
            if i not in row_map:continue
            j=row_map[i];d=r['PATHOLOGY']
            assert schema['diseases'][int(z['pathology_idx'][j])]==d
            if d not in pools:continue
            counts[d]['all']+=1
            if not 18<=int(float(r['AGE']))<=90:continue
            counts[d]['age_18_to_90']+=1
            try:
                tokens=ast.literal_eval(r['EVIDENCES']);initial=r['INITIAL_EVIDENCE'].split('_@_')[0]
                assert initial==eids[int(z['initial_evidence_idx'][j])]
                explicit={}
                for token in tokens:
                    e,sep,value=token.partition('_@_');assert e in ev
                    explicit.setdefault(e,[]).append(value if sep else '1')
                assert initial in explicit
                groups={}
                for e,values in explicit.items():
                    meta=ev[e];rendered=[]
                    for value in values:
                        if meta['data_type']=='B':assert value=='1';rendered.append('Yes')
                        elif value in meta.get('value_meaning',{}):
                            meaning=meta['value_meaning'][value]['en'];rendered.append({'Y':'Yes','N':'No'}.get(meaning,meaning))
                        else:
                            assert meta['data_type']=='C' and value in [str(v) for v in meta['possible-values']]
                            rendered.append('dataset scale value '+value)
                    groups.setdefault(meta['code_question'],[]).append({'evidence_id':e,'data_type':meta['data_type'],'question_en':meta['question_en'],'values':values,'answer_en':'; '.join(rendered),'source':'explicit_raw_token','is_antecedent':meta.get('is_antecedent',False)})
                for g in groups.values():g.sort(key=lambda x:int(x['evidence_id'].split('_')[1]))
                initial_group=ev[initial]['code_question'];new=[g for g in groups if g!=initial_group]
                counts[d]['valid_record']+=1
                if len(new)<8:continue
                counts[d]['at_least_8_new_groups']+=1
                cid=ids[j];order=sorted(new,key=lambda q:priority(cid+':order:'+q))
                pools[d].append({'case_id':cid,'source_split':'train','secondary_split':'discovery','source_row_zero_based':i,'gold_disease':d,'age':int(float(r['AGE'])),'sex':r['SEX'],
                    'initial_evidence_id':initial,'initial_question_group':initial_group,'explicit_evidence_groups':groups,'new_group_order':order,'available_new_groups':len(new),
                    'selected_new_groups':len(order),'evidence_selection':'Explicit raw tokens only; all new question families in hash order; age 18-90 and at least 8 new groups.'})
            except (ValueError,AssertionError,KeyError,SyntaxError) as err:bad.append({'case_id':ids[j],'reason':type(err).__name__})
    selected=[]
    for d in DISEASES:
        assert len(pools[d])>=2,(d,len(pools[d]))
        selected += sorted(pools[d],key=lambda x:priority(x['case_id']+':select'))[:2]
    (ROOT/'data').mkdir(exist_ok=True)
    private=ROOT/'data/pilot_cases.private.jsonl';assert not private.exists();private.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in selected))
    public=[]
    for index,r in enumerate(selected):
        seen=[r['initial_question_group']]
        for t in range(len(r['new_group_order'])+1):
            if t:seen.append(r['new_group_order'][t-1])
            public.append({'case_id':r['case_id'],'round':t,'age':r['age'],'sex':r['sex'],'new_question_group':seen[-1] if t else None,
                'revealed_groups':[{'question_group_id':g,'items':r['explicit_evidence_groups'][g]} for g in seen],
                'candidate_diseases':DISEASES,'mapping_offset':index%6,'reasoning_history':[]})
    pub=ROOT/'data/pilot_prefixes.public.jsonl';assert not pub.exists();pub.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in public))
    assert all('gold_disease' not in r for r in public)
    inventory={'date':'2026-11-18','status':'Design preparation only; no model loading/generation or probability measurement','seed':SEED,
        'selection_rule':'Within each disease, first two eligible discovery cases by SHA256(seed:case_id:select); age 18-90 and >=8 explicit new question families, initial evidence verified. No model outcome used.',
        'design_revision':'v1 before any LLM output: adult pilot age18-90; expose ALL explicit groups instead of truncating at10, so the final prefix is the full observed record. v0 preparation archived.',
        'sampling_limit':'Longer explicit-evidence records selected for instrumentation; not a representative accuracy sample. Six-way closed-candidate diagnosis.',
        'pool_counts':counts,'invalid_records':bad,'selected_case_count':len(selected),'public_prefix_count':len(public),
        'selected_cases':[{k:r[k] for k in ['case_id','gold_disease','age','sex','initial_evidence_id','initial_question_group','available_new_groups','selected_new_groups']} for r in selected],
        'legacy_initial_index_audit':{'checked_discovery_cases':len(ids),'mismatched':len(mismatches),'examples':mismatches[:6],
            'cause':'Stored initial_evidence_idx is ordinal in sorted evidence IDs; legacy readers interpret it as expanded atom index. New inputs use raw INITIAL_EVIDENCE directly. Legacy results not recomputed or overwritten.'},
        'sources':[{'file':str(p.relative_to(WORK)),'sha256':sha(p)} for p in [discovery,schema_path,raw/'release_evidences.json',raw/'release_conditions.json',raw/'train.csv']],
        'outputs':[{'file':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in [private,pub]],'source_sha256':sha(Path(__file__)),'api_cost_usd':0}
    dump(ROOT/'protocol/design_inventory.json',inventory)
    print(json.dumps({k:v for k,v in inventory.items() if k in ['selected_case_count','public_prefix_count','pool_counts','legacy_initial_index_audit']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
