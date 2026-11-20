"""Frozen local CPU expansion. Never use labels/differentials as input features.

Run from Seq:
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/ddx_classifier_expansion.py
"""
from __future__ import annotations

import ast
import collections
import csv
import hashlib
import heapq
import json
import platform
import re
import time
from pathlib import Path

import joblib
import numpy as np
import scipy
import sklearn
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import RidgeClassifier
from sklearn.metrics import confusion_matrix, f1_score

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT.parent / 'ClinicalBelief/data/raw'
OUT = ROOT / 'results/22_ddx_classifier_expansion'
DATA = ROOT / 'data/ddx_classifier_expansion'
SEED = 20261119
META = json.loads((RAW / 'release_evidences.json').read_text())
DISEASES = sorted(v['condition_name'] for v in json.loads((RAW / 'release_conditions.json').read_text()).values())
TOKEN = re.compile(r'E_\d+(?:_@_(?:V_\d+|\d+))?\Z')


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def parse(row, i, split):
    tokens = sorted(set(ast.literal_eval(row['EVIDENCES'])))
    assert all(TOKEN.fullmatch(t) for t in tokens)
    keys = sorted({t.split('_@_')[0] for t in tokens}, key=lambda k: int(k[2:]))
    assert set(keys) <= META.keys()
    assert row['PATHOLOGY'] in DISEASES
    return dict(case_id=f'ddx_{split}_{i:07d}', source_row_zero_based=i,
                gold=row['PATHOLOGY'], tokens=tokens, keys=keys)


def fact(c):
    return tuple(c['tokens'])


def inventory(c):
    return tuple(c['keys'])


def prepare():
    DATA.mkdir(parents=True, exist_ok=True)
    pools = collections.defaultdict(list)
    counts = collections.Counter()
    # Hash priority sampling is independent of row order and model performance.
    with (RAW / 'train.csv').open() as f:
        for i, row in enumerate(csv.DictReader(f)):
            d = row['PATHOLOGY']
            counts[d] += 1
            priority = int(hashlib.sha256(f'{SEED}:train:{i}'.encode()).hexdigest()[:16], 16)
            if len(pools[d]) < 500:
                heapq.heappush(pools[d], (-priority, i, row))
            elif priority < -pools[d][0][0]:
                heapq.heapreplace(pools[d], (-priority, i, row))
    train = []
    for d in DISEASES:
        for rank, (_, i, row) in enumerate(sorted(pools[d], reverse=True)):
            c = parse(row, i, 'train')
            c['within_class_rank'] = rank
            train.append(c)
    test = []
    with (RAW / 'test.csv').open() as f:
        for i, row in enumerate(csv.DictReader(f)):
            test.append(parse(row, i, 'test'))
    (DATA / 'train_cases.jsonl').write_text(''.join(json.dumps(c, ensure_ascii=False) + '\n' for c in train))
    # Store expanded test cases as structured input only; no generated narratives.
    (DATA / 'test_cases.jsonl').write_text(''.join(json.dumps(c, ensure_ascii=False) + '\n' for c in test))
    manifest = dict(seed=SEED, train_cases=len(train), test_cases=len(test), classes=DISEASES,
                    full_training_counts=dict(counts), sampled_training_counts=dict(collections.Counter(c['gold'] for c in train)),
                    test_counts=dict(collections.Counter(c['gold'] for c in test)),
                    source_hashes={p.name: sha(p) for p in [RAW / 'train.csv', RAW / 'test.csv', RAW / 'release_evidences.json', RAW / 'release_conditions.json']},
                    prepared_hashes={p.name: sha(p) for p in DATA.glob('*.jsonl')},
                    source_code_sha256=sha(Path(__file__)),
                    protocol_sha256=sha(ROOT / 'protocol/DDX_CLASSIFIER_EXPANSION.json'),
                    python=platform.python_version(), sklearn=sklearn.__version__, numpy=np.__version__, scipy=scipy.__version__)
    dump(DATA / 'manifest.json', manifest)
    return train, test, manifest


def text(c, mode='questions_only'):
    if 'original_questions' in c:
        assert mode == 'questions_only'
        return c['original_questions']
    return ' '.join(META[k]['question_en'] for k in c['keys'])


