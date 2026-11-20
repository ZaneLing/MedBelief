"""Single-field Yes/No/Unknown matched prompts; counterfactual, no new gold labels."""
import copy,hashlib,json,time
from pathlib import Path
import numpy as np
import mlx.core as mx
from phase14_run import ROOT,RUN,render
from phase6_measure import MODEL,load_model,capture
from phase9_names import score_names
from phase1_run_direct import sha,write_json

def main():
    assert (RUN/'completion.json').exists();dest=RUN/'polarity';dest.mkdir(exist_ok=True)
    data=ROOT/'data/belief_v2';cases=[c for c in map(json.loads,(data/'cases.private.jsonl').read_text().splitlines()) if c['deep_capture']]
    jobs={(r['case_id'],r['view'],r['round']):r for r in map(json.loads,(data/'jobs.public.jsonl').read_text().splitlines()) if r['order']=='base'};panel=json.loads((data/'panel.json').read_text())
    selected=[]
    for c in cases:
        choices=[t for t,g in enumerate(c['orders']['base'],1) if len(c['explicit_evidence_groups'][g])==1 and c['explicit_evidence_groups'][g][0]['data_type']=='B']
        assert choices;t=min(choices,key=lambda t:(abs(t-c['fixed_middle_round']),t));selected.append((c,t))
    spec={'source_sha256':sha(__file__),'protocol_sha256':sha(ROOT/'protocol/ANSWER_POLARITY_V2.md'),'selected':[{'case_id':c['case_id'],'round':t} for c,t in selected],'new_observations':24,'api_cost_usd':0}
    if (dest/'manifest.json').exists():assert json.loads((dest/'manifest.json').read_text())==spec
    else:write_json(dest/'manifest.json',spec);(dest/'source_snapshot.py').write_bytes(Path(__file__).read_bytes())
    model,tok=load_model();start=time.time()
    for i,(c,t) in enumerate(selected):
        path=dest/f"{c['case_id']}.json"
        if path.exists():continue
        row=jobs[c['case_id'],'panel',t];unknownrow=jobs[c['case_id'],'panel',t-1];counter=copy.deepcopy(row);item=counter['revealed_groups'][-1]['items'][0];assert item['answer_en']=='Yes' and len(counter['revealed_groups'][-1]['items'])==1
        evidence_id=item['evidence_id'];question=item['question_en'];item['answer_en']='No';item['values']=['counterfactual_no']
        e=render(counter,tok,panel);yes=render(row,tok,panel);unknown=render(unknownrow,tok,panel)
        assert e['prompt'].replace(question+' Answer: No.',question+' Answer: Yes.')==yes['prompt']
        assert unknown['prompt'].replace(question+' Answer: Unknown.',question+' Answer: Yes.')==yes['prompt']
        a,z,cache=capture(model,e['ids'],e['token_groups'],keep_cache=True);score=score_names(model,z,cache,e,validate=i==0)
        state=dest/f"{c['case_id']}.npz";np.savez_compressed(state,**{k:np.array(v) for k,v in a.items()},input_ids=e['ids'],token_groups=e['token_groups'])
        write_json(path,dict(case_id=c['case_id'],round=t,evidence_id=evidence_id,question=question,condition='counterfactual_no',source_label_not_used_as_counterfactual_truth=True,
            yes_job_id=row['job_id'],unknown_job_id=unknownrow['job_id'],tokens_no=len(e['ids']),tokens_yes=len(yes['ids']),tokens_unknown=len(unknown['ids']),
            yes_no_same_length=len(e['ids'])==len(yes['ids']),state_file=str(state.relative_to(RUN)),state_sha256=sha(state),prompt_sha256=hashlib.sha256(e['prompt'].encode()).hexdigest(),**score))
        del a,z,cache;mx.clear_cache();print(json.dumps({'polarity_case':i+1,'total':24,'elapsed':round(time.time()-start,1)}),flush=True)
    hashes=json.loads((RUN/'manifest.json').read_text())['model_hashes'];assert {f:sha(MODEL/f) for f in hashes}==hashes
    write_json(dest/'completion.json',dict(complete=True,new_observations=24,weights_unchanged=True,api_cost_usd=0))
if __name__=='__main__':main()
