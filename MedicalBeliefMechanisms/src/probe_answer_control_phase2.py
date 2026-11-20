"""Does an eligibility readout distinguish R1 status when a backup fixes the answer?"""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
from pathlib import Path
import hashlib,json
import numpy as np
from sklearn.metrics import balanced_accuracy_score
from sklearn.preprocessing import StandardScaler
from transfer_phase2 import load,target,fit
from strong_text_controls_phase2 import make_model
from analyze_phase2 import cell
ROOT=Path(__file__).resolve().parents[1]
def main():
    ar,aa,ah=load('phase2_pilot_4b');task='current_report_usable';run=ROOT/'runs/phase2c_answer_control_4b';meta=json.loads((run/'metadata.json').read_text());data=ROOT/meta['data']
    br=list(map(json.loads,data.read_text().splitlines()));ba=np.stack([np.load(run/'states'/(r['id']+'.npz'))['activations'] for r in br]).astype(np.float32);t=np.array([r['target_usable'] for r in br],int)
    assert ba.shape==(64,36,2560) and np.isfinite(ba).all() and len(set(t))==2
    strong=json.loads((ROOT/'runs/phase2_pilot_4b/strong_text_controls.json').read_text())['scopes']['primary'][task]['controls']
    output=run/'answer_control_readout';output.mkdir(exist_ok=True)
    result={'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'train_data_sha256':ah,'test_data_sha256':hashlib.sha256(data.read_bytes()).hexdigest(),
        'primary_training_scope':'all_2a_histories','secondary_training_scope':'2a_current_only','summary_layer':36,'test_ids':[r['id'] for r in br],'test_labels':t.tolist(),'results':{}}
    text=lambda rr:['\n'.join(m['content'] for m in r['messages']) if 'messages' in r else r['prompt'] for r in rr]
    masks={'no_backup':np.array([not r['backup_available'] for r in br]),'backup_present':np.array([r['backup_available'] for r in br])}
    def scores(p):
        z={}
        for name,ix in masks.items():
            z[name]={'balanced_accuracy':float(balanced_accuracy_score(t[ix],p[ix])),'n':int(ix.sum()),'usable_accuracy':float(np.mean(p[ix&(t==1)]==1)),'unusable_accuracy':float(np.mean(p[ix&(t==0)]==0))}
        return z
    for scope in ['all_2a_histories','2a_current_only']:
        keep=np.array([True if scope=='all_2a_histories' else r['history']=='current_only' for r in ar]);ra=[r for r,k in zip(ar,keep) if k]
        ra,x,y=target(ra,aa[keep],task);curves=[];preds=[];families=np.array([r['family_id'] for r in ra]);null=[]
        for seed in range(5):
            rng=np.random.default_rng(20261118+seed);yy=y.copy()
            for f in np.unique(families):
                ix=np.flatnonzero(families==f);yy[ix]=rng.permutation(yy[ix])
            null.append(yy)
        for layer in range(36):
            sc=StandardScaler();xt=sc.fit_transform(x[:,layer]);zt=sc.transform(ba[:,layer]);pred=fit(xt,y,zt)
            null_scores=[scores(fit(xt,yy,zt)) for yy in null]
            curves.append({'layer':layer+1,'strata':scores(pred),'random_label_scores':{s:[v[s]['balanced_accuracy'] for v in null_scores] for s in masks}});preds.append(pred.tolist())
        controls={}
        for kind,config in strong.items():
            model=make_model(kind,config['chosen_C']);model.fit(text(ra),y);p=model.predict(text(br));controls[kind]={'C':config['chosen_C'],'strata':scores(p),'predictions':p.tolist()}
        result['results'][scope]={'train_rows':len(ra),'layers':curves,'text_controls':controls,'layer_predictions':preds}
        (output/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(scope,curves[-1]['strata'],flush=True)
    (output/'completion.json').write_text(json.dumps({'complete':True,'test_records':64,'training_scopes':2})+'\n')
if __name__=='__main__':main()
