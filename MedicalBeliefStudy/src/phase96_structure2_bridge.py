"""Replace eight tail blocks by a weighted rank64 teacher-state bridge."""
import numpy as np
from sklearn.utils.extmath import randomized_svd
from phase90_structure2_prepare import *
def collect(cohort):
    xx=[];yy=[];ww=[]
    for c in cases():
        if c['cohort']!=cohort:continue
        a=np.load(RUN/'features/base'/(c['case_id']+'.npz'));xx.append(a['x20'].astype(np.float32));yy.append(a['x28'].astype(np.float32));ww.append(a['weight'])
    return np.concatenate(xx),np.concatenate(yy),np.concatenate(ww)
def main():
    dest=RUN/'bridge';dest.mkdir(exist_ok=True);x,y,w=collect('train');vx,vy,vw=collect('development');xm=np.average(x,axis=0,weights=w);ym=np.average(y,axis=0,weights=w);xc=x-xm;yc=y-ym
    _,_,vt=randomized_svd(xc*np.sqrt(w)[:,None],n_components=64,n_iter=4,random_state=20261120);left=vt.T;z=xc@left;gram=z.T@(w[:,None]*z);ridge=.01*np.trace(gram)/64;right=np.linalg.solve(gram+ridge*np.eye(64),z.T@(w[:,None]*yc)).astype(np.float32)
    arrays=dict(xmean=xm.astype(np.float32),ymean=ym.astype(np.float32),left=left.astype(np.float32),right=right);np.savez(dest/'rank64.npz',**arrays)
    def error(a,b,ww):
        pred=(a-xm)@left@right+ym;return dict(weighted_mse=float(np.average(np.mean((pred-b)**2,axis=1),weights=ww)),identity_mse=float(np.average(np.mean((a-b)**2,axis=1),weights=ww)))
    cfg=dict(name='exit20_bridge64',exit_layer=20,bridge_file=str((dest/'rank64.npz').relative_to(ROOT)))
    write(dest/'completion.json',dict(complete=True,configuration=cfg,rank=64,parameters=sum(a.size for a in arrays.values()),ridge=float(ridge),train=error(x,y,w),development=error(vx,vy,vw),source_sha256=sha(Path(__file__)),weights_sha256=sha(dest/'rank64.npz'),supervision='Full model hidden states on source-answer teacher-forced prefixes; no separate disease-label loss. Prefixes themselves use source answers.',api_cost_usd=0));print(json.dumps(read(dest/'completion.json')))
if __name__=='__main__':main()
