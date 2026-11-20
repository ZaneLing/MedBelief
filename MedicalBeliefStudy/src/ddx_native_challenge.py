"""Native-case answer challenge: same question identities, different raw labels.

Exploratory case selection defines a balanced conditional benchmark, not natural prevalence.
No medical counterfactuals are generated and no patient values or labels are changed.
"""
import ast
import collections
import csv
import hashlib
import json
import time

import joblib
import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression

from ddx_classifier_expansion import DATA, META, RAW, ROOT, features, text, metrics, dump, sha
from ddx_generator_audit import SUPPORT, compatible, certificate, signature

OUT=ROOT/'results/23_ddx_generator_audit'
BASE=ROOT/'results/22_ddx_classifier_expansion'


def loadsplit(split):
    if split=='test':return [json.loads(s) for s in (DATA/'test_cases.jsonl').read_text().splitlines()]
    cases=[]
    with (RAW/f'{split}.csv').open() as f:
        for i,r in enumerate(csv.DictReader(f)):
            tokens=sorted(set(ast.literal_eval(r['EVIDENCES'])))
            keys=sorted({t.partition('_@_')[0] for t in tokens},key=lambda k:int(k[2:]))
            cases.append(dict(case_id=f'ddx_{split}_{i:07d}',source_row_zero_based=i,gold=r['PATHOLOGY'],keys=keys,tokens=tokens))
    return cases


def choose(cases,excluded):
    pools=collections.defaultdict(lambda:collections.defaultdict(list))
    for c in cases:
        if signature(c['tokens']) not in excluded:
            pools[tuple(c['keys'])][c['gold']].append(c)
    chosen=[];groups=[]
    for keys,bylabel in sorted(pools.items()):
        if len(bylabel)<2:continue
        gid=hashlib.sha256('\n'.join(keys).encode()).hexdigest()[:16]
        group=[]
        for d,cs in sorted(bylabel.items()):
            c=dict(min(cs,key=lambda c:hashlib.sha256(('native-challenge-20261119:'+c['case_id']).encode()).hexdigest()))
            c['question_group_id']=gid
            group.append(c)
        assert len({text(c) for c in group})==1
        chosen+=group;groups.append(dict(group_id=gid,n_labels=len(bylabel),cases=[c['case_id'] for c in group]))
    return chosen,groups


def evaluate(cases):
    y=np.array([c['gold'] for c in cases]);result={};pred={}
    for name in ['all49_n500_questions_only','all49_n500_evidence_presence','all49_n500_evidence_values','logistic_evidence_presence','logistic_evidence_values']:
        b=joblib.load(BASE/f'{name}.joblib');mode=b['mode']
        x=b['vectorizer'].transform([text(c) if mode=='questions_only' else features(c,mode) for c in cases])
        p=b['classifier'].predict(x);result[name]=metrics(y,p);pred[name]=p
    return result,pred


def main():
    OUT.mkdir(exist_ok=True,parents=True)
    train=[json.loads(s) for s in (DATA/'train_cases.jsonl').read_text().splitlines()]
    excluded={signature(c['tokens']) for c in train}
    test=loadsplit('test');validate=loadsplit('validate')
    results={}
    for split,cs in [('test',test),('validate',validate)]:
        # Validation is also exact-fact disjoint from the entire exploratory test set.
        chosen,groups=choose(cs,excluded)
        r,pred=evaluate(chosen)
        upper=len(groups)/len(chosen)
        assert r['logistic_evidence_presence']['accuracy']<=upper+1e-12
        assert r['all49_n500_questions_only']['accuracy']<=upper+1e-12
        results[split]=dict(n=len(chosen),groups=len(groups),classes=len({c['gold'] for c in chosen}),
            conditional_question_only_upper_bound=upper,models=r,
            group_size_counts=dict(collections.Counter(g['n_labels'] for g in groups)))
        dump(OUT/f'native_challenge_{split}_groups.json',groups)
        (OUT/f'native_challenge_{split}.jsonl').write_text(''.join(json.dumps(c,ensure_ascii=False)+'\n' for c in chosen))
        with (OUT/f'native_challenge_{split}_predictions.csv').open('w') as f:
            w=csv.writer(f);w.writerow(['case_id','gold','question_group_id',*pred])
            w.writerows([c['case_id'],c['gold'],c['question_group_id'],*[pred[k][i] for k in pred]] for i,c in enumerate(chosen))
        print('native challenge',split,len(chosen),'groups',len(groups),'question upper',upper,
              {k:v['accuracy'] for k,v in r.items()},flush=True)
        excluded.update(signature(c['tokens']) for c in cs)
    # Controlled ablation: remove metadata-exclusive evidence, train and test alike.
    # This removes useful information; never interpret its drop as proof of invalid clinical reasoning.
    nonexclusive={k for k,m in SUPPORT.items() if m.bit_count()>1}
    def reduced(c):return {k:1. for k in c['keys'] if k in nonexclusive}
    v=DictVectorizer();X=v.fit_transform([reduced(c) for c in train]);yt=np.array([c['gold'] for c in train])
    m=LogisticRegression(C=1,solver='lbfgs',max_iter=1000).fit(X,yt)
    reductions={}
    for split,cs in [('test',test),('validate',validate)]:
        p=m.predict(v.transform([reduced(c) for c in cs]));y=np.array([c['gold'] for c in cs])
        counts=collections.Counter()
        cue_counts=collections.defaultdict(collections.Counter)
        for c in cs:
            ks=[k for k in c['keys'] if k not in nonexclusive]
            counts['any_singleton']+=bool(ks)
            counts['any_singleton_history']+=any(META[k]['is_antecedent'] for k in ks)
            counts['any_singleton_symptom']+=any(not META[k]['is_antecedent'] for k in ks)
            for k in ks:cue_counts[k][c['gold']]+=1
        reductions[split]=dict(model=metrics(y,p),counts=dict(counts),
            cue_counts={k:dict(v) for k,v in cue_counts.items()})
        print('without degree-one features',split,reductions[split]['model']['accuracy'],flush=True)
    # Describe the metadata itself, independently of patient labels.
    degree_one=[dict(evidence_id=k,question=META[k]['question_en'],is_antecedent=META[k]['is_antecedent'],
                    allowed_disease=next(d for d in json.loads((RAW/'release_conditions.json').read_text()).values()
                                         if k in d['symptoms'] or k in d['antecedents'])['condition_name'])
                for k,m in SUPPORT.items() if m.bit_count()==1]
    dump(OUT/'exclusive_evidence.json',degree_one)
    dump(OUT/'native_challenge_summary.json',dict(challenge=results,exclusive_feature_ablation=reductions,
        exclusive_features=len(degree_one),source_code_sha256=sha(__file__ if hasattr(__file__,'read_bytes') else __import__('pathlib').Path(__file__)),
        interpretation='Native labels and values retained. Labels used only to construct balanced groups and evaluate; the selected cohort is conditional and not representative of prevalence. Models frozen from stage 22, except a separately reported retraining after removal of degree-one metadata features.'))


if __name__=='__main__':main()
