"""Train-only lexical retrieval reader on MedQA and MedMCQA; no LLM calls."""
import collections
import hashlib
import json
import re
import time
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from lightweight_multidataset import ROOT, OUT, dump


def read(path):
    with path.open() as f:return [json.loads(s) for s in f]


def normalize(s):return re.sub(r'\W+',' ',s.lower()).strip()


def convert(rows,ds):
    cases=[]
    for i,r in enumerate(rows):
        if ds=='medqa':
            keys=sorted(r['options']);opts=[r['options'][k] for k in keys];gold=keys.index(r['answer_idx'])
        else:
            if r['choice_type']!='single':continue
            opts=[r[k] for k in ['opa','opb','opc','opd']];gold=int(r['cop'])
        assert len(opts)==4
        cases.append(dict(id=r.get('id',str(i)),question=r['question'],options=opts,gold=gold,answer=opts[gold]))
    return cases


def score(reader,cs):
    v,x,av,ax=reader
    started=time.perf_counter();q=v.transform([c['question'] for c in cs]);opts=[s for c in cs for s in c['options']]
    o=av.transform(opts);lex=v.transform(opts)
    out={k:[] for k in [1,5,20]};lexpred=[]
    for start in range(0,len(cs),32):
        sim=(q[start:start+32]@x.T).toarray();idx=np.argpartition(sim,-20,axis=1)[:,-20:]
        for j,ids in enumerate(idx):
            i=start+j;ids=ids[np.argsort(-sim[j,ids],kind='stable')];weights=sim[j,ids]**2
            am=(ax[ids]@o[i*4:i*4+4].T).toarray()
            for k in out:out[k].append(int(np.argmax(weights[:k]@am[:k])))
            lexpred.append(int(np.argmax((q[i]@lex[i*4:i*4+4].T).toarray())))
    out['lexical_only']=lexpred
    return out,time.perf_counter()-started


def run(ds):
    raw=ROOT/'data/belief_v4/raw'
    if ds=='medqa':
        paths=[raw/'medqa_train.jsonl',raw/'medqa_dev.jsonl',ROOT/'data/external_medqa/test.jsonl']
        train,dev,test=[convert(read(p),ds) for p in paths]
    else:
        paths=[raw/'decoded/medmcqa_train-00000-of-00001.jsonl',raw/'decoded/medmcqa_validation-00000-of-00001.jsonl']
        pool,test=[convert(read(p),ds) for p in paths]
        # Hold out about 10% of question groups; fixed first 2000 by hash for selection cost.
        gethash=lambda c:hashlib.sha256(normalize(c['question']).encode()).hexdigest()
        train=[c for c in pool if int(gethash(c)[:8],16)%10!=0]
        dev=sorted([c for c in pool if int(gethash(c)[:8],16)%10==0],key=gethash)[:2000]
    devkeys={normalize(c['question']) for c in dev}
    before=len(train);train=[c for c in train if normalize(c['question']) not in devkeys]
    # Preserve source prevalence for fit; explicitly report normalized-question test overlaps.
    trainkeys={normalize(c['question']) for c in train};fresh=np.array([normalize(c['question']) not in trainkeys for c in test])
    v=TfidfVectorizer(ngram_range=(1,2),min_df=2,max_features=60000,sublinear_tf=True,dtype=np.float32)
    av=TfidfVectorizer(analyzer='char_wb',ngram_range=(3,4),min_df=2,max_features=40000,dtype=np.float32)
    t=time.perf_counter();x=v.fit_transform([c['question'] for c in train]);ax=av.fit_transform([c['answer'] for c in train]);fit=time.perf_counter()-t
    reader=(v,x,av,ax);dv,dt=score(reader,dev);yd=np.array([c['gold'] for c in dev])
    selected=max([1,5,20],key=lambda k:np.mean(np.array(dv[k])==yd))
    predictions,pt=score(reader,test);yt=np.array([c['gold'] for c in test])
    majority=collections.Counter(c['gold'] for c in train).most_common(1)[0][0]
    results={}
    for k,p in predictions.items():
        a=np.array(p);results[str(k)]=dict(n=len(yt),correct=int(np.sum(a==yt)),accuracy=float(np.mean(a==yt)),
            fresh_n=int(fresh.sum()),fresh_accuracy=float(np.mean(a[fresh]==yt[fresh])))
    modelpath=OUT/f'{ds}_retrieval.joblib';joblib.dump(reader,modelpath,compress=3)
    result=dict(dataset=ds,train_n=len(train),dev_n=len(dev),test_n=len(test),train_rows_removed_for_dev_overlap=before-len(train),
        selected_k=selected,dev_accuracy={str(k):float(np.mean(np.array(p)==yd)) for k,p in dv.items()},
        all_k_results=results,selected=results[str(selected)],test_question_overlap=int((~fresh).sum()),
        majority_position_accuracy=float(np.mean(yt==majority)),fit_seconds=fit,
        dev_prediction_seconds=dt,test_prediction_seconds=pt,compressed_model_bytes=modelpath.stat().st_size,
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    dump(OUT/f'{ds}_results.json',result)
    dump(OUT/f'{ds}_predictions.json',[dict(id=c['id'],gold=c['gold'],prediction=predictions[selected][i],
        novel_question=bool(fresh[i])) for i,c in enumerate(test)])
    # Model-independent input file contains neither answer key nor explanations.
    (OUT/f'{ds}_gpt_inputs.jsonl').write_text(''.join(json.dumps(dict(id=c['id'],prompt=c['question']+'\n'+
        '\n'.join(f'{chr(65+j)}. {o}' for j,o in enumerate(c['options']))+'\nReturn only the answer letter.'),ensure_ascii=False)+'\n' for c in test))
    print(ds,json.dumps(result),flush=True)


if __name__=='__main__':
    OUT.mkdir(exist_ok=True,parents=True)
    for name in ['medqa','medmcqa']:run(name)
