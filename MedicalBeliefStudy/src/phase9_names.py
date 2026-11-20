"""Disease-name measurements without arbitrary answer-code bindings."""
import json,time,argparse,hashlib
import numpy as np
import mlx.core as mx
from phase6_measure import ROOT,MODEL,SYSTEM,load_model,capture
from phase6_name_control import clone,log_softmax,soft
from phase1_run_direct import sha,write_json,greedy_answer

def render(row,tok):
    lines=[f"Patient: age {row['age']} years; sex {row['sex']}.",'Cumulative findings:']
    for i,g in enumerate(row['revealed_groups']):
        lines.append(f'[Evidence group {i}: {g["question_group_id"]}]');lines += [x['question_en']+' Answer: '+x['answer_en']+'.' for x in g['items']]
    lines+=['Candidate diagnoses:']+['- '+d for d in row['candidate_diseases']]
    lines+=['Select the best-supported candidate for the current presentation at this point. Choose one listed diagnosis even if evidence is incomplete. '
            'Complete the JSON object with exactly one candidate diagnosis copied verbatim from the list. Do not abbreviate or add an explanation. '
            'The output must have the form {"diagnosis":"exact candidate diagnosis"}.']
    prompt=tok.apply_chat_template([{'role':'system','content':SYSTEM},{'role':'user','content':'\n'.join(lines)}],tokenize=False,add_generation_prompt=True,enable_thinking=False)+'{"diagnosis":"'
    enc=tok._tokenizer(prompt,add_special_tokens=False,return_offsets_mapping=True);ids=enc['input_ids'];offsets=enc['offset_mapping'];spans=[];labels=['format','candidates','demographics'];ends=[]
    start=prompt.index(lines[0]);spans.append((start,start+len(lines[0]),2))
    for i,g in enumerate(row['revealed_groups']):
        marker=f'[Evidence group {i}: {g["question_group_id"]}]';start=prompt.index(marker)+len(marker)
        end=prompt.index(f'[Evidence group {i+1}:',start) if i+1<len(row['revealed_groups']) else prompt.index('Candidate diagnoses:',start)
        spans.append((start,end,3+i));labels.append(g['question_group_id']);positions=[j for j,(a,b) in enumerate(offsets) if b>a and start<=(a+b)/2<end];ends.append(positions[-1])
    start=prompt.index('Candidate diagnoses:');spans.append((start,prompt.index('Select the best-supported',start),1));groups=np.zeros(len(ids),np.int16)
    for start,end,gi in spans:
        for j,(a,b) in enumerate(offsets):
            if b>a and start<=(a+b)/2<end:groups[j]=gi
    suffix=[]
    for disease in row['candidate_diseases']:
        full=tok.encode(prompt+disease+'"}',add_special_tokens=False);assert full[:len(ids)]==ids
        suffix.append(full[len(ids):]+[tok.eos_token_id])
    return {'prompt':prompt,'ids':ids,'token_groups':groups,'evidence_ends':ends,'group_labels':labels,'suffix':suffix}

def score_names(model,first,cache,encoded,validate=False):
    initial=np.array(log_softmax(first));suffix=encoded['suffix'];N=len(encoded['ids']);total=[];token_logp=[];check=None
    for beg in range(0,len(suffix),7):
        batch=suffix[beg:beg+7];K=len(batch);L=max(map(len,batch));padded=np.zeros((K,L),dtype=np.int32)
        for j,s in enumerate(batch):padded[j,:len(s)]=s
        cc=clone(cache,N,K);z=model(mx.array(padded[:,:-1]),cache=cc).astype(mx.float32)
        taken=mx.take_along_axis(log_softmax(z),mx.array(padded[:,1:,None]),axis=-1)[:,:,0];mx.eval(taken);values=np.array(taken)
        for j,s in enumerate(batch):
            v=[float(initial[s[0]])]+values[j,:len(s)-1].tolist();token_logp.append(v);total.append(float(np.sum(v)))
        if validate and beg==0:
            s=batch[0];zfull=model(mx.array([encoded['ids']+s[:-1]]))[0,N-1:].astype(mx.float32)
            direct=mx.take_along_axis(log_softmax(zfull),mx.array(s)[:,None],axis=-1).sum().item()
            check={'direct':direct,'cached':total[0],'absolute_error':abs(direct-total[0])};assert check['absolute_error']<.15
        del cc,z,taken;mx.clear_cache()
    return {'log_probability':total,'token_log_probability':token_logp,'q_sequence':soft(total).tolist(),
            'q_token_mean':soft(np.array(total)/list(map(len,suffix))).tolist(),'sequence_probability_mass':float(np.exp(total).sum()),'cache_validation':check}

