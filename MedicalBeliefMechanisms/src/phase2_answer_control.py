"""Separate target-report eligibility from final answer using a usable backup report."""
from pathlib import Path
import hashlib,itertools,json
from medical_materials_v2 import prompt
ROOT=Path(__file__).resolve().parents[1]
def main():
    rows=[]
    for di,d in enumerate(['aki','dvt']):
        for i,sign,usable,backup in itertools.product(range(4),['yes','no'],[True,False],[False,True]):
            family=f'answer_control_{d}_{i}';m=(di+i+2)%3
            if d=='aki':
                b=203+11*i;delta=[30,34,40,46][i] if sign=='yes' else [5,9,14,19][i];f={'baseline':b,'current':b+delta,'hours':24+4*i}
                r1=f"R1 lists a creatinine pair: {b} followed {f['hours']} hours later by {b+delta} micromol/L. Both laboratory measurements passed quality checks. "
                b2=b+17;delta2=delta+2
                r2=f"R2 independently lists a different complete creatinine pair from the current patient: {b2} followed 30 hours later by {b2+delta2} micromol/L. Both measurements passed quality checks; R2 is authorised and usable. "
                extra='There can be more than one reported pair. Apply the specified change criterion to the usable complete pair(s). If any usable pair meets it, choose meets; if usable pairs are present and none meets it, choose does not meet; if no usable complete pair is present, choose insufficient. '
            else:
                score=[3,5,4,6][i] if sign=='yes' else [0,-1,1,-2][i];f={'wells':score}
                r1=f"R1 lists an independently assessed two-level DVT Wells score of {score}. The assessment was signed off. "
                score2=[4,3,6,5][i] if sign=='yes' else [-1,0,-2,1][i]
                r2=f"R2 independently lists a second two-level DVT Wells score of {score2} for the current patient. This assessment was performed and signed off for this patient; R2 is usable. "
                extra='There can be more than one reported score. Choose the initial pathway from usable independently assessed score(s). If more than one usable score is present, they imply the same pathway in these records. If none is usable, choose insufficient. '
            identity='The patient register assigns R1 to the current patient; R1 remains usable. ' if usable else 'The amended patient register assigns R1 to a different person; none of R1 is usable for the current patient. '
            record=f"The current patient is an adult aged {66+i}, not pregnant. "+('DVT is suspected, no investigations have been done, and both initial tests are available within 4 hours. ' if d=='dvt' else '')
            record+=r1+identity+(r2 if backup else 'No R2 or other replacement report is available. ')
            text,labels=prompt(d,record,m);text=text.replace('CURRENT RECORD\n',extra+'\nCURRENT RECORD\n')
            rid=f"{family}_{sign}_{'valid' if usable else 'wrong_patient'}_{'backup' if backup else 'no_backup'}"
            rows.append({'id':rid,'family_id':family,'family_index':i+8,'domain':d,'current_sign':sign,'source':'valid' if usable else 'wrong_patient','target_report':'R1','target_usable':usable,'backup_available':backup,
                'gold':sign if usable or backup else 'unknown','facts':f,'mapping':m,'labels':labels,'history':'current_only','old_sign':None,'observed_initial':None,'prompt':text,'record':record,'rng_key':f'{family}:{sign}:{backup}'})
    path=ROOT/'data/phase2c_answer_control.jsonl';assert not path.exists();path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    proto={'date':'2026-11-18','source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'data_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'outputs_seen':False,'records':64,'families':8,
        'motivation':'In 2A/2B, relevant-report unusability is confounded with the correct answer being insufficient. Add a usable backup report so R1 eligibility varies while the correct medical answer is held fixed.',
        'design':'2 domains x 4 new numerical families x 2 numerical directions x 2 R1 eligibility states x 2 backup availability states. Backup and R1 numeric directions agree. This is an explicit-rule measurement control, not a naturalistic clinical test.',
        'readout':'Train R1 usability readout on all 2A primary families. Fix C=1 and scaling on 2A. All 36 layers. Text control parameters inherited from 2A training-family CV. Evaluate no-backup and backup strata separately; no tuning on 2C.',
        'interpretation':'Generalization to R1 status independent of final answer would strengthen the measurement; failure cannot prove the model lacks the status concept. No causal intervention and no medical-belief claim from this control alone.',
        'sampling':{'seed':20261118,'max_tokens':2048,'batch_size':16,'paired_random_streams':True},'api_cost_usd':0,'clinical_review_required':False}
    p=ROOT/'protocol/phase2c_answer_control.json';assert not p.exists();p.write_text(json.dumps(proto,indent=2)+'\n');print(json.dumps(proto,indent=2))
if __name__=='__main__':main()
