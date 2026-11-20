from pathlib import Path
import json,time,importlib.metadata,platform,os
os.environ['TOKENIZERS_PARALLELISM']='false'
import numpy as np
import mlx.core as mx
from mlx.utils import tree_map
from mlx_lm import load
from mlx_lm.generate import batch_generate
from mlx_lm.sample_utils import make_sampler
from mlx_lm.models.base import create_attention_mask

ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'runs/phase1b_mlx_check';out.mkdir(exist_ok=True)
model,tok=load(str(ROOT/'.models/Qwen3-1.7B'))
model.update(tree_map(lambda x:x.astype(mx.float16),model.parameters()));mx.eval(model.parameters())
rows=[r for r in map(json.loads,(ROOT/'data/phase1_cases.jsonl').read_text().splitlines()) if r['base_id'].endswith('_00') and r['prior']=='none' and r['mapping']==0 and r['stage']=='evidence']
primary={r['record_id']:r for r in map(json.loads,(ROOT/'runs/phase1_qwen3_1p7b/predictions.jsonl').read_text().splitlines())}
checks=[]
for r in rows:
    ids=tok.apply_chat_template([{'role':'user','content':r['prompt']}],tokenize=True,add_generation_prompt=True,enable_thinking=False)
    z=np.load(ROOT/'runs/phase1_qwen3_1p7b'/primary[r['record_id']]['activation_file'])
    assert np.array_equal(ids,z['input_ids']), 'Tokenizer changed'
    x=mx.array([ids]);tick=time.time();v=model(x)[0,-1].astype(mx.float32);mx.eval(v)
    p=mx.softmax(v);probs={s:float(p[tok.encode(c,add_special_tokens=False)[0]].item()) for s,c in r['label_tokens'].items()};mass=sum(probs.values());probs={k:v/mass for k,v in probs.items()}
    h=model.model.embed_tokens(x);mask=create_attention_mask(h,None);states=[]
    for layer in model.model.layers:
        h=layer(h,mask,None);states.append(h[0,-1])
    h=model.model.norm(h)
    captured=model.model.embed_tokens.as_linear(h)[0,-1].astype(mx.float32)
    mx.eval(captured,*states)
    diff=float(mx.max(mx.abs(captured-v)).item())
    assert diff<1e-5,('capture changes logits',diff)
    np.savez_compressed(out/(r['record_id']+'.npz'),states=np.array(mx.stack(states)))
    checks.append({'record_id':r['record_id'],'gold':r['gold'],'prediction':max(probs,key=probs.get),'primary_prediction':primary[r['record_id']]['prediction'],'probs':probs,'primary_probs':primary[r['record_id']]['semantic_probs'],'capture_logit_difference':diff,'seconds':time.time()-tick})
(out/'paired_scores.json').write_text(json.dumps(checks,indent=2)+'\n')
prompts=[];selected=[r for r in rows if not r['positive_report']]
for r in selected:prompts.append(tok.apply_chat_template([{'role':'user','content':r['prompt']}],tokenize=True,add_generation_prompt=True,enable_thinking=True))
mx.random.seed(20261118);tick=time.time()
generated=batch_generate(model,tok,prompts,max_tokens=1536,return_token_ids=True,sampler=make_sampler(temp=0.6,top_p=0.95,top_k=20),completion_batch_size=4,prefill_batch_size=2)
g=[{'record_id':r['record_id'],'gold':'B','generated_text':text,'tokens':len(ids)} for r,text,ids in zip(selected,generated.texts,generated.token_ids)]
(out/'thinking_generations.json').write_text(json.dumps(g,indent=2)+'\n')
summary={'packages':{p:importlib.metadata.version(p) for p in ['mlx','mlx-lm','transformers','numpy','tokenizers']},'architecture':platform.machine(),'weights_dtype':'float16; no quantization','score_checks':len(checks),'decision_changes':sum(r['prediction']!=r['primary_prediction'] for r in checks),'max_capture_logit_difference':max(r['capture_logit_difference'] for r in checks),'generation_seconds':time.time()-tick,'generated_tokens':sum(x['tokens'] for x in g),'api_cost_usd':0}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2),flush=True)
