"""Development-only prompt diagnostics. These cases cannot be confirmation data."""
from pathlib import Path
import json,os,itertools,time
os.environ['TOKENIZERS_PARALLELISM']='false'
import numpy as np
import torch
from transformers import AutoModelForCausalLM,AutoTokenizer
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runs/phase1b_grid';OUT.mkdir(exist_ok=True)
RULES={
 'aki':'A serum creatinine increase of at least 26 micromol/L within 48 hours meets the absolute-rise criterion. This question concerns this criterion only.',
 'bp':'The confirmation rule requires clinic systolic BP >=140 or diastolic BP >=90, AND daytime ABPM systolic mean >=135 or diastolic mean >=85. ABPM must have at least 14 daytime readings at 2 or more readings per hour.',
 'dvt':'For suspected DVT, use proximal leg-vein ultrasound first when the two-level Wells score is >=2. Use D-dimer first when the score is <=1. Both tests are available within 4 hours.'}
OPTIONS={
 'aki':{'yes':'The supplied pair meets the absolute creatinine-rise criterion.','no':'The supplied pair does not meet that criterion.','unknown':'Usable creatinine measurements are missing.'},
 'bp':{'yes':'The stated confirmation rule is met.','no':'Valid readings do not meet the stated confirmation rule.','unknown':'Required valid BP measurements are missing.'},
 'dvt':{'yes':'Proximal leg-vein ultrasound first.','no':'D-dimer first.','unknown':'Cannot choose a pathway without a usable Wells score.'}}
orders=[['yes','no','unknown'],['unknown','yes','no'],['no','unknown','yes']]
trials=[]
for domain,gold in itertools.product(RULES,['yes','no','unknown']):
    if domain=='aki':
        facts={} if gold=='unknown' else {'creatinine_before':70,'creatinine_after':100 if gold=='yes' else 78,'hours':24}
        sentence='No usable creatinine measurements are available.' if gold=='unknown' else f"Usable serum creatinine readings: 70 then {facts['creatinine_after']} micromol/L, 24 hours apart."
        aid='' if gold=='unknown' else f"Checked subtraction: {facts['creatinine_after']} - 70 = {facts['creatinine_after']-70}."
    elif domain=='bp':
        facts={'clinic_systolic':148,'clinic_diastolic':94}
        sentence='Clinic BP: 148/94 mmHg. '
        if gold=='unknown':sentence+='No usable ABPM data are available.'
        else:
            facts.update(abpm_systolic=140 if gold=='yes' else 124,abpm_diastolic=89 if gold=='yes' else 74,daytime_readings=16,readings_per_hour=2)
            sentence+=f"Valid daytime ABPM mean: {facts['abpm_systolic']}/{facts['abpm_diastolic']} mmHg, 16 daytime readings, 2 per hour."
        aid='' if gold=='unknown' else 'Checked ABPM comparison: '+('140 >= 135 and 89 >= 85.' if gold=='yes' else '124 < 135 and 74 < 85.')
    else:
        facts={} if gold=='unknown' else {'two_level_wells':2 if gold=='yes' else 1}
        sentence='No usable Wells score is available.' if gold=='unknown' else f"The independently assessed two-level Wells score is {facts['two_level_wells']}. No investigations have been performed."
        aid='' if gold=='unknown' else 'Checked score comparison: '+('2 >= 2.' if gold=='yes' else '1 < 2.')
    for style,mapping in itertools.product(['concise','structured','comparison_aid'],range(3)):
        labels=dict(zip(orders[mapping],'ABC'))
        body=json.dumps(facts) if style=='structured' else sentence
        prompt=f"An adult patient, not pregnant. All supplied readings or assessments belong to this patient and are valid.\nGuideline rule: {RULES[domain]}\nPatient information: {body}\n"
        if style=='comparison_aid':prompt+=aid+'\n'
        prompt+='Select the assessment or action justified by this information:\n'
        prompt+='\n'.join(f'{c}: {OPTIONS[domain][s]}' for s,c in sorted(labels.items(),key=lambda x:x[1]))
        prompt+='\nRespond with just the option letter.'
        trials.append({'id':f'{domain}_{gold}_{style}_m{mapping}','domain':domain,'gold':gold,'style':style,'mapping':mapping,'labels':labels,'prompt':prompt})
(ROOT/'data/phase1b_grid.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in trials))
(OUT/'protocol.json').write_text(json.dumps({'stage':'development only','records':len(trials),'base_scenarios':9,'comparison_aid':'localization control only; not eligible as primary calibration condition','api_cost_usd':0},indent=2)+'\n')
torch.set_num_threads(4)
tok=AutoTokenizer.from_pretrained(ROOT/'.models/Qwen3-1.7B',local_files_only=True)
model=AutoModelForCausalLM.from_pretrained(ROOT/'.models/Qwen3-1.7B',local_files_only=True,torch_dtype=torch.float16,attn_implementation='eager').to('mps').eval()
results=[]
with (OUT/'predictions.jsonl').open('w',buffering=1) as f:
    for t in trials:
        text=tok.apply_chat_template([{'role':'user','content':t['prompt']}],tokenize=False,add_generation_prompt=True,enable_thinking=False)
        inputs=tok(text,return_tensors='pt',add_special_tokens=False).to('mps')
        with torch.inference_mode():v=model(**inputs,use_cache=False,logits_to_keep=1).logits[0,-1].float()
        lp=torch.log_softmax(v,dim=-1).cpu().numpy();p={s:float(np.exp(lp[tok.encode(c,add_special_tokens=False)[0]])) for s,c in t['labels'].items()};mass=sum(p.values());p={k:v/mass for k,v in p.items()}
        top=tok.decode([int(lp.argmax())]);r={**{k:v for k,v in t.items() if k!='prompt'},'prediction':max(p,key=p.get),'probs':p,'candidate_mass':mass,'full_top_token':top,'full_prediction':{c:s for s,c in t['labels'].items()}.get(top.strip())}
        f.write(json.dumps(r)+'\n');results.append(r)
summary={}
for style in ['concise','structured','comparison_aid']:
    summary[style]={}
    for d in RULES:
        rr=[r for r in results if r['style']==style and r['domain']==d]
        summary[style][d]={'correct':sum(r['full_prediction']==r['gold'] for r in rr),'records':len(rr),'by_answer':{g:sum(r['full_prediction']==g for r in rr if r['gold']==g) for g in ['yes','no','unknown']}}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2),flush=True)