def features(c, mode):
    if mode == 'evidence_values':
        return dict.fromkeys(c['tokens'], 1.)
    if mode == 'initial_only':
        raise ValueError('Not implemented: do not substitute first sorted key for initial evidence')
    keys = c['keys']
    if mode == 'symptoms_only':
        keys = [k for k in keys if not META[k]['is_antecedent']]
    if mode == 'history_only':
        keys = [k for k in keys if META[k]['is_antecedent']]
    if mode == 'binary_only':
        keys = [k for k in keys if META[k]['data_type'] == 'B']
    return dict.fromkeys(keys, 1.)


def wilson(k, n):
    if not n:
        return [None, None]
    z = 1.959963984540054
    p = k / n
    center = (p + z*z / (2*n)) / (1 + z*z/n)
    radius = z * np.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1+z*z/n)
    return [float(center-radius), float(center+radius)]


def metrics(y, pred):
    n = len(y)
    if n == 0:
        return {'n': 0}
    correct = int(np.sum(y == pred))
    recalls = {d: float(np.mean(pred[y == d] == d)) for d in sorted(set(y))}
    return dict(n=n, correct=correct, accuracy=correct/n, wilson95=wilson(correct, n),
                balanced_accuracy=float(np.mean(list(recalls.values()))),
                macro_f1=float(f1_score(y, pred, labels=sorted(set(y)), average='macro', zero_division=0)),
                recall_per_disease=recalls)


def old_cases():
    old = [json.loads(s) for s in (ROOT / 'data/full49_v1/cases.private.jsonl').read_text().splitlines()]
    cases = []
    for c in old:
        items = [v for g in [c['initial_question_group']] + c['orders']['base'] for v in c['explicit_evidence_groups'][g]]
        tokens = sorted({v['evidence_id'] + ('' if v['data_type'] == 'B' else '_@_' + str(value)) for v in items for value in v['values']})
        cases.append(dict(case_id=c['case_id'], gold=c['gold_disease'], tokens=tokens,
                          keys=sorted({v['evidence_id'] for v in items}, key=lambda k: int(k[2:])),
                          original_questions=' '.join(v['question_en'] for v in items)))
    return cases


RESULTS = {}
PREDICTIONS = {}
MODELS = {}


def evaluate(name, train, test, mode, label_shuffle=False, question_map=None):
    started = time.perf_counter()
    ytrain = np.array([c['gold'] for c in train])
    y = np.array([c['gold'] for c in test])
    istext = mode == 'questions_only'
    def represent(c):
        if question_map is not None:
            return ' '.join(question_map[k] for k in c['keys'])
        return text(c) if istext else features(c, mode)
    vectorizer = (TfidfVectorizer(ngram_range=(1, 2), token_pattern=r'(?u)\b\w+\b') if istext else DictVectorizer())
    X = vectorizer.fit_transform([represent(c) for c in train])
    model = RidgeClassifier(alpha=1., solver='lsqr')
    model.fit(X, np.random.default_rng(SEED).permutation(ytrain) if label_shuffle else ytrain)
    fit_seconds = time.perf_counter() - started
    predictions, top3 = [], []
    for start in range(0, len(test), 4096):
        batch = test[start:start+4096]
        Z = vectorizer.transform([represent(c) for c in batch])
        scores = model.decision_function(Z)
        predictions.extend(model.classes_[scores.argmax(axis=1)])
        top3.extend(np.any(model.classes_[np.argpartition(scores, -3, axis=1)[:, -3:]] == y[start:start+len(batch), None], axis=1))
    pred = np.array(predictions)
    trainfacts, traininventories = {fact(c) for c in train}, {inventory(c) for c in train}
    freshfact = np.array([fact(c) not in trainfacts for c in test])
    freshinventory = np.array([inventory(c) not in traininventories for c in test])
    first_unique, seen = [], set()
    for i, c in enumerate(test):
        if fact(c) not in seen and freshfact[i]:
            first_unique.append(i)
        seen.add(fact(c))
    r = dict(training_n=len(train), classes=len(model.classes_), features=X.shape[1],
             all=metrics(y, pred), no_training_fact_overlap=metrics(y[freshfact], pred[freshfact]),
             unseen_question_inventory=metrics(y[freshinventory], pred[freshinventory]),
             unique_novel_facts=metrics(y[first_unique], pred[first_unique]),
             top3_accuracy=float(np.mean(top3)), train_fact_overlap=int((~freshfact).sum()),
             train_inventory_overlap=int((~freshinventory).sum()), fit_seconds=fit_seconds,
             total_seconds=time.perf_counter()-started)
    RESULTS[name] = r
    PREDICTIONS[name] = pred
    MODELS[name] = (vectorizer, model)
    np.savez_compressed(OUT / f'{name}.npz', case_ids=np.array([c['case_id'] for c in test]), gold=y, prediction=pred)
    if name.startswith('all49_n500'):
        joblib.dump(dict(vectorizer=vectorizer, classifier=model, mode=mode), OUT / f'{name}.joblib')
    dump(OUT / 'summary.partial.json', RESULTS)
    print(f'{name}: {r["all"]["correct"]}/{len(test)} = {r["all"]["accuracy"]:.4%}; macro recall={r["all"]["balanced_accuracy"]:.4%}; {r["total_seconds"]:.1f}s', flush=True)
    return r


