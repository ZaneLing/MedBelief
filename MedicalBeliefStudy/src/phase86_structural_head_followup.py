"""Unselected 130 cases: independently test selected heads and matched controls."""
import time
from mlx_lm.models.cache import make_prompt_cache
from phase1_run_direct import greedy_answer
from structural_v1_variants import *
from structural_v1_sustained import materialize_followup,numerical_control

def main():
    dest=DEST/'followup';spec=read(dest/'spec.json');lookup={c['case_id']:c for c in cases()};cs=[lookup[cid] for cid in spec['cases']];assert len(cs)==130
    manifest=dict(cases=spec['cases'],candidates=spec['candidates'],source_sha256=sha(__file__),variants_sha256=sha(ROOT/'src/structural_v1_variants.py'),sustained_sha256=sha(ROOT/'src/structural_v1_sustained.py'),spec_sha256=sha(dest/'spec.json'),api_cost_usd=0)
    if (dest/'manifest.json').exists():assert read(dest/'manifest.json')==manifest
    else:write_json(dest/'manifest.json',manifest)
    if not (dest/'numerical_control.json').exists():write_json(dest/'numerical_control.json',numerical_control(cs[0],spec['candidates'][1]))
    start=time.time()
    for cfg in spec['candidates']:
        paths=[dest/(c['case_id']+'_'+cfg['name']+'.json') for c in cs]
        if all(p.exists() for p in paths):continue
        model,tok=load_model();model=materialize(model,cfg);size=parameter_stats(model)
        for i,(c,p) in enumerate(zip(cs,paths)):
            if p.exists():continue
            rr=[]
            for cond in ['neutral','wrong']:
                for rot in [0,2]:
                    e=encoded(c,tok,cond,rot);o=score(model,e,True)
                    if i==0:
                        z=model(mx.array([e['ids']]))[0,-1].astype(mx.float32);q=mx.softmax(z[mx.array(codes(e))]);mx.eval(q);err=float(np.max(np.abs(np.array(q)-o['q'])));assert err<.01;o['native_q_error']=err
                    rr.append(dict(condition=cond,rotation=rot,prompt_sha256=hashlib.sha256(e['prompt'].encode()).hexdigest(),**o));mx.clear_cache()
            write_json(p,dict(case_id=c['case_id'],dataset=c['dataset'],candidate=cfg['name'],configuration=cfg,parameter_stats=size,conditions=rr))
            if i==0 or (i+1)%20==0:print(json.dumps(dict(kind='code',candidate=cfg['name'],cases=i+1,total=130,elapsed=round(time.time()-start,1))),flush=True)
        del model;mx.clear_cache()
    positive=dest/'gold_control';positive.mkdir(exist_ok=True)
    for cfg in [v for v in spec['candidates'] if v['name'] in spec['gold_control']['candidates']]:
        paths=[positive/(c['case_id']+'_'+cfg['name']+'.json') for c in cs]
        if all(p.exists() for p in paths):continue
        model,tok=load_model();model=materialize(model,cfg)
        for i,(c,p) in enumerate(zip(cs,paths)):
            if p.exists():continue
            rr=[]
            for rot in [0,2]:
                e=encoded(c,tok,'gold',rot);o=score(model,e,True);rr.append(dict(condition='gold',rotation=rot,prompt_sha256=hashlib.sha256(e['prompt'].encode()).hexdigest(),**o));mx.clear_cache()
            write_json(p,dict(case_id=c['case_id'],dataset=c['dataset'],candidate=cfg['name'],conditions=rr))
            if i==0 or (i+1)%20==0:print(json.dumps(dict(kind='oracle_gold_control',candidate=cfg['name'],cases=i+1,total=130,elapsed=round(time.time()-start,1))),flush=True)
        del model;mx.clear_cache()
    gen=dest/'generation';gen.mkdir(exist_ok=True)
    for cfg in spec['generation_configs']:
        paths=[gen/(c['case_id']+'_'+cfg['name']+'.json') for c in cs]
        if all(p.exists() for p in paths):continue
        model,tok=load_model();model=materialize_followup(model,cfg)
        for i,(c,p) in enumerate(zip(cs,paths)):
            if p.exists():continue
            rr=[];T=len(c['sentences'])
            for cond in ['neutral','wrong']:
                e=render(c,dict(condition=cond,mode='name',rotation=0,round=T,last_round=T,order='base'),tok);cache=make_prompt_cache(model);z=model(mx.array([e['ids']]),cache=cache)[0,-1].astype(mx.float32);mx.eval(z);tokens,text,stop=greedy_answer(model,tok,z,cache,limit=64)
                try:d=json.loads('{"diagnosis":"'+text)['diagnosis']
                except (ValueError,TypeError,KeyError):d=None
                rr.append(dict(condition=cond,generated_disease=d,text=text,stop=stop,correct=d==c['gold_disease'],listed=d in c['candidates'],tokens=len(tokens),prompt_sha256=hashlib.sha256(e['prompt'].encode()).hexdigest()))
                del z,cache;mx.clear_cache()
            write_json(p,dict(case_id=c['case_id'],dataset=c['dataset'],candidate=cfg['name'],conditions=rr))
            if i==0 or (i+1)%20==0:print(json.dumps(dict(kind='name',candidate=cfg['name'],cases=i+1,total=130,elapsed=round(time.time()-start,1))),flush=True)
        del model;mx.clear_cache()
    write_json(dest/'completion.json',dict(complete=True,cases=130,code_configurations=5,code_conditions=2600,oracle_gold_code_conditions=520,name_configurations=3,actual_generations=780,api_cost_usd=0))

if __name__=='__main__':main()
