"""Evaluate physically assembled candidates; freeze holdout configs first."""
import argparse,time
from structural_v1_variants import *
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--split',choices=['tune','test'],required=True);ap.add_argument('--limit',type=int,default=0);args=ap.parse_args()
    screen,tune,test=groups();cs=tune if args.split=='tune' else test
    selection=DEST/('development_candidates.json' if args.split=='tune' else 'selected.json');spec=read(selection);configs=spec['candidates'];dest=DEST/args.split;dest.mkdir(exist_ok=True)
    manifest=dict(split=args.split,cases=[c['case_id'] for c in cs],candidates=configs,selection_sha256=sha(selection),source_sha256=sha(__file__),variants_sha256=sha(ROOT/'src/structural_v1_variants.py'),api_cost_usd=0)
    if (dest/'manifest.json').exists():assert read(dest/'manifest.json')==manifest
    else:write_json(dest/'manifest.json',manifest)
    start=time.time();sizes=[]
    for config in configs:
        paths=[dest/(c['case_id']+'_'+config['name']+'.json') for c in cs]
        if all(p.exists() for p in paths):continue
        model,tok=load_model();model=materialize(model,config);size=parameter_stats(model);sizes.append(dict(name=config['name'],**size))
        for i,(c,p) in enumerate(zip(cs,paths)):
            if p.exists():continue
            rows=[]
            for cond in ['neutral','wrong']:
                for rot in [0,2]:
                    e=encoded(c,tok,cond,rot);o=score(model,e,True)
                    if i==0:
                        z=model(mx.array([e['ids']]))[0,-1].astype(mx.float32);q=mx.softmax(z[mx.array(codes(e))]);mx.eval(q);err=float(np.max(np.abs(np.array(q)-o['q'])));assert err<.01;o['native_q_error']=err
                    rows.append(dict(condition=cond,rotation=rot,prompt_sha256=hashlib.sha256(e['prompt'].encode()).hexdigest(),**o))
                    mx.clear_cache()
            write_json(p,dict(case_id=c['case_id'],dataset=c['dataset'],candidate=config['name'],configuration=config,parameter_stats=size,conditions=rows))
            if i==0 or (i+1)%20==0:print(json.dumps(dict(split=args.split,configuration=config['name'],cases=i+1,total=len(cs),elapsed=round(time.time()-start,1))),flush=True)
            if args.limit and i+1>=args.limit:return
        del model;mx.clear_cache()
    assert all((dest/(c['case_id']+'_'+v['name']+'.json')).exists() for c in cs for v in configs)
    write_json(dest/'completion.json',dict(complete=True,cases=len(cs),configurations=len(configs),conditions=4*len(cs)*len(configs),api_cost_usd=0))
if __name__=='__main__':main()