def inventory_audit(test):
    grouped = collections.defaultdict(list)
    for i, c in enumerate(test):
        grouped[inventory(c)].append(i)
    conflicts = []
    ceiling_correct = 0
    for key, indices in grouped.items():
        counts = collections.Counter(test[i]['gold'] for i in indices)
        ceiling_correct += max(counts.values())
        if len(counts) > 1:
            representatives = {}
            for i in indices:
                representatives.setdefault(test[i]['gold'], test[i])
            conflicts.append(dict(keys=list(key), n=len(indices), label_counts=dict(counts), examples=list(representatives.values())[:3]))
    conflicts.sort(key=lambda c: (-c['n'], c['keys']))
    facts = collections.defaultdict(collections.Counter)
    for c in test:
        facts[fact(c)][c['gold']] += 1
    summary = dict(unique_question_inventories=len(grouped), conflicting_inventory_count=len(conflicts),
                   cases_in_conflicting_inventories=sum(c['n'] for c in conflicts),
                   empirical_inventory_oracle_correct=ceiling_correct,
                   empirical_inventory_oracle_accuracy=ceiling_correct/len(test),
                   unique_fact_sets=len(facts), conflicting_fact_sets=sum(len(c)>1 for c in facts.values()),
                   empirical_fact_oracle_accuracy=sum(max(c.values()) for c in facts.values())/len(test),
                   note='Finite test-set upper bound for a deterministic function of this inventory; oracle uses test labels and is NOT a fitted-model score.')
    dump(OUT / 'inventory_audit.json', summary)
    dump(OUT / 'conflicting_inventory_examples.json', conflicts[:20])
    return summary


