"""Interleaved synchronized parameter and latency measurements on six fixed cases."""
from structure2_compat import *

def timed(model,tok,e,constrained=False):
    cache=make_prompt_cache(model);mx.synchronize();start=time.perf_counter();z=prefill(model,e['ids'],cache);mx.eval(z);mx.synchronize();pre=time.perf_counter()-start
    replay=(e['suffix'][0]+[tok.eos_token_id]*12)[:12];start=time.perf_counter()
    for k in replay:z=prefill(model,[k],cache);mx.eval(z)
    mx.synchronize();decode=time.perf_counter()-start
    mx.synchronize();start=time.perf_counter();o=(constrained_generate if constrained else generate)(model,tok,e);mx.synchronize();wall=time.perf_counter()-start
    return dict(prefill_seconds=pre,fixed12_decode_seconds=decode,actual_answer_seconds=wall,actual_tokens=o['tokens'],actual_stop=o['stop'])

def main():
    verify_amendment()
    spec=read(RUN/'confirmation_selection.json');dest=RUN/'timing';dest.mkdir(exist_ok=True);lookup={c['case_id']:c for c in cases()};ids=[]
    for ds in ['MedQA','MedMCQA']:ids += sorted([c['case_id'] for c in cases() if c['cohort']=='confirmation' and c['dataset']==ds],key=lambda c:rank(c+':timing'))[:3]
    write(dest/'manifest.json',dict(cases=ids,repetitions=2,conditions=['neutral','wrong'],selection_sha256=sha(RUN/'confirmation_selection.json'),fixed_decode='12 predetermined candidate0 suffix/EOS tokens, same for every model; no sampling and no candidate-trie bookkeeping in this kernel-only measurement.',actual_answer='End-to-end pretokenized autoregressive answer includes trie bookkeeping when used. Different output lengths reported.'))
    base,tok=load_model()
    for cfg in spec['configurations']:
        if cfg['name']=='baseline':continue
        p=dest/(cfg['name']+'.json')
        if p.exists():continue
        variant,_=load_model();variant=assemble(variant,cfg);rr=[];e=encode(lookup[ids[0]],tok);timed(base,tok,e);timed(variant,tok,e,cfg.get('constrained',False))
        for i,cid in enumerate(ids):
            for cond in ['neutral','wrong']:
                e=encode(lookup[cid],tok,cond)
                for rep in range(2):
                    if (i+rep)%2:
                        b=timed(variant,tok,e,cfg.get('constrained',False));a=timed(base,tok,e)
                    else:a=timed(base,tok,e);b=timed(variant,tok,e,cfg.get('constrained',False))
                    rr.append(dict(case_id=cid,condition=cond,repetition=rep,baseline=a,variant=b,ratios={f:b[f]/a[f] for f in ['prefill_seconds','fixed12_decode_seconds','actual_answer_seconds']}))
        write(p,dict(configuration=cfg,parameter_stats=parameter_stats(variant),baseline_parameter_stats=parameter_stats(base),trials=rr));print(json.dumps(dict(timing=cfg['name'],pairs=len(rr))),flush=True);del variant;mx.clear_cache()
    write(dest/'completion.json',dict(complete=True,cases=6,configurations=len(spec['configurations'])-1,paired_trials=(len(spec['configurations'])-1)*24,api_cost_usd=0))
if __name__=='__main__':main()
