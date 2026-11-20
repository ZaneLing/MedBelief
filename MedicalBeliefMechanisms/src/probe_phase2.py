"""Exploratory held-out-family readouts, with lexical and shuffled-label controls."""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[name]='1'
from pathlib import Path
import argparse,hashlib,json,warnings,importlib.metadata
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.preprocessing import StandardScaler
ROOT=Path(__file__).resolve().parents[1]

def fit_predict(train,test,y):
    model=LogisticRegression(C=1,solver='liblinear',max_iter=1000,random_state=20261118)
    model.fit(train,y)
    return model.predict(test)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-id',default='phase2_pilot_4b');ap.add_argument('--scope',choices=['primary','diagnostic_bp'],default='primary');args=ap.parse_args()
    run=ROOT/'runs'/args.run_id;metadata=json.loads((run/'metadata.json').read_text());data=ROOT/metadata['data']
    rows=[r for r in map(json.loads,data.read_text().splitlines()) if (r['domain'] in ['aki','dvt'] if args.scope=='primary' else r['domain']=='bp')]
    out=run/('probes_'+args.scope);out.mkdir(exist_ok=True)
    manifest={'data_sha256':hashlib.sha256(data.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'packages':{p:importlib.metadata.version(p) for p in ['numpy','scikit-learn','scipy']},'train_family_indices':[0,1],'test_family_indices':[2,3],'regularization_C':1,'shuffle_seeds':list(range(5)),
        'position':'Last prompt token, before any generated reasoning or answer','layer_selection':'None; all layers shown; final layer prespecified for numeric summary',
        'scope':args.scope,'interpretation':'Information recoverability only; no causal or persistent-belief inference'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    states=np.stack([np.load(run/'states'/(r['id']+'.npz'))['activations'] for r in rows]).astype(np.float32)
    assert states.shape==(len(rows),36,2560) and np.isfinite(states).all()
    results={}
    for task in ['current_report_numerical_direction','current_report_usable','old_report_numerical_direction','old_report_direction_facts_only']:
        keep=np.array([(r['history']=='old_facts' if task=='old_report_direction_facts_only' else r['old_sign'] is not None if task=='old_report_numerical_direction' else True) for r in rows])
        rr=[r for r,k in zip(rows,keep) if k];a=states[keep]
        if task=='current_report_numerical_direction':y=np.array([r['current_sign']=='yes' for r in rr],int)
        elif task=='current_report_usable':y=np.array([r['source']!='relevant_withdrawn' for r in rr],int)
        else:y=np.array([r['old_sign']=='yes' for r in rr],int)
        train=np.array([r['family_index'] in [0,1] for r in rr]);test=~train
        assert not {r['family_id'] for r,t in zip(rr,train) if t}&{r['family_id'] for r,t in zip(rr,test) if t}
        text=['\n'.join(m['content'] for m in r['messages']) for r in rr]
        tf=TfidfVectorizer(ngram_range=(1,2),lowercase=True)
        xt=tf.fit_transform([t for t,k in zip(text,train) if k]);xe=tf.transform([t for t,k in zip(text,test) if k])
        lexical=fit_predict(xt,xe,y[train]);lexscore=balanced_accuracy_score(y[test],lexical)
        train_families=np.array([r['family_id'] for r,t in zip(rr,train) if t]);shuffles=[]
        for seed in range(5):
            yy=y[train].copy();rng=np.random.default_rng(20261118+seed)
            for family in np.unique(train_families):
                index=np.flatnonzero(train_families==family);yy[index]=rng.permutation(yy[index])
            shuffles.append(yy)
        curves=[];predictions=[]
        for layer in range(a.shape[1]):
            sc=StandardScaler();xt=sc.fit_transform(a[train,layer]);xe=sc.transform(a[test,layer])
            pred=fit_predict(xt,xe,y[train]);score=balanced_accuracy_score(y[test],pred)
            nulls=[balanced_accuracy_score(y[test],fit_predict(xt,xe,yy)) for yy in shuffles]
            curves.append({'layer':layer+1,'balanced_accuracy':float(score),'random_label_scores':[float(s) for s in nulls]})
            predictions.append(pred)
        family_test=np.array([r['family_id'] for r,t in zip(rr,test) if t]);rng=np.random.default_rng(20261118)
        clusters=np.unique(family_test);boot=[]
        for _ in range(5000):
            ix=np.concatenate([np.flatnonzero(family_test==f) for f in rng.choice(clusters,size=len(clusters),replace=True)])
            boot.append(balanced_accuracy_score(y[test][ix],predictions[-1][ix]))
        item={'train_rows':int(train.sum()),'test_rows':int(test.sum()),'train_families':len(set(train_families)),'test_families':len(set(family_test)),
            'lexical_balanced_accuracy':float(lexscore),'layers':curves,'last_layer_family_bootstrap_95':np.quantile(boot,[.025,.975]).tolist(),
            'test_ids':[r['id'] for r,t in zip(rr,test) if t],'test_labels':y[test].tolist(),'layer_predictions':[p.tolist() for p in predictions],
            'lexical_predictions':lexical.tolist()}
        # An invalid report can still be represented; this does not establish that it drives the answer.
        if task=='current_report_numerical_direction':
            invalid=np.array([r['source']=='relevant_withdrawn' for r,t in zip(rr,test) if t])
            item['last_layer_invalid_report_bacc']=float(balanced_accuracy_score(y[test][invalid],predictions[-1][invalid]))
        results[task]=item
        (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
        print(task,curves[-1]['balanced_accuracy'],'lexical',lexscore,flush=True)
    (out/'completion.json').write_text(json.dumps({'complete':True,'targets':len(results),'rows':len(rows),'scope':args.scope},indent=2)+'\n')

if __name__=='__main__':main()
