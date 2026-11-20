"""Consolidated numbers for staged human-readable reporting, without overwriting prior reports."""
from pathlib import Path
import json
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
RUNS=['phase2_initial_4b','phase2_pilot_4b','phase2_bp_repair_dev','phase2_bp_repair_confirm','phase2b_initial_4b','phase2b_confirm_4b','phase2c_answer_control_4b','phase2d_partial_fact_4b']
def read(p):return json.loads((ROOT/p).read_text())
def main():
    counts=[];families=set();states=0
    for rid in RUNS:
        m=read(f'runs/{rid}/metadata.json');c=read(f'runs/{rid}/completion.json');rows=list(map(json.loads,(ROOT/m['data']).read_text().splitlines()));assert c['complete'] and len(rows)==c['records']
        families.update(r['family_id'] for r in rows);states+=len(rows) if m['capture'] else 0;counts.append({'run_id':rid,**c})
    result={'runs':counts,'records':sum(r['records'] for r in counts),'family_skeletons':len(families),'activation_files':states,'generation_tokens':sum(r['generation_tokens'] for r in counts),'api_cost_usd':0,
        'phase2a':read('runs/phase2_pilot_4b/analysis_v2.json'),'phase2b':read('runs/phase2b_confirm_4b/analysis_v2.json'),
        'bp_repairs':read('runs/phase2_bp_repair_analysis.json'),'phase2c_behavior':read('runs/phase2c_answer_control_4b/analysis.json'),'phase2d':read('runs/phase2d_partial_fact_4b/analysis.json')}
    a=read('runs/phase2_pilot_4b/probes_primary/results.json');text=read('runs/phase2_pilot_4b/strong_text_controls.json')['scopes']['primary'];b=read('runs/phase2b_confirm_4b/transfer_from_2a/results.json')
    result['readout_last_layer_2a']={k:{'hidden':v['layers'][-1]['balanced_accuracy'],'family_bootstrap_95':v['last_layer_family_bootstrap_95'],'words':text[k]['controls']['words_with_numbers']['balanced_accuracy'],'characters':text[k]['controls']['character_3_to_5']['balanced_accuracy']} for k,v in a.items()}
    result['readout_last_layer_transfer']={k:{'hidden':v['layers'][-1]['balanced_accuracy'],'by_source':v['layers'][-1]['by_source'],'family_bootstrap_95':v['last_layer_family_bootstrap_95'],'words':v['text_controls']['words_with_numbers']['balanced_accuracy'],'characters':v['text_controls']['character_3_to_5']['balanced_accuracy']} for k,v in b.items()}
    cc=read('runs/phase2c_answer_control_4b/answer_control_readout/results.json')['results']
    result['answer_control_last_layer']={scope:{'hidden':v['layers'][-1]['strata'],'text':{k:x['strata'] for k,x in v['text_controls'].items()}} for scope,v in cc.items()}
    candidate=read('protocol/phase2c_layer_candidate.json')
    result['layer_candidate_validation']={'protocol':candidate,'strata':cc['all_2a_histories']['layers'][candidate['selected_layer']-1]['strata']}
    repairs=read('runs/phase2c_answer_control_4b/source_readout_repairs/results.json')['results']
    result['readout_repairs_last_layer']={scope:{'train_rows':v['train_rows'],'test_rows':v['test_rows'],'hidden':v['layers'][-1]['strata'],'text':{k:x['strata'] for k,x in v['text_controls'].items()}} for scope,v in repairs.items()}
    (ROOT/'runs/phase2_summary.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# 阶段2：完整数字表\n','本表由已完成的原始记录生成；主要解释见[通俗报告](PHASE2_READ_FIRST.md)。病例变体不等于独立患者。\n','| 运行 | 记录数 | 正确数 | 未产生可判分答案 | 生成词元数 |','|---|---:|---:|---:|---:|']
    for r in counts:lines.append(f"| {r['run_id']} | {r['records']} | {r['correct']} | {r['parse_or_budget_failures']} | {r['generation_tokens']} |")
    lines+=['',f"合计{result['records']}条记录，{len(families)}个数值病例骨架，{states}份内部状态。API支出0美元。",'\n## 历史对照\n','| 组别 | 范围 | 保留判断后更差的配对数 | 更好的配对数 | 配对数 | 错误率差，百分点 | 病例重采样95%区间，百分点 |','|---|---|---:|---:|---:|---:|---|']
    for name in ['phase2a','phase2b']:
        for scope,v in result[name]['subsets'].items():
            for key in ['old_judgment_effect','raw_answer_effect']:
                if key not in v:continue
                e=v[key];ci=e['family_bootstrap_95_percentile'];lines.append(f"| {name} {key} | {scope} | {e['a_hurts']} | {e['a_helps']} | {e['pairs']} | {100*e['error_difference']:.2f} | {100*ci[0]:.2f}—{100*ci[1]:.2f} |")
    lines+=['\n零宽度区间来自小样本中所有差值恰好为零，不是总体等效性证明。','\n## 血压修正\n','| 组别 | 方法 | 报告可用 | 报告不可用 |','|---|---|---:|---:|']
    for split,v in result['bp_repairs']['splits'].items():
        for m,x in v['methods'].items():lines.append(f"| {split} | {m} | {x['usable']['correct']}/{x['usable']['n']} | {x['unusable']['correct']}/{x['unusable']['n']} |")
    lines+=['\n## 内部读出：预定最后一层\n','| 数据 | 目标 | 内部向量 | 词和数字 | 字符片段 |','|---|---|---:|---:|---:|']
    for key in ['readout_last_layer_2a','readout_last_layer_transfer']:
        for t,v in result[key].items():lines.append(f"| {key} | {t} | {100*v['hidden']:.1f}% | {100*v['words']:.1f}% | {100*v['characters']:.1f}% |")
    lines+=['\n## 最终答案相同的对照\n','| 训练范围 | 是否有替代报告 | 内部向量 | 词和数字 | 字符片段 |','|---|---|---:|---:|---:|']
    for scope,v in result['answer_control_last_layer'].items():
        for b in ['no_backup','backup_present']:lines.append(f"| {scope} | {b} | {100*v['hidden'][b]['balanced_accuracy']:.1f}% | {100*v['text']['words_with_numbers'][b]['balanced_accuracy']:.1f}% | {100*v['text']['character_3_to_5'][b]['balanced_accuracy']:.1f}% |")
    lines+=['\n## 读出方法修正：未见病例结果\n','| 训练方法 | 替代报告 | 内部向量 | 词和数字 | 字符片段 |','|---|---|---:|---:|---:|']
    for scope,v in result['readout_repairs_last_layer'].items():
        for b in ['no_backup','backup_present']:lines.append(f"| {scope} | {b} | {100*v['hidden'][b]['balanced_accuracy']:.1f}% | {100*v['text']['words_with_numbers'][b]['balanced_accuracy']:.1f}% | {100*v['text']['character_3_to_5'][b]['balanced_accuracy']:.1f}% |")
    lines+=['\n## 正确局部事实的跨任务复查\n','| 任务 | 说明 | 报告可用 | 报告不可用 |','|---|---|---:|---:|']
    for d,v in result['phase2d']['domains'].items():
        for m in ['baseline','numbers']:x=v[m];lines.append(f"| {d} | {m} | {x['usable']['correct']}/{x['usable']['n']} | {x['unusable']['correct']}/{x['unusable']['n']} |")
    (ROOT/'reports/PHASE2_TABLES.md').write_text('\n'.join(lines)+'\n');print(json.dumps({k:result[k] for k in ['records','family_skeletons','activation_files','generation_tokens','api_cost_usd']},indent=2))
if __name__=='__main__':main()
