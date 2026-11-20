"""Frozen paired medical-belief pilot, following successful calibration only."""
from pathlib import Path
import argparse,hashlib,itertools,json
from medical_materials_v2 import DOMAINS,OPTIONS,prompt,report,introduction
ROOT=Path(__file__).resolve().parents[1]

def new_facts(domain,i,positive,old=False):
    assert 0<=i<4
    if domain=='aki':
        b=111+7*i+(9 if old else 0);delta=[28,35,39,44][i] if positive else [3,7,11,17][i]
        return {'baseline':b,'current':b+delta,'hours':[16,28,40,46][i]}
    if domain=='bp':
        return {'clinic_s':153+i,'clinic_d':95+i%2,'abpm_s':(142+i if positive else 129-i),
                'abpm_d':(88+i%3 if positive else 79-i%3),'n_daytime':18+2*i,'per_hour':2+i%2}
    return {'wells':[3,5,4,2][i] if positive else [0,-1,1,-2][i]}

def intro(d,f,i):
    return introduction(d,f,i+6)

def initial_rows():
    rows=[]
    for di,d in enumerate(DOMAINS):
        for i,s in itertools.product(range(4),['yes','no']):
            f=new_facts(d,i,s=='yes',True);m=(di+i)%3
            record=intro(d,f,i)+report(d,f,'R0')+' At this initial time, R0 is verified as belonging to this patient; its measurements and assessment are usable.'
            text,labels=prompt(d,record,m)
            rows.append({'id':f'belief_{d}_{i}_initial_{s}','family_id':f'belief_{d}_{i}',
                'domain':d,'family_index':i,'phase':'initial','old_sign':s,'gold':s,'mapping':m,
                'facts':f,'record':record,'prompt':text,'labels':labels})
    return rows

def current_text(d,i,new_sign,source,m):
    f=new_facts(d,i,new_sign=='yes');r1=report(d,f,'R1')
    wrappers=[f'Newly arrived report: {r1}',f'The current replacement record reads: {r1}',
              f'Updated measurements or assessment from the reporting service: {r1}',f'Current report received today. {r1}']
    old_invalid='The earlier R0 record was found to belong to a different patient. All R0 measurements and assessments are invalid for this patient. Any conclusion based on R0 must be reassessed.'
    r9=f'R9: measured standing height {164+3*i} cm. Height is not an input to the supplied rule.'
    if source=='both_valid':
        audit='Source audit: R1 and R9 both belong to this patient and remain usable.'
    else:
        withdrawn,retained=('R1','R9') if source=='relevant_withdrawn' else ('R9','R1')
        audit=(f'Source audit: {withdrawn} belongs to another patient. The entire {withdrawn} report is withdrawn and cannot be used. '
               f'{retained} belongs to this patient and remains usable. No replacement for {withdrawn} exists.')
    record=intro(d,f,i)+old_invalid+' '+wrappers[i]+' '+r9+' '+audit+' There is no other usable evidence for the rule.'
    text,labels=prompt(d,record,m)
    return text,labels,f,record

def save(rows,path):
    p=ROOT/path;p.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    return hashlib.sha256(p.read_bytes()).hexdigest()

