"""49-disease frozen observations with native attention and observed head weights."""
from pathlib import Path
import argparse, hashlib, importlib.metadata, json, os, time
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
import numpy as np
import mlx.core as mx
from mlx.utils import tree_map
from mlx_lm import load
from mlx_lm.models.base import create_attention_mask, scaled_dot_product_attention
from mlx_lm.models.cache import KVCache
from phase1_run_direct import output_head, scores, sha, write_json

ROOT = Path(__file__).resolve().parents[1]
CODES = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvw'
MODEL = ROOT.parent/'MedicalBeliefMechanisms/.models/Qwen3-1.7B'
SYSTEM = ('You are analyzing a synthetic patient record for research. Compare the listed diagnoses using only '
          'the cumulative findings shown. Distinguish past medical history from the current presentation. '
          'Missing information is unknown. Some recorded ordinal scales have unspecified endpoint meanings; '
          'do not invent a clinical interpretation for their endpoints.')

def render(row, tok, mode='code'):
    diseases=row['candidate_diseases']; offset=(row['mapping_offset']+row['rotation'])%len(diseases)
    mapping={c:diseases[(i+offset)%len(diseases)] for i,c in enumerate(CODES[:len(diseases)])}
    lines=[f"Patient: age {row['age']} years; sex {row['sex']}.", 'Cumulative findings:']
    for i,g in enumerate(row['revealed_groups']):
        lines.append(f'[Evidence group {i}: {g["question_group_id"]}]')
        lines += [x['question_en']+' Answer: '+x['answer_en']+'.' for x in g['items']]
    if mode=='code':
        lines += ['Candidate diagnoses:']+[f'{c}: {d}' for c,d in mapping.items()]
        lines += ['Select the best-supported candidate for the current presentation at this point. '
                  'Choose one listed diagnosis even if evidence is incomplete. After "Diagnosis code:", '
                  'output exactly one space followed by one case-sensitive letter from the list. '
                  'Uppercase and lowercase letters are different codes. Do not output a numerical probability.']
        stub='Diagnosis code:'
    else:
        lines += ['Give only the single most likely diagnosis for the current presentation, without explanation.']
        stub='Most likely diagnosis:'
    messages=[{'role':'system','content':SYSTEM},{'role':'user','content':'\n'.join(lines)}]
    prompt=tok.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)+stub
    encoded=tok._tokenizer(prompt,add_special_tokens=False,return_offsets_mapping=True)
    ids=encoded['input_ids']; offsets=encoded['offset_mapping']
    spans=[]; labels=['format','candidates','demographics']
    demo=prompt.index(lines[0]);spans.append((demo,demo+len(lines[0]),2))
    ends=[]
    for i,g in enumerate(row['revealed_groups']):
        marker=f'[Evidence group {i}: {g["question_group_id"]}]'
        start=prompt.index(marker)+len(marker)
        if i+1<len(row['revealed_groups']):end=prompt.index(f'[Evidence group {i+1}:',start)
        else:end=prompt.index('Candidate diagnoses:' if mode=='code' else 'Give only the single',start)
        spans.append((start,end,3+i));labels.append(g['question_group_id'])
        positions=[j for j,(a,b) in enumerate(offsets) if b>a and start<=(a+b)/2<end]
        assert positions;ends.append(positions[-1])
    if mode=='code':
        start=prompt.index('Candidate diagnoses:');end=prompt.index('Select the best-supported',start)
        spans.append((start,end,1))
    token_groups=np.zeros(len(ids),np.int16)
    for start,end,gi in spans:
        for j,(a,b) in enumerate(offsets):
            if b>a and start<=(a+b)/2<end:token_groups[j]=gi
    cids=[]
    if mode=='code':
        inverse={d:c for c,d in mapping.items()}
        for disease in diseases:
            suffix=tok.encode(' '+inverse[disease],add_special_tokens=False)
            assert len(suffix)==1 and tok.encode(prompt+' '+inverse[disease],add_special_tokens=False)==ids+suffix
            cids.append(suffix[0])
    return {'prompt':prompt,'ids':ids,'candidate_ids':cids,'mapping':mapping,
            'token_groups':token_groups,'group_labels':labels,'evidence_ends':ends}