def stress_missingness(train, test):
    vectorizer, model = MODELS['all49_n500_evidence_presence']
    y = np.array([c['gold'] for c in test])
    results = {}
    for drop in [.25, .5, .75]:
        rng = np.random.default_rng(SEED)
        pred = []
        for start in range(0, len(test), 4096):
            inputs = [{k: 1. for k in c['keys'] if rng.random() >= drop} for c in test[start:start+4096]]
            pred.extend(model.predict(vectorizer.transform(inputs)))
        results[str(drop)] = metrics(y, np.array(pred))
    dump(OUT / 'missingness_stress.json', results)
    return results


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    print('Preparing fixed official-split expansion...', flush=True)
    train, test, manifest = prepare()
    assert not {c['case_id'] for c in train} & {c['case_id'] for c in test}
    print(f'Prepared {len(train)} training and {len(test)} test cases, 49 diseases.', flush=True)
    audit = inventory_audit(test)
    print('Inventory audit:', json.dumps(audit), flush=True)
    old = old_cases()
    oldlabels = {c['gold'] for c in old}
    oldtest = [c for c in test if c['gold'] in oldlabels]
    for mode in ['questions_only', 'evidence_presence']:
        evaluate('old120_' + mode, old, oldtest, mode)
    for size in [5, 20, 100, 500]:
        subset = [c for c in train if c['within_class_rank'] < size]
        for mode in ['evidence_presence', 'evidence_values', 'questions_only']:
            evaluate(f'all49_n{size}_{mode}', subset, test, mode)
    for mode in ['symptoms_only', 'history_only', 'binary_only']:
        evaluate('control_' + mode, train, test, mode)
    evaluate('control_shuffled_labels', train, test, 'evidence_presence', label_shuffle=True)
    # Literal-name ablation only: does not claim to remove all synonyms or medical semantics.
    terms = set(DISEASES)
    for disease in DISEASES:
        terms.update(s.strip() for s in disease.split('/') if len(s.strip()) >= 3)
        terms.add(re.sub(r'\s*\([^)]*\)', '', disease).strip())
    pattern = re.compile(r'(?<!\w)(?:' + '|'.join(re.escape(s) for s in sorted(terms, key=len, reverse=True)) + r')(?!\w)', re.I)
    masked = {k: pattern.sub('condition', v['question_en']) for k, v in META.items()}
    dump(OUT / 'literal_name_ablation.json', {k: {'before': META[k]['question_en'], 'after': v} for k, v in masked.items() if v != META[k]['question_en']})
    evaluate('control_masked_disease_names', train, test, 'questions_only', question_map=masked)
    stress = stress_missingness(train, test)
    y = np.array([c['gold'] for c in test])
    # A constant panel has exactly identical rows, so an intercept-only empirical classifier is equivalent.
    common = collections.Counter(c['gold'] for c in train).most_common(1)[0][0]
    fixed = dict(predicted_class=common, result=metrics(y, np.full(len(y), common)),
                 note='Constructed zero-information control, with the training-majority class (ties broken by training order); no evidence-derived presence markers.')
    dump(OUT / 'fixed_panel_control.json', fixed)
    main_names = [f'all49_n500_{m}' for m in ['questions_only', 'evidence_presence', 'evidence_values']]
    with (OUT / 'predictions.csv').open('w') as f:
        writer = csv.writer(f)
        writer.writerow(['case_id', 'gold', *main_names])
        writer.writerows([c['case_id'], c['gold'], *[PREDICTIONS[n][i] for n in main_names]] for i, c in enumerate(test))
    confusion = {}
    for name in main_names:
        cm = confusion_matrix(y, PREDICTIONS[name], labels=DISEASES)
        confusion[name] = sorted([dict(gold=DISEASES[i], predicted=DISEASES[j], n=int(cm[i,j])) for i in range(49) for j in range(49) if i != j and cm[i,j]], key=lambda x: -x['n'])
    dump(OUT / 'confusions.json', confusion)
    errs = [dict(**c, predictions={n: str(PREDICTIONS[n][i]) for n in main_names}) for i,c in enumerate(test) if any(PREDICTIONS[n][i] != c['gold'] for n in main_names)]
    (OUT / 'error_cases.jsonl').write_text(''.join(json.dumps(c, ensure_ascii=False)+'\n' for c in errs))
    # Paired comparison: exact same test patients and training sample.
    qp = PREDICTIONS[main_names[0]] == y
    vp = PREDICTIONS[main_names[2]] == y
    paired = dict(values_right_questions_wrong=int(np.sum(vp & ~qp)), questions_right_values_wrong=int(np.sum(qp & ~vp)),
                  both_right=int(np.sum(qp & vp)), both_wrong=int(np.sum(~qp & ~vp)))
    old_test_ids = {c['case_id'] for c in map(json.loads, (ROOT/'data/belief_v2/cases.private.jsonl').read_text().splitlines())}
    fresh = np.array([c['case_id'] not in old_test_ids for c in test])
    summary = dict(manifest=manifest, inventory_audit=audit, experiments=RESULTS, missingness=stress,
                   fixed_panel=fixed, paired_questions_vs_values=paired,
                   previously_studied_test_cases=int((~fresh).sum()),
                   previously_unstudied_test_cases={n: metrics(y[fresh], PREDICTIONS[n][fresh]) for n in main_names},
                   total_seconds=time.perf_counter()-started, paid_api_calls=0)
    dump(OUT / 'summary.json', summary)
    print('Completed:', OUT / 'summary.json', 'seconds=', summary['total_seconds'], flush=True)


if __name__ == '__main__':
    main()