def prepare():
    initial=initial_rows();digest=save(initial,'data/phase2_pilot_initial.jsonl')
    # Freeze all current factual stimuli before any initial or final generation.
    shells=[]
    for di,d in enumerate(DOMAINS):
        for i,s,source in itertools.product(range(4),['yes','no'],['both_valid','relevant_withdrawn','irrelevant_withdrawn']):
            m=(di+i)%3;text,labels,f,record=current_text(d,i,s,source,m)
            shells.append({'family_id':f'belief_{d}_{i}','domain':d,'family_index':i,'current_sign':s,'source':source,
                'gold':'unknown' if source=='relevant_withdrawn' else s,'mapping':m,'labels':labels,'prompt':text,'record':record,'facts':f})
    sd=save(shells,'data/phase2_pilot_current_shells.jsonl')
    manifest={'date':'2026-11-18','role':'Exploratory phase 2 pilot, not full 60-family phase 2 confirmation',
        'families':12,'initial_rows':24,'current_rows_planned':360,'initial_sha256':digest,'current_shells_sha256':sd,
        'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'outputs_seen':False,
        'required_calibration':'All three frozen phase1B gates pass in every domain for the selected model/configuration',
        'history_conditions':['current_only','old_facts','own_judgment_summary'],
        'source_conditions':['both_valid','relevant_withdrawn','irrelevant_withdrawn'],
        'sampling':{'seed':20261118,'max_tokens':2048,'temperature':0.6,'top_p':.95,'top_k':20},
        'probe_split':{'train_family_indices':[0,1],'test_family_indices':[2,3]},
        'probe_tasks':['current_report_numerical_direction','current_report_usable','old_report_numerical_direction'],
        'probe_model':'L2 logistic regression, C=1, per-layer train-only scaling; no layer selection on test',
        'probe_controls':['word 1-2 gram TFIDF, fit on training data only','within-family shuffled training labels'],
        'primary_comparison':'own_judgment_summary versus old_facts, paired by family, old sign, current sign, source; family cluster bootstrap',
        'secondary':'Withdraw relevant versus irrelevant report, conditional on history and current evidence',
        'invalid_initial_rule':'If initial output is censored or unparseable, omit its own-summary branch and report missingness; never substitute a desired judgment',
        'interpretation':'History is replayed context; old conclusion is a standardized summary of the actual generated judgment, not verbatim reasoning or persistent memory',
        'clinical_review_required':False,'paid_api_cost_usd':0}
    p=ROOT/'protocol/phase2_pilot.json'
    assert not p.exists(),'Do not overwrite a frozen protocol'
    p.write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2))

def assemble(initial_run):
    initial={r['id']:r for r in initial_rows()}
    actual={r['id']:r for r in map(json.loads,(ROOT/'runs'/initial_run/'predictions.jsonl').read_text().splitlines())}
    assert set(initial)==set(actual),'Initial run must finish before assembly'
    manifest=json.loads((ROOT/'protocol/phase2_pilot.json').read_text())
    shells_path=ROOT/'data/phase2_pilot_current_shells.jsonl'
    assert hashlib.sha256(shells_path.read_bytes()).hexdigest()==manifest['current_shells_sha256']
    rows=[];missing=[]
    for shell in map(json.loads,shells_path.read_text().splitlines()):
        base=f"{shell['family_id']}_{shell['current_sign']}_{shell['source']}"
        rows.append({**shell,'id':base+'_current_only','history':'current_only','old_sign':None,'observed_initial':None,
            'messages':[{'role':'user','content':shell['prompt']}]})
        for old_sign in ['yes','no']:
            iid=f"{shell['family_id']}_initial_{old_sign}";old=initial[iid];observed=actual[iid]['prediction']
            for history in ['old_facts','own_judgment_summary']:
                if history=='own_judgment_summary' and observed is None:
                    missing.append({'base':base,'initial_id':iid});continue
                summary='The earlier assessment was not retained. The earlier report is preserved in the conversation.'
                if history=='own_judgment_summary':summary='My initial assessment based on R0: '+OPTIONS[shell['domain']][observed]
                messages=[{'role':'user','content':old['prompt']},{'role':'assistant','content':summary},{'role':'user','content':shell['prompt']}]
                rows.append({**shell,'id':base+'_'+old_sign+'_'+history,'history':history,'old_sign':old_sign,
                    'observed_initial':observed,'initial_correct':observed==old_sign,'initial_id':iid,'messages':messages})
    assert len({r['id'] for r in rows})==len(rows)
    digest=save(rows,'data/phase2_pilot_current.jsonl')
    result={'records':len(rows),'data_sha256':digest,'initial_run':initial_run,'missing_own_branches':missing,
        'initial_correct':sum(actual[k]['prediction']==initial[k]['gold'] for k in initial),'initial_total':len(initial),
        'initial_predictions_sha256':hashlib.sha256((ROOT/'runs'/initial_run/'predictions.jsonl').read_bytes()).hexdigest()}
    (ROOT/'protocol/phase2_pilot_assembly.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','assemble']);p.add_argument('--initial-run')
    a=p.parse_args();prepare() if a.action=='prepare' else assemble(a.initial_run)
