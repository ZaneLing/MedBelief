"""Check quantized Qwen3 capture against its unmodified full forward pass."""
from pathlib import Path
import hashlib,json,os
os.environ['TOKENIZERS_PARALLELISM']='false'
import mlx.core as mx
import numpy as np
from mlx.utils import tree_map
from mlx_lm import load
from mlx_lm.models.base import create_attention_mask

ROOT=Path(__file__).resolve().parents[1]
def main():
    model,tok=load(str(ROOT/'.models/Qwen3-4B-8bit'))
    model.update(tree_map(lambda x:x.astype(mx.float16) if mx.issubdtype(x.dtype,mx.floating) else x,model.parameters()))
    mx.eval(model.parameters())
    rows=[json.loads(x) for x in (ROOT/'data/phase1b_development_defined.jsonl').read_text().splitlines()]
    checks=[]
    for r in rows:
        if r['mapping']!=0:continue
        ids=tok.apply_chat_template([{'role':'user','content':r['prompt']}],tokenize=True,add_generation_prompt=True,enable_thinking=True)
        x=mx.array([ids]);v=model(x)[0,-1].astype(mx.float32);mx.eval(v)
        h=model.model.embed_tokens(x);mask=create_attention_mask(h,None);states=[]
        for layer in model.model.layers:
            h=layer(h,mask,None);states.append(h[0,-1])
        manual=model.model.embed_tokens.as_linear(model.model.norm(h))[0,-1].astype(mx.float32)
        a=mx.stack(states);mx.eval(manual,a)
        delta=float(mx.max(mx.abs(v-manual)).item())
        assert delta<1e-5 and a.shape==(36,2560) and np.isfinite(np.array(a)).all()
        checks.append({'id':r['id'],'capture_logit_difference':delta,'activation_shape':list(a.shape),'tokens':len(ids)})
    p=ROOT/'runs/phase1b_4b_capture_check';p.mkdir(exist_ok=True)
    result={'checks':checks,'max_difference':max(x['capture_logit_difference'] for x in checks),'api_cost_usd':0,
            'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (p/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