def selected_jobs():
    rows=[json.loads(s) for s in (ROOT/'data/full49_v1/jobs.public.jsonl').read_text().splitlines()]
    cases={r['case_id']:r for r in map(json.loads,(ROOT/'data/full49_v1/cases.private.jsonl').read_text().splitlines())}
    return [r for r in rows if r['rotation']==0 and ((r['order']=='base' and (r['round'] in [0,r['last_round']//2,r['last_round']] or cases[r['case_id']]['deep_capture'])) or
                  (r['order'] in ['reverse','shuffle'] and r['round']==r['last_round'] and cases[r['case_id']]['deep_capture']))]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--limit',type=int,default=0);args=ap.parse_args();dest=ROOT/'runs/structured_names_v1'
    for f in ['observations','states']:(dest/f).mkdir(parents=True,exist_ok=True)
    selected=selected_jobs();spec={'source_sha256':sha(__file__),'helpers':{name:sha(ROOT/'src'/name) for name in ['phase6_measure.py','phase6_name_control.py','phase1_run_direct.py']},
        'protocol_sha256':sha(ROOT/'protocol/STRUCTURED_NAME_ADAPTATION.md'),'jobs':len(selected),'candidate_diseases':selected[0]['candidate_diseases'],
        'source_inputs_sha256':sha(ROOT/'data/full49_v1/jobs.public.jsonl'),'model_hashes':json.loads((ROOT/'runs/full49_v1/manifest.json').read_text())['model_hashes'],'api_cost_usd':0}
    p=dest/'manifest.json'
    if p.exists():assert json.loads(p.read_text())==spec
    else:write_json(p,spec);(dest/'source_snapshot.py').write_bytes(__file__ and open(__file__,'rb').read())
    model,tok=load_model();start=time.time();done=0
    for i,row in enumerate(selected):
        path=dest/'observations'/f"{row['job_id']}.json"
        if path.exists():continue
        e=render(row,tok);a,z,cache=capture(model,e['ids'],e['token_groups'],e['evidence_ends'],row['deep_capture'],keep_cache=True)
        result=score_names(model,z,cache,e,validate=done<2 or i%50==0)
        ids,text,stop=greedy_answer(model,tok,z,clone(cache,len(e['ids'])),limit=64)
        try:generated=json.loads('{"diagnosis":"'+text)['diagnosis']
        except (ValueError,KeyError,TypeError):generated=None
        npz=dest/'states'/f"{row['job_id']}.npz";np.savez_compressed(npz,**{k:np.array(v) for k,v in a.items()},input_ids=np.array(e['ids']),token_groups=e['token_groups'],evidence_end_positions=e['evidence_ends'])
        rec={k:row[k] for k in ['job_id','case_id','family','order','round','last_round','deep_capture']};rec.update(result)
        rec.update(input_tokens=len(e['ids']),group_labels=e['group_labels'],group_token_counts=np.bincount(e['token_groups']).tolist(),
                   suffix_ids=e['suffix'],generated_text=text,generated_disease=generated,generated_in_candidates=generated in row['candidate_diseases'],free_stop=stop,
                   attention_max_error=float(np.array(a['attention_reconstruction_relative_rms']).max()),state_file=str(npz.relative_to(dest)),state_sha256=sha(npz),
                   prompt_sha256=hashlib.sha256(e['prompt'].encode()).hexdigest())
        write_json(path,rec);del a,z,cache;mx.clear_cache();done+=1
        if done==1 or done%10==0:print(json.dumps({'name_observation':i+1,'total':len(selected),'elapsed':time.time()-start}),flush=True)
        if args.limit and done>=args.limit:break
    if len(list((dest/'observations').glob('ddx*.json')))==len(selected):
        assert {f:sha(MODEL/f) for f in spec['model_hashes']}==spec['model_hashes'];write_json(dest/'completion.json',{'complete':True,'observations':len(selected),'weights_unchanged':True,'api_cost_usd':0})

if __name__=='__main__':main()
