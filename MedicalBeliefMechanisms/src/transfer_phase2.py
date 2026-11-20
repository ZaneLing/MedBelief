"""Train readouts on phase 2A; test every preselected layer on new phase 2B families."""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']: os.environ[k]='1'
from pathlib import Path
import hashlib,json
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.preprocessing import StandardScaler
from strong_text_controls_phase2 import make_model,TASKS
ROOT=Path(__file__).resolve().parents[1]

def load(run_id):
    run=ROOT/'runs'/run_id;meta=json.loads((run/'metadata.json').read_text());data=ROOT/meta['data']
    rows=[r for r in map(json.loads,data.read_text().splitlines()) if r['domain'] in ['aki','dvt'] and r['history']!='own_raw_final']
    state=np.stack([np.load(run/'states'/(r['id']+'.npz'))['activations'] for r in rows]).astype(np.float32)
    assert state.shape==(len(rows),36,2560) and np.isfinite(state).all()
    return rows,state,hashlib.sha256(data.read_bytes()).hexdigest()

def target(rows,states,task):
    keep=np.array([r['history']=='old_facts' if task=='old_report_direction_facts_only' else r['old_sign'] is not None if task=='old_report_numerical_direction' else True for r in rows]);rr=[r for r,k in zip(rows,keep) if k]
    if task=='current_report_numerical_direction':y=np.array([r['current_sign']=='yes' for r in rr],int)
    elif task=='current_report_usable':y=np.array([r['source'] in ['both_valid','irrelevant_withdrawn','valid'] for r in rr],int)
    else:y=np.array([r['old_sign']=='yes' for r in rr],int)
    return rr,states[keep],y

def fit(x,y,z):
    m=LogisticRegression(C=1,solver='liblinear',max_iter=2000,random_state=20261118);m.fit(x,y);return m.predict(z)

def describe(rr,y,p):
    result={'balanced_accuracy':float(balanced_accuracy_score(y,p)), 'accuracy':float(np.mean(y==p)), 'by_source':{}}
    for source in sorted({r['source'] for r in rr}):
        ix=np.array([r['source']==source for r in rr]);v={'n':int(ix.sum()),'accuracy':float(np.mean(y[ix]==p[ix]))}
        if len(set(y[ix]))==2:v['balanced_accuracy']=float(balanced_accuracy_score(y[ix],p[ix]))
        result['by_source'][source]=v
    return result

def main():
    ar,aa,ah=load('phase2_pilot_4b');br,ba,bh=load('phase2b_confirm_4b')
    assert not {r['family_id'] for r in ar}&{r['family_id'] for r in br}
    out=ROOT/'runs/phase2b_confirm_4b/transfer_from_2a';out.mkdir(exist_ok=True)
    strong=json.loads((ROOT/'runs/phase2_pilot_4b/strong_text_controls.json').read_text())
    manifest={'train_run':'phase2_pilot_4b','test_run':'phase2b_confirm_4b','train_data_sha256':ah,'test_data_sha256':bh,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'common_history_conditions_only':True,'hidden_C':1,'hidden_class_weight':None,'source_label':'Usable only if source in [both_valid, irrelevant_withdrawn, valid]',
        'layer_selection':'All 36 layers; final layer prespecified summary','text_C_selection':'Inherited from 2A training-family-only CV, refit text vocabulary and model on all 2A primary families',
        'shuffle_control':'5 permutations of labels within each training family, identical across layers','interpretation':'Recoverability and transfer, not causation or belief identification'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');results={}
    for task in TASKS:
        ra,x,y=target(ar,aa,task);rb,z,t=target(br,ba,task);families=np.array([r['family_id'] for r in ra]);null=[]
        for seed in range(5):
            rng=np.random.default_rng(20261118+seed);yy=y.copy()
            for f in np.unique(families):
                ix=np.flatnonzero(families==f);yy[ix]=rng.permutation(yy[ix])
            null.append(yy)
        curves=[];predictions=[]
        for layer in range(36):
            scaler=StandardScaler();xt=scaler.fit_transform(x[:,layer]);zt=scaler.transform(z[:,layer]);pred=fit(xt,y,zt)
            curves.append({'layer':layer+1,**describe(rb,t,pred),'random_label_scores':[float(balanced_accuracy_score(t,fit(xt,yy,zt))) for yy in null]});predictions.append(pred.tolist())
        texts=lambda rr:['\n'.join(m['content'] for m in r['messages']) for r in rr]
        controls={}
        for kind,details in strong['scopes']['primary'][task]['controls'].items():
            model=make_model(kind,details['chosen_C']);model.fit(texts(ra),y);pred=model.predict(texts(rb));controls[kind]={'C':details['chosen_C'],**describe(rb,t,pred),'predictions':pred.tolist()}
        test_families=np.array([r['family_id'] for r in rb]);clusters=np.unique(test_families);rng=np.random.default_rng(20261118);boot=[];last=np.array(predictions[-1])
        for _ in range(5000):
            ix=np.concatenate([np.flatnonzero(test_families==f) for f in rng.choice(clusters,len(clusters),replace=True)]);boot.append(balanced_accuracy_score(t[ix],last[ix]))
        results[task]={'train_rows':len(ra),'test_rows':len(rb),'train_families':len(set(families)),'test_families':len(clusters),'layers':curves,'text_controls':controls,
            'last_layer_family_bootstrap_95':np.quantile(boot,[.025,.975]).tolist(),'test_ids':[r['id'] for r in rb],'test_labels':t.tolist(),'layer_predictions':predictions}
        (out/'results.json').write_text(json.dumps(results,indent=2)+'\n');print(task,curves[-1]['balanced_accuracy'],flush=True)
    (out/'completion.json').write_text(json.dumps({'complete':True,'targets':len(results),'test_rows':len(br)})+'\n')
if __name__=='__main__':main()
