from pathlib import Path
import json,os,time,inspect,hashlib
os.environ['TOKENIZERS_PARALLELISM']='false'
import numpy as np
import torch,transformers
from transformers import AutoTokenizer,AutoModelForCausalLM
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'runs/phase1b_reference';out.mkdir(exist_ok=True)
rows=[r for r in map(json.loads,(ROOT/'data/phase1_cases.jsonl').read_text().splitlines())
      if r['base_id'].endswith('_00') and r['prior']=='none' and r['stage'] in ['initial','evidence','withdrawn']]
primary={r['record_id']:r for r in map(json.loads,(ROOT/'runs/phase1_qwen3_1p7b/predictions.jsonl').read_text().splitlines())}
(out/'protocol.json').write_text(json.dumps({'record_ids':[r['record_id'] for r in rows],'transformers':transformers.__version__,'torch':torch.__version__,'purpose':'Same weights and prompts, different library version','api_cost_usd':0},indent=2)+'\n')
torch.set_num_threads(4)
tok=AutoTokenizer.from_pretrained(ROOT/'.models/Qwen3-1.7B',local_files_only=True)
model=AutoModelForCausalLM.from_pretrained(ROOT/'.models/Qwen3-1.7B',local_files_only=True,torch_dtype=torch.float16,attn_implementation='eager').to('mps').eval()
results=[];cache={}
for r in rows:
    key=r['prompt_sha256']
    if key not in cache:
        text=tok.apply_chat_template([{'role':'user','content':r['prompt']}],tokenize=False,add_generation_prompt=True,enable_thinking=False)
        inputs=tok(text,return_tensors='pt',add_special_tokens=False).to('mps')
        with torch.inference_mode():v=model(**inputs,use_cache=False,logits_to_keep=1).logits[0,-1].float()
        lp=torch.log_softmax(v,dim=-1).cpu().numpy();p={k:float(np.exp(lp[tok.encode(c,add_special_tokens=False)[0]])) for k,c in r['label_tokens'].items()};mass=sum(p.values());p={k:v/mass for k,v in p.items()}
        cache[key]={'prediction':max(p,key=p.get),'semantic_probs':p,'candidate_mass':mass,'full_top_token':tok.decode([int(lp.argmax())])}
    old=primary[r['record_id']];result={'record_id':r['record_id'],'gold':r['gold'],**cache[key],'primary_prediction':old['prediction'],'probability_l1_difference':sum(abs(cache[key]['semantic_probs'][k]-old['semantic_probs'][k]) for k in old['semantic_probs'])}
    results.append(result)
(out/'predictions.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in results))
summary={'records':len(results),'unique_prompts':len(cache),'correct':sum(r['prediction']==r['gold'] for r in results),'decision_changes':sum(r['prediction']!=r['primary_prediction'] for r in results),'mean_probability_l1_difference':float(np.mean([r['probability_l1_difference'] for r in results])),'max_probability_l1_difference':max(r['probability_l1_difference'] for r in results),'transformers':transformers.__version__}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2),flush=True)
