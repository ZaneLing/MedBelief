"""Audit completion, input/output correspondence, activations and frozen files."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
from transformers import AutoTokenizer
ROOT=Path(__file__).resolve().parents[1]

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    required={'phase1b_confirm_1p7b':162,'phase1b_confirm_4b':162,'phase1b_confirm_4b_direct':162,
              'phase1b_bp_decomposition':108,'phase1b_bp_repeat':54}
    token=AutoTokenizer.from_pretrained(ROOT/'.models/Qwen3-4B-8bit',local_files_only=True)
    checks=[];assets=[];state_count=0;tokens=0
    for name,n in required.items():
        run=ROOT/'runs'/name;meta=json.loads((run/'metadata.json').read_text());completion=json.loads((run/'completion.json').read_text())
        source=run/'source_snapshot.py';assert digest(source)==meta['source_sha256']
        data=ROOT/meta['data'];assert digest(data)==meta['data_sha256']
        inp={r['id']:r for r in map(json.loads,data.read_text().splitlines())};rr=list(map(json.loads,(run/'predictions.jsonl').read_text().splitlines()))
        assert len(inp)==len(rr)==n and {r['id'] for r in rr}==set(inp) and completion['records']==n and completion['complete']
        assert completion['correct']==sum(r['prediction']==r['gold'] for r in rr)
        assert completion['parse_or_budget_failures']==sum(r['prediction'] is None for r in rr)
        assert completion['generation_tokens']==sum(r['generated_tokens'] for r in rr)
        for r in rr:
            assert r['gold']==inp[r['id']]['gold'] and r['labels']==inp[r['id']]['labels']
            assert r['prediction'] is None or (r['finish_reason']=='stop' and inp[r['id']]['labels'][r['prediction']]==r['letter'])
            if meta['capture']:
                f=run/r['activation_file'];a=np.load(f);assert a['activations'].shape==(36,2560) and np.isfinite(a['activations']).all()
                assert str(a['id'])==r['id']
                ids=token.apply_chat_template([{'role':'user','content':inp[r['id']]['prompt']}],tokenize=True,return_dict=False,add_generation_prompt=True,enable_thinking=meta['thinking'])
                assert np.array_equal(a['input_ids'],ids),r['id']
                state_count+=1
                assets.append(f)
        checks.append({'run_id':name,'records':n,'generated_tokens':completion['generation_tokens'],'cost_usd':0,'input_output_and_state_checks_pass':True})
        tokens+=completion['generation_tokens']
        assets.extend([data,source,run/'metadata.json',run/'completion.json',run/'predictions.jsonl'])
    frozen=json.loads((ROOT/'protocol/code_before_inference.json').read_text())
    for r in frozen['files']:assert digest(ROOT/r['file'])==r['sha256'],r['file']
    assets+=list((ROOT/'figures/phase1b').glob('*'))
    assets+=[ROOT/'reports/PHASE1B_READ_FIRST.md',ROOT/'reports/PHASE1B_AUDIT.md',ROOT/'runs/phase1b_bp_decomposition/analysis.json']
    assets+=[ROOT/p for p in ['README.md','paper/PAPER_LOGIC.md','protocol/STAGES.md','protocol/INTERNAL_MEASUREMENTS.md',
        'protocol/phase1b_confirmation.json','protocol/phase1b_bp_decomposition.json','protocol/qwen3_4b_8bit_snapshot.json',
        'src/analyze_calibration.py','src/analyze_evidence_diagnosis.py','src/build_evidence_diagnosis.py','src/mlx_experiment.py',
        'src/write_phase1b_report.py','src/plot_current_stages.py','src/verify_phase1b_delivery.py']]
    summary={'date':'2026-11-18','phase1b':'Completed and delivered; full three-domain calibration not passed',
        'calibrated_domains_in_4b_thinking':['aki','dvt'],'phase2':'Prepared only; not run',
        'clinical_review_required':False,'core_records':sum(required.values()),'core_generated_tokens':tokens,'activation_files':state_count,
        'api_cost_usd':0,'original_phase1_frozen_files_unchanged':True,'checks':checks,
        'files':[{'file':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(set(assets))]}
    assert state_count==162
    (ROOT/'protocol/phase1b_delivery.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='files'},indent=2))

if __name__=='__main__':main()
