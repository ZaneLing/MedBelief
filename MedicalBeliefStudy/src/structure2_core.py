"""Real structural variants and small residual adapters; frozen Qwen3 backbone."""
import hashlib,json,time
import numpy as np
import mlx.core as mx
import mlx.nn as nn
from mlx.utils import tree_flatten
from mlx_lm.models.base import create_attention_mask
from mlx_lm.models.cache import make_prompt_cache
from phase90_structure2_prepare import ROOT,DATA,RUN,DOC,read,write,rank,sha,cases
from belief_v4_core import load_model,render
from structural_v1_variants import AttentionOnly,LowRankMLP,replacement_arrays

def encode(c,tok,condition='neutral',t=None):
    T=len(c['sentences']);return render(c,dict(condition=condition,mode='name',rotation=0,round=t or T,last_round=T,order='base'),tok)

class ScaledMLP(nn.Module):
    def __init__(self,mlp,scale):super().__init__();self.original=mlp;self.scale=scale
    def __call__(self,x):return self.original(x)*self.scale

class SmallAdapter(nn.Module):
    def __init__(self,kind='bottleneck',rank=16):
        super().__init__();self.kind=kind;self.rank=rank
        if kind=='diagonal':self.scale=mx.zeros((2048,));self.bias=mx.zeros((2048,))
        else:
            self.down=mx.random.normal((2048,rank))*.02;self.down_bias=mx.zeros((rank,));self.up=mx.zeros((rank,2048));self.up_bias=mx.zeros((2048,))
    def __call__(self,x):
        dtype=x.dtype;x=x.astype(mx.float32)
        if self.kind=='diagonal':y=x*mx.exp(mx.tanh(self.scale))+self.bias
        else:y=x+mx.tanh(x@self.down+self.down_bias)@self.up+self.up_bias
        return y.astype(dtype)

class Bridge(nn.Module):
    def __init__(self,arrays):
        super().__init__()
        for k in ['xmean','ymean','left','right']:setattr(self,k,mx.array(arrays[k],mx.float32))
    def __call__(self,x):return (((x.astype(mx.float32)-self.xmean)@self.left)@self.right+self.ymean).astype(x.dtype)

class AdaptedNorm(nn.Module):
    def __init__(self,norm,adapter):super().__init__();self.original=norm;self.adapter=adapter
    def __call__(self,x):return self.adapter(self.original(x))

class ContrastModel(nn.Module):
    def __init__(self,base,config):super().__init__();self.model=base.model;self.args=base.args;self.config=config
    @property
    def layers(self):return self.model.layers
    def __call__(self,inputs,cache=None):
        h=self.model.embed_tokens(inputs);cache=cache or [None]*len(self.layers);mask=create_attention_mask(h,cache[0]);early=None
        for l,(b,c) in enumerate(zip(self.layers,cache),1):
            h=b(h,mask,c)
            if l==self.config['contrast_layer']:early=self.model.norm(h[:,-1:])
        z=self.model.embed_tokens.as_linear(self.model.norm(h[:,-1:])).astype(mx.float32);ze=self.model.embed_tokens.as_linear(early).astype(mx.float32)
        result=z-self.config['contrast_strength']*ze
        allowed=z>=mx.max(z,axis=-1,keepdims=True)+np.log(self.config['plausibility'])
        return mx.where(allowed,result,-1e9)

