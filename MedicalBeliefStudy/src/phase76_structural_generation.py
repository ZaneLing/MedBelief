"""Cross-interface check: actual complete disease-name generation, 60 held-out cases."""
import time
from mlx_lm.models.cache import make_prompt_cache
from phase1_run_direct import greedy_answer
from structural_v1_variants import *
def main():
    _,_,test=groups();cs=[]
    for ds in ['MedQA','MedMCQA','MMLU']:cs+=sorted([c for c in test if c['dataset']==ds],key=lambda c:rank(c['case_id']+':generation'))[:20]
    configs=read(DEST/'selected.json')['candidates'];dest=DEST/'generation';dest.mkdir(exist_ok=True)
    spec=dict(cases=[c['case_id'] for c in cs],candidates=configs,source_sha256=sha(__file__),selection_sha256=sha(DEST/'selected.json'),limit=64,api_cost_usd=0)
    if (dest/'manifest.json').exists():assert read(dest/'manifest.json')==spec
    else:write_json(dest/'manifest.json',spec)
    start=time.time()
    for config in configs:
        paths=[dest/(c['case_id']+'_'+config['name']+'.json') for c in cs]
        if all(p.exists() for p in paths):continue
        model,tok=load_model();model=materialize(model,config)
        for i,(c,p) in enumerate(zip(cs,paths)):
            if p.exists():continue
            rr=[];T=len(c['sentences'])
            for cond in ['neutral','wrong']:
                e=render(c,dict(condition=cond,mode='name',rotation=0,round=T,last_round=T,order='base'),tok);cache=make_prompt_cache(model)
                z=model(mx.array([e['ids']]),cache=cache)[0,-1].astype(mx.float32);mx.eval(z)
                tokens,text,stop=greedy_answer(model,tok,z,cache,limit=64)
                try:d=json.loads('{"diagnosis":"'+text)['diagnosis']
                except (ValueError,TypeError,KeyError):d=None
                rr.append(dict(condition=cond,generated_disease=d,text=text,stop=stop,correct=d==c['gold_disease'],listed=d in c['candidates'],tokens=len(tokens),prompt_sha256=hashlib.sha256(e['prompt'].encode()).hexdigest()))
                del z,cache;mx.clear_cache()
            write_json(p,dict(case_id=c['case_id'],dataset=c['dataset'],candidate=config['name'],conditions=rr))
            if i==0 or (i+1)%20==0:print(json.dumps(dict(candidate=config['name'],cases=i+1,total=60,elapsed=round(time.time()-start,1))),flush=True)
        del model;mx.clear_cache()
    write_json(dest/'completion.json',dict(complete=True,cases=60,configurations=len(configs),actual_generations=120*len(configs),api_cost_usd=0))
if __name__=='__main__':main()

