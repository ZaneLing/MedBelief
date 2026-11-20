"""New cases, concise source reports, and a new reason evidence may be unusable."""
from pathlib import Path
import argparse,hashlib,itertools,json,re
from medical_materials_v2 import prompt,OPTIONS
from cases import rule_answer
ROOT=Path(__file__).resolve().parents[1]
DOMAINS=['aki','dvt'];STATUSES=['valid','wrong_patient','not_qualified']

def facts(d,i,positive,old=False):
    assert 0<=i<4
    if d=='aki':
        b=147+9*i+(11 if old else 0);delta=[31,38,43,47][i] if positive else [6,10,16,21][i]
        return {'baseline':b,'current':b+delta,'hours':[20,30,38,44][i]}
    return {'wells':[4,6,7,3][i] if positive else [-1,1,0,-2][i]}

def evidence(d,f,rid):
    if d=='aki':return f"Form {rid} lists two serum creatinine results: {f['baseline']} micromol/L followed {f['hours']} hours later by {f['current']} micromol/L."
    return f"Form {rid} has the two-level DVT Wells score field filled with {f['wells']}."

def introduction(d,i):
    return f"Current patient: an adult aged {62+i}, not pregnant. "+('DVT is suspected, no tests have been done, and both initial tests can be completed within 4 hours. ' if d=='dvt' else '')

def source(d,status):
    if status=='valid':
        return ('R1 is allocated to the current patient. Both laboratory results passed quality checks and were authorised for interpretation.' if d=='aki' else
                'R1 is allocated to the current patient. The score was independently assessed for this patient and signed off for use.')
    if status=='wrong_patient':
        return ('Both measurements on R1 passed laboratory quality checks. The amended patient register assigns R1 to someone else, not the current patient.' if d=='aki' else
                'The score on R1 was independently assessed and signed off. The amended patient register assigns R1 to someone else, not the current patient.')
    return ('R1 is allocated to the current patient. The laboratory detected failed calibration affecting both listed measurements; the numeric entries are provisional, and neither result is authorised for interpretation.' if d=='aki' else
            'R1 is allocated to the current patient. Its numeric score field is an auto-filled placeholder; no independent Wells assessment has been performed for this patient, and this field has not been signed off for use.')

def compact_prompt(d,record,m):
    text,labels=prompt(d,record,m)
    # Same rule and answer definitions; remove the development instruction that
    # explicitly tells the model which conceptual distinction to attend to.
    text=text.replace('Apply the supplied medical rule to the current usable evidence. Report validity and whether a numerical rule is met are separate questions.',
                      'Use the supplied medical rule to assess the current record.')
    return text,labels

def write(path,rows):
    p=ROOT/path;assert not p.exists(),f'Frozen file already exists: {p}'
    p.write_text(''.join(json.dumps(x)+'\n' for x in rows));return hashlib.sha256(p.read_bytes()).hexdigest()

def prepare():
    initial=[];shells=[]
    for di,d in enumerate(DOMAINS):
        for i in range(4):
            family=f'confirm_{d}_{i}';m=(i+2*di+1)%3
            for sign in ['yes','no']:
                f=facts(d,i,sign=='yes',True);record=introduction(d,i)+evidence(d,f,'R0')+' '+source(d,'valid').replace('R1','R0')
                text,labels=compact_prompt(d,record,m)
                text+="\nBefore the final answer line, write one brief sentence stating the medical assessment supported by this initial report."
                initial.append({'id':family+'_initial_'+sign,'family_id':family,'family_index':i+4,'domain':d,'old_sign':sign,'gold':sign,'facts':f,'labels':labels,'mapping':m,'prompt':text,'record':record})
            for sign,status in itertools.product(['yes','no'],STATUSES):
                f=facts(d,i,sign=='yes');r=introduction(d,i)+'Correction to the earlier record: R0 was filed under the wrong patient and is allocated to someone else. '
                r+=evidence(d,f,'R1')+' '+source(d,status)+' No other current report is available.'
                text,labels=compact_prompt(d,r,m);gold=rule_answer(d,f,usable=status=='valid')
                shells.append({'family_id':family,'family_index':i+4,'domain':d,'current_sign':sign,'source':status,'gold':gold,'facts':f,'labels':labels,'mapping':m,'prompt':text,'record':r})
    hashes={'initial':write('data/phase2b_initial.jsonl',initial),'shells':write('data/phase2b_shells.jsonl',shells)}
    protocol={'date':'2026-11-18','outputs_seen':False,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'data_sha256':hashes,
        'role':'Independent-case development confirmation; 8 new simplified families, not a broad clinical generalization claim',
        'initial_records':16,'families':8,'current_records_planned':288,
        'history_conditions':['current_only','old_facts','own_judgment_summary','own_raw_final_on_opposed_reports'],
        'source_conditions':STATUSES,'new_eligibility_causes':{'aki':'measurement calibration failed; numerical entries not authorised','dvt':'unassessed auto-filled score placeholder'},
        'design_changes':'New numbers and wording; omit explicit reassess-old-conclusion sentence and leading validity-vs-numerical-rule coaching. Full source facts and outcome definitions retained.',
        'raw_history':'Actual initial medical-assessment prose after the thinking block, retained verbatim after removing standalone option-letter answer lines. A brief assessment sentence is requested initially. Includes more explanation/repetition than summary, so any effect is not uniquely ownership or belief.',
        'initial_format_amendment':'Before any phase2B outputs: phase2A had 6/24 initial final responses containing only a letter declaration. Request an assessment sentence in phase2B and remove standalone answer letters when replaying raw prose, to avoid making the raw-history contrast just letter copying. Pre-amendment files are archived.',
        'primary_comparison':'own_judgment_summary versus old_facts in the same current condition; raw final versus old_facts only where assigned old and current numeric direction oppose',
        'sampling':{'seed':20261118,'max_tokens':2048,'batch_size':16,'paired_random_streams':True},
        'transfer_readout':'Train only on phase2A primary data, test new families; fixed C=1 hidden readouts, all 36 layers, no selection using new cases. Text control tuning uses phase2A training data only.',
        'analysis_limits':'New source qualification condition is an outcome under study, not previously calibrated. Check no-history performance before attributing its errors to prior conclusions.',
        'clinical_review_required':False,'api_cost_usd':0}
    p=ROOT/'protocol/phase2b_confirmation.json';assert not p.exists();p.write_text(json.dumps(protocol,indent=2)+'\n');print(json.dumps(protocol,indent=2))

