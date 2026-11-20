"""Training-only activation salience, then real matrix slicing controls."""
from structure2_core import *
from structural_v1_core import attention_parts
def main():
    dest=RUN/'calibration';dest.mkdir(exist_ok=True);spec=read(DATA/'manifest.json');cs={c['case_id']:c for c in cases()};model,tok=load_model();mlp=np.zeros((28,6144),np.float64);att=np.zeros((28,8),np.float64);tokens=0
    for i,cid in enumerate(spec['calibration']):
        c=cs[cid];assert c['cohort']=='train';e=encode(c,tok);h=model.model.embed_tokens(mx.array([e['ids']]));mask=create_attention_mask(h,None);ix=mx.array(np.unique(np.linspace(0,len(e['ids'])-1,16,dtype=int)));tokens+=len(ix)
        for l,b in enumerate(model.layers):
            update,q,k,v,heads=attention_parts(b,h,mask);mid=h+update;x=b.post_attention_layernorm(mid);xs=x[0,ix];m=b.mlp;activation=nn.silu(m.gate_proj(xs))*m.up_proj(xs)
            score=mx.mean(mx.abs(activation.astype(mx.float32)),axis=0)*mx.sqrt(mx.sum(m.down_proj.weight.astype(mx.float32)**2,axis=0))
            a=mx.take(heads[0],ix,axis=1).astype(mx.float32);headmag=mx.sqrt(mx.mean(a*a,axis=(1,2)));ow=b.self_attn.o_proj.weight.astype(mx.float32).reshape(2048,16,128);hnorm=mx.sqrt(mx.sum(ow*ow,axis=(0,2)));headscore=(headmag*hnorm).reshape(8,2).sum(-1)
            h=mid+m(x);mx.eval(h,score,headscore);mlp[l]+=np.array(score);att[l]+=np.array(headscore)
        mx.clear_cache()
        if i==0 or (i+1)%16==0:print(json.dumps(dict(calibration=i+1,total=64)),flush=True)
    write(dest/'ranking.json',dict(mlp={str(l+1):np.argsort(-mlp[l]).tolist() for l in range(28)},attention_groups={str(l+1):np.argsort(-att[l]).tolist() for l in range(28)},calibration_cases=spec['calibration'],sampled_tokens=tokens,group_indexing='zero-based KV groups, each includes two query heads',method='Mean absolute SwiGLU channel activation times down-column L2; attention head RMS output times O-column L2, summed per KV group.',source_sha256=sha(ROOT/'src/phase91_structure2_calibrate.py')))
    np.savez(dest/'scores.npz',mlp=mlp,attention_groups=att)
    # New decode implementation and zero adapter must leave a native model unchanged.
    e=encode(cs[spec['calibration'][0]],tok);native=model(mx.array([e['ids']]))[0,-1].astype(mx.float32);own=prefill(model,e['ids'],make_prompt_cache(model));mx.eval(native,own);err=float(mx.max(mx.abs(native-own)).item());assert err<.02 and int(mx.argmax(native).item())==int(mx.argmax(own).item())
    norm=model.model.norm;model.model.norm=AdaptedNorm(norm,SmallAdapter('bottleneck',16));zero=prefill(model,e['ids'],make_prompt_cache(model));mx.eval(zero);zerr=float(mx.max(mx.abs(own-zero)).item());assert zerr<.02
    write(dest/'completion.json',dict(complete=True,cases=64,native_logit_max_error=err,zero_adapter_logit_max_error=zerr,api_cost_usd=0))
if __name__=='__main__':main()
