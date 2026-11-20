"""Synthetic, guideline-bounded medical evidence materials; no patient records."""
from pathlib import Path
import hashlib,itertools,json

ROOT=Path(__file__).resolve().parents[1]
DOMAINS=['aki','bp','dvt']
ORDERS=[['yes','no','unknown'],['unknown','yes','no'],['no','unknown','yes']]
RULES={
 'aki':'Evaluate only whether the supplied pair meets the absolute creatinine-rise criterion: an increase of at least 26 micromol/L within 48 hours. Compare the observed values at their actual times; do not predict later measurements. Do not evaluate other AKI criteria or diagnose the cause. Both values must be usable measurements from this patient.',
 'bp':'Evaluate only this hypertension confirmation rule: clinic (systolic BP >=140 OR diastolic BP >=90), AND daytime ABPM (systolic mean >=135 OR diastolic mean >=85), in mmHg. The ABPM mean must use at least 14 daytime readings with at least 2 readings per waking hour. If the clinic threshold is met but ABPM data are missing or ineligible, there is insufficient evidence to evaluate this rule.',
 'dvt':'An adult with suspected DVT has had no investigations. Both ultrasound and D-dimer are available within 4 hours. A usable independently assessed two-level DVT Wells score >=2 calls for proximal leg-vein ultrasound first; a score <=1 calls for D-dimer first. If no usable score is available, the pathway is undetermined.'}
OPTIONS={
 'aki':{'yes':'The usable pair meets the specified creatinine-rise criterion.','no':'The usable pair does not meet that criterion.','unknown':'Insufficient usable measurements to evaluate that criterion.'},
 'bp':{'yes':'The usable readings meet the specified confirmation rule.','no':'The usable readings do not meet the specified confirmation rule.','unknown':'Insufficient eligible measurements to evaluate that rule.'},
 'dvt':{'yes':'Proximal leg-vein ultrasound first.','no':'D-dimer first.','unknown':'Insufficient usable information to choose either pathway.'}}

def facts(domain,i,positive,series='calibration'):
    off=0 if series=='calibration' else 17
    if domain=='aki':
        b=83+5*i+off;delta=26+3*i if positive else 4+2*i
        return {'baseline':b,'current':b+delta,'hours':[24,48,18,36,12,42][i%6]}
    if domain=='bp':
        return {'clinic_s':145+i,'clinic_d':92+i%3,'abpm_s':135+i if positive else 125-i,
                'abpm_d':83+i%4 if positive else 78-i%3,'n_daytime':14+2*i,'per_hour':2+i%2}
    return {'wells':2+i%4 if positive else 1-i%3}

def report(domain,f,report_id='R1'):
    if domain=='aki':return f"{report_id}: serum creatinine was {f['baseline']} and then {f['current']} micromol/L, {f['hours']} hours apart."
    if domain=='bp':return f"{report_id}: daytime ABPM mean {f['abpm_s']}/{f['abpm_d']} mmHg, calculated from {f['n_daytime']} valid daytime readings. The monitor was programmed for {f['per_hour']} measurements per waking hour. The monitoring protocol and all other quality requirements were met."
    return f"{report_id}: independently assessed two-level DVT Wells score {f['wells']}."

def introduction(domain,f,i):
    s=f"This is a synthetic adult patient aged {47+2*i}, not pregnant. "
    if domain=='bp':s+=f"The clinic BP is {f['clinic_s']}/{f['clinic_d']} mmHg, measured properly. "
    if domain=='dvt':s+='DVT is suspected; no investigations have been performed. '
    return s

def answer_options(domain,mapping):
    labels=dict(zip(ORDERS[mapping],'ABC'))
    return '\n'.join(f'{letter}: {OPTIONS[domain][s]}' for s,letter in sorted(labels.items(),key=lambda x:x[1])),labels

def prompt(domain,record,mapping):
    options,labels=answer_options(domain,mapping)
    text=(f"Apply the supplied medical rule to the current usable evidence. Report validity and whether a numerical rule is met are separate questions.\n"
          f"RULE\n{RULES[domain]}\nCURRENT RECORD\n{record}\n"
          "Interpret the three outcomes precisely: meets = usable required data are present and satisfy the rule; does not meet = usable required data are present and fail the rule; insufficient = the required usable data are missing. Inability to confirm because data are missing belongs to insufficient, not does not meet.\n"
          f"Choose the assessment justified now.\n{options}\n"
          "Think through the current evidence. End your response with a line in the form 'Final answer: X', replacing X with one option letter.")
    return text,labels

def make_calibration():
    rows=[]
    for d,i,gold in itertools.product(DOMAINS,range(6),['yes','no','unknown']):
        positive=(gold=='yes') if gold!='unknown' else bool(i%2)
        f=facts(d,i,positive);intro=introduction(d,f,i);r=report(d,f)
        if gold!='unknown':
            variations=[f"{r} Source check: this report belongs to this patient; all listed values are usable.",
                f"Confirmed patient-specific measurements: {r} All measurement conditions are satisfied.",
                f"Current verified report: {r} There is no source dispute or later correction.",
                f"The laboratory or assessment service has now supplied {r} Identity and measurement quality checks passed.",
                f"Patient identity verified. {r} Use these values; there are no other relevant measurements.",
                f"An earlier empty record was replaced by the verified current report: {r} These are the only usable values."]
            record=intro+variations[i]
        elif i%3==0:
            record=intro+'The required report has not arrived. There is no other usable report.'
        elif i%3==1:
            record=intro+r+' Identity audit: this entire report belongs to another patient. None of its values are usable here. No replacement report exists.'
        else:
            record=intro+r+' The reporting service has withdrawn the entire report as invalid. None of its values are usable. No replacement or other usable report exists.'
        for m in range(3):
            text,labels=prompt(d,record,m)
            rows.append({'id':f'cal_{d}_{i}_{gold}_m{m}','family_id':f'cal_{d}_{i}','scenario_id':f'cal_{d}_{i}_{gold}',
                'domain':d,'gold':gold,'mapping':m,'labels':labels,'facts':f,'record':record,'prompt':text,
                'clinical_review':'not independently reviewed','prompt_sha256':hashlib.sha256(text.encode()).hexdigest()})
    return rows

if __name__=='__main__':
    rows=make_calibration();p=ROOT/'data/phase1b_confirmation.jsonl'
    assert len(rows)==162 and len({r['id'] for r in rows})==162
    p.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    manifest={'records':162,'families':18,'current_record_versions':54,'option_rotations':3,'date':'2026-11-18',
        'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'model_outputs_seen':False,
        'role':'Confirmation of selected thinking-enabled medical rule measurement; no model fitting on these cases',
        'gate':{'accuracy_per_domain':0.9,'accuracy_per_answer_per_domain':0.8,'all_three_rotations_agree_per_domain':0.95},
        'clinical_review':False,'api_cost_usd':0}
    (ROOT/'protocol/phase1b_confirmation.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))
