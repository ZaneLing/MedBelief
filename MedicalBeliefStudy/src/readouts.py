from pathlib import Path
import os
os.environ['OPENBLAS_NUM_THREADS']='2';os.environ['OMP_NUM_THREADS']='2'
import argparse,json,hashlib,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def probs(x):x=np.maximum(x,1e-6);return x/x.sum(-1,keepdims=True)
def kl(p,q):return np.sum(p*(np.log(np.maximum(p,1e-12))-np.log(np.maximum(q,1e-12))),axis=-1)
def features(run,rows):
 out=[]
 for r in rows:
  with np.load(run/r['state_file']) as a:h=a['residual_stages'][:,4].astype(np.float64)
  out.append(h/np.linalg.norm(h,axis=-1,keepdims=True))
 return np.array(out)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run-id',default='expanded_v1');ap.add_argument('--fit-only',action='store_true');args=ap.parse_args()
 run=ROOT/'runs'/args.run_id;dest=run/'readouts';dest.mkdir(exist_ok=True)
 rows=[json.loads(p.read_text()) for p in sorted((run/'observations').glob('*.json'))]
 train=[r for r in rows if r['cohort']=='readout_train'];dev=[r for r in rows if r['cohort']=='readout_dev']
 assert len(train)==360 and len(dev)==180
 fitpath=dest/'frozen_readouts.npz'
 if not fitpath.exists():
  x=features(run,train);xd=features(run,dev);y=np.array([r['q'] for r in train]);yd=np.array([r['q'] for r in dev])
  rng=np.random.default_rng(20261119);perm=(rng.permutation(120)[:,None]*3+np.arange(3)).reshape(-1);ys=y[perm]
  weights=[];shuffled=[];means=[];alphas=[];scores=[];ymean=y.mean(0);ysmean=ys.mean(0)
  for l in range(28):
   xx=x[:,l];mean=xx.mean(0);xx=xx-mean;dd=xd[:,l]-mean
   kernel=xx@xx.T;val,vec=np.linalg.eigh(kernel);val=np.maximum(val,0);yt=vec.T@(y-ymean);yst=vec.T@(ys-ysmean)
   trials=[]
   for alpha in [.001,.01,.1,1.,10.]:
    w=xx.T@(vec@(yt/(val[:,None]+alpha)));pred=probs(dd@w+ymean);trials.append((float(kl(yd,pred).mean()),alpha,w))
   loss,alpha,w=min(trials,key=lambda a:a[0]);ws=xx.T@(vec@(yst/(val[:,None]+alpha)))
   weights.append(w);shuffled.append(ws);means.append(mean);alphas.append(alpha)
   scores.append({'layer':l+1,'alpha':alpha,'dev_kl':loss,'dev_raw_kl':float(kl(yd,np.array([r['layer_q'][l] for r in dev])).mean())})
   print(json.dumps(scores[-1]),flush=True)
  np.savez_compressed(fitpath,weights=np.array(weights,dtype=np.float32),shuffled_weights=np.array(shuffled,dtype=np.float32),means=np.array(means,dtype=np.float32),ymean=ymean,alphas=alphas)
  dump(dest/'fit_manifest.json',{'training_cases':120,'development_cases':60,'training_observations':360,'development_observations':180,
   'train_ids':[r['job_id'] for r in train],'dev_ids':[r['job_id'] for r in dev],'training_target':'same-prefix model support; no ground truth',
   'per_layer':scores,'source_sha256':sha(__file__),'protocol_sha256':sha(ROOT/'protocol/ANALYSIS_SUPPLEMENT.md'),'frozen_readout_sha256':sha(fitpath)})
 if args.fit_only:return
 assert (run/'completion.json').exists()
 rows=[r for r in rows if r['cohort'] in ['replication','pilot']]
 z=np.load(fitpath);w=z['weights'];ws=z['shuffled_weights'];mean=z['means'];ym=z['ymean'];predictions=[];shuffled_predictions=[]
 for i,r in enumerate(rows):
  with np.load(run/r['state_file']) as a:h=a['residual_stages'][:,4].astype(np.float32)
  h=h/np.linalg.norm(h,axis=-1,keepdims=True)-mean
  pred=probs(np.einsum('lh,lhd->ld',h,w)+ym);ps=probs(np.einsum('lh,lhd->ld',h,ws)+ym)
  # Last layer remains the real output, rather than a fitted approximation.
  pred[-1]=r['q'];ps[-1]=r['q'];predictions.append(pred);shuffled_predictions.append(ps)
  if (i+1)%1000==0:print('decoded',i+1,flush=True)
 pred=np.array(predictions);ps=np.array(shuffled_predictions)
 np.savez_compressed(dest/'heldout_predictions.npz',job_ids=np.array([r['job_id'] for r in rows]),calibrated=pred.astype(np.float32),shuffled=ps.astype(np.float32))
 # Evaluate on the two core mappings of base trajectories, case-weighted.
 selected=[i for i,r in enumerate(rows) if r['cohort']=='replication' and r['order']=='base' and r['rotation'] in [0,3]]
 ids=sorted({rows[i]['case_id'] for i in selected});result=[]
 for l in range(28):
  cases=[]
  for cid in ids:
   ix=[i for i in selected if rows[i]['case_id']==cid];yy=np.array([rows[i]['q'] for i in ix]);raw=np.array([rows[i]['layer_q'][l] for i in ix])
   cases.append({'raw_kl':float(kl(yy,raw).mean()),'calibrated_kl':float(kl(yy,pred[ix,l]).mean()),
    'shuffled_kl':float(kl(yy,ps[ix,l]).mean()),'constant_kl':float(kl(yy,probs(ym)).mean()),
    'raw_agreement':float((raw.argmax(-1)==yy.argmax(-1)).mean()),'calibrated_agreement':float((pred[ix,l].argmax(-1)==yy.argmax(-1)).mean()),
    'shuffled_agreement':float((ps[ix,l].argmax(-1)==yy.argmax(-1)).mean())})
  result.append({'layer':l+1,**{k:float(np.mean([c[k] for c in cases])) for k in cases[0]}})
 dump(dest/'heldout_quality.json',result);dump(dest/'completion.json',{'complete':True,'decoded':len(rows),'heldout_cases':60,'quality_weighting':'each case equal; base order; rotations0,3','source_sha256':sha(__file__)})
if __name__=='__main__':main()
