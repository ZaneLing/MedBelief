"""Readable case-level evidence with exact inputs and links to recorded outputs."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
HN={'current_only':'只看当前材料','old_facts':'保留旧事实','own_judgment_summary':'再保留自己的旧判断摘要','own_raw_final':'再保留自己的旧判断原文'}
SN={'both_valid':'当前报告可用','relevant_withdrawn':'当前关键报告属于别人','irrelevant_withdrawn':'只撤回无关身高报告','valid':'当前报告可用','wrong_patient':'当前报告属于别人','not_qualified':'当前报告未达到可使用条件'}
AN={'aki':{'yes':'达到所给肌酐变化标准','no':'未达到这条变化标准','unknown':'资料不足',None:'没有产生可判分的答案'},'dvt':{'yes':'先做超声','no':'先做D-dimer','unknown':'资料不足，不能选定路径',None:'没有产生可判分的答案'},'bp':{'yes':'满足给定血压确认规则','no':'不满足这条规则','unknown':'资料不足',None:'没有产生可判分的答案'}}
def main():
    parts=['# 阶段2：病例到底怎样使用\n','这些是程序生成的受控医学材料，不是真实患者。正确答案只针对题目明确给出的规则。每一行都对应已经保存的实际模型输出。\n']
    for run_id,family in [('phase2_pilot_4b','belief_aki_0'),('phase2b_confirm_4b','confirm_aki_0'),('phase2b_confirm_4b','confirm_dvt_0')]:
        run=ROOT/'runs'/run_id;meta=json.loads((run/'metadata.json').read_text());inp={r['id']:r for r in map(json.loads,(ROOT/meta['data']).read_text().splitlines())};rr=list(map(json.loads,(run/'predictions.jsonl').read_text().splitlines()))
        rows=[r for r in rr if r['family_id']==family and r['current_sign']=='yes' and r['old_sign'] in [None,'no']]
        parts.append(f'## 病例 `{family}`\n')
        if rows[0]['domain']=='aki':
            f=rows[0]['facts'];parts.append(f"当前报告的肌酐从 **{f['baseline']} 升到 {f['current']}**，相隔 **{f['hours']} 小时**。如果报告可用，这个变化达到题目给定标准。旧报告支持相反方向，随后发现旧报告属于另一人。\n")
        else:parts.append(f"当前报告填着 **Wells评分 {rows[0]['facts']['wells']}**。若该评分经过独立评估且可用于本患者，所给路径要求先做超声。旧报告的数值按规则应支持先做D-dimer，但本病例的实际初始回答错误地拒绝了负分，给出资料不足；随后旧报告被判定属于另一人。保留的是这个真实初始回答，不伪造正确旧结论。\n")
        parts.append('| 当前报告情况 | 给模型保留什么 | 应有回答 | 实际回答 | 记录ID |\n|---|---|---|---|---|')
        for r in sorted(rows,key=lambda x:(x['source'],list(HN).index(x['history']))):
            parts.append(f"| {SN[r['source']]} | {HN[r['history']]} | {AN[r['domain']][r['gold']]} | {AN[r['domain']][r['prediction']]} | `{r['id']}` |")
        parts.append('\n下面是该病例实际使用的一份完整输入，便于检查有没有把答案偷偷写进去。表中的其他条件通过改变来源状态或对话历史构造，完整版本在数据文件。\n')
        chosen=next(r for r in rows if r['source'] in ['both_valid','valid'] and r['history']=='own_judgment_summary');x=inp[chosen['id']]
        for message in x['messages']:parts.append(f"**{message['role']}**\n\n```text\n{message['content']}\n```\n")
        parts.append(f"[本运行的全部原始输出](../runs/{run_id}/predictions.jsonl)；[实际输入](../{meta['data']})。\n")
    parts.append('## 本轮所有错误，全部保留\n')
    for rid in ['phase2_pilot_4b','phase2b_confirm_4b']:
        rr=json.loads((ROOT/'runs'/rid/'errors_with_inputs.json').read_text());parts.append(f'### {rid}：{len(rr)}条\n')
        for r in rr:
            parts.append(f"- `{r['id']}`：应答“{AN[r['domain']][r['gold']]}”，实际“{AN[r['domain']][r['prediction']]}”；旧判断方向为`{r['observed_initial']}`，当前数值方向为`{r['current_sign']}`。")
        if not rr:parts.append('本运行没有判错或未完成答案。')
    (ROOT/'reports/PHASE2_CASES.md').write_text('\n'.join(parts)+'\n')
if __name__=='__main__':main()
