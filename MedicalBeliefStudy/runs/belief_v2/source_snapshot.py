"""Matched full disease-name scoring; fixed-question panel and original append."""
import argparse, hashlib, json, time
from pathlib import Path
import numpy as np
import mlx.core as mx
from phase6_measure import ROOT, MODEL, SYSTEM, load_model, capture
from phase9_names import render as append_render, score_names
from phase6_name_control import clone
from phase1_run_direct import sha,write_json,greedy_answer

RUN=ROOT/'runs/belief_v2'
def render(row,tok,panel):
    if row['view']=='append':return append_render(row,tok)
    known={v['evidence_id']:v for g in row['revealed_groups'] for v in g['items']}
    lines=[f"Patient: age {row['age']} years; sex {row['sex']}.",'Fixed questionnaire. Unknown means not available; it does not mean No.'];types=[2,0]
    for item in panel:
        key=item['evidence_id'];v=known.get(key)
        answer=('Recorded; value withheld' if row['view']=='presence' else v['answer_en']) if v else 'Unknown'
        lines.append(item['question_en']+' Answer: '+answer+'.');types.append((4 if item['is_antecedent'] else 3) if v else 5)
    lines+=['Candidate diagnoses:']+['- '+d for d in row['candidate_diseases']]
    types += [1]*(1+len(row['candidate_diseases']))
    lines+=['Select the best-supported candidate for the current presentation at this point. Choose one listed diagnosis even if evidence is incomplete. '
            'Complete the JSON object with exactly one candidate diagnosis copied verbatim from the list. Do not abbreviate or add an explanation. '
            'The output must have the form {"diagnosis":"exact candidate diagnosis"}.'];types.append(0)
    body='\n'.join(lines)
    prompt=tok.apply_chat_template([{'role':'system','content':SYSTEM},{'role':'user','content':body}],tokenize=False,add_generation_prompt=True,enable_thinking=False)+'{"diagnosis":"'
    enc=tok._tokenizer(prompt,add_special_tokens=False,return_offsets_mapping=True);ids=enc['input_ids'];offsets=enc['offset_mapping'];groups=np.zeros(len(ids),np.int16)
    pos=prompt.index(body)
    for line,kind in zip(lines,types):
        end=pos+len(line)
        for j,(a,b) in enumerate(offsets):
            if b>a and pos<=(a+b)/2<end:groups[j]=kind
        pos=end+1
    suffix=[]
    for d in row['candidate_diseases']:
        s=tok.encode(prompt+d+'"}',add_special_tokens=False);assert s[:len(ids)]==ids;suffix.append(s[len(ids):]+[tok.eos_token_id])
    return dict(prompt=prompt,ids=ids,token_groups=groups,evidence_ends=[],group_labels=['format','candidates','demographics','known_current','known_history','unknown_questions'],suffix=suffix)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--limit',type=int,default=0);args=ap.parse_args()
    for sub in ['observations','states']:(RUN/sub).mkdir(parents=True,exist_ok=True)
    data=ROOT/'data/belief_v2';jobs=[json.loads(s) for s in (data/'jobs.public.jsonl').read_text().splitlines()];panel=json.loads((data/'panel.json').read_text())
    spec={'source_sha256':sha(__file__),'data_manifest_sha256':sha(data/'manifest.json'),'scorer_sha256':sha(ROOT/'src/phase9_names.py'),
          'capture_sha256':sha(ROOT/'src/phase6_measure.py'),'protocol_sha256':sha(ROOT/'protocol/MECHANISM_CONTINUATION_V2.md'),
          'jobs':len(jobs),'candidate_diseases':jobs[0]['candidate_diseases'],'model_hashes':json.loads((ROOT/'runs/structured_names_v1/manifest.json').read_text())['model_hashes'],'api_cost_usd':0}
    if (RUN/'manifest.json').exists():assert json.loads((RUN/'manifest.json').read_text())==spec
    else:write_json(RUN/'manifest.json',spec);(RUN/'source_snapshot.py').write_bytes(Path(__file__).read_bytes())
    model,tok=load_model();start=time.time();done=0
    for i,row in enumerate(jobs):
        path=RUN/'observations'/f"{row['job_id']}.json"
        if path.exists():continue
        e=render(row,tok,panel);a,z,cache=capture(model,e['ids'],e['token_groups'],keep_cache=True)
        errors=np.array(a['attention_reconstruction_relative_rms']);assert np.isfinite(errors).all() and errors.max()<.02
        assert np.allclose(np.array(a['attention_by_group']).sum(-1),1,atol=1e-5)
        result=score_names(model,z,cache,e,validate=done==0 or i%100==0)
        _,text,stop=greedy_answer(model,tok,z,clone(cache,len(e['ids'])),limit=48)
        try:generated=json.loads('{"diagnosis":"'+text)['diagnosis']
        except (ValueError,KeyError,TypeError):generated=None
        sp=RUN/'states'/f"{row['job_id']}.npz";np.savez_compressed(sp,**{k:np.array(v) for k,v in a.items()},input_ids=e['ids'],token_groups=e['token_groups'])
        rec={k:row[k] for k in ['job_id','case_id','cohort','family','view','order','round','last_round','deep_capture']}
        rec.update(result);rec.update(input_tokens=len(e['ids']),group_labels=e['group_labels'],group_token_counts=np.bincount(e['token_groups']).tolist(),suffix_ids=e['suffix'],
            generated_text=text,generated_disease=generated,free_stop=stop,attention_max_error=float(errors.max()),state_file=str(sp.relative_to(RUN)),state_sha256=sha(sp),prompt_sha256=hashlib.sha256(e['prompt'].encode()).hexdigest())
        write_json(path,rec);done+=1;del a,z,cache;mx.clear_cache()
        if done==1 or done%10==0:print(json.dumps({'job':i+1,'total':len(jobs),'view':row['view'],'tokens':len(e['ids']),'elapsed':round(time.time()-start,1)}),flush=True)
        if args.limit and done>=args.limit:break
    if len(list((RUN/'observations').glob('*.json')))==len(jobs):
        assert {f:sha(MODEL/f) for f in spec['model_hashes']}==spec['model_hashes']
        write_json(RUN/'completion.json',dict(complete=True,observations=len(jobs),weights_unchanged=True,api_cost_usd=0))
if __name__=='__main__':main()
