"""Resumable local medical-evidence experiments with independent per-trial RNG."""
from pathlib import Path
import argparse,hashlib,importlib.metadata,json,os,re,time
os.environ['TOKENIZERS_PARALLELISM']='false'
import numpy as np
import mlx.core as mx
from mlx.utils import tree_map
from mlx_lm import load
from mlx_lm.generate import BatchGenerator
from mlx_lm.sample_utils import apply_top_p,apply_top_k
from mlx_lm.models.base import create_attention_mask

ROOT=Path(__file__).resolve().parents[1]

class TrialSampler:
    """Official top-p then top-k filters, with an explicit independent RNG key."""
    def __init__(self,seed,trial_id,thinking):
        self.prefix=f'{seed}:{trial_id}:';self.step=0;self.thinking=thinking
    def __call__(self,logprobs):
        if not self.thinking:return mx.argmax(logprobs,axis=-1)
        digest=hashlib.sha256((self.prefix+str(self.step)).encode()).digest();self.step+=1
        key=mx.array([int.from_bytes(digest[:4],'little'),int.from_bytes(digest[4:8],'little')],dtype=mx.uint32)
        filtered=apply_top_k(apply_top_p(logprobs,0.95),20)
        return mx.random.categorical(filtered/0.6,key=key)

def parse_final(text,thinking=True):
    closed='</think>' in text
    if thinking and not closed:return None,False
    tail=text.rsplit('</think>',1)[-1].replace('<|im_end|>','').strip()
    tail=tail.replace('**','').replace('`','').strip()
    pattern=r'(?:(?:final\s+answer|answer|final)\s*:\s*)?(?:([ABC])[.]?|\\boxed\{([ABC])\})'
    match=re.fullmatch(pattern,tail,flags=re.I)
    if match:return next((g.upper() for g in match.groups() if g),None),closed
    # Read explicit answer declarations outside the thinking block; never scan
    # arbitrary reasoning for candidate letters. Contradictory declarations fail.
    declarations=re.findall(r'(?im)^(?:final\s+answer|answer)\s*:\s*([ABC])\b',tail)
    leading=re.match(r'^([ABC])[:.)](?:\s|$)',tail)
    if leading:declarations.append(leading.group(1))
    choices={x.upper() for x in declarations}
    return (next(iter(choices)) if len(choices)==1 else None),closed

