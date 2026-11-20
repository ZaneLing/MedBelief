"""Preselected 24-case name-string and unconstrained-generation interface control."""
from pathlib import Path
import json, time, argparse, re
import numpy as np
import mlx.core as mx
from mlx_lm.models.cache import KVCache, make_prompt_cache
from phase6_measure import ROOT, MODEL, load_model, SYSTEM
from phase1_run_direct import sha, write_json, greedy_answer

def render_name(row,tok):
    system=SYSTEM.replace('Compare the listed diagnoses','Assess the current presentation')
    lines=[f"Patient: age {row['age']} years; sex {row['sex']}.",'Cumulative findings:']
    for i,g in enumerate(row['revealed_groups']):
        lines.append(f'[Evidence group {i}: {g["question_group_id"]}]')
        lines += [x['question_en']+' Answer: '+x['answer_en']+'.' for x in g['items']]
    lines+=['Give only the single most likely diagnosis for the current presentation, without explanation.']
    p=tok.apply_chat_template([{'role':'system','content':system},{'role':'user','content':'\n'.join(lines)}],tokenize=False,add_generation_prompt=True,enable_thinking=False)+'Most likely diagnosis:'
    return p,tok.encode(p,add_special_tokens=False)

def clone(cache,N,batch=1):
    out=[]
    for src in cache:
        c=KVCache();k=src.keys[...,:N,:];v=src.values[...,:N,:]
        c.state=(mx.broadcast_to(k,(batch,)+k.shape[1:]),mx.broadcast_to(v,(batch,)+v.shape[1:]),N);out.append(c)
    return out

def soft(x):
    x=np.array(x,dtype=float);p=np.exp(x-x.max());return p/p.sum()

def log_softmax(x):
    shifted=x-mx.max(x,axis=-1,keepdims=True)
    return shifted-mx.logsumexp(shifted,axis=-1,keepdims=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--limit',type=int,default=0);args=ap.parse_args()
    run=ROOT/'runs/full49_v1';dest=run/'name_controls';dest.mkdir(exist_ok=True)
    jobs=[json.loads(s) for s in (ROOT/'data/full49_v1/jobs.public.jsonl').read_text().splitlines()]
    selected=[r for r in jobs if r['deep_capture'] and r['order']=='base' and r['round']==r['last_round'] and r['rotation']==0];assert len(selected)==24
    assert all((run/'observations'/f"{r['job_id']}.json").exists() for r in selected)
    manifest={'source_sha256':sha(__file__),'protocol_sha256':sha(ROOT/'protocol/FULL49_PHASES_6_8.md'),'cases':24,
              'sequence_score':'log P(space + canonical name + EOS | no-candidate prompt)',
              'length_sensitivity':'mean token log probability including EOS','free_generation_max_tokens':64,'candidate_order':selected[0]['candidate_diseases']}
    p=dest/'manifest.json'
    if p.exists():assert json.loads(p.read_text())==manifest
    else:write_json(p,manifest)
    model,tok=load_model();start=time.time();done=0
    for i,row in enumerate(selected):
        path=dest/f"{row['case_id']}.json"
        if path.exists():continue
        prompt,ids=render_name(row,tok);N=len(ids);cache=make_prompt_cache(model)
        first=model(mx.array([ids]),cache=cache)[0,-1].astype(mx.float32);mx.eval(first)
        initial=np.array(log_softmax(first));suffix=[]
        for d in row['candidate_diseases']:
            tokens=tok.encode(' '+d,add_special_tokens=False)
            assert tok.encode(prompt+' '+d,add_special_tokens=False)==ids+tokens
            suffix.append(tokens+[tok.eos_token_id])
        total=[];lengths=[];check=None
        for beg in range(0,49,7):
            batch=suffix[beg:beg+7];K=len(batch);L=max(map(len,batch));padded=np.full((K,L),tok.eos_token_id,dtype=np.int32)
            for j,s in enumerate(batch):padded[j,:len(s)]=s
            cc=clone(cache,N,K)
            z=model(mx.array(padded[:,:-1]),cache=cc).astype(mx.float32)
            lp=log_softmax(z);taken=mx.take_along_axis(lp,mx.array(padded[:,1:,None]),axis=-1)[:,:,0]
            mx.eval(taken);values=np.array(taken)
            for j,s in enumerate(batch):total.append(float(initial[s[0]]+values[j,:len(s)-1].sum()));lengths.append(len(s))
            # One non-batched full-prompt sequence calculation verifies shared-prefix scoring.
            if beg==0:
                s=batch[0];full=model(mx.array([ids+s[:-1]]))[0,N-1:].astype(mx.float32)
                direct=mx.take_along_axis(log_softmax(full),mx.array(s)[:,None],axis=-1).sum().item()
                check={'direct_log_probability':direct,'cached_log_probability':total[0],'absolute_error':abs(direct-total[0])}
                assert check['absolute_error']<.15,check
            del cc,z,lp,taken;mx.clear_cache()
        generated_ids,text,stop=greedy_answer(model,tok,first,clone(cache,N),limit=64)
        # Exact canonical match is deliberately distinct from clinically judged synonym matching.
        norm=lambda s:re.sub(r'[^a-z0-9]','',s.lower())
        exact=[d for d in row['candidate_diseases'] if norm(text)==norm(d)]
        write_json(path,{'case_id':row['case_id'],'family':row['family'],'input_tokens':N,'prompt':prompt,
                        'log_probability':total,'token_counts':lengths,'q_sequence':soft(total).tolist(),
                        'q_token_mean':soft(np.array(total)/lengths).tolist(),'free_text':text,'free_ids':generated_ids,
                        'free_stop':stop,'exact_canonical_match':exact[0] if len(exact)==1 else None,'cache_validation':check})
        del cache,first;mx.clear_cache();done+=1;print(json.dumps({'name_case':i+1,'total':24,'elapsed':time.time()-start}),flush=True)
        if args.limit and done>=args.limit:break
    if len(list(dest.glob('ddx*.json')))==24:
        hashes=json.loads((run/'manifest.json').read_text())['model_hashes'];assert {f:sha(MODEL/f) for f in hashes}==hashes
        write_json(dest/'completion.json',{'complete':True,'cases':24,'api_cost_usd':0})

if __name__=='__main__':main()
