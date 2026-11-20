"""Shared CPU-only analysis of the frozen v3 observations."""
import collections,hashlib,json
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
from analyze_stages import ROOT,setup,savefig,ci,fmt,csvwrite,js

ZH=json.loads((ROOT/'results/14_fixed_panel/disease_display_names.json').read_text())
PATTERNS={'stable_gold':'始终首选来源病','acquired_gold':'转向来源病后保持','recovered_gold':'曾离开来源病，最后回来','lost_gold':'曾选来源病，最后离开','stable_other':'始终固定另一病','switching_other':'在其他疾病间变动'}
def read(p):return json.loads(Path(p).read_text())
def rows(p):return list(map(json.loads,Path(p).read_text().splitlines()))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def clean(x):
 if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
 if isinstance(x,(list,tuple)):return [clean(v) for v in x]
 if isinstance(x,np.ndarray):return clean(x.tolist())
 if isinstance(x,np.generic):return clean(x.item())
 if isinstance(x,float) and not np.isfinite(x):return None
 return x
def dump(p,x):Path(p).write_text(json.dumps(clean(x),ensure_ascii=False,indent=2)+'\n')
def norm(x):return x/np.maximum(np.linalg.norm(x,axis=-1,keepdims=True),1e-12)
def summary(v):return ci([x for x in v if x is not None and np.isfinite(x)])
def rho(x,y):
 x=np.asarray(x);y=np.asarray(y)
 return float(spearmanr(x,y).statistic) if len(x)>=3 and np.ptp(x)>1e-10 and np.ptp(y)>1e-10 else None
def pattern(hit,pred):
 if all(hit):return 'stable_gold'
 if not any(hit):return 'stable_other' if len(set(pred))==1 else 'switching_other'
 if not hit[-1]:return 'lost_gold'
 if any(hit[t-1] and not hit[t] for t in range(1,len(hit))):return 'recovered_gold'
 return 'acquired_gold'
def stable(hit):return next((i for i in range(len(hit)) if all(hit[i:])),None)
def path_metrics(q,gi):
 q=np.asarray(q);pred=q.argmax(-1);hit=pred==gi;tv=.5*np.abs(np.diff(q,axis=0)).sum(-1);sw=pred[1:]!=pred[:-1];big=np.max(np.abs(np.diff(q,axis=0)),axis=-1)>=.5
 return dict(updates=len(q)-1,switches=int(sw.sum()),big_updates=int(big.sum()),any_switch=bool(sw.any()),any_big=bool(big.any()),switch_rate=float(sw.mean()),big_rate=float(big.mean()),final_hit=bool(hit[-1]),ever_hit=bool(hit.any()),regression=bool(np.any(hit[:-1]&~hit[1:])),first_hit=next((i for i,h in enumerate(hit) if h),None),stable_hit=stable(hit),pattern=pattern(hit,pred),max_step_share=float(tv.max()/tv.sum()) if tv.sum()>1e-12 else 0.,gold_decrease_rate=float(np.mean(np.diff(q[:,gi])< -1e-4)),native_prefix_hit=float(hit.mean()))
def sign_permutation(x,seed=20261119):
 x=np.asarray([v for v in x if np.isfinite(v)]);rng=np.random.default_rng(seed)
 if not len(x):return None
 z=(rng.choice([-1,1],(20000,len(x)))*x).mean(-1)
 return float((1+np.sum(abs(z)>=abs(x.mean())-1e-14))/20001)
def holm(p):
 order=np.argsort(p);out=np.empty(len(p));last=0
 for i,j in enumerate(order):last=max(last,min(1.,p[j]*(len(p)-i)));out[j]=last
 return out.tolist()
def load_record(run,c,t=None,view='append',order='base'):
 t=len(c['orders']['base']) if t is None else t
 return read(run/'observations'/f"{c['case_id']}_{view}_{order}_t{t:02d}.json")
def support_margin(r,g,c):return float(r['log_probability'][g]-r['log_probability'][c])
def readout(run,r,head,view='append',model='1.7b',all_stages=False):
 with np.load(run/r['state_file']) as a:x=a['residual_stages'].astype(float)
 if not all_stages:x=x[:,4]
 w=head['weights'] if model=='4b' else head[f'weights_{view}_0.1'];m=head['train_center'] if model=='4b' else head[f'center_{view}'];b=head['bias']
 return np.einsum('lsd,ldc->lsc',norm(x)-m[:,None,:],w)+b if all_stages else np.einsum('ld,ldc->lc',norm(x)-m,w)+b
def evidence_type(items):
 if any(x['is_antecedent'] for x in items):return '既往史/风险资料'
 return '当前症状/体征资料'
def measurement_checks(records,cases,diseases):
 return dict(greedy_exact_label=summary([r['generated_disease']==c['gold_disease'] for r,c in zip(records,cases)]),greedy_listed=sum(r['generated_disease'] in diseases for r in records),canonical_mass_median=float(np.median([r['sequence_probability_mass'] for r in records])),canonical_mass_below_point1=sum(r['sequence_probability_mass']<.1 for r in records),sequence_tokenmean_agreement=summary([np.argmax(r['q_sequence'])==np.argmax(r['q_token_mean']) for r in records]),attention_max_error=max(r['attention_max_error'] for r in records))