def assemble(model,config):
    calibration=read(RUN/'calibration/ranking.json') if config.get('mlp_keep') or config.get('attention_keep_groups') else None
    replacements=replacement_arrays(config['rank']) if config.get('replace_mlps') else {};layers=[]
    for l,b in enumerate(model.model.layers,1):
        if l>config.get('exit_layer',28) or l in config.get('drop_blocks',[]):continue
        if config.get('mlp_keep') and l in config.get('mlp_layers',range(1,29)):
            n=int(6144*config['mlp_keep']);keep=mx.array(sorted(calibration['mlp'][str(l)][:n]));m=b.mlp;m.gate_proj.weight=m.gate_proj.weight[keep];m.up_proj.weight=m.up_proj.weight[keep];m.down_proj.weight=m.down_proj.weight[:,keep]
        if config.get('attention_keep_groups'):
            groups=sorted(calibration['attention_groups'][str(l)][:config['attention_keep_groups']]);a=b.self_attn
            ki=mx.array([g*128+k for g in groups for k in range(128)]);qi=mx.array([g*256+k for g in groups for k in range(256)])
            a.q_proj.weight=a.q_proj.weight[qi];a.k_proj.weight=a.k_proj.weight[ki];a.v_proj.weight=a.v_proj.weight[ki];a.o_proj.weight=a.o_proj.weight[:,qi];a.n_kv_heads=len(groups);a.n_heads=2*len(groups)
        if l in config.get('drop_mlps',[]):b=AttentionOnly(b)
        elif l in config.get('replace_mlps',[]):b.mlp=LowRankMLP(replacements[l])
        elif l in config.get('scale_layers',[]):b.mlp=ScaledMLP(b.mlp,config['mlp_scale'])
        layers.append(b)
    model.model.layers=layers;model.model.num_hidden_layers=len(layers);model.args.num_hidden_layers=len(layers)
    if config.get('adapter_file'):
        adapter=SmallAdapter(config['adapter_kind'],config.get('adapter_rank',16));adapter.load_weights(str(ROOT/config['adapter_file']));model.model.norm=AdaptedNorm(model.model.norm,adapter)
    if config.get('bridge_file'):
        a=np.load(ROOT/config['bridge_file']);model.model.norm=AdaptedNorm(model.model.norm,Bridge(a))
    mx.eval(model.parameters())
    return ContrastModel(model,config) if config.get('contrast_layer') else model

def parameter_stats(model):
    a=[v for _,v in tree_flatten(model.parameters())];return dict(parameters=sum(v.size for v in a),weight_bytes=sum(v.size*v.itemsize for v in a),layers=len(model.layers))

def prefill(model,ids,cache):
    if isinstance(model,ContrastModel):return model(mx.array([ids]),cache=cache)[0,-1].astype(mx.float32)
    h=model.model(mx.array([ids]),cache=cache)[0,-1];return model.model.embed_tokens.as_linear(h).astype(mx.float32)

def generate(model,tok,e,limit=64):
    cache=make_prompt_cache(model);z=prefill(model,e['ids'],cache);mx.eval(z);ids=[];eos=set(tok.eos_token_ids);stop='max_tokens'
    for _ in range(limit):
        k=int(mx.argmax(z).item())
        if k in eos:stop='eos';break
        ids.append(k);z=prefill(model,[k],cache);mx.eval(z)
    text=tok.decode(ids)
    try:d=json.loads('{"diagnosis":"'+text)['diagnosis']
    except (ValueError,TypeError,KeyError):d=None
    return dict(text=text,generated_disease=d,stop=stop,tokens=len(ids),prompt_sha256=hashlib.sha256(e['prompt'].encode()).hexdigest())

def run_cases(config,cohort,conditions=('neutral','wrong'),folder=None):
    dest=RUN/(folder or cohort)/config['name'];dest.mkdir(parents=True,exist_ok=True);cs=[c for c in cases() if c['cohort']==cohort]
    manifest=dict(configuration=config,cohort=cohort,cases=[c['case_id'] for c in cs],conditions=list(conditions),cases_sha256=sha(DATA/'cases.private.jsonl'),core_sha256=sha(ROOT/'src/structure2_core.py'))
    if (dest/'manifest.json').exists():assert read(dest/'manifest.json')==manifest
    else:write(dest/'manifest.json',manifest)
    if all((dest/(c['case_id']+'.json')).exists() for c in cs):return
    model,tok=load_model();model=assemble(model,config);size=parameter_stats(model);start=time.time()
    for i,c in enumerate(cs):
        p=dest/(c['case_id']+'.json')
        if p.exists():continue
        rr=[]
        for cond in conditions:
            e=encode(c,tok,cond);o=generate(model,tok,e);rr.append(dict(condition=cond,correct=o['generated_disease']==c['gold_disease'],listed=o['generated_disease'] in c['candidates'],**o));mx.clear_cache()
        write(p,dict(case_id=c['case_id'],dataset=c['dataset'],configuration=config,parameter_stats=size,conditions=rr))
        if i==0 or (i+1)%20==0:print(json.dumps(dict(stage=folder or cohort,candidate=config['name'],case=i+1,total=len(cs),elapsed=round(time.time()-start,1))),flush=True)
    write(dest/'completion.json',dict(complete=True,cases=len(cs),generations=len(cs)*len(conditions),parameter_stats=size));del model;mx.clear_cache()
