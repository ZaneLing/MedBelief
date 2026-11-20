"""Recheck actual outputs, exact model inputs, raw-history provenance, and frozen history."""
from pathlib import Path
import hashlib,json
import numpy as np
from transformers import AutoTokenizer
ROOT=Path(__file__).resolve().parents[1]
RUNS=['phase2_initial_4b','phase2_pilot_4b','phase2_bp_repair_dev','phase2_bp_repair_confirm','phase2b_initial_4b','phase2b_confirm_4b','phase2c_answer_control_4b','phase2d_partial_fact_4b','phase3_future_pilot_4b','phase3_future_repeat_4b','phase3_update_repairs_4b']
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check_rule_label(x,run_name):
    f=x['facts'];d=x['domain']
    if d=='aki':positive=f['hours']<=48 and f['current']-f['baseline']>=26
    elif d=='dvt':positive=f['wells']>=2
    else:
        assert d=='bp' and f['n_daytime']>=14 and f['per_hour']>=2
        positive=(f['clinic_s']>=140 or f['clinic_d']>=90) and (f['abpm_s']>=135 or f['abpm_d']>=85)
    if run_name.startswith('phase3'):usable=x['target_usable']
    elif 'backup_available' in x:usable=x['target_usable'] or x['backup_available']
    elif 'usable' in x:usable=x['usable']
    elif 'source' in x:
        assert x['source'] in ['both_valid','irrelevant_withdrawn','relevant_withdrawn','valid','wrong_patient','not_qualified']
        usable=x['source'] in ['both_valid','irrelevant_withdrawn','valid']
    else:usable=True
    assert x['gold']==('unknown' if not usable else ('yes' if positive else 'no')),x['id']
