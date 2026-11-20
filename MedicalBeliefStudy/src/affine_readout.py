from pathlib import Path
import os
os.environ['OPENBLAS_NUM_THREADS']='2';os.environ['OMP_NUM_THREADS']='2'
import argparse,json,hashlib
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp
from readouts import kl
ROOT=Path(__file__).resolve().parents[1]
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def softmax(x):return np.exp(x-logsumexp(x,axis=-1,keepdims=True))
def getz(run,rows):
 result=[]
 for r in rows:
  with np.load(run/r['state_file']) as a:z=a['layer_candidate_logits'].astype(np.float64)
  result.append(z-z.mean(-1,keepdims=True))
 return np.array(result)
def fit(x,y,alpha):
 def fun(theta):
  w=theta[:36].reshape(6,6);b=theta[36:];zz=x@w+b;logs=zz-logsumexp(zz,axis=-1,keepdims=True);pred=np.exp(logs);diff=(pred-y)/len(x)
  loss=-np.sum(y*logs)/len(x)+alpha*(np.sum((w-np.eye(6))**2)+np.sum(b**2))
  grad=np.r_[(x.T@diff+2*alpha*(w-np.eye(6))).ravel(),diff.sum(0)+2*alpha*b]
  return loss,grad
 return minimize(fun,np.r_[np.eye(6).ravel(),np.zeros(6)],jac=True,method='L-BFGS-B',options={'maxiter':500,'ftol':1e-11})
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run-id',default='expanded_v1');ap.add_argument('--fit-only',action='store_true');args=ap.parse_args();run=ROOT/'runs'/args.run_id;dest=run/'readouts'
 rows=[json.loads(p.read_text()) for p in sorted((run/'observations').glob('*.json'))];train=[r for r in rows if r['cohort']=='readout_train'];dev=[r for r in rows if r['cohort']=='readout_dev'];assert len(train)==360 and len(dev)==180
 path=dest/'affine_frozen.npz'
 if not path.exists():
  x=getz(run,train);xd=getz(run,dev);y=np.array([r['q'] for r in train]);yd=np.array([r['q'] for r in dev]);ww=[];bb=[];audit=[]
  for l in range(28):
   best=(float(kl(yd,softmax(xd[:,l])).mean()),'identity',np.eye(6),np.zeros(6));trials=[]
   if l<27:
    for alpha in [.001,.01,.1,1.,10.]:
     r=fit(x[:,l],y,alpha);w=r.x[:36].reshape(6,6);b=r.x[36:];loss=float(kl(yd,softmax(xd[:,l]@w+b)).mean())
     trials.append({'alpha':alpha,'success':bool(r.success),'iterations':int(r.nit),'dev_kl':loss})
     if r.success and loss<best[0]:best=(loss,str(alpha),w,b)
   ww.append(best[2]);bb.append(best[3]);audit.append({'layer':l+1,'selected':best[1],'dev_kl':best[0],'trials':trials})
   print(json.dumps({k:v for k,v in audit[-1].items() if k!='trials'}),flush=True)
  np.savez_compressed(path,weights=ww,biases=bb)
  dump(dest/'affine_fit_manifest.json',{'training_cases':120,'development_cases':60,'layers':audit,'protocol_sha256':hashlib.sha256((ROOT/'protocol/AFFINE_READOUT.md').read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
 if args.fit_only:return
 assert (run/'completion.json').exists()
 rr=[r for r in rows if r['cohort'] in ['replication','pilot']];z=getz(run,rr);f=np.load(path);pred=softmax(np.einsum('nlk,lkd->nld',z,f['weights'])+f['biases'])
 pred[:,-1]=np.array([r['q'] for r in rr]);np.savez_compressed(dest/'affine_predictions.npz',job_ids=np.array([r['job_id'] for r in rr]),support=pred.astype(np.float32))
 cases=sorted({r['case_id'] for r in rr if r['cohort']=='replication'});quality=[]
 for l in range(28):
  loss=[];agree=[]
  for cid in cases:
   idx=[i for i,r in enumerate(rr) if r['case_id']==cid and r['order']=='base' and r['rotation'] in [0,3]];y=np.array([rr[i]['q'] for i in idx]);pp=pred[idx,l]
   loss.append(float(kl(y,pp).mean()));agree.append(float((pp.argmax(-1)==y.argmax(-1)).mean()))
  quality.append({'layer':l+1,'affine_kl':float(np.mean(loss)),'affine_agreement':float(np.mean(agree))})
 dump(dest/'affine_quality.json',quality);dump(dest/'affine_completion.json',{'complete':True,'decoded':len(rr),'heldout_cases':60})
if __name__=='__main__':main()
