"""Post-expansion diagnostic checks; no hyperparameter tuning or clinical claims."""
import collections
import csv
import json
import time

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import normalize

from ddx_classifier_expansion import DATA, DISEASES, META, OUT, RAW, ROOT, SEED, dump, features, metrics, text


def reproduce_original():
    from ddx_classifier_expansion import old_cases
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import RidgeClassifier
    old = old_cases()
    y = np.array([c['gold'] for c in old])
    docs = [c['original_questions'] for c in old]
    saved = np.load(ROOT/'results/11_disease_information/heldout_predictions.npz')
    assert list(saved['case_ids']) == [c['case_id'] for c in old]
    fold = saved['fold']
    pred = np.empty(len(old), object)
    for fi in range(5):
        tr, te = np.flatnonzero(fold != fi), np.flatnonzero(fold == fi)
        v = TfidfVectorizer(ngram_range=(1,2), token_pattern=r'(?u)\b\w+\b')
        X = v.fit_transform([docs[i] for i in tr])
        m = RidgeClassifier(alpha=1, solver='lsqr').fit(X,y[tr])
        pred[te] = m.predict(v.transform([docs[i] for i in te]))
    new = [json.loads(s) for s in (ROOT/'data/belief_v2/cases.private.jsonl').read_text().splitlines()]
    newdocs = [' '.join(v['question_en'] for g in [c['initial_question_group']]+c['orders']['base'] for v in c['explicit_evidence_groups'][g]) for c in new]
    v = TfidfVectorizer(ngram_range=(1,2), token_pattern=r'(?u)\b\w+\b')
    m = RidgeClassifier(alpha=1, solver='lsqr').fit(v.fit_transform(docs),y)
    newpred = m.predict(v.transform(newdocs))
    r = dict(old_fivefold_questions_correct=int(np.sum(pred==y)),
             old_train_new120_questions_correct=int(np.sum(newpred==np.array([c['gold_disease'] for c in new]))), n=120)
    assert r['old_fivefold_questions_correct'] == 120
    assert r['old_train_new120_questions_correct'] == 119
    dump(OUT/'original_reproduction.json',r)


