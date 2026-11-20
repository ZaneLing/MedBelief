"""Exploratory readout repairs; all choices frozen before phase2C model outputs."""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
from pathlib import Path
import hashlib,json
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.preprocessing import StandardScaler
from transfer_phase2 import load,target,fit
from strong_text_controls_phase2 import make_model
ROOT=Path(__file__).resolve().parents[1]
def main():
    ar,aa,ah=load('phase2_pilot_4b');br,ba,bh=load('phase2b_confirm_4b');run=ROOT/'runs/phase2c_answer_control_4b';meta=json.loads((run/'metadata.json').read_text());path=ROOT/meta['data']
    cr=list(map(json.loads,path.read_text().splitlines()));ca=np.stack([np.load(run/'states'/(r['id']+'.npz'))['activations'] for r in cr]).astype(np.float32)
    # Keep the same rule for reading labels; C target is explicitly R1, not any usable report.
    cy=np.array([r['target_usable'] for r in cr],int);out=run/'source_readout_repairs';out.mkdir(exist_ok=True)
    controls=json.loads((ROOT/'runs/phase2_pilot_4b/strong_text_controls.json').read_text())['scopes']['primary']['current_report_usable']['controls']
    cp=ROOT/'protocol/phase2c_readout_repairs.json';proto=json.loads(cp.read_text());assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==proto['source_sha256']
    text=lambda rr:['\n'.join(m['content'] for m in r['messages']) if 'messages' in r else r['prompt'] for r in rr]
    result={'protocol':proto,'results':{}}
    for name in ['train_2a_2b_test_2c','train_2c_half_test_other_half']:
        if name=='train_2a_2b_test_2c':
            ra,x,y=target(ar+br,np.concatenate([aa,ba]),'current_report_usable');rt=cr;z=ca;t=cy
        else:
            train=np.array([r['family_index'] in [8,9] for r in cr]);ra=[r for r,k in zip(cr,train) if k];rt=[r for r,k in zip(cr,train) if not k];x=ca[train];z=ca[~train];y=cy[train];t=cy[~train]
        assert not {r['family_id'] for r in ra}&{r['family_id'] for r in rt}
        masks={'no_backup':np.array([not r['backup_available'] for r in rt]),'backup_present':np.array([r['backup_available'] for r in rt])}
        def score(p):return {s:{'n':int(ix.sum()),'balanced_accuracy':float(balanced_accuracy_score(t[ix],p[ix])),'usable_accuracy':float(np.mean(p[ix&(t==1)]==1)),'unusable_accuracy':float(np.mean(p[ix&(t==0)]==0))} for s,ix in masks.items()}
        families=np.array([r['family_id'] for r in ra]);null=[]
        for seed in range(5):
            rng=np.random.default_rng(20261118+seed);yy=y.copy()
            for f in np.unique(families):
                ix=np.flatnonzero(families==f);yy[ix]=rng.permutation(yy[ix])
            null.append(yy)
        layers=[];preds=[]
        for layer in range(36):
            sc=StandardScaler();xt=sc.fit_transform(x[:,layer]);zt=sc.transform(z[:,layer]);p=fit(xt,y,zt);ns=[score(fit(xt,yy,zt)) for yy in null]
            layers.append({'layer':layer+1,'strata':score(p),'random_label_scores':{s:[v[s]['balanced_accuracy'] for v in ns] for s in masks}});preds.append(p.tolist())
        tc={}
        for kind,config in controls.items():
            # C parameters are inherited, never selected using 2C test labels.
            m=make_model(kind,config['chosen_C']);m.fit(text(ra),y);p=m.predict(text(rt));tc[kind]={'C':config['chosen_C'],'strata':score(p),'predictions':p.tolist()}
        item={'train_rows':len(ra),'test_rows':len(rt),'train_families':len(set(families)),'test_families':len({r['family_id'] for r in rt}),'layers':layers,'text_controls':tc,'test_ids':[r['id'] for r in rt],'test_labels':t.tolist(),'layer_predictions':preds}
        result['results'][name]=item;(out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(name,layers[-1]['strata'],flush=True)
    (out/'completion.json').write_text(json.dumps({'complete':True,'readout_methods':2})+'\n')
if __name__=='__main__':main()
