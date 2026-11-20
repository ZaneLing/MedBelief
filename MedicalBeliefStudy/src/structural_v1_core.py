"""Frozen structural experiments; source-preserving v4 prompts and MLX model."""
import hashlib,json
from pathlib import Path
import numpy as np
import mlx.core as mx
from mlx_lm.models.base import create_attention_mask,scaled_dot_product_attention
from belief_v4_core import ROOT,DATA,MODEL,load_model,render,output_head,sha,write_json

DEST=ROOT/'runs/structural_v1';DOC=ROOT/'research_v5_structural'
def read(p):return json.loads(p.read_text())
def rank(s):return hashlib.sha256(('structural-v1:'+s).encode()).hexdigest()
def cases():
    keep={r['case_id'] for r in read(DATA/'text_audit.json')['rows'] if r['strict_keep']}
    return [c for c in map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines()) if c['case_id'] in keep]
def groups():
    cs=cases();dev=[c for c in cs if c['cohort']=='development' and c['mechanism_capture']]
    screen=[]
    for ds in ['MedQA','MedMCQA','MMLU']:screen+=sorted([c for c in dev if c['dataset']==ds],key=lambda c:rank(c['case_id']))[:6]
    ids={c['case_id'] for c in screen};tune=[c for c in dev if c['case_id'] not in ids];test=[c for c in cs if c['cohort']=='confirmation']
    assert len(screen)==18 and len(tune)==27 and len(test)==345
    return screen,tune,test
def encoded(c,tok,cond,rot,t=None):
    T=len(c['sentences']);return render(c,dict(condition=cond,mode='code',rotation=rot,round=t or T,last_round=T,order='base'),tok)
def codes(e):return [s[0] for s in e['suffix']]
def candidate_logits(model,h,ids):
    # Bias-free tied head; its four rows give exactly the candidate logits.
    return (model.model.norm(h)@model.model.embed_tokens.weight[mx.array(ids)].T).astype(mx.float32)
def outcome(model,h,ids,full=False):
    z=output_head(model,h).astype(mx.float32) if full else candidate_logits(model,h,ids)
    zz=z[...,mx.array(ids)] if full else z;q=mx.softmax(zz,axis=-1);mx.eval(zz,q)
    out=dict(q=np.array(q).tolist(),candidate_logits=np.array(zz).tolist())
    if full:
        lp=zz-mx.logsumexp(z,axis=-1,keepdims=True);mx.eval(lp)
        out.update(candidate_mass=np.array(mx.exp(lp).sum(-1)).tolist(),first_is_code=np.isin(np.array(mx.argmax(z,axis=-1)),ids).tolist())
    return out
def attention_parts(b,h,mask=None,offset=0,prefix=None):
    x=b.input_layernorm(h);a=b.self_attn;B,N,_=x.shape
    q=a.q_norm(a.q_proj(x).reshape(B,N,a.n_heads,-1)).transpose(0,2,1,3)
    k=a.k_norm(a.k_proj(x).reshape(B,N,a.n_kv_heads,-1)).transpose(0,2,1,3)
    v=a.v_proj(x).reshape(B,N,a.n_kv_heads,-1).transpose(0,2,1,3)
    q=a.rope(q,offset=offset);k=a.rope(k,offset=offset)
    if prefix is not None:
        pk,pv=prefix;pk=mx.broadcast_to(pk,(B,*pk.shape[1:]));pv=mx.broadcast_to(pv,(B,*pv.shape[1:]))
        k=mx.concatenate([pk,k],axis=2);v=mx.concatenate([pv,v],axis=2)
    heads=scaled_dot_product_attention(q,k,v,cache=None,scale=a.scale,mask=mask)
    att=a.o_proj(heads.transpose(0,2,1,3).reshape(B,N,-1))
    return att,q,k,v,heads
