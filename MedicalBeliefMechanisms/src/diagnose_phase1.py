"""Post-primary calibration diagnostics. Preserve primary results unchanged."""
from pathlib import Path
import gc
import hashlib
import json
import time

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runs/phase1_diagnostics'
OUT.mkdir(exist_ok=True)
rows=[json.loads(x) for x in (ROOT/'data/phase1_cases.jsonl').read_text().splitlines()]
primary={x['record_id']:x for x in map(json.loads,(ROOT/'runs/phase1_qwen3_1p7b/predictions.jsonl').read_text().splitlines())}
chosen=[r for r in rows if r['stage']=='evidence' and r['prior']=='none' and r['mapping']==0]
trials=[]
for r in chosen:
    rule=r['prompt'].split('RULE\n',1)[1].split('\n\nINITIAL RECORD',1)[0]
    question=r['prompt'].split('TARGET QUESTION\n',1)[1].split('\n\nOPTIONS',1)[0]
    extra=''
    if r['domain']=='bp':
        f=r['facts'];extra=f"Clinic BP is {f['clinic_s']}/{f['clinic_d']} mmHg. The adult patient is not pregnant. "
    minimal=(f"Apply this rule: {rule}\nAll measurements below are usable and belong to this patient. "
        f"{extra}{r['evidence_text']}\nQuestion: {question}\n"
        "A: Yes, the rule is met.\nB: No, the rule is not met.\nC: Insufficient information.\nReturn only A, B, or C.")
    trials.append({'id':'minimal_'+r['record_id'],'condition':'minimal','original_id':r['record_id'],
        'prompt':minimal,'gold':r['gold'],'labels':r['label_tokens']})
for r in chosen:
    if not r['base_id'].endswith('_00'):continue
    trials.append({'id':'no_source_'+r['record_id'],'condition':'source_sentence_removed',
        'original_id':r['record_id'],'prompt':r['prompt'].replace('\n\n'+r['source_text'],''),
        'gold':r['gold'],'labels':r['label_tokens']})
for i,(question,gold) in enumerate([
    ('What is 2+2? A: 4. B: 5. C: 6.','A'),
    ('Which number is larger? A: 3. B: 9. C: They are equal.','B'),
    ('Which word names a fruit? A: chair. B: stone. C: apple.','C')]):
    trials.append({'id':f'toy_{i}','condition':'simple_sanity','prompt':question+' Return only A, B, or C.',
        'gold':gold,'labels':{x:x for x in 'ABC'}})
cpu_rows=[r for r in chosen if r['base_id'].endswith('_00')]
plan={'purpose':'Post-primary diagnostic; not a preregistered mechanism test',
    'trigger':'No-prior valid-report accuracy was 50% in each domain',
    'mps_prompts':len(trials),'cpu_fp32_original_prompts':len(cpu_rows),
    'cpu_record_ids':[r['record_id'] for r in cpu_rows],
    'paid_api_cost_usd':0,'trials':trials}
(ROOT/'protocol/phase1_diagnostics.json').write_text(json.dumps(plan,indent=2)+'\n')
tokenizer=AutoTokenizer.from_pretrained(ROOT/'.models/Qwen3-1.7B',local_files_only=True)
torch.manual_seed(20261117);torch.set_num_threads(4)


def score(model,prompt,labels,device):
    text=tokenizer.apply_chat_template([{'role':'user','content':prompt}],tokenize=False,
        add_generation_prompt=True,enable_thinking=False)
    inputs=tokenizer(text,return_tensors='pt',add_special_tokens=False).to(device)
    with torch.inference_mode():
        logits=model(**inputs,use_cache=False,logits_to_keep=1).logits[0,-1].float()
    lp=torch.log_softmax(logits,dim=-1).cpu().numpy()
    probs={k:float(np.exp(lp[tokenizer.encode(v,add_special_tokens=False)[0]])) for k,v in labels.items()}
    mass=sum(probs.values());probs={k:v/mass for k,v in probs.items()}
    top=tokenizer.decode([int(lp.argmax())])
    return {'prediction':max(probs,key=probs.get),'probs':probs,'candidate_mass':mass,'full_top_token':top,
        'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest()}


results=[]
for device,dtype in [('mps',torch.float16),('cpu',torch.float32)]:
    model=AutoModelForCausalLM.from_pretrained(ROOT/'.models/Qwen3-1.7B',local_files_only=True,
        torch_dtype=dtype,attn_implementation='eager').to(device).eval()
    this=trials if device=='mps' else [{'id':'cpu_'+r['record_id'],'condition':'cpu_fp32_original',
        'original_id':r['record_id'],'prompt':r['prompt'],'gold':r['gold'],'labels':r['label_tokens']} for r in cpu_rows]
    for t in this:
        tick=time.time();result={k:v for k,v in t.items() if k!='prompt'}
        result.update(score(model,t['prompt'],t['labels'],device));result.update(device=device,dtype=str(dtype),seconds=time.time()-tick)
        if 'original_id' in t:
            original=primary[t['original_id']]
            result['primary_prediction']=original['prediction'];result['primary_probs']=original['semantic_probs']
        results.append(result)
        (OUT/'predictions.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in results))
        print(json.dumps({'done':len(results),'id':t['id'],'prediction':result['prediction'],'gold':t['gold']}),flush=True)
    del model;gc.collect()
    if device=='mps':torch.mps.empty_cache()
summary={}
for condition in sorted({r['condition'] for r in results}):
    rr=[r for r in results if r['condition']==condition]
    summary[condition]={'records':len(rr),'correct':sum(r['prediction']==r['gold'] for r in rr),
        'accuracy':float(np.mean([r['prediction']==r['gold'] for r in rr]))}
summary['cpu_vs_mps_primary']={'records':len(cpu_rows),'decision_changes':sum(r['prediction']!=r['primary_prediction'] for r in results if r['condition']=='cpu_fp32_original')}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2),flush=True)
