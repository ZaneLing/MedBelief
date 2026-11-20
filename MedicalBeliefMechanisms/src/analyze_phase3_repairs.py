"""Summarize every future-update variant without selecting successful cases."""
from pathlib import Path
import json
import numpy as np
from analyze_phase2 import cell
from plot_phase2 import plt,COLORS,save
ROOT=Path(__file__).resolve().parents[1]
def read(run):return list(map(json.loads,(ROOT/'runs'/run/'predictions.jsonl').read_text().splitlines()))
def main():
    names=['phase3_future_pilot_4b','phase3_future_repeat_4b','phase3_update_repairs_4b']
    for n in names:assert json.loads((ROOT/'runs'/n/'completion.json').read_text())['complete']
    original,repeat,repairs=[read(n) for n in names];base={r['id']:r for r in original}
    sets={'original':original,'second_seed':repeat,**{k:[r for r in repairs if r['update_variant']==k] for k in ['neutral_update','explicit_status','without_previous_answer']}}
    out={}
    for k,rr in sets.items():
        assert len(rr)==32
        errors=[r for r in rr if r['prediction']!=r['gold']]
        matched=[]
        for r in rr:
            b=base[r.get('original_future_id',r['id'])]
            matched.append((b['prediction']==b['gold'],r['prediction']==r['gold']))
        out[k]={'overall':cell(rr),'r1_unusable':cell([r for r in rr if not r['target_usable']]),'r1_usable':cell([r for r in rr if r['target_usable']]),
          'by_family':{f:cell([r for r in rr if r['family_id']==f]) for f in sorted({r['family_id'] for r in rr})},
          'errors':[{'id':r['id'],'original_id':r.get('original_future_id',r['id']),'domain':r['domain'],'family_id':r['family_id'],'expected':r['gold'],'actual':r['prediction'],'previous':r['current_prediction'],'finish_reason':r['finish_reason']} for r in errors],
          'improvements_vs_original':sum(not a and b for a,b in matched),'worsenings_vs_original':sum(a and not b for a,b in matched),
          'repeated_original_errors':sum(not a and not b for a,b in matched)}
    forecast=json.loads((ROOT/'runs/phase3_future_pilot_4b/analysis.json').read_text())
    held=forecast['test_ids'];actual={r['id']:r for r in repeat};y=np.array([actual[i]['prediction']!=actual[i]['current_prediction'] for i in held],int)
    from sklearn.metrics import balanced_accuracy_score
    fixed={'repeat_targets_changed':y.tolist(),'hidden_layer36':float(balanced_accuracy_score(y,forecast['layer_predictions'][35])),
       'word_text':float(balanced_accuracy_score(y,forecast['text_controls']['words_with_numbers']['predictions'])),
       'character_text':float(balanced_accuracy_score(y,forecast['text_controls']['character_3_to_5']['predictions']))}
    result={'conditions':out,'fixed_pilot_predictions_scored_on_second_seed':fixed,'records':160,'families':8,'api_cost_usd':0,
       'interpretation_limit':'Exploratory follow-ups reuse current cases and responses. Two seeds are sampling checks, not independent case replication. Removing assistant changes length/conversation structure. Prompt repair is not an internal causal intervention.'}
    (ROOT/'runs/phase3_followup_summary.json').write_text(json.dumps(result,indent=2)+'\n')
    labels=['Original\nseed 1','Original\nseed 2','Clearer\nupdate','Restated\nR1 status','No previous\nanswer'];fig,ax=plt.subplots(figsize=(9,4.5));xx=np.arange(5)
    for off,key,color,label in [(-.18,'r1_usable',COLORS[0],'R1 still usable (16 each)'),(.18,'r1_unusable',COLORS[3],'R1 already unusable (16 each)')]:
        vals=[v[key]['correct']/v[key]['n'] for v in out.values()];bars=ax.bar(xx+off,vals,.34,label=label,color=color)
        for b,v in zip(bars,out.values()):ax.text(b.get_x()+b.get_width()/2,b.get_height()+.015,f"{v[key]['correct']}/{v[key]['n']}",ha='center',fontsize=9)
    ax.set_xticks(xx,labels);ax.set_ylim(0,1.15);ax.set_ylabel('Correct future decision');ax.set_title('After R2 is withdrawn, does the model use only surviving evidence?');ax.legend(loc='lower left',fontsize=8)
    fig.text(.5,.01,'Same 8 numerical families reused. Follow-ups were designed after seeing the first pilot errors.',ha='center',fontsize=9,color='#555');fig.tight_layout(rect=(0,.05,1,1));save(fig,'12_future_update_repairs')
    md=['# 后续更新试验：错误、复测与修正','', '模型当前回答正确以后，撤回支持它的R2报告。若R1本来有效，原结论可以保持；若R1本来属于别人，就应改答资料不足。每种条件32条，使用同一批8个数值病例骨架。','', '| 条件 | 总正确数 | R1仍有效 | R1本来无效 | 比首次变好／变坏 |','|---|---:|---:|---:|---:|']
    cn=['原措辞，首次采样','原措辞，第二次采样','更清楚的更新句','明确重申R1原状态','删除上一次模型回答']
    for label,v in zip(cn,out.values()):md.append(f"| {label} | {v['overall']['correct']}/32 | {v['r1_usable']['correct']}/16 | {v['r1_unusable']['correct']}/16 | {v['improvements_vs_original']}／{v['worsenings_vs_original']} |")
    md+=['','![后续更新与修正](../figures/phase2/12_future_update_repairs.png)','','## 首次错误的具体病例','', 'DVT病例中，R1评分为4，但属于另一人；R2评分为6，属于当前病人。模型原先正确回答先做超声，并在回答中明确说R1不能用。随后撤回R2，模型却把R1当成可以用，仍选超声。它此前说对了来源状态，不能保证后续正确保留这个状态。','', '首次3条错误来自两个数值骨架，但共享第3种更新措辞：“R1 has not been amended; retain its previous source status.” 更新后生成的解释把“未修改”读成“仍然有效”。这些解释帮助定位待排查的题面问题，不是可信的内部机制证据。','', '## 当前内部状态能提前预测吗','', f"在4个训练骨架、4个留出骨架上，用当前答案和任务类别预测是否改口，平衡正确率为{forecast['answer_domain_only']['balanced_accuracy']:.1%}。加入当前内部状态的预定末层为{forecast['layers'][35]['balanced_accuracy']:.1%}；只看当前题目及当前回答文字也为{forecast['text_controls']['words_with_numbers']['balanced_accuracy']:.1%}。没有观察到内部状态相对文字基线的增益。",'', f"把首次训练所得预测保持不变，对第二随机种子的实际更新重新评分：内部状态{fixed['hidden_layer36']:.1%}，词文字基线{fixed['word_text']:.1%}，字符文字基线{fixed['character_text']:.1%}。这仍是同一组病例的采样检查。",'', '这是阶段3的小型预试验。尚未控制当前答案概率；尚未建立“可见文字＋内部状态”对“可见文字”的严格增量模型；没有内部因果干预。不能写成完整机制验证。','', '## 全部错误列表','']
    for label,v in zip(cn,out.values()):
        md.append('**'+label+'**')
        md+=['']+[f"- `{r['id']}`：应为 `{r['expected']}`，实际 `{r['actual']}`。" for r in v['errors']]+(['无错误。'] if not v['errors'] else [])+['']
    md+=['## 可复查材料','','[完整设计及修订](../protocol/phase3_update_repairs.json)、[汇总JSON](../runs/phase3_followup_summary.json)、[首次输入](../data/phase3_future_pilot.jsonl)、[修正输入](../data/phase3_update_repairs.jsonl)。所有原始输出保存在三个运行目录的 `predictions.jsonl`，没有删除失败案例。']
    (ROOT/'reports/PHASE3_PILOT_READ_FIRST.md').write_text('\n'.join(md)+'\n')
    print(json.dumps({k:{'correct':v['overall']['correct'],'errors':v['errors']} for k,v in out.items()},indent=2))
if __name__=='__main__':main()