def capture(model,e):
    h=model.model.embed_tokens(mx.array([e['ids']]));mask=create_attention_mask(h,None);records=[]
    member=mx.array(np.eye(5,dtype=np.float32)[e['token_groups']])
    for b in model.model.layers:
        pre=h;att,q,k,v,heads=attention_parts(b,pre,mask);mid=pre+att;x=b.post_attention_layernorm(mid);mlp=b.mlp(x);h=mid+mlp
        kk=mx.repeat(k,b.self_attn.n_heads//b.self_attn.n_kv_heads,axis=1)
        weights=mx.softmax(q[:,:,-1:,:].astype(mx.float32)@kk.astype(mx.float32).transpose(0,1,3,2)*b.self_attn.scale,axis=-1)
        grouped=weights[0,:,0]@member
        # Materialize now; retain only quantities needed for exact interventions.
        mx.eval(h,k,v,heads,grouped,x,mlp)
        records.append(dict(pre=pre,mid=mid,post=h,mlp_input=x,mlp=mlp,k=k,v=v,heads=heads[0,:,-1],attention=grouped))
    return records,mask
def resume_global(model,rec,mask,start,kind):
    r=rec[start];b=model.model.layers[start]
    if kind=='block':h=r['pre']
    elif kind=='mlp':h=r['mid']
    elif kind=='attention':h=r['pre']+b.mlp(b.post_attention_layernorm(r['pre']))
    else:raise ValueError(kind)
    for block in model.model.layers[start+1:]:h=block(h,mask=mask,cache=None)
    return h[0,-1]
def resume_anchor(model,rec,start,hs):
    # Each branch changes only the final input position. Earlier token states
    # are identical by causal attention, so their baseline KV are exact.
    h=hs[:,None,:];offset=rec[0]['pre'].shape[1]-1
    for l in range(start+1,len(rec)):
        b=model.model.layers[l];r=rec[l];att,*_=attention_parts(b,h,None,offset,(r['k'][:,:,:-1],r['v'][:,:,:-1]))
        mid=h+att;h=mid+b.mlp(b.post_attention_layernorm(mid))
    return h[:,0,:]
def anchor_branches(model,rec,l):
    b=model.model.layers[l];r=rec[l];pre=r['pre'][0,-1];heads=r['heads'];nh=heads.shape[0]
    rows=[];labels=[]
    for j in range(nh):
        keep=mx.array([0 if k==j else 1 for k in range(nh)],dtype=heads.dtype)[:,None]
        rows.append((heads*keep).reshape(-1));labels.append('head_'+str(j+1))
    rows.extend([mx.zeros_like(heads).reshape(-1),heads.reshape(-1)])
    att=b.self_attn.o_proj(mx.stack(rows));mid=pre[None]+att
    changed=mid+b.mlp(b.post_attention_layernorm(mid))
    # 16 heads, whole attention, sham, MLP, block.
    hs=mx.concatenate([changed,r['mid'][0,-1:,:],pre[None]],axis=0)
    labels+=['attention','sham','mlp','block']
    return labels,resume_anchor(model,rec,l,hs)
def forward(model,e,config,replacements=None,full=True):
    h=model.model.embed_tokens(mx.array([e['ids']]));mask=create_attention_mask(h,None)
    for l,b in enumerate(model.model.layers,start=1):
        if l>config.get('exit_layer',28):break
        if l in config.get('drop_blocks',[]):continue
        mid=h+b.self_attn(b.input_layernorm(h),mask,cache=None)
        if l in config.get('drop_mlps',[]):h=mid;continue
        x=b.post_attention_layernorm(mid)
        if l in config.get('replace_mlps',[]):
            rr=replacements[l];mlp=((x.astype(mx.float32)-rr['xmean'])@rr['left'])@rr['right']+rr['ymean'];h=mid+mlp.astype(mid.dtype)
        else:h=mid+b.mlp(x)
    return outcome(model,h[0,-1],codes(e),full)

