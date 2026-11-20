"""Prepare an untouched validation cohort; no model-dependent selection."""
from pathlib import Path
import ast, collections, csv, hashlib, json

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'data/full49_v1'
SEED = 'medical-belief-full49-20261118-v1'
FAMILIES = {
    'respiratory': ['Pneumonia', 'Bronchitis', 'Bronchospasm / acute asthma exacerbation',
                    'Pulmonary embolism', 'Spontaneous pneumothorax', 'Acute pulmonary edema'],
    'cardiovascular': ['Stable angina', 'Possible NSTEMI / STEMI', 'Pericarditis', 'Atrial fibrillation'],
    'ent': ['URTI', 'Viral pharyngitis', 'Acute otitis media'],
    'neurologic': ['Cluster headache', 'Myasthenia gravis', 'Guillain-Barré syndrome', 'Acute dystonic reactions'],
    'systemic': ['Anemia', 'SLE', 'HIV (initial infection)'],
    'digestive': ['GERD', 'Boerhaave', 'Inguinal hernia', 'Pancreatic neoplasm'],
}

def rank(value):
    return hashlib.sha256((SEED + ':' + value).encode()).hexdigest()

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(8*1024*1024), b''): h.update(chunk)
    return h.hexdigest()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def groups_from_raw(row, metadata):
    explicit = {}
    for token in ast.literal_eval(row['EVIDENCES']):
        key, sep, value = token.partition('_@_')
        explicit.setdefault(key, []).append(value if sep else '1')
    groups = {}
    for key, values in explicit.items():
        meta = metadata[key]; answers = []
        for value in values:
            if meta['data_type'] == 'B':
                assert value == '1'; answer = 'Yes'
            elif value in meta.get('value_meaning', {}):
                answer = meta['value_meaning'][value]['en']
                answer = {'Y':'Yes', 'N':'No'}.get(answer, answer)
            else:
                assert str(value) in list(map(str, meta['possible-values']))
                answer = f"Recorded scale value {value} on the dataset's 0-10 scale; endpoint meanings are unspecified"
            answers.append(answer)
        groups.setdefault(meta['code_question'], []).append({
            'evidence_id': key, 'question_en': meta['question_en'], 'answer_en': '; '.join(answers),
            'values': values, 'data_type': meta['data_type'], 'is_antecedent': meta['is_antecedent']})
    for values in groups.values(): values.sort(key=lambda v: int(v['evidence_id'][2:]))
    initial = metadata[row['INITIAL_EVIDENCE'].split('_@_')[0]]['code_question']
    assert initial in groups
    return groups, initial

def signature(age, sex, groups):
    facts = sorted((x['evidence_id'], tuple(sorted(x['values']))) for g in groups.values() for x in g)
    return hashlib.sha256(json.dumps([age, sex, facts]).encode()).hexdigest()

