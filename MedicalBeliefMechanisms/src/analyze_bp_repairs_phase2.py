"""Analyze frozen BP repair development and new-family confirmation separately."""
import json
from pathlib import Path
from analyze_phase2 import cell,paired
ROOT=Path(__file__).resolve().parents[1]
def main():
    selection=json.loads((ROOT/'protocol/phase2_bp_repair_selection.json').read_text());out={'selection':selection,'splits':{}}
    for split,runid in [('development','phase2_bp_repair_dev'),('confirmation','phase2_bp_repair_confirm')]:
        run=ROOT/'runs'/runid;meta=json.loads((run/'metadata.json').read_text());inp={r['id']:r for r in map(json.loads,(ROOT/meta['data']).read_text().splitlines())}
        rows=list(map(json.loads,(run/'predictions.jsonl').read_text().splitlines()));assert len(rows)==len(inp) and {r['id'] for r in rows}==set(inp)
        methods=sorted({r['method'] for r in rows});items={}
        for method in methods:
            rr=[r for r in rows if r['method']==method]
            items[method]={'overall':cell(rr),'usable':cell([r for r in rr if r['usable']]),'unusable':cell([r for r in rr if not r['usable']])}
            if method!='baseline':items[method]['paired_vs_baseline']=paired(rows,'method',method,'baseline',['family_id','current_sign','usable'])
        out['splits'][split]={'methods':items,'records':len(rows),'families':len({r['family_id'] for r in rows}),'errors':[r for r in rows if r['prediction']!=r['gold']]}
    (ROOT/'runs/phase2_bp_repair_analysis.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({s:{m:d['overall'] for m,d in x['methods'].items()} for s,x in out['splits'].items()},indent=2))
if __name__=='__main__':main()
