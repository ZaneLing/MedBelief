"""Analysis utilities, deliberately independent of MLX/GPU runtime."""
import collections,json
import numpy as np
from phase41_multisource_analyze import ROOT,DATA,read,write,csvwrite,stat,fmt
RUN=ROOT/'runs/structural_v1'
def js(q,p):
    q=np.maximum(np.array(q,float),1e-30);p=np.maximum(np.array(p,float),1e-30);m=(q+p)/2
    return float(.5*np.sum(q*np.log(q/m)+p*np.log(p/m)))
def load(split):
    src=RUN/split;spec=read(src/'manifest.json');cs={c['case_id']:c for c in map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines())};rows=[];sizes={}
    for cid in spec['cases']:
        c=cs[cid];g,w=c['gold_index'],c['wrong_index'];base=read(src/(cid+'_baseline.json'));bb={(r['condition'],r['rotation']):r for r in base['conditions']}
        for cfg in spec['candidates']:
            z=read(src/(cid+'_'+cfg['name']+'.json'));sizes[cfg['name']]=z['parameter_stats']
            for cond in ['neutral','wrong']:
                rr=[]
                for r in [r for r in z['conditions'] if r['condition']==cond]:
                    b=bb[cond,r['rotation']];q=np.array(r['q']);p=np.array(b['q']);pred=q.argmax();bp=p.argmax();ok=pred==g;bok=bp==g;lp=np.array(r['candidate_logits'])
                    rr.append(dict(accuracy=int(ok),strict_accuracy=int(ok and r['first_is_code']),accuracy_change=int(ok)-int(bok),strict_accuracy_change=int(ok and r['first_is_code'])-int(bok and b['first_is_code']),fidelity=int(pred==bp),js=js(q,p),gold_support=float(q[g]),wrong_support=float(q[w]),margin=float(lp[g]-lp[w]),candidate_mass=r['candidate_mass'],code_rate=int(r['first_is_code']),code_rate_change=int(r['first_is_code'])-int(b['first_is_code']),repaired=int(ok and not bok),damaged=int(bok and not ok)))
                rows.append(dict(case_id=cid,dataset=c['dataset'],condition=cond,candidate=cfg['name'],**{f:float(np.mean([r[f] for r in rr])) for f in rr[0]}))
    return rows,sizes,spec
def summarize(rows):
    rr=[]
    for name in dict.fromkeys(r['candidate'] for r in rows):
        for ds in ['all','MedQA','MedMCQA','MMLU']:
            for cond in ['neutral','wrong']:
                sub=[r for r in rows if r['candidate']==name and r['condition']==cond and (ds=='all' or r['dataset']==ds)]
                if not sub:continue
                rr.append(dict(candidate=name,dataset=ds,condition=cond,**{f:stat([r[f] for r in sub]) for f in ['accuracy','strict_accuracy','accuracy_change','strict_accuracy_change','fidelity','code_rate','candidate_mass','repaired','damaged']},js_mean=float(np.mean([r['js'] for r in sub]))))
    return rr

