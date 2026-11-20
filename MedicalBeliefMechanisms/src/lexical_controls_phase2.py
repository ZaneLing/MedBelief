"""Fair text controls that retain one-digit scores and negative numeric signs."""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
from pathlib import Path
import argparse,hashlib,json,importlib.metadata
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
ROOT=Path(__file__).resolve().parents[1]
TASKS=['current_report_numerical_direction','current_report_usable','old_report_numerical_direction','old_report_direction_facts_only']

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-id',default='phase2_pilot_4b');args=ap.parse_args();run=ROOT/'runs'/args.run_id
    meta=json.loads((run/'metadata.json').read_text());data=ROOT/meta['data'];all_rows=list(map(json.loads,data.read_text().splitlines()))
    output={'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'data_sha256':hashlib.sha256(data.read_bytes()).hexdigest(),
        'note':'Added before inspecting readout scores: default word tokenization omits one-digit Wells scores. Both improved controls are reported; no choice based on test performance.',
        'scopes':{},'sklearn_version':importlib.metadata.version('scikit-learn')}
    for scope in ['primary','diagnostic_bp']:
        rows=[r for r in all_rows if (r['domain'] in ['aki','dvt'] if scope=='primary' else r['domain']=='bp')];results={}
        for task in TASKS:
            rr=[r for r in rows if (r['history']=='old_facts' if task=='old_report_direction_facts_only' else r['old_sign'] is not None if task=='old_report_numerical_direction' else True)]
            train=np.array([r['family_index'] in [0,1] for r in rr]);test=~train
            if task=='current_report_numerical_direction':y=np.array([r['current_sign']=='yes' for r in rr],int)
            elif task=='current_report_usable':y=np.array([r['source']!='relevant_withdrawn' for r in rr],int)
            else:y=np.array([r['old_sign']=='yes' for r in rr],int)
            texts=['\n'.join(m['content'] for m in r['messages']) for r in rr];controls={}
            for name,vectorizer in [('words_with_numbers',TfidfVectorizer(ngram_range=(1,2),token_pattern=r'(?u)[+-]?\d+(?:\.\d+)?|\b\w+\b')),
                                    ('character_3_to_5',TfidfVectorizer(analyzer='char',ngram_range=(3,5)))]:
                x=vectorizer.fit_transform([s for s,t in zip(texts,train) if t]);z=vectorizer.transform([s for s,t in zip(texts,test) if t])
                clf=LogisticRegression(C=1,solver='liblinear',max_iter=1000,random_state=20261118);clf.fit(x,y[train]);pred=clf.predict(z)
                controls[name]={'balanced_accuracy':float(balanced_accuracy_score(y[test],pred)),'predictions':pred.tolist(),'vocabulary_features':x.shape[1]}
            results[task]={'controls':controls,'test_ids':[r['id'] for r,t in zip(rr,test) if t],'test_labels':y[test].tolist()}
        output['scopes'][scope]=results
    (run/'lexical_controls_v2.json').write_text(json.dumps(output,indent=2)+'\n');print('Wrote lexical controls for both scopes')

if __name__=='__main__':main()
