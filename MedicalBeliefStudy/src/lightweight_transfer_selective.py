"""Exploratory follow-up: transfer and held-out-calibration abstention."""
import collections
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.naive_bayes import BernoulliNB
from sklearn.pipeline import make_pipeline

from lightweight_multidataset import DATA, OUT, dump, facts, features, signature, metrics


def wilson(k,n):
    if not n:return None
    z=1.95996398454;p=k/n;d=1+z*z/n
    return [(p+z*z/(2*n)-z*np.sqrt(p*(1-p)/n+z*z/(4*n*n)))/d,
            (p+z*z/(2*n)+z*np.sqrt(p*(1-p)/n+z*z/(4*n*n)))/d]


def main():
    cohorts={d:{s:json.loads((DATA/f'dxformer/data/{d}/{s}_set.json').read_text()) for s in ['train','test']} for d in ['dxy','mz4','mz10']}
    transfers=[]
    for source,target in [('mz4','mz10'),('mz10','mz4'),('dxy','mz4'),('mz4','dxy')]:
        tr=cohorts[source]['train'];common=set(c['label'] for c in tr)&set(c['label'] for c in cohorts[target]['test'])
        tr=[c for c in tr if c['label'] in common];te=[c for c in cohorts[target]['test'] if c['label'] in common]
        m=make_pipeline(DictVectorizer(),LogisticRegression(C=1,max_iter=2000))
        m.fit([features(c,'all_values',[]) for c in tr],[c['label'] for c in tr])
        p=m.predict([features(c,'all_values',[]) for c in te]);y=np.array([c['label'] for c in te])
        seen={signature(c) for c in tr};fresh=np.array([signature(c) not in seen for c in te])
        vocab={k for c in tr for k in facts(c)};keys=[k for c in te for k in facts(c)]
        transfers.append(dict(source=source,target=target,common_labels=sorted(common),train_n=len(tr),
            test=metrics(y,p),fresh=metrics(y[fresh],p[fresh]),exact_overlap=int((~fresh).sum()),
            unknown_field_occurrence_fraction=sum(k not in vocab for k in keys)/len(keys)))
    selective={}
    for ds,cohort in cohorts.items():
        tr=cohort['train'];te=cohort['test'];y=np.array([c['label'] for c in tr]);yt=np.array([c['label'] for c in te])
        groups=[signature(c) for c in tr]
        fit,cal=next(StratifiedGroupKFold(5,shuffle=True,random_state=9041).split(tr,y,groups))
        xx=[features(c,'all_values',[]) for c in tr];xt=[features(c,'all_values',[]) for c in te]
        candidates=[]
        for name,est in [('fixed_logistic_C1',LogisticRegression(C=1,max_iter=2000)),('fixed_nb_a1',BernoulliNB(alpha=1))]:
            m=make_pipeline(DictVectorizer(),est);m.fit([xx[i] for i in fit],y[fit])
            probs=m.predict_proba([xx[i] for i in cal]);confidence=probs.max(axis=1);correct=m.classes_[probs.argmax(axis=1)]==y[cal]
            eligible=[]
            for threshold in np.unique(confidence):
                mask=confidence>=threshold;n=int(mask.sum());k=int(correct[mask].sum())
                if n>=20 and k/n>=.95:eligible.append((n,float(threshold),k))
            n,threshold,k=max(eligible,default=(0,1.01,0))
            candidates.append((n,name,threshold,k,m))
        n,name,threshold,k,m=max(candidates,key=lambda x:x[0])
        probs=m.predict_proba(xt);p=m.classes_[probs.argmax(axis=1)];accept=probs.max(axis=1)>=threshold
        fresh=np.array([signature(c) not in set(groups) for c in te])
        a=int(accept.sum());cor=int(np.sum(p[accept]==yt[accept]));af=int((accept&fresh).sum());cf=int(np.sum(p[accept&fresh]==yt[accept&fresh]))
        selective[ds]=dict(model=name,fit_n=len(fit),calibration_n=len(cal),threshold=threshold,
            calibration_accepted=n,calibration_correct=k,test_n=len(te),test_accepted=a,test_correct=cor,
            test_coverage=a/len(te),test_selective_accuracy=cor/a if a else None,test_selective_wilson95=wilson(cor,a),
            fresh_test_n=int(fresh.sum()),fresh_accepted=af,fresh_correct=cf,fresh_selective_accuracy=cf/af if af else None,
            note='Threshold/model chosen on calibration only for >=95% empirical accuracy with >=20 cases. This is not a population guarantee. All original training facts excluded in fresh subset.')
        joblib.dump(dict(pipeline=m,threshold=threshold),OUT/f'{ds}_selective.joblib',compress=3)
    dump(OUT/'transfer_selective.json',dict(transfer=transfers,selective=selective))
    print(json.dumps(dict(transfer=transfers,selective=selective),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
