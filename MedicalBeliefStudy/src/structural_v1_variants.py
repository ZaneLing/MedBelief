"""Real module removal/replacement and a separate diagnostic-position head gate."""
import mlx.nn as nn
from mlx.utils import tree_flatten
from structural_v1_core import *

class AttentionOnly(nn.Module):
    def __init__(self,b):
        super().__init__();self.self_attn=b.self_attn;self.input_layernorm=b.input_layernorm
    def __call__(self,x,mask=None,cache=None):return x+self.self_attn(self.input_layernorm(x),mask,cache)

class LowRankMLP(nn.Module):
    def __init__(self,r):
        super().__init__()
        for k in ['xmean','ymean','left','right']:setattr(self,k,mx.array(r[k],dtype=mx.float32))
    def __call__(self,x):return (((x.astype(mx.float32)-self.xmean)@self.left)@self.right+self.ymean).astype(x.dtype)

class AnchorGate(nn.Module):
    def __init__(self,a,heads):
        super().__init__();self.original=a;self.drop=tuple(h-1 for h in heads)
    def __call__(self,x,mask=None,cache=None):
        a=self.original;B,N,_=x.shape;offset=cache.offset if cache is not None else 0
        if offset or N==1:return a(x,mask,cache)
        q=a.q_norm(a.q_proj(x).reshape(B,N,a.n_heads,-1)).transpose(0,2,1,3)
        k=a.k_norm(a.k_proj(x).reshape(B,N,a.n_kv_heads,-1)).transpose(0,2,1,3)
        v=a.v_proj(x).reshape(B,N,a.n_kv_heads,-1).transpose(0,2,1,3)
        q=a.rope(q);k=a.rope(k)
        if cache is not None:k,v=cache.update_and_fetch(k,v)
        out=scaled_dot_product_attention(q,k,v,cache=cache,scale=a.scale,mask=mask)
        keep=mx.array([0 if j in self.drop else 1 for j in range(a.n_heads)],dtype=out.dtype)[None,:,None,None]
        out=mx.concatenate([out[:,:,:-1],out[:,:,-1:]*keep],axis=2)
        return a.o_proj(out.transpose(0,2,1,3).reshape(B,N,-1))

def replacement_arrays(rank):
    p=DEST/'linear'/f'rank_{rank}.npz';arr=np.load(p);layers=read(DEST/'linear/manifest.json')['layers']
    return {l:{k:arr[f'L{l}_{k}'] for k in ['xmean','ymean','left','right']} for l in layers}

def materialize(model,config):
    repl=replacement_arrays(config['rank']) if config.get('replace_mlps') else {};layers=[]
    for l,b in enumerate(model.model.layers,start=1):
        if l>config.get('exit_layer',28) or l in config.get('drop_blocks',[]):continue
        if l in config.get('drop_mlps',[]):b=AttentionOnly(b)
        elif l in config.get('replace_mlps',[]):b.mlp=LowRankMLP(repl[l])
        heads=config.get('anchor_drop_heads',{}).get(str(l))
        if heads:b.self_attn=AnchorGate(b.self_attn,heads)
        layers.append(b)
    model.model.layers=layers;model.model.num_hidden_layers=len(layers);model.args.num_hidden_layers=len(layers)
    return model

def parameter_stats(model):
    arrays=[v for _,v in tree_flatten(model.parameters())]
    return dict(parameters=sum(v.size for v in arrays),weight_bytes=sum(v.size*v.itemsize for v in arrays),blocks=len(model.model.layers))

def last_hidden(model,e):
    h=model.model.embed_tokens(mx.array([e['ids']]));mask=create_attention_mask(h,None)
    for b in model.model.layers:h=b(h,mask=mask,cache=None)
    return h[0,-1]

def score(model,e,full=True):return outcome(model,last_hidden(model,e),codes(e),full)