def capture(model, ids, token_groups=None, evidence_ends=None, deep=False, keep_cache=False):
    h=model.model.embed_tokens(mx.array([ids]));mask=create_attention_mask(h,None)
    stages=[];group_att=[];recon_errors=[];cache=[];token_att=[];head_out=[];ev_states=[]
    membership=None
    if token_groups is not None:
        membership=mx.array(np.eye(int(token_groups.max())+1,dtype=np.float32)[token_groups])
    for block in model.model.layers:
        pre=h;x=block.input_layernorm(pre);a=block.self_attn;B,L,D=x.shape
        query=a.q_norm(a.q_proj(x).reshape(B,L,a.n_heads,-1)).transpose(0,2,1,3)
        key=a.k_norm(a.k_proj(x).reshape(B,L,a.n_kv_heads,-1)).transpose(0,2,1,3)
        value=a.v_proj(x).reshape(B,L,a.n_kv_heads,-1).transpose(0,2,1,3)
        query=a.rope(query);key=a.rope(key)
        out=scaled_dot_product_attention(query,key,value,cache=None,scale=a.scale,mask=mask)
        att=a.o_proj(out.transpose(0,2,1,3).reshape(B,L,-1))
        mid=pre+att;mlp=block.mlp(block.post_attention_layernorm(mid));h=mid+mlp
        stages.append(mx.stack([v[0,-1] for v in [pre,att,mid,mlp,h]]))
        if membership is not None:
            k=mx.repeat(key,a.n_heads//a.n_kv_heads,axis=1)
            v=mx.repeat(value,a.n_heads//a.n_kv_heads,axis=1)
            weights=mx.softmax((query[:,:,-1:,:].astype(mx.float32)@k.astype(mx.float32).transpose(0,1,3,2))*a.scale,axis=-1)
            group_att.append(weights[0,:,0]@membership)
            reconstructed=(weights@v.astype(mx.float32))[0,:,0]
            native=out[0,:,-1].astype(mx.float32)
            recon_errors.append(mx.sqrt(mx.mean((reconstructed-native)**2)/(mx.mean(native**2)+1e-12)))
            if deep:
                token_att.append(weights[0,:,0].astype(mx.float16));head_out.append(out[0,:,-1])
        if deep and evidence_ends:ev_states.append(h[0,mx.array(evidence_ends)])
        if keep_cache:
            c=KVCache();c.state=(key,value,len(ids));cache.append(c)
    states=mx.stack(stages);logits=output_head(model,states[-1,4]).astype(mx.float32)
    arrays={'residual_stages':states}
    if membership is not None:
        arrays.update(attention_by_group=mx.stack(group_att),attention_reconstruction_relative_rms=mx.stack(recon_errors))
    if deep:
        arrays.update(attention_by_token=mx.stack(token_att),head_outputs=mx.stack(head_out),evidence_end_states=mx.stack(ev_states))
    mx.eval(logits,*arrays.values())
    return arrays,logits,cache

def load_model(model_dir=MODEL):
    model,tok=load(str(model_dir));model.update(tree_map(lambda a:a.astype(mx.float16) if mx.issubdtype(a.dtype,mx.floating) else a,model.parameters()))
    model.eval();mx.eval(model.parameters());return model,tok

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-id',default='full49_v1');ap.add_argument('--limit',type=int,default=0)
    args=ap.parse_args();run=ROOT/'runs'/args.run_id
    for name in ['observations','states']:(run/name).mkdir(parents=True,exist_ok=True)
    data=ROOT/'data/full49_v1';jobs=[json.loads(s) for s in (data/'jobs.public.jsonl').read_text().splitlines()]
    model_files=list(MODEL.glob('*.safetensors'))+[MODEL/'config.json',MODEL/'tokenizer.json',MODEL/'tokenizer_config.json']
    manifest={'run_id':args.run_id,'model':'Qwen3-1.7B','device':mx.device_info(),'jobs':len(jobs),'dtype':'FP16 from BF16, frozen, not quantized',
              'model_hashes':{p.name:sha(p) for p in model_files},'input_sha256':sha(data/'jobs.public.jsonl'),
              'protocol_sha256':sha(ROOT/'protocol/FULL49_PHASES_6_8.md'),'source_sha256':sha(__file__),
              'candidate_diseases':jobs[0]['candidate_diseases'],'api_cost_usd':0,
              'packages':{p:importlib.metadata.version(p) for p in ['mlx','mlx-lm','numpy']}}
    path=run/'manifest.json'
    if path.exists():assert json.loads(path.read_text())==manifest,'Create a new run ID for changed observations'
    else:write_json(path,manifest);(run/'source_snapshot.py').write_bytes(Path(__file__).read_bytes())
    model,tok=load_model();start=time.time();done=0
    for ji,row in enumerate(jobs):
        path=run/'observations'/f"{row['job_id']}.json"
        if path.exists():continue
        tick=time.time();encoded=render(row,tok)
        arrays,terminal,_=capture(model,encoded['ids'],encoded['token_groups'],encoded['evidence_ends'],row['deep_capture'])
        # Decode three positions per layer; intermediate projections are uncalibrated readouts.
        states=arrays['residual_stages'];readouts=states[:,[0,2,4]].reshape(-1,states.shape[-1])
        projected=output_head(model,readouts).astype(mx.float32)
        z,p,q=scores(projected,encoded['candidate_ids']);z=z.reshape(28,3,49);p=p.reshape(28,3,49);q=q.reshape(28,3,49)
        native_check=None
        if ji%100==0 or done<3:
            native=model(mx.array([encoded['ids']]))[0,-1].astype(mx.float32);mx.eval(native)
            na,ta=np.array(native),np.array(terminal)
            native_check={'max_logit_error':float(np.max(np.abs(na-ta))),
                          'allclose':bool(np.allclose(na,ta,atol=1e-3,rtol=1e-3)),'same_argmax':bool(na.argmax()==ta.argmax())}
            assert native_check['allclose'] and native_check['same_argmax'],native_check
        errors=np.array(arrays['attention_reconstruction_relative_rms'])
        assert np.isfinite(errors).all() and errors.max()<0.02,errors.tolist()
        attention=np.array(arrays['attention_by_group']);assert np.allclose(attention.sum(-1),1,atol=1e-5)
        finalz,finalp,finalq=scores(terminal,encoded['candidate_ids'])
        assert np.allclose(finalz,z[-1,-1],atol=1e-3,rtol=1e-3)
        saved={k:np.array(v) for k,v in arrays.items()}
        saved.update(component_logits=z,component_support=q,component_candidate_mass=p.sum(-1),
                     input_ids=np.array(encoded['ids'],np.int32),candidate_ids=np.array(encoded['candidate_ids'],np.int32),
                     token_groups=encoded['token_groups'],evidence_end_positions=np.array(encoded['evidence_ends'],np.int32))
        state_path=run/'states'/f"{row['job_id']}.npz";temp=state_path.with_suffix('.tmp.npz');np.savez_compressed(temp,**saved);temp.replace(state_path)
        first=int(mx.argmax(terminal).item());inv={cid:d for cid,d in zip(encoded['candidate_ids'],row['candidate_diseases'])}
        record={k:row[k] for k in ['job_id','case_id','family','order','round','last_round','rotation','deep_capture']}
        record.update(q=finalq.tolist(),z=finalz.tolist(),p=finalp.tolist(),candidate_mass=float(finalp.sum()),
                      input_tokens=len(encoded['ids']),code_to_disease=encoded['mapping'],group_labels=encoded['group_labels'],
                      group_token_counts=np.bincount(encoded['token_groups'],minlength=len(encoded['group_labels'])).tolist(),
                      greedy_first_text=tok.decode([first]),greedy_first_disease=inv.get(first),native_check=native_check,
                      max_attention_reconstruction_relative_rms=float(errors.max()),
                      prompt_sha256=hashlib.sha256(encoded['prompt'].encode()).hexdigest(),state_sha256=sha(state_path),
                      state_file=str(state_path.relative_to(run)),elapsed_sec=time.time()-tick)
        write_json(path,record);done+=1
        del arrays,states,projected,terminal,saved;mx.clear_cache()
        if done==1 or done%20==0:print(json.dumps({'job':ji+1,'total':len(jobs),'elapsed':round(time.time()-start,1),'seconds_per_job':round((time.time()-start)/done,3)}),flush=True)
        if args.limit and done>=args.limit:break
    n=len(list((run/'observations').glob('*.json')))
    if n==len(jobs):
        assert manifest['model_hashes']=={p.name:sha(p) for p in model_files}
        write_json(run/'completion.json',{'complete':True,'observations':n,'weights_unchanged':True,'elapsed_this_invocation':time.time()-start,'api_cost_usd':0})
    print(json.dumps({'saved':n,'expected':len(jobs),'elapsed':time.time()-start}),flush=True)

if __name__=='__main__':main()
