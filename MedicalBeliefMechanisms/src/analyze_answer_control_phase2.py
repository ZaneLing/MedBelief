"""Behavior and matched-answer checks for the backup-report control."""
from pathlib import Path
import json
from analyze_phase2 import cell,paired
ROOT=Path(__file__).resolve().parents[1]
def main():
    run=ROOT/'runs/phase2c_answer_control_4b';meta=json.loads((run/'metadata.json').read_text());inp={r['id']:r for r in map(json.loads,(ROOT/meta['data']).read_text().splitlines())};rows=list(map(json.loads,(run/'predictions.jsonl').read_text().splitlines()));assert len(rows)==64 and {r['id'] for r in rows}==set(inp)
    out={'overall':cell(rows),'cells':[],'api_cost_usd':0}
    for d in ['aki','dvt']:
        for backup in [False,True]:
            for usable in [True,False]:
                rr=[r for r in rows if r['domain']==d and r['backup_available']==backup and r['target_usable']==usable]
                out['cells'].append({'domain':d,'backup_available':backup,'target_usable':usable,**cell(rr)})
    rr=[r for r in rows if r['backup_available']];out['same_correct_answer_pairs']=paired(rr,'source','wrong_patient','valid',['family_id','current_sign'])
    assert all(x['a_gold']==x['b_gold'] for x in out['same_correct_answer_pairs']['changes'])
    out['errors']=[{**r,'prompt':inp[r['id']]['prompt']} for r in rows if r['prediction']!=r['gold']]
    (run/'analysis.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='errors'},indent=2))
if __name__=='__main__':main()
