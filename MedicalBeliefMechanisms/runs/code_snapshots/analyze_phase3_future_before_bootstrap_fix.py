"""Predict actual future changes from current information, with strong visible-text controls."""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
from pathlib import Path
import hashlib,json
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.preprocessing import StandardScaler
from strong_text_controls_phase2 import make_model
from analyze_phase2 import cell
from plot_phase2 import plt,COLORS,save
ROOT=Path(__file__).resolve().parents[1]
def main():
    run=ROOT/'runs/phase3_future_pilot_4b';meta=json.loads((run/'metadata.json').read_text());inp={r['id']:r for r in map(json.loads,(ROOT/meta['data']).read_text().splitlines())};out=list(map(json.loads,(run/'predictions.jsonl').read_text().splitlines()));assert len(out)==32 and {r['id'] for r in out}==set(inp)
    rr=[r for r in out if r['prediction'] is not None];excluded=[r['id'] for r in out if r['prediction'] is None]
    current={r['id']:r for r in map(json.loads,(ROOT/'data/phase2c_answer_control.jsonl').read_text().splitlines())}
    states=np.stack([np.load(ROOT/'runs/phase2c_answer_control_4b/states'/(r['current_id']+'.npz'))['activations'] for r in rr]).astype(np.float32)
    y=np.array([r['prediction']!=r['current_prediction'] for r in rr],int);train=np.array([r['family_index'] in [8,9] for r in rr]);test=~train;groups=np.array([r['family_id'] for r,k in zip(rr,train) if k]);base=np.array([[r['current_prediction']=='yes',r['domain']=='dvt'] for r in rr],float)
    assert not {r['family_id'] for r,k in zip(rr,train) if k}&{r['family_id'] for r,k in zip(rr,train) if not k}
    texts=np.array([current[r['current_id']]['prompt']+'\nCURRENT RESPONSE\n'+inp[r['id']]['current_response']+'\nSEMANTIC_CURRENT_ANSWER '+r['current_prediction']+' DOMAIN '+r['domain'] for r in rr],object)
    result={'protocol':json.loads((ROOT/'protocol/phase3_future_pilot.json').read_text()),'analysis_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'behavior':cell(out),'excluded_from_forecasting':excluded,
        'by_r1_status':{str(s):cell([r for r in out if r['target_usable']==s]) for s in [True,False]},'future_change_count':int(y.sum()),'unchanged_count':int((y==0).sum()),
        'train_rows':int(train.sum()),'test_rows':int(test.sum()),'test_ids':[r['id'] for r,k in zip(rr,test) if k],'test_labels_changed':y[test].tolist(),
        'errors':[{**r,'messages':inp[r['id']]['messages']} for r in out if r['prediction']!=r['gold']]}
    if len(set(y[train]))<2 or len(set(y[test]))<2:
        result['forecast_status']='No two-class target available in train/test; no fabricated classification result';(run/'analysis.json').write_text(json.dumps(result,indent=2)+'\n');return
    def fit(x,yy,z):
        m=LogisticRegression(C=1,class_weight='balanced',solver='liblinear',max_iter=2000,random_state=20261118);m.fit(x,yy);return m.predict(z)
    base_pred=fit(base[train],y[train],base[test]);result['answer_domain_only']={'balanced_accuracy':float(balanced_accuracy_score(y[test],base_pred)),'predictions':base_pred.tolist()}
    tc={}
    for kind in ['words_with_numbers','character_3_to_5']:
        cv=[]
        for c in [.1,1,10,100,1000]:
            scores=[]
            for a,b in LeaveOneGroupOut().split(texts[train],y[train],groups):
                m=make_model(kind,c);m.fit(texts[train][a].tolist(),y[train][a]);p=m.predict(texts[train][b].tolist());scores.append(float(balanced_accuracy_score(y[train][b],p)))
            cv.append({'C':c,'mean':float(np.mean(scores)),'folds':scores})
        chosen=max(cv,key=lambda x:x['mean']);m=make_model(kind,chosen['C']);m.fit(texts[train].tolist(),y[train]);p=m.predict(texts[test].tolist());tc[kind]={'chosen_C':chosen['C'],'training_cv':cv,'balanced_accuracy':float(balanced_accuracy_score(y[test],p)),'predictions':p.tolist()}
    result['text_controls']=tc;null=[]
    for seed in range(5):
        yy=y[train].copy();rng=np.random.default_rng(20261118+seed)
        for f in np.unique(groups):
            ix=np.flatnonzero(groups==f);yy[ix]=rng.permutation(yy[ix])
        null.append(yy)
    layers=[];preds=[]
    for layer in range(36):
        sc=StandardScaler();x=np.column_stack([sc.fit_transform(states[train,layer]),base[train]]);z=np.column_stack([sc.transform(states[test,layer]),base[test]]);p=fit(x,y[train],z);preds.append(p.tolist())
        layers.append({'layer':layer+1,'balanced_accuracy':float(balanced_accuracy_score(y[test],p)),'random_label_scores':[float(balanced_accuracy_score(y[test],fit(x,yy,z))) for yy in null]})
    result['layers']=layers;result['layer_predictions']=preds;result['primary_layer']=36;result['secondary_layer']=26
    test_families=np.array([r['family_id'] for r,k in zip(rr,test) if k]);clusters=np.unique(test_families);rng=np.random.default_rng(20261118);p=np.array(preds[-1]);word=np.array(tc['words_with_numbers']['predictions']);char=np.array(tc['character_3_to_5']['predictions']);boot=[[],[]]
    for _ in range(5000):
        ix=np.concatenate([np.flatnonzero(test_families==f) for f in rng.choice(clusters,len(clusters),replace=True)])
        for k,q in enumerate([word,char]):boot[k].append(balanced_accuracy_score(y[test][ix],p[ix])-balanced_accuracy_score(y[test][ix],q[ix]))
    result['last_layer_minus_text']={k:{'difference':layers[-1]['balanced_accuracy']-tc[k]['balanced_accuracy'],'family_bootstrap_95':np.quantile(b,[.025,.975]).tolist()} for k,b in zip(['words_with_numbers','character_3_to_5'],boot)}
    result['limits']='4 train and 4 test numerical families; no current-confidence control; all layers shown; predictive recoverability only, no hidden belief or causal conclusion.'
    (run/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    fig,ax=plt.subplots(figsize=(9,4.2));xx=np.arange(1,37);ns=np.array([r['random_label_scores'] for r in layers]);ax.plot(xx,[r['balanced_accuracy'] for r in layers],color=COLORS[1],lw=2,label='State + current answer + domain');ax.plot(xx,ns.mean(1),color='#888',lw=1,label='Shuffled future labels (5)');ax.fill_between(xx,ns.min(1),ns.max(1),color='#888',alpha=.12)
    ax.axhline(result['answer_domain_only']['balanced_accuracy'],color='#555',ls=':',label='Current answer + domain only')
    for kind,color,label in [('words_with_numbers',COLORS[2],'Visible text + answer: words'),('character_3_to_5',COLORS[3],'Visible text + answer: characters')]:ax.axhline(tc[kind]['balanced_accuracy'],color=color,ls='--',label=label)
    ax.set_xlim(1,36);ax.set_ylim(0,1.04);ax.set_xlabel('Transformer layer before current reasoning');ax.set_ylabel('Future-change balanced accuracy');ax.set_title('Same current answer: can we predict the actual later update?');ax.legend(loc='lower left',fontsize=8)
    fig.text(.5,.005,f"Train: {train.sum()} trajectories / 4 families. Test: {test.sum()} trajectories / 4 families. Future outcomes excluded from predictor inputs.",ha='center',fontsize=9,color='#555');fig.tight_layout(rect=(0,.05,1,1));save(fig,'11_future_update_prediction')
    print(json.dumps({'behavior':result['behavior'],'base':result['answer_domain_only']['balanced_accuracy'],'text':{k:v['balanced_accuracy'] for k,v in tc.items()},'layer36':layers[-1]['balanced_accuracy'],'layer26':layers[25]['balanced_accuracy']},indent=2))
if __name__=='__main__':main()
