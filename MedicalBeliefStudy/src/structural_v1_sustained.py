"""Matched intervention through every generated answer token, not only prefill."""
from mlx_lm.models.cache import make_prompt_cache
from structural_v1_variants import *

class SustainedAnchorGate(AnchorGate):
    def __call__(self,x,mask=None,cache=None):
        offset=cache.offset if cache is not None else 0
        if not offset:return super().__call__(x,mask,cache)
        a=self.original;B,N,_=x.shape
        q=a.q_norm(a.q_proj(x).reshape(B,N,a.n_heads,-1)).transpose(0,2,1,3)
        k=a.k_norm(a.k_proj(x).reshape(B,N,a.n_kv_heads,-1)).transpose(0,2,1,3)
        v=a.v_proj(x).reshape(B,N,a.n_kv_heads,-1).transpose(0,2,1,3)
        q=a.rope(q,offset=offset);k=a.rope(k,offset=offset);k,v=cache.update_and_fetch(k,v)
        out=scaled_dot_product_attention(q,k,v,cache=cache,scale=a.scale,mask=mask)
        keep=mx.array([0 if j in self.drop else 1 for j in range(a.n_heads)],dtype=out.dtype)[None,:,None,None]
        return a.o_proj((out*keep).transpose(0,2,1,3).reshape(B,N,-1))

def materialize_followup(model,config):
    if not config.get('gate_during_decode'):return materialize(model,config)
    for l,b in enumerate(model.model.layers,1):
        if str(l) in config['anchor_drop_heads']:b.self_attn=SustainedAnchorGate(b.self_attn,config['anchor_drop_heads'][str(l)])
    return model

def numerical_control(case,head_config):
    base,tok=load_model();sham,_=load_model()
    for l in head_config['anchor_drop_heads']:b=sham.model.layers[int(l)-1];b.self_attn=SustainedAnchorGate(b.self_attn,[])
    e=encoded(case,tok,'neutral',0);bc=make_prompt_cache(base);sc=make_prompt_cache(sham);x=mx.array([e['ids']]);errors=[];top_changes=0
    tokens=tok.encode(' A short diagnostic answer is being generated.',add_special_tokens=False)[:8]
    for step in range(len(tokens)+1):
        a=base(x,cache=bc)[0,-1].astype(mx.float32);b=sham(x,cache=sc)[0,-1].astype(mx.float32);mx.eval(a,b);errors.append(float(mx.max(mx.abs(a-b)).item()));top_changes+=int(mx.argmax(a).item()!=mx.argmax(b).item())
        if step<len(tokens):x=mx.array([[tokens[step]]])
    assert max(errors)<.02 and top_changes==0
    for b in sham.model.layers:
        if isinstance(b.self_attn,SustainedAnchorGate):b.self_attn=b.self_attn.original
    base=materialize(base,head_config);sustained=dict(head_config,gate_during_decode=True);sham=materialize_followup(sham,sustained)
    a=score(base,e,True);b=score(sham,e,True);err=float(np.max(np.abs(np.array(a['q'])-b['q'])));assert err<.01
    del base,sham,bc,sc;mx.clear_cache()
    return dict(complete=True,empty_gate_cached_steps=len(errors),max_empty_gate_logit_error=max(errors),empty_gate_top_changes=top_changes,selected_gate_prefill_q_error=err)
