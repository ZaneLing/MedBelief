"""Training-family-only tuning for text controls; test labels never select C."""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import LeaveOneGroupOut
ROOT=Path(__file__).resolve().parents[1]
TASKS=['current_report_numerical_direction','current_report_usable','old_report_numerical_direction','old_report_direction_facts_only']

def make_model(kind,c):
    vectorizer=TfidfVectorizer(ngram_range=(1,2),token_pattern=r'(?u)[+-]?\d+(?:\.\d+)?|\b\w+\b') if kind=='words_with_numbers' else TfidfVectorizer(analyzer='char',ngram_range=(3,5))
    return make_pipeline(vectorizer,LogisticRegression(C=c,class_weight='balanced',solver='liblinear',max_iter=2000,random_state=20261118))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-id',default='phase2_pilot_4b');a=ap.parse_args();run=ROOT/'runs'/a.run_id
    meta=json.loads((run/'metadata.json').read_text());data=ROOT/meta['data'];all_rows=list(map(json.loads,data.read_text().splitlines()))
    out={'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'data_sha256':hashlib.sha256(data.read_bytes()).hexdigest(),
        'reason':'Fixed-C TFIDF can predict only the majority class because normalized text features have small magnitudes. Add balanced-class, training-family-only C selection; preserve prior controls.',
        'selection':'Leave one training family out; average balanced accuracy; C in [.1,1,10,100,1000]; ties choose smaller C. Fit vocabulary separately inside every fold.',
        'development_revision':True,'test_family_indices':[2,3],'scopes':{}}
    for scope in ['primary','diagnostic_bp']:
        rows=[r for r in all_rows if (r['domain'] in ['aki','dvt'] if scope=='primary' else r['domain']=='bp')];results={}
        for task in TASKS:
            rr=[r for r in rows if (r['history']=='old_facts' if task=='old_report_direction_facts_only' else r['old_sign'] is not None if task=='old_report_numerical_direction' else True)]
            train=np.array([r['family_index'] in [0,1] for r in rr]);test=~train
            if task=='current_report_numerical_direction':y=np.array([r['current_sign']=='yes' for r in rr],int)
            elif task=='current_report_usable':y=np.array([r['source']!='relevant_withdrawn' for r in rr],int)
            else:y=np.array([r['old_sign']=='yes' for r in rr],int)
            texts=np.array(['\n'.join(m['content'] for m in r['messages']) for r in rr],dtype=object)
            trtext,try_=texts[train],y[train];groups=np.array([r['family_id'] for r,t in zip(rr,train) if t]);controls={}
            for kind in ['words_with_numbers','character_3_to_5']:
                cv=[]
                for c in [.1,1,10,100,1000]:
                    scores=[]
                    for fit,val in LeaveOneGroupOut().split(trtext,try_,groups):
                        model=make_model(kind,c);model.fit(trtext[fit].tolist(),try_[fit]);pred=model.predict(trtext[val].tolist())
                        scores.append(float(balanced_accuracy_score(try_[val],pred)))
                    cv.append({'C':c,'training_family_scores':scores,'mean':float(np.mean(scores))})
                best=max(cv,key=lambda x:x['mean']);model=make_model(kind,best['C']);model.fit(trtext.tolist(),try_);pred=model.predict(texts[test].tolist())
                controls[kind]={'chosen_C':best['C'],'training_cv':cv,'balanced_accuracy':float(balanced_accuracy_score(y[test],pred)),'predictions':pred.tolist()}
            results[task]={'controls':controls,'test_ids':[r['id'] for r,t in zip(rr,test) if t],'test_labels':y[test].tolist()}
            print(scope,task,'complete',flush=True)
        out['scopes'][scope]=results
        (run/'strong_text_controls.json').write_text(json.dumps(out,indent=2)+'\n')
    (run/'strong_text_controls_complete.json').write_text(json.dumps({'complete':True,'scopes':2,'tasks_per_scope':4})+'\n')

if __name__=='__main__':main()