def main():
    assert (OUT/'summary.json').exists(), 'Run expansion first'
    reproduce_original()
    train = [json.loads(s) for s in (DATA/'train_cases.jsonl').read_text().splitlines()]
    test = [json.loads(s) for s in (DATA/'test_cases.jsonl').read_text().splitlines()]
    y = np.array([c['gold'] for c in test])
    bundle = joblib.load(OUT/'all49_n500_evidence_presence.joblib')
    v, m = bundle['vectorizer'], bundle['classifier']
    X = v.transform([features(c, 'evidence_presence') for c in train])
    ytrain = np.array([c['gold'] for c in train])
    # A separate literal-similarity baseline: empirical disease centroids, cosine distance.
    centers = normalize(np.stack([np.asarray(X[ytrain == d].mean(axis=0)).ravel() for d in DISEASES]))
    Z = v.transform([features(c, 'evidence_presence') for c in test])
    pred = np.array(DISEASES)[np.asarray(normalize(Z) @ centers.T).argmax(axis=1)]
    result = {'cosine_nearest_disease_centroid': metrics(y, pred)}
    result['cosine_note'] = 'Prototypes are estimated from the same labeled training cases; no gradient descent, but it is still supervised fitting.'
    # Additional conventional classifier, specified before execution. Fixed C=1;
    # report both views; do not select hyperparameters using test scores.
    result['logistic_regression'] = {}
    for mode in ['evidence_presence', 'evidence_values']:
        b = joblib.load(OUT/f'all49_n500_{mode}.joblib')
        vec = b['vectorizer']
        trainx = vec.transform([features(c, mode) for c in train])
        testx = vec.transform([features(c, mode) for c in test])
        start = time.perf_counter()
        logreg = LogisticRegression(C=1., solver='lbfgs', max_iter=1000)
        logreg.fit(trainx, ytrain)
        fit_seconds = time.perf_counter()-start
        lp = logreg.predict(testx)
        from ddx_classifier_expansion import fact, inventory
        ft, inv = {fact(c) for c in train}, {inventory(c) for c in train}
        novel = np.array([fact(c) not in ft for c in test])
        unseen = np.array([inventory(c) not in inv for c in test])
        r = dict(all=metrics(y,lp), no_training_fact_overlap=metrics(y[novel],lp[novel]),
                 unseen_question_inventory=metrics(y[unseen],lp[unseen]),
                 fit_seconds=fit_seconds, iterations=logreg.n_iter_.tolist())
        result['logistic_regression'][mode] = r
        np.savez_compressed(OUT/f'logistic_{mode}.npz', case_ids=np.array([c['case_id'] for c in test]), gold=y, prediction=lp)
        joblib.dump(dict(vectorizer=vec, classifier=logreg, mode=mode),OUT/f'logistic_{mode}.joblib')
        print(f'Logistic {mode}: {r["all"]["accuracy"]:.4%}; fit {fit_seconds:.1f}s',flush=True)
    # Probe presentation sensitivity without changing any question or symptom membership.
    bq = joblib.load(OUT/'all49_n500_questions_only.joblib')
    rng = np.random.default_rng(SEED)
    pred = []
    for start in range(0, len(test), 4096):
        docs = [' '.join(META[k]['question_en'] for k in rng.permutation(c['keys'])) for c in test[start:start+4096]]
        pred.extend(bq['classifier'].predict(bq['vectorizer'].transform(docs)))
    canonical = np.load(OUT/'all49_n500_questions_only.npz')['prediction']
    result['shuffled_question_order'] = metrics(y, np.array(pred))
    result['shuffled_order_prediction_changes'] = int(np.sum(np.array(pred) != canonical))
    # Identity-only features: permuting all columns changes no score when weights are permuted too.
    perm = np.random.default_rng(SEED).permutation(Z.shape[1])
    original_scores = m.decision_function(Z[:1000])
    renamed_scores = Z[:1000, perm] @ m.coef_[:, perm].T + m.intercept_
    result['opaque_feature_renaming_max_score_error'] = float(np.max(np.abs(original_scores - renamed_scores)))
    assert np.allclose(original_scores, renamed_scores)
    # Independently compare our raw CSV parser with the prior project evidence parser.
    from phase6_prepare import groups_from_raw
    checkrows = set(np.random.default_rng(SEED).choice(len(test), 100, replace=False).tolist())
    with (RAW/'test.csv').open() as f:
        checked = 0
        for i, row in enumerate(csv.DictReader(f)):
            if i not in checkrows:
                continue
            groups, _ = groups_from_raw(row, META)
            tokens = {item['evidence_id'] + ('' if item['data_type'] == 'B' else '_@_'+str(value))
                      for group in groups.values() for item in group for value in item['values']}
            assert tokens == set(test[i]['tokens'])
            checked += 1
    result['independent_parser_checks'] = checked
    # Locate two true official cases with identical questions, where retaining values resolves both.
    vals = np.load(OUT/'all49_n500_evidence_values.npz')['prediction']
    groups = collections.defaultdict(list)
    for i, c in enumerate(test):
        groups[tuple(c['keys'])].append(i)
    pairs = []
    for key, indices in groups.items():
        bylabel = {}
        for i in indices:
            if vals[i] == y[i]:
                bylabel.setdefault(y[i], i)
        if len(bylabel) > 1:
            ix = list(bylabel.values())[:2]
            assert text(test[ix[0]]) == text(test[ix[1]])
            pairs.append(dict(question_count=len(key), questions=[META[k]['question_en'] for k in key],
                              cases=[dict(**test[i], question_prediction=str(canonical[i]), value_prediction=str(vals[i])) for i in ix]))
    pairs.sort(key=lambda p: p['question_count'])
    dump(OUT/'matched_question_different_disease_cases.json', pairs[:10])
    # Whole-batch prediction, already encoded features, measured locally; excludes text preprocessing.
    elapsed = []
    for _ in range(3):
        start = time.perf_counter()
        m.predict(Z)
        elapsed.append(time.perf_counter()-start)
    result['presence_model_cpu_batch_prediction_seconds'] = elapsed
    result['presence_model_prediction_microseconds_per_case_median'] = float(np.median(elapsed)*1e6/len(test))
    result['model_file_bytes'] = {p.name: p.stat().st_size for p in OUT.glob('*.joblib')}
    dump(OUT/'followup_checks.json', result)
    print(json.dumps({k:v if not isinstance(v,dict) else {a:b for a,b in v.items() if a!='recall_per_disease'} for k,v in result.items()}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