def capture(model,ids):
    h=model.model.embed_tokens(mx.array([ids]));mask=create_attention_mask(h,None);states=[]
    for layer in model.model.layers:
        h=layer(h,mask,None);states.append(h[0,-1])
    a=mx.stack(states).astype(mx.float16);mx.eval(a)
    return np.array(a)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',required=True);ap.add_argument('--run-id',required=True)
    ap.add_argument('--seed',type=int,default=20261118);ap.add_argument('--max-tokens',type=int,default=1536)
    ap.add_argument('--batch-size',type=int,default=8);ap.add_argument('--capture',action='store_true');ap.add_argument('--no-thinking',action='store_true')
    ap.add_argument('--model-dir',default='.models/Qwen3-1.7B');ap.add_argument('--model-manifest',default='protocol/model_snapshot.json')
    args=ap.parse_args();thinking=not args.no_thinking
    data=ROOT/args.data;rows=[json.loads(x) for x in data.read_text().splitlines()]
    assert len({r['id'] for r in rows})==len(rows)
    run=ROOT/'runs'/args.run_id;run.mkdir(exist_ok=True);state_dir=run/'states';state_dir.mkdir(exist_ok=True)
    snapshot=json.loads((ROOT/args.model_manifest).read_text());model_config=json.loads((ROOT/args.model_dir/'config.json').read_text())
    config={'data':args.data,'data_sha256':hashlib.sha256(data.read_bytes()).hexdigest(),'seed':args.seed,'thinking':thinking,'max_tokens':args.max_tokens,
        'batch_size':args.batch_size,'capture':args.capture,'capture_position':'last prompt token, before any answer or thinking generation',
        'model':snapshot['id'],'revision':snapshot['sha'],'model_dir':args.model_dir,
        'dtype':'floating tensors cast to float16; packed integer tensors preserved','source_quantization':model_config.get('quantization',None),
        'sampler':'independent SHA256-derived per-trial/per-token key; top_p=.95, top_k=20, temperature=.6; greedy if thinking disabled',
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'packages':{p:importlib.metadata.version(p) for p in ['mlx','mlx-lm','transformers','numpy','tokenizers']},'api_cost_usd':0}
    conf=run/'metadata.json'
    if conf.exists():assert json.loads(conf.read_text())==config,'Use a new run ID after changing configuration or code'
    else:
        conf.write_text(json.dumps(config,indent=2)+'\n')
        (run/'source_snapshot.py').write_bytes(Path(__file__).read_bytes())
    existing=[];result_file=run/'predictions.jsonl'
    if result_file.exists():existing=[json.loads(x) for x in result_file.read_text().splitlines()]
    done={r['id'] for r in existing};todo=[r for r in rows if r['id'] not in done]
    if not todo:print('Already complete');return
    model,tok=load(str(ROOT/args.model_dir))
    model.update(tree_map(lambda x:x.astype(mx.float16) if mx.issubdtype(x.dtype,mx.floating) else x,model.parameters()));mx.eval(model.parameters())
    prompts=[]
    for n,r in enumerate(todo):
        messages=r.get('messages',[{'role':'user','content':r['prompt']}])
        ids=tok.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,enable_thinking=thinking)
        prompts.append(ids)
        if args.capture:
            path=state_dir/(r['id']+'.npz')
            if not path.exists():
                a=capture(model,ids);assert a.shape==(model_config['num_hidden_layers'],model_config['hidden_size']) and np.isfinite(a).all()
                np.savez_compressed(path,activations=a,input_ids=np.array(ids),id=r['id'])
        if (n+1)%48==0:print(json.dumps({'prepared':n+1,'total':len(todo)}),flush=True)
    gen=BatchGenerator(model,stop_tokens=[[t] for t in tok.eos_token_ids],completion_batch_size=args.batch_size,prefill_batch_size=min(2,args.batch_size))
    uids=gen.insert(prompts,max_tokens=[args.max_tokens]*len(todo),samplers=[TrialSampler(args.seed,r['id'],thinking) for r in todo])
    lookup=dict(zip(uids,todo));tokens={u:[] for u in uids};start=time.time()
    with result_file.open('a',buffering=1) as fp:
        while responses:=gen.next_generated():
            for response in responses:
                uid=response.uid
                if response.finish_reason!='stop':tokens[uid].append(response.token)
                if response.finish_reason is None:continue
                r=lookup[uid];text=tok.decode(tokens[uid]);letter,closed=parse_final(text,thinking)
                prediction={v:k for k,v in r['labels'].items()}.get(letter) if response.finish_reason=='stop' else None
                result={**{k:v for k,v in r.items() if k not in ['prompt','messages','record']},'prediction':prediction,'letter':letter,
                    'generated_text':text,'generated_tokens':len(tokens[uid]),'finish_reason':response.finish_reason,'thinking_closed':closed,
                    'valid_final_format':letter is not None,'seed':args.seed,'activation_file':f'states/{r["id"]}.npz' if args.capture else None}
                fp.write(json.dumps(result)+'\n');existing.append(result)
                if len(existing)%12==0:print(json.dumps({'completed':len(existing),'total':len(rows),'elapsed_sec':round(time.time()-start,1)}),flush=True)
    gen.close();assert len(existing)==len(rows)
    summary={'complete':True,'records':len(existing),'correct':sum(r['prediction']==r.get('gold') for r in existing),
        'parse_or_budget_failures':sum(r['prediction'] is None for r in existing),'generation_tokens':sum(r['generated_tokens'] for r in existing),
        'generation_elapsed_this_invocation_sec':time.time()-start,'api_cost_usd':0}
    (run/'completion.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()
