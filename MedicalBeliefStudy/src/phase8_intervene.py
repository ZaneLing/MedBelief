"""Frozen middle-round interventions and nonclinical-content controls on full49."""
from pathlib import Path
import argparse, json, time
import numpy as np
import mlx.core as mx
from phase6_measure import ROOT, MODEL, load_model, render, capture
from phase1_run_direct import scores, sha, write_json
from content_and_depth import replay_anchor

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-id',default='full49_v1');ap.add_argument('--limit',type=int,default=0)
    args=ap.parse_args();run=ROOT/'runs'/args.run_id
    assert (run/'completion.json').exists()
    for name in ['content_controls','depth_interventions']:(run/name).mkdir(exist_ok=True)
    jobs=[json.loads(s) for s in (ROOT/'data/full49_v1/jobs.public.jsonl').read_text().splitlines()]
    lookup={(j['case_id'],j['order'],j['round'],j['rotation']):j for j in jobs}
    selected=[j for j in jobs if j['order']=='base' and j['round']==j['last_round']//2 and j['rotation'] in [0,16]]
    assert len(selected)==240
    spec={'prefixes':len(selected),'layers':[24,25,26,27,28],'source_sha256':sha(__file__),
          'measurement_source_sha256':sha(ROOT/'src/phase6_measure.py'),
          'protocol_sha256':sha(ROOT/'protocol/FULL49_PHASES_6_8.md'),'observations_manifest_sha256':sha(run/'manifest.json')}
    for name in ['content_controls','depth_interventions']:
        p=run/name/'manifest.json'
        if p.exists():assert json.loads(p.read_text())==spec
        else:write_json(p,spec)
    model,tok=load_model();start=time.time();done=0
    for index,row in enumerate(selected):
        oid=row['job_id'];content_path=run/'content_controls'/f'{oid}.json'
        paths=[run/'depth_interventions'/f'{oid}_l{l}.json' for l in range(24,29)]
        if content_path.exists() and all(p.exists() for p in paths):continue
        oldrow=lookup[row['case_id'],'base',row['round']-1,row['rotation']]
        current=render(row,tok);previous=render(oldrow,tok);cids=current['candidate_ids']
        curarrays,curz,cache=capture(model,current['ids'],current['token_groups'],keep_cache=True)
        oldarrays,oldz,_=capture(model,previous['ids'],previous['token_groups'])
        bz,bp,bq=scores(curz,cids);_,op,oq=scores(oldz,cids)
        if not content_path.exists():
            conditions=[]
            admin={'question_group_id':'ADMIN','items':[{'question_en':'Record handling:',
                   'answer_en':"The entries above have been placed in the same patient's research file. No additional clinical information is provided"}]}
            repeat={**oldrow['revealed_groups'][0],'question_group_id':'REPEAT_INITIAL'}
            for label,extra in [('administrative',admin),('repeat_initial',repeat)]:
                newrow={**oldrow,'revealed_groups':oldrow['revealed_groups']+[extra]}
                encoded=render(newrow,tok);arrays,z,_=capture(model,encoded['ids'],encoded['token_groups'])
                _,p,q=scores(z,cids)
                path=run/'content_controls'/f'{oid}_{label}.npz'
                np.savez_compressed(path,**{k:np.array(v) for k,v in arrays.items()},input_ids=np.array(encoded['ids']),token_groups=encoded['token_groups'])
                conditions.append({'condition':label,'q':q.tolist(),'candidate_mass':float(p.sum()),'input_tokens':len(encoded['ids']),
                                   'group_labels':encoded['group_labels'],'state_file':str(path.relative_to(run))})
                del arrays
            write_json(content_path,{'job_id':oid,'case_id':row['case_id'],'family':row['family'],'rotation':row['rotation'],
                                     'previous_q':oq.tolist(),'real_q':bq.tolist(),'previous_tokens':len(previous['ids']),
                                     'real_tokens':len(current['ids']),'conditions':conditions})
        curstates=curarrays['residual_stages'];oldstates=oldarrays['residual_stages']
        for layer,path in zip(range(23,28),paths):
            if path.exists():continue
            pre,att,mid,mlp,post=[curstates[layer,j] for j in range(5)]
            oa=oldstates[layer,1];om=oldstates[layer,3];block=model.model.layers[layer]
            mids=mx.stack([pre+oa,pre+att+mx.roll(oa-att,257)])
            posts=mids+block.mlp(block.post_attention_layernorm(mids))
            hs=mx.stack([post,posts[0],mid+om,posts[1],mid+mlp+mx.roll(om-mlp,257)])
            end=replay_anchor(model,hs,layer,cache,len(current['ids']));z,p,q=scores(end,cids)
            stable=bool(np.allclose(z[0],bz,atol=1e-3,rtol=1e-3) and q[0].argmax()==bq.argmax())
            write_json(path,{'job_id':oid,'case_id':row['case_id'],'family':row['family'],'rotation':row['rotation'],
                       'round':row['round'],'layer':layer+1,'previous_q':oq.tolist(),'current_q':bq.tolist(),
                       'components':['sham','previous_attention','previous_mlp','shifted_attention_difference','shifted_mlp_difference'],
                       'q':q.tolist(),'candidate_mass':p.sum(-1).tolist(),'numerically_stable':stable,
                       'sham_max_candidate_logit_error':float(np.abs(z[0]-bz).max())})
        del curarrays,oldarrays,curstates,oldstates,cache;mx.clear_cache();done+=1
        if done==1 or done%10==0:print(json.dumps({'prefix':index+1,'total':240,'elapsed':round(time.time()-start,1)}),flush=True)
        if args.limit and done>=args.limit:break
    if all((run/'content_controls'/f"{r['job_id']}.json").exists() for r in selected):
        write_json(run/'content_controls/completion.json',{'complete':True,'prefixes':240,'new_control_forwards':480,'api_cost_usd':0})
    if len(list((run/'depth_interventions').glob('ddx*.json')))==1200:
        write_json(run/'depth_interventions/completion.json',{'complete':True,'prefix_depth_records':1200,'api_cost_usd':0})
    original=json.loads((run/'manifest.json').read_text())['model_hashes']
    assert {name:sha(MODEL/name) for name in original}==original

if __name__=='__main__':main()
