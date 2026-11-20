"""Frozen-CV lightweight baselines on published diagnosis-dialogue partitions."""
import collections
import hashlib
import json
import platform
import re
import time
from pathlib import Path

import joblib
import numpy as np
from sklearn.base import clone
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.naive_bayes import BernoulliNB
from sklearn.pipeline import make_pipeline
from sklearn.svm import LinearSVC, SVC

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/lightweight_multidataset'
OUT=ROOT/'results/24_lightweight_multidataset'


def dump(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')


def facts(c):
    # Match the author's utils.filter_duplicate: explicit state wins on overlap.
    return {**c['imp_sxs'],**c['exp_sxs']}


def signature(c):
    return json.dumps(facts(c),sort_keys=True,ensure_ascii=False)


def features(c,view,removed):
    fs=c['exp_sxs'] if view=='explicit_values' else facts(c)
    return {k if view=='all_identities' else k+'='+str(v):1.
            for k,v in fs.items() if view!='no_label_fields' or k not in removed}


def metrics(y,p):
    if not len(y):return {'n':0}
    return dict(n=len(y),correct=int(np.sum(y==p)),accuracy=float(accuracy_score(y,p)),
        balanced_accuracy=float(balanced_accuracy_score(y,p)),macro_f1=float(f1_score(y,p,average='macro',zero_division=0)))


def models():
    return [(f'logistic_C{c}',LogisticRegression(C=c,max_iter=2000)) for c in [.1,1,10]]+[
        (f'linear_svm_C{c}',LinearSVC(C=c,max_iter=20000)) for c in [.1,1,10]]+[
        (f'rbf_svm_C{c}',SVC(C=c,gamma='scale')) for c in [1,10,100]]+[
        (f'bernoulli_nb_a{a}',BernoulliNB(alpha=a)) for a in [.1,1]]+[
        ('extra_trees',ExtraTreesClassifier(n_estimators=200,min_samples_leaf=2,random_state=20261120,n_jobs=1))]


def run(ds):
    train=json.loads((DATA/f'dxformer/data/{ds}/train_set.json').read_text())
    test=json.loads((DATA/f'dxformer/data/{ds}/test_set.json').read_text())
    y=np.array([c['label'] for c in train]);yt=np.array([c['label'] for c in test])
    groups=np.array([signature(c) for c in train]);seen=set(groups)
    fresh=np.array([signature(c) not in seen for c in test])
    names=set(y)|{re.sub(r'^(小儿|儿童)','',d) for d in y}
    removed=sorted({k for c in train for k in facts(c) if k in names})
    folds=list(StratifiedGroupKFold(5,shuffle=True,random_state=20261120).split(train,y,groups))
    counts=collections.defaultdict(set)
    for c in train:counts[signature(c)].add(c['label'])
    result=dict(train_n=len(train),test_n=len(test),classes=sorted(set(y)),
        majority_accuracy=float(np.mean(yt==collections.Counter(y).most_common(1)[0][0])),
        train_unique_facts=len(seen),train_conflicting_fact_vectors=sum(len(x)>1 for x in counts.values()),
        test_exact_fact_overlap=int((~fresh).sum()),label_named_fields_removed=removed,
        state_counts=dict(collections.Counter(str(v) for c in train for v in facts(c).values())),views={})
    for view in ['all_identities','all_values','explicit_values','no_label_fields']:
        xs=[features(c,view,removed) for c in train];xt=[features(c,view,removed) for c in test]
        scores=[];started=time.perf_counter()
        for name,est in models():
            pred=np.empty(len(y),dtype=y.dtype)
            for tr,va in folds:
                m=make_pipeline(DictVectorizer(),clone(est));m.fit([xs[i] for i in tr],y[tr])
                pred[va]=m.predict([xs[i] for i in va])
            scores.append(dict(model=name,cv_accuracy=float(np.mean(pred==y))))
        best=max(range(len(scores)),key=lambda i:scores[i]['cv_accuracy'])
        name,est=models()[best];m=make_pipeline(DictVectorizer(),est)
        t=time.perf_counter();m.fit(xs,y);fit=time.perf_counter()-t
        t=time.perf_counter();p=m.predict(xt);batch=time.perf_counter()-t
        modelpath=OUT/f'{ds}_{view}.joblib';joblib.dump(m,modelpath,compress=3)
        # Warm calls include dictionary vectorization, exclude disk load and JSON parsing.
        latency=[]
        for i in range(100):
            t=time.perf_counter();m.predict([xt[i%len(xt)]]);latency.append((time.perf_counter()-t)*1000)
        dedup=[];seen_pair=set()
        for i,c in enumerate(train):
            key=(signature(c),c['label'])
            if key not in seen_pair:dedup.append(i);seen_pair.add(key)
        dm=clone(m);dm.fit([xs[i] for i in dedup],y[dedup]);dp=dm.predict(xt)
        coef=getattr(m[-1],'coef_',None)
        numeric_bytes=coef.nbytes+getattr(m[-1],'intercept_',np.array([])).nbytes if coef is not None else None
        r=dict(selected=name,cv_selection=scores,all_test=metrics(yt,p),fresh_test=metrics(yt[fresh],p[fresh]),
            refit_deduplicated_train_n=len(dedup),refit_deduplicated_test=metrics(yt,dp),
            refit_deduplicated_fresh=metrics(yt[fresh],dp[fresh]),fit_seconds=fit,selection_seconds=time.perf_counter()-started,
            batch_predict_seconds=batch,warm_single_ms_median=float(np.median(latency)),
            warm_single_ms_p95=float(np.quantile(latency,.95)),compressed_model_bytes=modelpath.stat().st_size,
            linear_coefficient_bytes=numeric_bytes,feature_count=len(m[0].feature_names_))
        result['views'][view]=r
        dump(OUT/f'{ds}_{view}_predictions.json',[dict(pid=c['pid'],gold=c['label'],prediction=str(pred),
            novel_facts=bool(novel)) for c,pred,novel in zip(test,p,fresh)])
        # Identical input for a later LLM comparison; labels are kept in a separate file.
        promptrows=[]
        for c in test:
            vals=c['exp_sxs'] if view=='explicit_values' else facts(c)
            vals={k:v for k,v in vals.items() if view!='no_label_fields' or k not in removed}
            content=sorted(vals) if view=='all_identities' else {k:{'0':'否','1':'是','2':'不确定'}.get(str(v),str(v)) for k,v in sorted(vals.items())}
            promptrows.append(dict(id=f"{ds}:{c['pid']}",prompt='从候选疾病中选择一个最可能的疾病，只输出疾病名。未列出的症状表示未观察，不代表阴性。\n候选疾病：'+json.dumps(sorted(set(y)),ensure_ascii=False)+'\n已记录资料：'+json.dumps(content,ensure_ascii=False)))
        (OUT/f'{ds}_{view}_gpt_inputs.jsonl').write_text(''.join(json.dumps(c,ensure_ascii=False)+'\n' for c in promptrows))
        print(ds,view,name,'CV',scores[best]['cv_accuracy'],'test',r['all_test']['accuracy'],'fresh',r['fresh_test'].get('accuracy'),'bytes',r['compressed_model_bytes'],flush=True)
    dump(OUT/f'{ds}_results.json',result)
    return result


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    result={}
    for ds in ['dxy','mz4','mz10']:
        result[ds]=run(ds);dump(OUT/'diagnostic_summary.json',result)
    dump(OUT/'environment.json',dict(platform=platform.platform(),python=platform.python_version(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),api_calls=0))


if __name__=='__main__':main()
