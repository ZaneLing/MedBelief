"""Low-rank linear teacher-output fits; no diagnosis labels used for fitting."""
import json,hashlib
import numpy as np
from sklearn.utils.extmath import randomized_svd
from phase41_multisource_analyze import ROOT,read,write

RUN=ROOT/'runs/structural_v1'
def main():
    dest=RUN/'linear';assert read(dest/'anchors_complete.json')['complete'];spec=read(RUN/'development_candidates.json');layers=spec['rankings']['mlp'][:4];meta=read(dest/'anchor_rows.json');a=np.load(dest/'anchors.npz');train=np.array([r['split']=='train' for r in meta]);scores=[];weights={16:{},64:{}}
    for l in layers:
        xx=[];yy=[]
        for p in sorted((RUN/'screen').glob('*.npz')):
            with np.load(p) as z:xx.append(z['x'][l-1].astype(np.float32));yy.append(z['y'][l-1].astype(np.float32))
        # Preserve uniform-token teacher coverage; give the decision position
        # a fixed 8x training weight so it is not almost absent by chance.
        x=np.concatenate(xx+[np.repeat(a['x'][train,l-1].astype(np.float32),8,axis=0)]);y=np.concatenate(yy+[np.repeat(a['y'][train,l-1].astype(np.float32),8,axis=0)])
        xm=x.mean(0);ym=y.mean(0);xc=x-xm;yc=y-ym
        _,_,vt=randomized_svd(xc,n_components=64,n_iter=3,random_state=7300+l);projection=vt.T
        for rank in [16,64]:
            left=projection[:,:rank];z=xc@left;gram=z.T@z;ridge=.01*np.trace(gram)/rank;right=np.linalg.solve(gram+np.eye(rank,dtype=np.float32)*ridge,z.T@yc).astype(np.float32)
            r=dict(xmean=xm,ymean=ym,left=left,right=right)
            for k,v in r.items():weights[rank][f'L{l}_{k}']=v
            for split,mask in [('train',train),('tune',~train)]:
                tx=a['x'][mask,l-1].astype(np.float32);ty=a['y'][mask,l-1].astype(np.float32);pred=((tx-xm)@left)@right+ym
                mse=float(np.mean((pred-ty)**2)/np.mean(ty**2));cos=float(np.mean(np.sum(pred*ty,-1)/(np.linalg.norm(pred,axis=1)*np.linalg.norm(ty,axis=1)+1e-10)))
                scores.append(dict(layer=l,rank=rank,split=split,relative_mse=mse,cosine=cos,anchor_records=int(mask.sum()),training_rows=len(x),ridge=float(ridge)))
        print(json.dumps(dict(layer=l,training_rows=len(x))),flush=True)
    for rank,w in weights.items():np.savez_compressed(dest/f'rank_{rank}.npz',**w)
    write(dest/'manifest.json',dict(complete=True,layers=layers,ranks=[16,64],fit='PCA input subspace and ridge teacher MLP output',anchor_repeat=8,random_tokens_per_prompt=32,train_cases=18,tune_cases=27,uses_diagnosis_labels_for_fit=False,fit_metrics=scores,source_sha256=hashlib.sha256(open(__file__,'rb').read()).hexdigest(),api_cost_usd=0))
if __name__=='__main__':main()