def main():
    raw = ROOT.parent / 'ClinicalBelief/data/raw'
    ev = json.loads((raw/'release_evidences.json').read_text())
    cond = json.loads((raw/'release_conditions.json').read_text())
    diseases = sorted(v['condition_name'] for v in cond.values())
    assert len(diseases) == 49
    target = {d:f for f, ds in FAMILIES.items() for d in ds}; assert len(target) == 24
    old = [json.loads(s) for s in (ROOT/'data/cases.private.jsonl').read_text().splitlines()]
    excluded = {signature(c['age'], c['sex'], c['explicit_evidence_groups']) for c in old}
    pools = collections.defaultdict(list); failures = []; duplicates = 0
    with (raw/'validate.csv').open() as f:
        for i, row in enumerate(csv.DictReader(f)):
            if row['PATHOLOGY'] not in target or not 18 <= int(float(row['AGE'])) <= 90: continue
            try:
                groups, initial = groups_from_raw(row, ev)
                if len(groups) < 5: continue
                sig = signature(int(float(row['AGE'])), row['SEX'], groups)
                if sig in excluded: duplicates += 1; continue
                diff = dict(ast.literal_eval(row['DIFFERENTIAL_DIAGNOSIS']))
                assert set(diff).issubset(diseases) and abs(sum(diff.values()) - 1) < 1e-6
                cid = f'ddx_validate_{i:07d}'
                pools[row['PATHOLOGY']].append({
                    'case_id': cid, 'source_row_zero_based': i, 'source_split': 'validate',
                    'family': target[row['PATHOLOGY']], 'gold_disease': row['PATHOLOGY'],
                    'age': int(float(row['AGE'])), 'sex': row['SEX'], 'initial_question_group': initial,
                    'explicit_evidence_groups': groups, 'reference_differential': diff, 'signature': sig})
            except (ValueError, KeyError, AssertionError, SyntaxError) as error:
                failures.append({'source_row': i, 'error': str(error)})
    chosen = []; used = set(excluded)
    for disease in target:
        selected = []
        for case in sorted(pools[disease], key=lambda c:rank(c['case_id']+':select')):
            if case['signature'] in used: continue
            selected.append(case); used.add(case['signature'])
            if len(selected) == 5: break
        assert len(selected) == 5, (disease, len(selected))
        chosen.extend(selected)
    chosen.sort(key=lambda c: rank(c['case_id']+':run'))
    jobs = []
    for ci, case in enumerate(chosen):
        seq = sorted((g for g in case['explicit_evidence_groups'] if g != case['initial_question_group']),
                     key=lambda g:rank(case['case_id']+':base:'+g))
        case['orders'] = {'base':seq, 'reverse':list(reversed(seq)),
                          'shuffle':sorted(seq,key=lambda g:rank(case['case_id']+':shuffle:'+g))}
        case['mapping_offset'] = int(rank(case['case_id']+':map')[:8],16)%49
        case['fixed_middle_round'] = len(seq)//2
        case['deep_capture'] = ci < 24
        for order, sequence in case['orders'].items():
            rounds = range(len(seq)+1) if order != 'shuffle' else [len(seq)]
            for t in rounds:
                rotations = [0,16,32] if t in {0, len(seq)//2, len(seq)} else [0,16]
                if order == 'reverse' and t == 0: continue  # identical prompt to base t0
                for rotation in rotations:
                    jobs.append({'job_id':f"{case['case_id']}_{order}_t{t:02d}_m{rotation}",
                        'case_id':case['case_id'], 'family':case['family'], 'age':case['age'], 'sex':case['sex'],
                        'order':order, 'round':t, 'last_round':len(seq), 'rotation':rotation,
                        'mapping_offset':case['mapping_offset'], 'candidate_diseases':diseases,
                        'revealed_groups':[{'question_group_id':g,'items':case['explicit_evidence_groups'][g]}
                                           for g in [case['initial_question_group']]+sequence[:t]],
                        'deep_capture':case['deep_capture'] and order=='base' and rotation==0})
    DEST.mkdir(parents=True,exist_ok=True)
    for name, rows in [('cases.private.jsonl',chosen),('jobs.public.jsonl',jobs)]:
        path=DEST/name; content=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows)
        if path.exists(): assert path.read_text()==content, 'Frozen inputs changed'
        else:path.write_text(content)
    manifest={'seed':SEED,'cases':len(chosen),'diseases':diseases,'sampled_diseases':24,
              'families':FAMILIES,'family_cases':dict(collections.Counter(c['family'] for c in chosen)),
              'jobs':len(jobs),'base_prefixes':sum(len(c['orders']['base'])+1 for c in chosen),
              'deep_capture_cases':[c['case_id'] for c in chosen if c['deep_capture']],
              'eligible_per_disease':{d:len(pools[d]) for d in target},'excluded_prior_duplicates':duplicates,
              'invalid_records':failures,'max_groups':max(len(c['orders']['base'])+1 for c in chosen),
              'source_hashes':{p.name:sha(p) for p in [raw/'validate.csv',raw/'release_conditions.json',raw/'release_evidences.json']},
              'input_hashes':{p.name:sha(p) for p in DEST.glob('*.jsonl')},'preparation_sha256':sha(__file__)}
    write(ROOT/'protocol/FULL49_COHORT.json',manifest)
    print(json.dumps({k:manifest[k] for k in ['cases','sampled_diseases','family_cases','jobs','base_prefixes','max_groups','invalid_records']},indent=2))

if __name__ == '__main__': main()