def main():
    tok=AutoTokenizer.from_pretrained(ROOT/'.models/Qwen3-4B-8bit',local_files_only=True);checks=[];files=[];all_inputs={};all_outputs={};states=0
    for name in RUNS:
        run=ROOT/'runs'/name;m=json.loads((run/'metadata.json').read_text());c=json.loads((run/'completion.json').read_text());data=ROOT/m['data'];snap=run/'source_snapshot.py'
        assert digest(data)==m['data_sha256'] and digest(snap)==m['source_sha256']
        inp_list=list(map(json.loads,data.read_text().splitlines()));inp={r['id']:r for r in inp_list};out=list(map(json.loads,(run/'predictions.jsonl').read_text().splitlines()))
        assert len(inp_list)==len(inp)==len(out)==len({r['id'] for r in out})==c['records'] and {r['id'] for r in out}==set(inp) and c['complete']
        assert c['correct']==sum(r['prediction']==r['gold'] for r in out)
        assert c['parse_or_budget_failures']==sum(r['prediction'] is None for r in out)
        assert c['generation_tokens']==sum(r['generated_tokens'] for r in out)
        for r in out:
            x=inp[r['id']];assert r['gold']==x['gold'] and r['labels']==x['labels']
            check_rule_label(x,name)
            assert r['prediction'] is None or (r['finish_reason']=='stop' and x['labels'][r['prediction']]==r['letter'])
            messages=x['messages'] if 'messages' in x else [{'role':'user','content':x['prompt']}]
            ids=tok.apply_chat_template(messages,tokenize=True,return_dict=False,add_generation_prompt=True,enable_thinking=m['thinking'])
            if 'prompt_tokens' in r:assert len(ids)==r['prompt_tokens']
            if m['capture']:
                f=run/r['activation_file'];a=np.load(f);assert a['activations'].shape==(36,2560) and np.isfinite(a['activations']).all() and str(a['id'])==r['id']
                messages=x['messages'] if 'messages' in x else [{'role':'user','content':x['prompt']}]
                ids=tok.apply_chat_template(messages,tokenize=True,return_dict=False,add_generation_prompt=True,enable_thinking=m['thinking'])
                assert np.array_equal(a['input_ids'],ids),r['id'];states+=1;files.append(f)
                if 'prompt_tokens' in r:assert len(ids)==r['prompt_tokens']
        all_inputs[name]=inp;all_outputs[name]={r['id']:r for r in out}
        checks.append({'run_id':name,**c,'input_output_exact_token_and_state_checks':True,'rule_label_recomputed_from_structured_facts':True})
        files += [data,snap,run/'metadata.json',run/'completion.json',run/'predictions.jsonl']
    pair_counts={}
    for name,initial in [('phase2_pilot_4b','phase2_initial_4b'),('phase2b_confirm_4b','phase2b_initial_4b')]:
        inp=all_inputs[name];groups={}
        for x in inp.values():
            if x['history']=='current_only':continue
            key=tuple(x[k] for k in ['family_id','current_sign','source','old_sign']);groups.setdefault(key,{})[x['history']]=x
            iid=x.get('initial_id',x['family_id']+'_initial_'+x['old_sign']);actual=all_outputs[initial][iid]
            assert x['observed_initial']==actual['prediction']
            if x['history']=='own_raw_final':
                tail=actual['generated_text'].rsplit('</think>',1)[-1].strip()
                for line in x['messages'][1]['content'].splitlines():assert line in tail
        for group in groups.values():
            assert 'old_facts' in group
            assert 'own_judgment_summary' in group or group['old_facts']['observed_initial'] is None
            assert len({x['rng_key'] for x in group.values()})==1
            assert len({x['messages'][-1]['content'] for x in group.values()})==1
            assert len({x['messages'][0]['content'] for x in group.values()})==1
        pair_counts[name]=len(groups)
    for name in RUNS[-3:]:
        for x in all_inputs[name].values():
            actual=all_outputs['phase2c_answer_control_4b'][x['current_id']]
            original=all_inputs['phase2c_answer_control_4b'][x['current_id']]
            assert x['current_prediction']==actual['prediction']
            assert x['current_response']==actual['generated_text'].rsplit('</think>',1)[-1].strip()
            assert x['messages'][0]['content']==original['prompt']
            assert x['gold']==(original['current_sign'] if original['target_usable'] else 'unknown')
            if x.get('update_variant')!='without_previous_answer':assert x['messages'][1]['content']==x['current_response']
    old=json.loads((ROOT/'protocol/phase1b_delivery.json').read_text());historical=[]
    mutable=['README.md','paper/PAPER_LOGIC.md','protocol/STAGES.md','protocol/INTERNAL_MEASUREMENTS.md']
    for x in old['files']:
        p=ROOT/x['file'];archived=False
        if digest(p)!=x['sha256']:
            assert x['file'] in mutable,x['file'];p=ROOT/'protocol/archives/phase1b_delivery'/x['file'];archived=True
        assert digest(p)==x['sha256'],str(p);historical.append({'file':x['file'],'verified_at':str(p.relative_to(ROOT)),'archived_document':archived})
    original=json.loads((ROOT/'protocol/code_before_inference.json').read_text())
    for x in original['files']:assert digest(ROOT/x['file'])==x['sha256']
    files += list((ROOT/'figures/phase2').glob('*'))+list((ROOT/'reports').glob('PHASE2*.md'))+list((ROOT/'reports').glob('PHASE3*.md'))
    files += [ROOT/p for p in ['README.md','paper/PAPER_LOGIC.md','protocol/STAGES.md','protocol/INTERNAL_MEASUREMENTS.md','protocol/PHASE2_EXECUTION.md','protocol/phase2b_confirmation.json','protocol/phase2b_assembly.json','protocol/phase2_bp_repair_selection.json','runs/phase2_bp_repair_analysis.json']]
    files += list((ROOT/'src').glob('*phase2*.py'))+[ROOT/'src/mlx_experiment_v2.py']
    for folder in ['runs/phase2_pilot_4b','runs/phase2b_confirm_4b']:
        files += list((ROOT/folder).glob('analysis_v2.json'))+list((ROOT/folder).glob('errors_with_inputs.json'))
    for folder in ['runs/phase2_pilot_4b/probes_primary','runs/phase2_pilot_4b/probes_diagnostic_bp','runs/phase2b_confirm_4b/transfer_from_2a','runs/phase2c_answer_control_4b/answer_control_readout','runs/phase2c_answer_control_4b/source_readout_repairs']:files += list((ROOT/folder).glob('*.json'))
    files += [ROOT/'runs/phase2d_partial_fact_4b/analysis.json',ROOT/'protocol/phase2d_partial_fact.json',ROOT/'runs/phase2c_answer_control_4b/analysis.json',ROOT/'protocol/phase2c_answer_control.json',ROOT/'runs/phase2_pilot_4b/strong_text_controls.json',ROOT/'runs/phase2_pilot_4b/lexical_controls_v2.json']
    files += [ROOT/'runs/phase2_summary.json',ROOT/'protocol/SOURCES.md']
    files += [p for p in (ROOT/'protocol').glob('phase2*.json') if p.name!='phase2_delivery.json']
    files += list((ROOT/'data').glob('phase2*.jsonl'))
    files += list((ROOT/'src').glob('*phase3*.py'))+list((ROOT/'protocol').glob('phase3*.json'))+list((ROOT/'data').glob('phase3*.jsonl'))
    files += list((ROOT/'runs/phase3_future_pilot_4b').glob('analysis*.json'))+[ROOT/'runs/phase3_followup_summary.json',ROOT/'runs/code_snapshots/analyze_phase3_future_before_bootstrap_fix.py']
    result={'date':'2026-11-18','status':'Phase 2A-D and readout repairs completed; phase 3 small future-update pilot, second-seed repeat and wording/history controls completed; full phase 3 and phase 4 not completed',
        'records':sum(x['records'] for x in checks),'generation_tokens':sum(x['generation_tokens'] for x in checks),'activation_files':states,'api_cost_usd':0,
        'checks':checks,'matched_history_groups':pair_counts,'historical_phase1_and_phase1b_results_unchanged':True,'historical_files':historical,
        'files':[{'file':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(set(files))]}
    (ROOT/'protocol/phase2_delivery.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['files','historical_files']},indent=2))
if __name__=='__main__':main()
