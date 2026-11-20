"""Post-hoc task decomposition of the BP validity failure; no causal claim."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]

def main():
    rows=list(map(json.loads,(ROOT/'data/phase1b_confirmation.jsonl').read_text().splitlines()))
    original=[r for r in rows if r['domain']=='bp'];new=[]
    for r in original:
        i=int(r['family_id'].rsplit('_',1)[1]);absent=r['gold']=='unknown' and i%3==0
        for task in ['numeric_content','source_eligibility']:
            if task=='numeric_content':
                gold='unknown' if absent else ('yes' if r['facts']['abpm_s']>=135 or r['facts']['abpm_d']>=85 else 'no')
                question=('This branch asks only what the R1 document numerically states, not whether it is usable for this patient. '
                    'If R1 is present, do its stated ABPM mean numbers reach systolic >=135 OR diastolic >=85? '
                    'Read the document numbers even when it belongs to someone else or is withdrawn. If no R1 numbers are present, select the no-numbers option.')
                answers={'yes':'The stated R1 ABPM mean reaches at least one numerical threshold.',
                    'no':'The stated R1 ABPM mean is below both numerical thresholds.',
                    'unknown':'No R1 ABPM mean numbers are present to read.'}
            else:
                gold='unknown' if absent else ('no' if r['gold']=='unknown' else 'yes')
                question=('This branch asks only about the latest source status of report R1, not the BP numerical thresholds or a hypertension conclusion. '
                    'According to the current record and its latest audit, what is R1\'s status for use as this patient\'s evidence?')
                answers={'yes':'R1 is present and currently usable for this patient.',
                    'no':'R1 is present but the latest record says it is invalid or belongs to another patient.',
                    'unknown':'The required R1 report has not arrived; no R1 document is present.'}
            # Preserve the exact rule and current record. Ask each branch in a fresh conversation.
            prefix=r['prompt'].split('Interpret the three outcomes precisely:')[0]
            choices='\n'.join(f'{letter}: {answers[s]}' for s,letter in sorted(r['labels'].items(),key=lambda p:p[1]))
            text=prefix+question+'\n'+choices+"\nThink through the current record. End with one line 'Final answer: X', replacing X with one option letter."
            new.append({**r,'id':'decompose_'+task+'_'+r['id'],'original_id':r['id'],'original_decision_gold':r['gold'],
                        'task':task,'gold':gold,'prompt':text,'prompt_sha256':hashlib.sha256(text.encode()).hexdigest()})
    def save(name,rs):
        path=ROOT/'data'/name;assert not path.exists();path.write_text(''.join(json.dumps(r)+'\n' for r in rs));return hashlib.sha256(path.read_bytes()).hexdigest()
    hashes={'decomposition_sha256':save('phase1b_bp_decomposition.jsonl',new),
            'repeat_sha256':save('phase1b_bp_repeat.jsonl',original)}
    protocol={'date':'2026-11-18','role':'Post-hoc diagnostic follow-up; BP domain chosen after its errors were observed',
        'families':6,'original_decision_trials':54,'branch_trials':108,'original_decision_seeds':[20261118,20261119],
        'branch_seed':20261118,'model':'Qwen/Qwen3-4B-MLX-8bit','thinking':True,'max_tokens':2048,
        'branch_outputs_seen':False,'data':hashes,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'primary_report':'On all 12 present-but-unusable cases: numeric-content correctness, source-status correctness, decision correctness, and their paired cross-tabulation',
        'interpretation_limit':'Different questions can redirect attention. Correct isolated answers do not prove those facts were represented or used in the original decision computation.',
        'stage_status':'Diagnostic follow-up within phase 1B; does not override failed calibration gates or establish an internal causal mechanism',
        'api_cost_usd':0}
    (ROOT/'protocol/phase1b_bp_decomposition.json').write_text(json.dumps(protocol,indent=2)+'\n');print(json.dumps(protocol,indent=2))

if __name__=='__main__':main()
