"""All-layer/global-module and all-head/anchor deletion on 18 development cases."""
import argparse,time
from structural_v1_core import *

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--limit',type=int,default=0);args=ap.parse_args()
    screen,tune,test=groups();dest=DEST/'screen';dest.mkdir(exist_ok=True,parents=True)
    spec=dict(source_sha256=sha(__file__),core_sha256=sha(ROOT/'src/structural_v1_core.py'),cases_sha256=sha(DATA/'cases.private.jsonl'),protocol_sha256=sha(DOC/'PROTOCOL.md'),screen=[c['case_id'] for c in screen],tune=[c['case_id'] for c in tune],test=[c['case_id'] for c in test],api_cost_usd=0)
    if (dest/'manifest.json').exists():assert read(dest/'manifest.json')==spec
    else:write_json(dest/'manifest.json',spec)
    model,tok=load_model();start=time.time();done=0
    for ci,c in enumerate(screen):
        for cond in ['neutral','wrong']:
            for rot in [0,2]:
                key=f'{c["case_id"]}_{cond}_r{rot}';p=dest/(key+'.json')
                if p.exists():continue
                e=encoded(c,tok,cond,rot);ids=codes(e);rec,mask=capture(model,e);base=outcome(model,rec[-1]['post'][0,-1],ids,True)
                native=model(mx.array([e['ids']]))[0,-1].astype(mx.float32);nq=mx.softmax(native[mx.array(ids)]);mx.eval(nq);native_err=float(np.max(np.abs(np.array(nq)-base['q'])));assert native_err<.01
                rows=[];headrows=[];geometry=[];samples_x=[];samples_y=[];layers_q=[]
                pos=np.random.default_rng(int(rank(key)[:8],16)).choice(len(e['ids']),min(32,len(e['ids'])),replace=False);pos.sort();ix=mx.array(pos)
                sham_err=0.;sham_switches=0
                for l,r in enumerate(rec):
                    for kind in ['block','attention','mlp']:
                        h=resume_global(model,rec,mask,l,kind);o=outcome(model,h,ids);rows.append(dict(layer=l+1,kind=kind,**o));del h
                    labels,hs=anchor_branches(model,rec,l);o=outcome(model,hs,ids)
                    sham=np.array(o['q'][labels.index('sham')]);sham_err=max(sham_err,float(np.max(np.abs(sham-base['q']))));sham_switches+=int(sham.argmax()!=np.argmax(base['q']))
                    for j,label in enumerate(labels):headrows.append(dict(layer=l+1,component=label,q=o['q'][j],candidate_logits=o['candidate_logits'][j]))
                    mx.eval(r['pre'],r['post']);x=r['pre'][0].astype(mx.float32);y=r['post'][0].astype(mx.float32)
                    cos=(mx.sum(x*y,-1)/(mx.sqrt(mx.sum(x*x,-1)*mx.sum(y*y,-1))+1e-10));dx=mx.sqrt(mx.sum((y-x)**2,-1)/(mx.sum(x*x,-1)+1e-10));mx.eval(cos,dx)
                    geometry.append(dict(layer=l+1,block_influence=float(1-mx.mean(cos).item()),relative_update=float(mx.mean(dx).item()),attention=np.array(r['attention']).tolist()))
                    samples_x.append(np.array(r['mlp_input'][0,ix]));samples_y.append(np.array(r['mlp'][0,ix]));layers_q.append(outcome(model,r['post'][0,-1],ids)['q'])
                    del hs;mx.clear_cache()
                assert sham_err<.02,dict(sham_err=sham_err,key=key)
                arrays=dest/(key+'.npz');np.savez_compressed(arrays,x=np.stack(samples_x),y=np.stack(samples_y),positions=pos)
                write_json(p,dict(case_id=c['case_id'],dataset=c['dataset'],condition=cond,rotation=rot,prompt_sha256=hashlib.sha256(e['prompt'].encode()).hexdigest(),baseline=base,native_q_error=native_err,global_deletions=rows,anchor_deletions=headrows,geometry=geometry,layer_q=layers_q,sham_q_error=sham_err,sham_top_changes=sham_switches,samples_file=arrays.name))
                done+=1;print(json.dumps(dict(case=ci+1,total_cases=18,condition=cond,rotation=rot,seconds=round(time.time()-start,1),sham_q_error=sham_err)),flush=True)
                del rec,mask,native,nq;mx.clear_cache()
                if args.limit and done>=args.limit:return
    files=[p for p in dest.glob('*.json') if p.name not in ['manifest.json','completion.json']];assert len(files)==72
    write_json(dest/'completion.json',dict(complete=True,cases=18,prompts=72,global_deletions=72*28*3,anchor_deletions=72*28*19,anchor_shams=72*28,api_cost_usd=0))
if __name__=='__main__':main()
