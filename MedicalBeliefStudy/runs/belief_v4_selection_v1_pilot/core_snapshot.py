"""Frozen forward measurements and aligned interventions for external cases."""
import hashlib,json
from pathlib import Path
import numpy as np
import mlx.core as mx
from mlx_lm.models.base import create_attention_mask,scaled_dot_product_attention
from mlx_lm.models.cache import KVCache
from phase6_measure import ROOT,MODEL,load_model
from phase1_run_direct import output_head,sha,write_json,greedy_answer
from phase9_names import score_names
from phase6_name_control import clone

DATA=ROOT/'data/belief_v4';RUN=ROOT/'runs/belief_v4'
LAYERS=[14,21,28]

def jobs_for(c):
    T=len(c['sentences']);jobs={}
    def add(t,condition,mode='name',rotation=0,order='base'):
        name=f'{c["case_id"]}_{condition}_{mode}_r{rotation}_{order}_t{t:02d}'
        jobs[name]=dict(job_id=name,case_id=c['case_id'],round=t,last_round=T,condition=condition,mode=mode,rotation=rotation,order=order)
    for t in [T-1,T]:
        for condition in ['neutral','gold','wrong','mention']:add(t,condition)
    add(T,'none');add(T,'none',order='reverse')
    if c['trajectory_capture']:
        for t in range(1,T+1):
            for condition in ['neutral','gold','wrong']:add(t,condition)
        for condition in ['neutral','wrong']:
            for rotation in [0,2]:add(T,condition,mode='code',rotation=rotation)
    return list(jobs.values())

def render(c,row,tok):
    sentences=c['sentences'][:row['round']]
    if row['order']=='reverse':sentences=list(reversed(sentences))
    code=['ABCD'[(j+c['code_rotation']+row['rotation'])%4] for j in range(4)]
    candidates='\n'.join((f'{code[i]}: ' if row['mode']=='code' else '- ')+d for i,d in enumerate(c['candidates']))
    evidence='\n'.join(sentences)
    body='Current patient findings:\n'+evidence+'\n\n'+c['diagnostic_question']+'\nCandidate diagnoses:\n'+candidates+'\nSelect the best-supported listed diagnosis using only the current patient facts. Missing facts are unknown. A previous assessment may be wrong. Reassess it.'
    if row['mode']=='code':body+=' Complete the JSON object with the one exact diagnosis code. Do not explain.';stub='{"diagnosis_code":"';answers=code
    else:body+=' Complete the JSON object with one exact candidate diagnosis. Do not abbreviate or explain.';stub='{"diagnosis":"';answers=c['candidates']
    msgs=[dict(role='system',content='You are analyzing a medical examination vignette for research. Evaluate the current patient facts and compare the listed diagnoses. Do not invent additional findings.')]
    condition=row['condition'];old=None
    if condition!='none':
        if condition=='mention':old=json.dumps({'diagnosis':'Undetermined','unendorsed_candidate':c['wrong_disease']},separators=(',',':'))
        else:old=json.dumps({'diagnosis':c['gold_disease'] if condition=='gold' else c['wrong_disease'] if condition=='wrong' else 'Undetermined'},separators=(',',':'))
        msgs.extend([dict(role='user',content='An earlier partial record was assessed.'),dict(role='assistant',content=old)])
    msgs.append(dict(role='user',content=body));prompt=tok.apply_chat_template(msgs,tokenize=False,add_generation_prompt=True,enable_thinking=False)+stub
    enc=tok._tokenizer(prompt,add_special_tokens=False,return_offsets_mapping=True);ids=enc['input_ids'];offsets=enc['offset_mapping'];groups=np.zeros(len(ids),np.int16)
    body_start=prompt.index(body);start=prompt.index(evidence,body_start);cursor=start;ends=[];spans=[]
    for i,s in enumerate(sentences):
        a=prompt.index(s,cursor);b=a+len(s);spans.append((a,b,2 if i==len(sentences)-1 else 1));cursor=b
        pos=[j for j,(l,r) in enumerate(offsets) if r>l and a<=(l+r)/2<b];assert pos;ends.append(pos[-1])
    ca=prompt.index('Candidate diagnoses:',cursor);cb=prompt.index('Select the best-supported',ca);spans.append((ca,cb,4))
    if old:a=prompt.index(old);spans.append((a,a+len(old),3))
    for a,b,g in spans:
        for j,(l,r) in enumerate(offsets):
            if r>l and a<=(l+r)/2<b:groups[j]=g
    suffix=[]
    for answer in answers:
        full=tok.encode(prompt+answer+'"}',add_special_tokens=False);assert full[:len(ids)]==ids
        suffix.append(full[len(ids):]+[tok.eos_token_id])
    newp=np.flatnonzero(groups==2);oldp=np.flatnonzero(groups==1)[-len(newp):]
    return dict(prompt=prompt,ids=ids,token_groups=groups,evidence_ends=ends,new_positions=newp,old_positions=oldp,suffix=suffix,answers=answers,code_to_disease=dict(zip(code,c['candidates'])))

