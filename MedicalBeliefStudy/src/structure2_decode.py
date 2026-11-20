"""Separate candidate-trie decoding control, preserving the frozen core runner."""
from structure2_core import *

def constrained_generate(model,tok,e,limit=64):
    suffixes=e['suffix'];cache=make_prompt_cache(model);z=prefill(model,e['ids'],cache);mx.eval(z);prefix=[];stop='max_tokens';eos=set(tok.eos_token_ids)
    for _ in range(limit):
        allowed=sorted({s[len(prefix)] for s in suffixes if len(s)>len(prefix) and s[:len(prefix)]==prefix});assert allowed
        j=int(mx.argmax(z[mx.array(allowed)]).item());k=allowed[j]
        if k in eos:stop='eos';break
        prefix.append(k);z=prefill(model,[k],cache);mx.eval(z)
    text=tok.decode(prefix)
    try:d=json.loads('{"diagnosis":"'+text)['diagnosis']
    except (ValueError,TypeError,KeyError):d=None
    return dict(text=text,generated_disease=d,stop=stop,tokens=len(prefix),prompt_sha256=hashlib.sha256(e['prompt'].encode()).hexdigest())

def run_config(config,cohort,conditions=('neutral','wrong'),folder=None):
    if not config.get('constrained'):return run_cases(config,cohort,conditions,folder)
    dest=RUN/(folder or cohort)/config['name'];dest.mkdir(parents=True,exist_ok=True);cs=[c for c in cases() if c['cohort']==cohort]
    manifest=dict(configuration=config,cohort=cohort,cases=[c['case_id'] for c in cs],conditions=list(conditions),cases_sha256=sha(DATA/'cases.private.jsonl'),core_sha256=sha(ROOT/'src/structure2_core.py'),decoder_sha256=sha(ROOT/'src/structure2_decode.py'))
    if (dest/'manifest.json').exists():assert read(dest/'manifest.json')==manifest
    else:write(dest/'manifest.json',manifest)
    if all((dest/(c['case_id']+'.json')).exists() for c in cs):return
    model,tok=load_model();model=assemble(model,config);size=parameter_stats(model);start=time.time()
    for i,c in enumerate(cs):
        p=dest/(c['case_id']+'.json')
        if p.exists():continue
        rr=[]
        for cond in conditions:
            e=encode(c,tok,cond);o=constrained_generate(model,tok,e);rr.append(dict(condition=cond,correct=o['generated_disease']==c['gold_disease'],listed=o['generated_disease'] in c['candidates'],**o));mx.clear_cache()
        write(p,dict(case_id=c['case_id'],dataset=c['dataset'],configuration=config,parameter_stats=size,conditions=rr))
        if i==0 or (i+1)%20==0:print(json.dumps(dict(stage=folder or cohort,candidate=config['name'],case=i+1,total=len(cs),elapsed=round(time.time()-start,1))),flush=True)
    write(dest/'completion.json',dict(complete=True,cases=len(cs),generations=len(cs)*len(conditions),parameter_stats=size));del model;mx.clear_cache()

def grammar_configs():
    cfg=read(RUN/'pruning_selection.json')['selected']
    return [dict(name='baseline_constrained',constrained=True),dict(name='exit20_constrained',exit_layer=20,constrained=True),dict(cfg,name='pruned_constrained',constrained=True)]