def assemble():
    proto=json.loads((ROOT/'protocol/phase2b_confirmation.json').read_text())
    for name,path in [('initial','data/phase2b_initial.jsonl'),('shells','data/phase2b_shells.jsonl')]:assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==proto['data_sha256'][name]
    initial={r['id']:r for r in map(json.loads,(ROOT/'data/phase2b_initial.jsonl').read_text().splitlines())}
    actual={r['id']:r for r in map(json.loads,(ROOT/'runs/phase2b_initial_4b/predictions.jsonl').read_text().splitlines())};assert set(initial)==set(actual)
    shells=list(map(json.loads,(ROOT/'data/phase2b_shells.jsonl').read_text().splitlines()));rows=[];missing=[]
    for s in shells:
        base=f"{s['family_id']}_{s['current_sign']}_{s['source']}"
        rows.append({**s,'id':base+'_current_only','history':'current_only','old_sign':None,'observed_initial':None,'analysis_role':'primary',
            'rng_key':base+':None','messages':[{'role':'user','content':s['prompt']}]})
        for old in ['yes','no']:
            iid=s['family_id']+'_initial_'+old;start=initial[iid];obs=actual[iid]['prediction']
            hs=['old_facts','own_judgment_summary']+(['own_raw_final'] if old!=s['current_sign'] else [])
            for h in hs:
                if h!='old_facts' and obs is None:missing.append({'base':base,'initial_id':iid,'history':h});continue
                middle='The earlier assessment was not retained. The earlier report is preserved in the conversation.'
                if h=='own_judgment_summary':middle='My initial assessment based on R0: '+OPTIONS[s['domain']][obs]
                if h=='own_raw_final':
                    tail=actual[iid]['generated_text'].rsplit('</think>',1)[-1].strip()
                    middle='\n'.join(line for line in tail.splitlines() if not re.fullmatch(r'\s*(?:(?:final\s+answer|answer)\s*:\s*)?[ABC][.]?\s*',line.replace('**','').replace('`',''),flags=re.I)).strip()
                    if not middle:
                        missing.append({'base':base,'initial_id':iid,'history':h,'reason':'No assessment prose remained after removing answer-only lines'});continue
                rows.append({**s,'id':base+'_'+old+'_'+h,'history':h,'old_sign':old,'observed_initial':obs,'initial_correct':obs==old,'initial_id':iid,'analysis_role':'primary',
                    'rng_key':base+':'+old,'messages':[{'role':'user','content':start['prompt']},{'role':'assistant','content':middle},{'role':'user','content':s['prompt']}]})
    sha=write('data/phase2b_current.jsonl',rows)
    manifest={'records':len(rows),'data_sha256':sha,'initial_correct':sum(actual[k]['prediction']==initial[k]['gold'] for k in initial),'initial_records':len(initial),'missing_branches':missing,
        'initial_predictions_sha256':hashlib.sha256((ROOT/'runs/phase2b_initial_4b/predictions.jsonl').read_bytes()).hexdigest()}
    (ROOT/'protocol/phase2b_assembly.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','assemble']);a=ap.parse_args();prepare() if a.action=='prepare' else assemble()
