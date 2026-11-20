"""Frozen teacher-forced states for full-vocabulary adapter training; no test cases."""
from structure2_core import *
def extract(config,folder,depths):
    dest=RUN/'features'/folder;dest.mkdir(parents=True,exist_ok=True);cs=[c for c in cases() if c['cohort'] in ['train','development']]
    manifest=dict(configuration=config,cases=[c['case_id'] for c in cs],depths=depths,source_sha256=sha(ROOT/'src/phase94_structure2_features.py'),core_sha256=sha(ROOT/'src/structure2_core.py'),cases_sha256=sha(DATA/'cases.private.jsonl'))
    if (dest/'manifest.json').exists():assert read(dest/'manifest.json')==manifest
    else:write(dest/'manifest.json',manifest)
    model,tok=load_model();model=assemble(model,config);start=time.time();checks=[]
    for i,c in enumerate(cs):
        p=dest/(c['case_id']+'.npz')
        if p.exists():continue
        rr={k:[] for k in ['y','weight']+[f'x{l}' for l in depths]}
        for cond in ['neutral','wrong']:
            e=encode(c,tok,cond);suffix=e['suffix'][c['gold_index']];P=len(e['ids']);ids=e['ids']+suffix[:-1];ix=mx.array(np.arange(P-1,P-1+len(suffix)));h=model.model.embed_tokens(mx.array([ids]));mask=create_attention_mask(h,None)
            for l,b in enumerate(model.layers,1):
                h=b(h,mask,None)
                if l in depths:
                    x=model.model.norm(h[0,ix]);mx.eval(x);rr[f'x{l}'].append(np.array(x).astype(np.float16))
            weights=np.ones(len(suffix),np.float32)*.5/max(1,len(suffix)-1);weights[0]=.5;rr['weight'].append(weights);rr['y'].append(np.array(suffix,np.int32))
            if i==0:
                first=mx.array(rr[f'x{depths[-1]}'][-1][0]);zz=model.model.embed_tokens.as_linear(first).astype(mx.float32);native=prefill(model,e['ids'],make_prompt_cache(model));mx.eval(zz,native);diff=float(mx.max(mx.abs(zz-native)).item());same=int(mx.argmax(zz).item())==int(mx.argmax(native).item());assert diff<.2 and same;checks.append(dict(condition=cond,teacher_prefix_logit_error=diff,same_first_token=same))
            mx.clear_cache()
        np.savez(p,**{k:np.concatenate(v) for k,v in rr.items()})
        if i==0 or (i+1)%40==0:print(json.dumps(dict(features=folder,cases=i+1,total=len(cs),elapsed=round(time.time()-start,1))),flush=True)
    write(dest/'completion.json',dict(complete=True,cases=len(cs),teacher_prefix_checks=checks,parameter_stats=parameter_stats(model)));del model;mx.clear_cache()
def main():
    extract(dict(name='baseline'),'base',[20,24,28]);cfg=read(RUN/'pruning_selection.json')['selected']
    if cfg.get('exit_layer') in [20,24]:write(RUN/'features/pruned_alias.json',dict(folder='base',depth=cfg['exit_layer']))
    else:
        depth=28-len(cfg.get('drop_blocks',[]));extract(cfg,'pruned',[depth]);write(RUN/'features/pruned_alias.json',dict(folder='pruned',depth=depth))
if __name__=='__main__':main()
