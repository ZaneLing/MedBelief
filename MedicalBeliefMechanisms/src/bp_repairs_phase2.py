"""New BP cases: development method selection, then untouched-case confirmation."""
from pathlib import Path
import argparse,hashlib,json
from medical_materials_v2 import prompt
from cases import rule_answer
ROOT=Path(__file__).resolve().parents[1]
METHODS=['baseline','numbers','source','binding','quality_wording']
TIE_ORDER=['binding','source','quality_wording','numbers']

def build(i,sign,usable,method):
    split='development' if i<4 else 'confirmation';positive=sign=='yes'
    f={'clinic_s':158+i,'clinic_d':96+i%3,'abpm_s':(140+i if i%2==0 else 131-i%3) if positive else 128-i,
       'abpm_d':(81+i%2 if i%2==0 else 86+i%3) if positive else 79-i%4,'n_daytime':18+2*i,'per_hour':2+i%2}
    intro=f"This synthetic adult patient is aged {52+i}, not pregnant, with properly measured clinic BP {f['clinic_s']}/{f['clinic_d']} mmHg. "
    q='technically successful daytime measurements' if method=='quality_wording' else 'valid daytime readings'
    report=(f"R1 gives a daytime ABPM mean of {f['abpm_s']}/{f['abpm_d']} mmHg, calculated from {f['n_daytime']} {q}. "
        f"The monitor was programmed for {f['per_hour']} measurements per waking hour. The monitoring protocol and all other quality requirements were met. ")
    if usable:
        audit='The latest source audit confirms that the entire report belongs to this patient and remains usable.'
    elif i%2==0:
        audit='The latest identity audit establishes that the entire report belongs to a different patient. None of its values can be used here. There is no replacement report.'
    else:
        audit='The reporting service has withdrawn the entire report as invalid. None of its values can be used for this patient. There is no replacement report.'
    s=f['abpm_s']>=135;d=f['abpm_d']>=85
    notes={
        'baseline':'Blood pressure values in this record are expressed in millimetres of mercury. The question concerns the current assessment under the stated rule; retain these reporting units.',
        'numbers':f"Reading only the printed numbers: systolic is {'at or above' if s else 'below'} 135; diastolic is {'at or above' if d else 'below'} 85. The printed ABPM mean therefore {'satisfies' if s or d else 'does not satisfy'} the numerical OR condition.",
        'source':('The current source-status field for R1 is: belongs to this patient and usable.' if usable else 'The current source-status field for R1 is: excluded and not usable for this patient.')+' This field refers to the whole report.',
        'binding':'Apply patient-specific eligibility before applying numerical thresholds. Measurement quality does not establish patient identity or current report validity. Excluded reports supply no usable numbers to the patient-level rule.',
    }
    note=notes['baseline'] if method=='quality_wording' else notes[method]
    record=intro+report+audit+' No other ABPM report is available.\nREVIEW NOTE\n'+note
    text,labels=prompt('bp',record,i%3);gold=rule_answer('bp',f,usable=usable)
    base=f"bprep_{i}_{sign}_{'valid' if usable else 'invalid'}"
    return {'id':base+'_'+method,'family_id':f'bprep_{i}','family_index':i,'split':split,'domain':'bp',
        'method':method,'current_sign':sign,'usable':usable,'gold':gold,'labels':labels,'mapping':i%3,
        'facts':f,'record':record,'prompt':text,'rng_key':base,'prompt_sha256':hashlib.sha256(text.encode()).hexdigest()}

def write_frozen(path,rows):
    p=ROOT/path;assert not p.exists(),f'Frozen output already exists: {p}'
    p.write_text(''.join(json.dumps(r)+'\n' for r in rows));return hashlib.sha256(p.read_bytes()).hexdigest()

def prepare():
    rows=[build(i,s,u,m) for i in range(8) for s in ['yes','no'] for u in [True,False] for m in METHODS]
    assert len(rows)==160 and len({r['id'] for r in rows})==160
    hashes={}
    for split in ['development','confirmation']:
        hashes[split]=write_frozen(f'data/phase2_bp_repair_{split}.jsonl',[r for r in rows if r['split']==split])
    manifest={'date':'2026-11-18','outputs_seen':False,'data_sha256':hashes,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'new_families':8,'development_families':[0,1,2,3],'confirmation_families':[4,5,6,7],
        'methods':METHODS,'selection_tie_order':TIE_ORDER,'paired_random_streams':True,
        'if_development_baseline_perfect':'Run all methods in confirmation, exploratory ceiling/generalization analysis; do not claim a selected repair',
        'otherwise':'Select highest accuracy non-baseline method, ties by fixed order, compare with baseline in confirmation',
        'primary_metric':'Family-paired error difference; also report valid versus invalid report performance',
        'clinical_review_required':False,'api_cost_usd':0}
    (ROOT/'protocol/phase2_bp_repairs.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2))

def select():
    path=ROOT/'runs/phase2_bp_repair_dev/predictions.jsonl';rr=list(map(json.loads,path.read_text().splitlines()));assert len(rr)==80
    scores={m:sum(r['prediction']==r['gold'] for r in rr if r['method']==m) for m in METHODS}
    if scores['baseline']==16:selected=METHODS;reason='Development baseline at ceiling; no repair selected'
    else:
        best=max(TIE_ORDER,key=lambda m:scores[m]);selected=['baseline',best];reason='Highest development accuracy non-baseline method; frozen tie order used'
    heldout=ROOT/'data/phase2_bp_repair_confirmation.jsonl';manifest=json.loads((ROOT/'protocol/phase2_bp_repairs.json').read_text())
    assert hashlib.sha256(heldout.read_bytes()).hexdigest()==manifest['data_sha256']['confirmation']
    rows=[r for r in map(json.loads,heldout.read_text().splitlines()) if r['method'] in selected]
    sha=write_frozen('data/phase2_bp_repair_selected_confirmation.jsonl',rows)
    selection={'scores_out_of_16':scores,'selected_methods':selected,'reason':reason,'confirmation_rows':len(rows),
        'selected_data_sha256':sha,'development_predictions_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'confirmation_outputs_seen':False}
    p=ROOT/'protocol/phase2_bp_repair_selection.json';assert not p.exists();p.write_text(json.dumps(selection,indent=2)+'\n');print(json.dumps(selection,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','select']);a=p.parse_args();prepare() if a.action=='prepare' else select()