def capture(model,e,keep_patch=False):
    ids=e['ids'];h=model.model.embed_tokens(mx.array([ids]));mask=create_attention_mask(h,None);groups=e['token_groups'];member=mx.array(np.eye(5,dtype=np.float32)[groups]);newp=e['new_positions'];oldp=np.flatnonzero(groups==1)
    stages=[];means=[];atts=[];errs=[];cache=[];patches={};ends=[]
    for l,b in enumerate(model.model.layers):
        pre=h;x=b.input_layernorm(pre);a=b.self_attn;B,L,D=x.shape
        q=a.q_norm(a.q_proj(x).reshape(B,L,a.n_heads,-1)).transpose(0,2,1,3)
        k=a.k_norm(a.k_proj(x).reshape(B,L,a.n_kv_heads,-1)).transpose(0,2,1,3)
        v=a.v_proj(x).reshape(B,L,a.n_kv_heads,-1).transpose(0,2,1,3)
        q=a.rope(q);k=a.rope(k);out=scaled_dot_product_attention(q,k,v,cache=None,scale=a.scale,mask=mask)
        att=a.o_proj(out.transpose(0,2,1,3).reshape(B,L,-1));mid=pre+att;mlp=b.mlp(b.post_attention_layernorm(mid));h=mid+mlp
        stages.append(mx.stack([z[0,-1] for z in [pre,att,mid,mlp,h]]))
        means.append(mx.stack([h[0,mx.array(newp)].mean(0),h[0,mx.array(oldp)].mean(0) if len(oldp) else mx.zeros_like(h[0,-1])]))
        ends.append(h[0,mx.array(e['evidence_ends'])])
        kk=mx.repeat(k,a.n_heads//a.n_kv_heads,axis=1);vv=mx.repeat(v,a.n_heads//a.n_kv_heads,axis=1)
        weights=mx.softmax(q[:,:,-1:,:].astype(mx.float32)@kk.astype(mx.float32).transpose(0,1,3,2)*a.scale,axis=-1)
        atts.append(weights[0,:,0]@member)
        rec=(weights@vv.astype(mx.float32))[0,:,0];native=out[0,:,-1].astype(mx.float32)
        errs.append(mx.sqrt(mx.mean((rec-native)**2)/(mx.mean(native**2)+1e-12)))
        cc=KVCache();cc.state=(k,v,len(ids));cache.append(cc)
        if keep_patch and l+1 in LAYERS:
            patches[f'new_L{l+1}']=h[0,mx.array(newp)];patches[f'anchor_L{l+1}']=h[0,-1:]
            patches[f'old_L{l+1}']=h[0,mx.array(e['old_positions'])]
    arrays=dict(residual_stages=mx.stack(stages),evidence_means=mx.stack(means),evidence_end_states=mx.stack(ends),attention_by_group=mx.stack(atts),attention_reconstruction_relative_rms=mx.stack(errs),**patches)
    z=output_head(model,h[0,-1]).astype(mx.float32);mx.eval(z,*arrays.values())
    return arrays,z,cache

def patched_forward(model,e,layer,positions,delta):
    """Change post-block states, recompute downstream blocks and their KV caches."""
    h=model.model.embed_tokens(mx.array([e['ids']]));mask=create_attention_mask(h,None);cache=[];before=None;after=None
    for l,b in enumerate(model.model.layers):
        cc=KVCache();h=b(h,mask=mask,cache=cc);cache.append(cc)
        if l+1==layer:
            ix=mx.array(positions);before=h[0,ix];after=(before.astype(mx.float32)+mx.array(delta,mx.float32)).astype(h.dtype)
            assert np.array_equal(np.asarray(positions),np.arange(positions[0],positions[-1]+1))
            h=mx.concatenate([h[:,:positions[0]],after[None],h[:,positions[-1]+1:]],axis=1)
    z=output_head(model,h[0,-1]).astype(mx.float32);mx.eval(z,before,after)
    return z,cache,np.array(before),np.array(after)

def decoded(model,tok,z,cache,e):
    _,txt,stop=greedy_answer(model,tok,z,clone(cache,len(e['ids'])),limit=64)
    stub='{"diagnosis_code":"' if 'diagnosis_code' in e['prompt'][-30:] else '{"diagnosis":"'
    try:value=next(iter(json.loads(stub+txt).values()))
    except (ValueError,TypeError,StopIteration):value=None
    if stub.startswith('{"diagnosis_code'):value=e['code_to_disease'].get(value)
    return dict(generated_disease=value,generated_text=txt,generated_stop=stop)
