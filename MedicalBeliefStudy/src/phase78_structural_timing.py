"""Paired synchronized latency; actual materialized models, no inferred speedups."""
import time
from structural_v1_variants import *
def elapsed(model,e):
    start=time.perf_counter();h=last_hidden(model,e);z=output_head(model,h);mx.eval(z);return time.perf_counter()-start
def main():
    _,_,test=groups();cs=[]
    for ds in ['MedQA','MedMCQA','MMLU']:cs+=sorted([c for c in test if c['dataset']==ds],key=lambda c:rank(c['case_id']+':timing'))[:2]
    configs=read(DEST/'selected.json')['candidates'];dest=DEST/'timing';dest.mkdir(exist_ok=True)
    spec=dict(cases=[c['case_id'] for c in cs],candidates=configs,source_sha256=sha(__file__),paired_repetitions=3,warmups=3,metric='prefill of pretokenized code prompt and final full-vocabulary head; synchronous mx.eval; no generation',device=mx.device_info(),api_cost_usd=0)
    if (dest/'manifest.json').exists():assert read(dest/'manifest.json')==spec
    else:write_json(dest/'manifest.json',spec)
    for ci,config in enumerate(configs):
        if config['name']=='baseline':continue
        p=dest/(config['name']+'.json')
        if p.exists():continue
        base,tok=load_model();model,_=load_model();model=materialize(model,config);inputs=[(c,cond,encoded(c,tok,cond,0)) for c in cs for cond in ['neutral','wrong']]
        for _ in range(3):elapsed(base,inputs[0][2]);elapsed(model,inputs[0][2])
        rr=[];rng=np.random.default_rng(7800+ci)
        for c,cond,e in inputs:
            for rep in range(3):
                order=['baseline','variant'] if rng.integers(2) else ['variant','baseline'];times={}
                for name in order:times[name]=elapsed(base if name=='baseline' else model,e)
                rr.append(dict(case_id=c['case_id'],condition=cond,repeat=rep,input_tokens=len(e['ids']),order=order,baseline_seconds=times['baseline'],variant_seconds=times['variant'],ratio=times['variant']/times['baseline']))
        write_json(p,dict(candidate=config['name'],parameter_stats=parameter_stats(model),baseline_parameters=parameter_stats(base),trials=rr));print(json.dumps(dict(candidate=config['name'],median_ratio=float(np.median([r['ratio'] for r in rr])))),flush=True)
        del base,model;mx.clear_cache()
    write_json(dest/'completion.json',dict(complete=True,cases=6,paired_trials=(len(configs)-1)*36,configurations=len(configs)-1,api_cost_usd=0))
if __name__=='__main__':main()

