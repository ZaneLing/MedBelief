"""Old-MLP interventions with complete disease-name continuation scores."""
import json,time
import numpy as np
import mlx.core as mx
from mlx_lm.models.cache import KVCache
from mlx_lm.models.base import create_attention_mask
from phase9_names import render,score_names,selected_jobs
from phase6_measure import ROOT,MODEL,load_model,capture
from phase1_run_direct import sha,write_json,output_head

def patched_prefill(model,ids,layer,patch):
    h=model.model.embed_tokens(mx.array([ids]));mask=create_attention_mask(h,None);cache=[]
    for l,b in enumerate(model.model.layers):
        c=KVCache();pre=h;att=b.self_attn(b.input_layernorm(pre),mask,c);mid=pre+att;mlp=b.mlp(b.post_attention_layernorm(mid));h=mid+mlp
        if l==layer:h=mx.concatenate([h[:,:-1],(mid[0,-1]+patch)[None,None,:]],axis=1)
        cache.append(c)
    z=output_head(model,h[0,-1]).astype(mx.float32);mx.eval(z);return z,cache

def main():
    run=ROOT/'runs/structured_names_v1';assert (run/'completion.json').exists();dest=run/'interventions';dest.mkdir(exist_ok=True)
    rows=selected_jobs();lookup={(r['case_id'],r['order'],r['round']):r for r in rows};selected=[r for r in rows if r['deep_capture'] and r['order']=='base' and r['round']==r['last_round']//2];assert len(selected)==24
    spec={'source_sha256':sha(__file__),'scorer_sha256':sha(ROOT/'src/phase9_names.py'),'protocol_sha256':sha(ROOT/'protocol/STRUCTURED_NAME_ADAPTATION.md'),
          'candidate_order_protocol_sha256':sha(ROOT/'protocol/STRUCTURED_NAME_CANDIDATE_ORDER.md'),
          'content_protocol_sha256':sha(ROOT/'protocol/NAME_CONTENT_CONTROLS.md'),'cases':24,'layers':[26,27,28],'shift':257}
    p=dest/'manifest.json'
    if p.exists():assert json.loads(p.read_text())==spec
    else:write_json(p,spec)
    model,tok=load_model();start=time.time()
    orderdest=run/'candidate_order';orderdest.mkdir(exist_ok=True)
    for row in [r for r in rows if r['deep_capture'] and r['order']=='base' and r['round']==r['last_round']]:
        path=orderdest/f"{row['case_id']}.json"
        if path.exists():continue
        e=render({**row,'candidate_diseases':list(reversed(row['candidate_diseases']))},tok);a,z,cache=capture(model,e['ids'],keep_cache=True)
        result=score_names(model,z,cache,e)
        # All array fields below are explicitly restored to canonical disease order.
        for key in ['q_sequence','q_token_mean','log_probability','token_log_probability']:result[key]=list(reversed(result[key]))
        write_json(path,{'case_id':row['case_id'],'condition':'reversed_candidate_list','canonical_diseases':row['candidate_diseases'],**result})
        del a,z,cache;mx.clear_cache()
    write_json(orderdest/'completion.json',{'complete':True,'cases':24,'source_sha256':sha(__file__)})
    for i,row in enumerate(selected):
        path=dest/f"{row['case_id']}.json"
        if path.exists():continue
        old=lookup[row['case_id'],'base',row['round']-1];e=render(row,tok)
        currec=json.loads((run/'observations'/f"{row['job_id']}.json").read_text());oldrec=json.loads((run/'observations'/f"{old['job_id']}.json").read_text())
        with np.load(run/currec['state_file']) as a:current=mx.array(a['residual_stages'])
        with np.load(run/oldrec['state_file']) as a:previous=mx.array(a['residual_stages'])
        content=[];admin_state=None
        admin={'question_group_id':'ADMIN','items':[{'question_en':'Record handling:',
               'answer_en':"The entries above have been placed in the same patient's research file. No additional clinical information is provided"}]}
        repeat={**old['revealed_groups'][0],'question_group_id':'REPEAT_INITIAL'}
        for label,extra in [('administrative',admin),('repeat_initial',repeat)]:
            er=render({**old,'revealed_groups':old['revealed_groups']+[extra]},tok)
            arrays,rz,rc=capture(model,er['ids'],er['token_groups'],keep_cache=True);result=score_names(model,rz,rc,er)
            statefile=dest/f"{row['case_id']}_{label}.npz";np.savez_compressed(statefile,**{k:np.array(v) for k,v in arrays.items()},input_ids=er['ids'],token_groups=er['token_groups'])
            content.append({'condition':label,'input_tokens':len(er['ids']),'state_file':str(statefile.relative_to(run)),**result})
            if label=='administrative':admin_state=arrays['residual_stages']
            del arrays,rz,rc;mx.clear_cache()
        z,cache=patched_prefill(model,e['ids'],27,current[27,3]);sham=score_names(model,z,cache,e);del cache
        q=np.array(currec['q_sequence']);s=np.array(sham['q_sequence']);m=(q+s)/2
        distance=float(.5*np.sum(q*np.log((q+1e-30)/(m+1e-30))+s*np.log((s+1e-30)/(m+1e-30))))
        stable=bool(distance<1e-5 and q.argmax()==s.argmax());conditions=[]
        for l in [25,26,27]:
            for label,patch in [('previous_mlp',previous[l,3]),('direction_control',current[l,3]+mx.roll(previous[l,3]-current[l,3],257))]:
                z,cache=patched_prefill(model,e['ids'],l,patch);result=score_names(model,z,cache,e)
                conditions.append({'layer':l+1,'condition':label,**result});del cache;mx.clear_cache()
        z,cache=patched_prefill(model,e['ids'],27,admin_state[27,3]);result=score_names(model,z,cache,e)
        conditions.append({'layer':28,'condition':'administrative_source_mlp',**result});del cache,admin_state
        write_json(path,{'case_id':row['case_id'],'family':row['family'],'round':row['round'],'old_q':oldrec['q_sequence'],'current_q':currec['q_sequence'],
                       'sham_q':sham['q_sequence'],'sham_js':distance,'numerically_stable':stable,'conditions':conditions,'content_controls':content,
                       'old_input_tokens':oldrec['input_tokens'],'current_input_tokens':currec['input_tokens']})
        del current,previous,z;mx.clear_cache();print(json.dumps({'intervention_case':i+1,'total':24,'elapsed':time.time()-start}),flush=True)
    assert len(list(dest.glob('ddx*.json')))==24
    hashes=json.loads((run/'manifest.json').read_text())['model_hashes'];assert {f:sha(MODEL/f) for f in hashes}==hashes
    write_json(dest/'completion.json',{'complete':True,'cases':24,'active_conditions':168,'sham_conditions':24,'natural_content_conditions':48,'candidate_order_conditions':24,'api_cost_usd':0})

if __name__=='__main__':main()
