from pathlib import Path
import json,time,hashlib,os
os.environ['TOKENIZERS_PARALLELISM']='false'
import torch
from transformers import AutoModelForCausalLM,AutoTokenizer

ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'runs/phase1b_pilot';out.mkdir(exist_ok=True)
rows={r['record_id']:r for r in map(json.loads,(ROOT/'data/phase1_cases.jsonl').read_text().splitlines())}
cases=[{'id':name,'prompt':rows[name]['prompt'],'gold':'B'} for name in
       ['aki_00_0_none_m0_evidence','dvt_00_0_none_m0_evidence']]
for change,gold in [(8,'B'),(30,'A')]:
    cases.append({'id':f'abstract_{change}','prompt':f'A rule is met if a quantity increases by at least 26 within 48 hours. It rises from 70 to {70+change} in 24 hours. Is the rule met? A: Yes. B: No. C: Insufficient information. Return only A, B, or C.','gold':gold})
trials=[]
for c in cases:
    for mode in ['letter','direct','thinking']:
        prompt=c['prompt']
        if mode=='direct':
            prompt=prompt.replace('Return exactly one uppercase letter, A, B, or C. Do not add an explanation.','Explain the decision briefly and end with the correct letter.')
            prompt=prompt.replace('Return only A, B, or C.','Explain the calculation briefly and end with the correct letter.')
        trials.append({**c,'prompt':prompt,'mode':mode})
(ROOT/'protocol/phase1b_pilot.json').write_text(json.dumps({'trials':trials,'thinking_budget':768,'thinking_sampling':{'temperature':0.6,'top_p':0.95,'top_k':20},'seed':20261118,'cost_usd':0},indent=2)+'\n')
torch.set_num_threads(4)
tok=AutoTokenizer.from_pretrained(ROOT/'.models/Qwen3-1.7B',local_files_only=True)
model=AutoModelForCausalLM.from_pretrained(ROOT/'.models/Qwen3-1.7B',local_files_only=True,torch_dtype=torch.float16,attn_implementation='eager').to('mps').eval()
with (out/'generations.jsonl').open('w',buffering=1) as f:
    for t in trials:
        torch.manual_seed(20261118)
        text=tok.apply_chat_template([{'role':'user','content':t['prompt']}],tokenize=False,add_generation_prompt=True,enable_thinking=t['mode']=='thinking')
        inputs=tok(text,return_tensors='pt',add_special_tokens=False).to('mps');tick=time.time()
        kwargs={'do_sample':True,'temperature':0.6,'top_p':0.95,'top_k':20} if t['mode']=='thinking' else {'do_sample':False}
        with torch.inference_mode():
            ids=model.generate(**inputs,max_new_tokens=768 if t['mode']=='thinking' else 96,**kwargs)
        new=ids[0,inputs.input_ids.shape[1]:].tolist()
        result={**t,'generated_text':tok.decode(new,skip_special_tokens=False),'generated_tokens':len(new),'seconds':time.time()-tick,'prompt_sha256':hashlib.sha256(t['prompt'].encode()).hexdigest(),'thinking_closed':151668 in new,'eos_reached':bool(new and new[-1]==151645)}
        f.write(json.dumps(result)+'\n');print(json.dumps(result),flush=True)
