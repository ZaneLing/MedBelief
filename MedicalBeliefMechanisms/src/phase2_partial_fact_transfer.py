"""New-domain follow-up of the partial-numerical-fact error observed in BP."""
from pathlib import Path
import hashlib,itertools,json
from medical_materials_v2 import prompt
ROOT=Path(__file__).resolve().parents[1]
def main():
    rows=[]
    for di,d in enumerate(['aki','dvt']):
        for i,sign,usable,method in itertools.product(range(3),['yes','no'],[True,False],['baseline','numbers']):
            family=f'partial_fact_{d}_{i}';m=(di+2*i)%3
            if d=='aki':
                b=259+13*i;delta=[32,37,45][i] if sign=='yes' else [8,13,20][i];hours=[22,32,42][i];f={'baseline':b,'current':b+delta,'hours':hours}
                report=f"R1 records serum creatinine {b} followed {hours} hours later by {b+delta} micromol/L. Both measurements passed technical laboratory quality checks. "
                baseline='The creatinine concentrations are reported in micromol/L, and the interval is reported in hours. This note describes the measurement units used in the record for the current assessment.'
                numbers=f"Reading only the printed values: the change is {delta} micromol/L over {hours} hours. The numerical increase is {'at or above' if sign=='yes' else 'below'} 26 micromol/L. This printed pair therefore {'satisfies' if sign=='yes' else 'does not satisfy'} the specified numerical change condition."
            else:
                score=[3,5,6][i] if sign=='yes' else [1,0,-1][i];f={'wells':score}
                report=f"R1 records an independently assessed two-level DVT Wells score of {score}. The assessment was signed off. "
                baseline='The Wells score is reported as a numerical clinical assessment score. Both named investigations are available within the stated time window; this note describes the terminology used in the current record.'
                numbers=f"Reading only the printed score: {score} is {'at or above 2' if sign=='yes' else 'at or below 1'}. The printed score therefore falls in the numerical branch labelled {'proximal leg-vein ultrasound first' if sign=='yes' else 'D-dimer first'} under the supplied two-level rule."
            intro=f"Current patient: an adult aged {57+i}, not pregnant. "+('DVT is suspected and no investigations have been done. Both initial tests are available within 4 hours. ' if d=='dvt' else '')
            audit='The latest source check verifies that the entire R1 report belongs to this patient and remains usable. ' if usable else ('The identity audit establishes that the entire R1 report belongs to another patient. None of its contents can be used for the current patient. ' if i%2==0 else 'The reporting service has withdrawn the entire R1 report as invalid. None of its contents can be used for the current patient. ')
            record=intro+report+audit+'No replacement or other report is available.\nREVIEW NOTE\n'+(baseline if method=='baseline' else numbers)
            text,labels=prompt(d,record,m);rid=f"{family}_{sign}_{'valid' if usable else 'invalid'}_{method}"
            rows.append({'id':rid,'family_id':family,'family_index':i+12,'domain':d,'current_sign':sign,'usable':usable,'method':method,'gold':sign if usable else 'unknown','facts':f,'mapping':m,'labels':labels,'prompt':text,'record':record,'rng_key':f'{family}:{sign}:{usable}'})
    p=ROOT/'data/phase2d_partial_fact.jsonl';assert not p.exists();p.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    out={'date':'2026-11-18','source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'data_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'outputs_seen':False,'records':48,'families':6,
        'motivation':'Exploratory new-domain test, designed after BP development had two numerical-note errors and one new BP confirmation example had repeated the pattern. Do not call it preregistered before the BP observations.',
        'observed_trigger_ids':['bprep_0_no_invalid_numbers','bprep_3_no_invalid_numbers','bprep_4_no_invalid_numbers'],
        'design':'AKI and DVT, 3 new numerical families each; positive/negative printed result x usable/unusable report x neutral units note/correct partial numerical conclusion. The note never changes source eligibility.',
        'primary_metric':'Within-case error difference of numerical note versus neutral note, unusable reports; report both domains and directions, all failures, and usable-report controls.',
        'interpretation':'Tests whether the BP cue effect extends beyond its compound OR rule. No prior-judgment manipulation; this cannot alone establish belief persistence.',
        'sampling':{'seed':20261118,'max_tokens':2048,'batch_size':16,'paired_random_streams':True},'capture':False,'api_cost_usd':0}
    proto=ROOT/'protocol/phase2d_partial_fact.json';assert not proto.exists();proto.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()
