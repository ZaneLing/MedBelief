"""Whole-set follow-ups after the first future-update pilot; retain all outcomes."""
from pathlib import Path
import copy,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    original=ROOT/'data/phase3_future_pilot.jsonl'
    rows=list(map(json.loads,original.read_text().splitlines()));assert len(rows)==32
    assert (ROOT/'runs/phase3_future_pilot_4b/completion.json').exists()
    variants=[]
    suffix=" Apply the same supplied medical rule and the same A/B/C answer options to the evidence justified now. End with 'Final answer: X'."
    for r in rows:
        for variant in ['neutral_update','explicit_status','without_previous_answer']:
            x=copy.deepcopy(r);x['original_future_id']=r['id'];x['id']=r['id']+'_'+variant;x['update_variant']=variant
            if variant in ['neutral_update','explicit_status']:
                update='New information: report R2 belongs to a different patient and cannot be used for this patient. All information previously given about report R1 remains exactly as stated. No new evidence is available.'
                if variant=='explicit_status':
                    update+=' In particular, R1 remains '+('usable evidence for this patient.' if r['target_usable'] else 'unusable evidence for this patient because it belongs to a different person.')
                x['messages'][-1]['content']=update+suffix;x['prompt']=update+suffix
            else:
                # Retain both original user messages, including the exact update wording.
                x['messages']=[m for m in x['messages'] if m['role']!='assistant']
            variants.append(x)
    data=ROOT/'data/phase3_update_repairs.jsonl';assert not data.exists()
    data.write_text(''.join(json.dumps(r)+'\n' for r in variants))
    protocol={'date':'2026-11-18','role':'Exploratory follow-up after seeing 3/32 first-pilot errors; not independent case confirmation',
      'prior_errors_seen':True,'new_outputs_seen':False,'families_reused':8,
      'whole_set_repeat':{'records':32,'data':str(original.relative_to(ROOT)),'sha256':sha(original),'seed':20261119},
      'repairs':{'records':96,'data':str(data.relative_to(ROOT)),'sha256':sha(data),'seed':20261118,
        'variants':['Neutral update avoids the ambiguous has-not-been-amended phrase, leaves R1 status implicit','Explicit reminder of R1 existing status, no new clinical fact','Remove the previous assistant answer only, preserving original user prompts']},
      'reason':'All 3 errors occurred in family-index10 wording, where R1 has not been amended could be misread as reversal of its earlier amended ownership. Test wording and previous-answer alternatives before attributing persistence to belief.',
      'primary_analysis':'Report all 32 rows per condition, all 16 unavailable-R1 rows, errors by family/domain, original-error overlap, and matched improvements/worsenings. No selected-case-only retry.',
      'limits':'Same numerical families and current model answers reused; prompt repairs change text/length, removing assistant also changes conversation structure. No causal intervention inside model.',
      'sampling':{'max_tokens':2048,'batch_size':16,'same_rng_keys_within_seed':True},'api_cost_usd':0,'source_sha256':sha(Path(__file__))}
    p=ROOT/'protocol/phase3_update_repairs.json';assert not p.exists();p.write_text(json.dumps(protocol,indent=2)+'\n')
    for run,d,seed in [('phase3_future_repeat_4b',original,20261119),('phase3_update_repairs_4b',data,20261118)]:
        cmd=[str(ROOT/'.runtime_mlx/bin/python'),'src/mlx_experiment_v2.py','--data',str(d.relative_to(ROOT)),'--run-id',run,'--model-dir','.models/Qwen3-4B-8bit','--model-manifest','protocol/qwen3_4b_8bit_snapshot.json','--max-tokens','2048','--batch-size','16','--seed',str(seed)]
        with (ROOT/'runs'/f'{run}.log').open('w') as log:subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        print(run+' completed',flush=True)
if __name__=='__main__':main()
