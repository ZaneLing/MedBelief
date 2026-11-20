"""Create a readable report strictly from completed runs and paired analyses."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]

def main():
    runs=[('1.7B，思考生成','phase1b_confirm_1p7b'),('4B，思考生成','phase1b_confirm_4b'),('4B，直接作答','phase1b_confirm_4b_direct')]
    analyses={n:json.loads((ROOT/'runs'/n/'analysis.json').read_text()) for _,n in runs}
    diag=json.loads((ROOT/'runs/phase1b_bp_decomposition/analysis.json').read_text())
    invalid=diag['groups']['present_but_unusable'];allrows=diag['groups']['all']
    rows=[]
    for label,n in runs:
        a=analyses[n];ds=a['domains'];total=sum(d['correct'] for d in ds.values())
        cells=[f"{ds[d]['correct']}/54" for d in ['aki','bp','dvt']]
        passed='、'.join({'aki':'肌酐','bp':'血压','dvt':'DVT'}[d] for d in ds if ds[d]['all_gates_pass']) or '无'
        rows.append('| '+ ' | '.join([label,*cells,f'{total}/162',passed])+' |')
    choices=[r for r in diag['paired_records'] if r['unusable_report'] and r['numeric_correct'] and r['source_correct'] and not r['decision_seed1_correct'] and not r['decision_seed2_correct']]
    first_only=[r for r in diag['paired_records'] if r['unusable_report'] and r['numeric_correct'] and r['source_correct'] and not r['decision_seed1_correct']]
    example=choices[0]['id'] if choices else (first_only[0]['id'] if first_only else None)
    texts={r['id']:r for r in map(json.loads,(ROOT/'data/phase1b_confirmation.jsonl').read_text().splitlines())}
    if example:
        e=texts[example];f=e['facts'];story=(f"一个实测例子（`{example}`）：诊室血压{f['clinic_s']}/{f['clinic_d']}，报告里的日间动态血压均值{f['abpm_s']}/{f['abpm_d']}，"
          f"来自{f['n_daytime']}个有效读数。但题目同时明确说这整份报告不能用于该病人。我们分别问数值是否过线、报告是否可用，模型都答对；"+
          ('问当前医学规则是否满足时，两次采样都没有回答应有的“资料不足”。' if choices else '问当前医学规则是否满足时，原采样没有回答应有的“资料不足”，第二次采样则答对了；这个错误没有在该次复测中保持。')+
          "这些是分开的提问，不能说它在同一次推理中同时知道和忽略了失效信息。")
    else:story='本组没有出现“数值题、来源题都正确，最终判断错误”的同一条配对记录，不能挑一个例子作此叙述。'
    finding=('本轮找到一个具体线索：**模型能分别答对数值题和报告有效性题，但最终医学判断仍可能出错。** 这值得继续研究，还不能归因为它在坚持旧信念。'
             if invalid['both_branches_correct_decision_seed1_wrong'] else
             '本轮定位到医学证据有效性处理不稳定。分解结果没有提供“子问题正确、最终判断错误”的配对证据，不能预设这种机制。')
    report=f'''# 医学信念实验：模型是否真正按证据的有效性作判断？

阶段1B交付｜2026-11-18｜全部本地运行，收费API支出 **0美元**。

{finding}

我们按你的要求研究LLM的医学信念，医生审核不作为阶段门槛。当前先使用三类规则明确的医学情境，把“知识不会”“数据没读懂”和“证据处理出错”分开。

## 先看一个简单例子

{story}

这个实验关心的是：**一份报告即使数字清楚，也可能没有资格支持当前病人的医学判断。模型能否把这两件事结合起来？**

## 本轮实际做了什么

第一部分是基础校准：肌酐变化标准、血压确认规则、DVT初始检查路径。18个病例骨架，54种当前证据情境，每种轮换3次答案位置；三个模型配置各跑162条，共486条确认／配置选择记录。

第二部分追查血压错误：保留同一批病例，分别问“报告里的数值说明什么”和“报告目前是否可用于这个病人”，共108条；再换随机种子重复54条原判断题。核心确认及后续诊断合计648条，另有开发和软件排查记录。

后续诊断在看到血压错误后才设计，属于探索；重复的是同一批病例，不冒称新病例验证。所有分支独立作答，前一个问题的答案没有交给后一个问题。

## 基础判断的结果

| 配置 | 肌酐 | 血压 | DVT | 合计 | 通过全部预定门槛的任务 |
|---|---:|---:|---:|---:|---|
{chr(10).join(rows)}

门槛没有改：每域总体正确率至少90%，每类答案至少80%，同一情境换3种选项顺序的一致率至少95%。4B思考配置的血压总体正确率为90.7%，但“资料不足”题只有13/18正确，仍不通过。总分高不能掩盖这一缺口。

![三个配置的分项校准](../figures/phase1b/01_calibration.png)

图从左到右：总体正确率、资料不足题正确率、选项轮换一致率；虚线为预定门槛。数字是试次统计，轮换选项不会产生新的独立病例。

1.7B使用FP16完整权重，4B使用官方8-bit权重；思考配置采用采样，直接作答采用贪心生成。因此这些差异不能单独归因为参数规模或思考模式。

## 追查结果：分开问与合起来判断

下面只比较**有具体数值、但报告已经不可用**的12条血压记录。这是4个病例骨架各轮换3次选项，不是12个独立患者。

| 同一份材料，分别问什么 | 正确数 |
|---|---:|
| 只读报告里的数值，是否达到阈值 | {invalid['numeric_correct']}/12 |
| 只问来源：这份报告是否已失效 | {invalid['source_correct']}/12 |
| 对病人给出最终判断，原随机种子 | {invalid['decision_seed1_correct']}/12 |
| 对病人给出最终判断，第二随机种子 | {invalid['decision_seed2_correct']}/12 |

![数值、来源和最终判断的分解对照](../figures/phase1b/03_evidence_decomposition.png)

在原种子下，有{invalid['both_branches_correct_decision_seed1_wrong']}条记录的数值题和来源题都正确，最终判断却错误；第二种子下为{invalid['both_branches_correct_decision_seed2_wrong']}条。两次最终判断都错、同时两个子问题都正确的配对记录有{invalid['both_branches_correct_both_decision_seeds_wrong']}条，来自{invalid['both_branches_correct_both_decision_seeds_wrong_families']}个病例骨架。这些结果支持继续检查“证据条件怎样进入医学结论”，还不等于已经定位内部原因。

全54条血压记录中，数值题{allrows['numeric_correct']}/54、来源题{allrows['source_correct']}/54；最终判断原种子{allrows['decision_seed1_correct']}/54、第二种子{allrows['decision_seed2_correct']}/54。完整配对表保存在[分析文件](../runs/phase1b_bp_decomposition/analysis.json)，没有只保留失败例子。

第二次采样另有{(54-allrows['decision_seed2_correct'])-(12-invalid['decision_seed2_correct'])}条非无效报告条件的判断错误。具体的有效报告失败中，模型把139/83的ABPM均值误判为未满足“收缩压≥135或舒张压≥85”。因此，条件组合或规则应用失败仍是需要排除的解释；不能把所有错误归入证据有效性机制。

## 它与“医学信念”的关系

当前证据涉及医学判断的一个基础环节：模型怎样决定什么能够算作证据。结果尚未证明它在维护自己的旧判断，因为本轮主要判断题没有让模型先形成一个真实的旧结论。

两个子问题分开能答对，只说明这些事实可以在对应问法下被正确提取。问题本身会改变注意方向，不能据此断言模型在原判断内部“明知故犯”。这里仍有来源信息没被正确整合、三种答案含义混淆、血压规则结构影响等竞争解释。

本轮没有证明新机制，也没有完成新颖性认定。能交付的是一个可核查的失败模式和下一步需要区分的解释，不把它提前写成论文结论。

## 内部表示记录到了哪一步

4B模型有36层，每层2560维。后续诊断的162条输入均保存了**读完问题、尚未生成任何思考或答案**时的每层向量；每条为`36 × 2560`数组，同时保存精确输入词元。正常前向与手工记录前向的9条检查中，最后位置logits差值均为0。

这些数组是真实模型状态，但还不是“医学信念分数”。本轮没有训练或交付已验证的信念读出器，没有做因果干预，也没有用二维散点图冒充内部机制证据。下一步应在新病例上分开测量数值、来源条件和最终判断，并检验哪类信息真正影响输出。

## 阶段状态与接下来怎么做

**阶段1B的运行和诊断已经交付；三类医学任务尚未整体通过。** 4B思考配置在肌酐、DVT域通过，血压域保留为失败域。阶段2正式机制实验尚未启动，准备好的阶段2材料和代码不算实验结果。

下一阶段分两条线：在已经通过校准的医学任务中，测试“模型自己形成旧判断—有效反证—依据撤回”的完整过程；对血压失败，使用新数值和新措辞，比较只补充正确数值、只补充正确来源状态、补充“来源状态决定报告能否使用”这条关系，确定差异来自哪里。先冻结新设计，再跑新病例；不能拿本轮选出的失败病例反复调试后宣称独立复现。

论文主线继续保持：**医学证据怎样进入判断，依据改变后判断怎样更新，以及哪些内部状态实际参与这个过程。** 本轮完成其中的测量和错误定位，不转向排行榜或题库建设。

## 文件与复现

- [开发修订、实现排查和运行审计](PHASE1B_AUDIT.md)
- [原始确认材料](../data/phase1b_confirmation.jsonl)；[后续分解材料](../data/phase1b_bp_decomposition.jsonl)
- [1.7B原始输出](../runs/phase1b_confirm_1p7b/predictions.jsonl)；[4B思考输出](../runs/phase1b_confirm_4b/predictions.jsonl)；[4B直接输出](../runs/phase1b_confirm_4b_direct/predictions.jsonl)
- [分解问题的原始输出](../runs/phase1b_bp_decomposition/predictions.jsonl)；[第二随机种子的判断输出](../runs/phase1b_bp_repeat/predictions.jsonl)
- [确认协议](../protocol/phase1b_confirmation.json)；[事后诊断协议](../protocol/phase1b_bp_decomposition.json)
- 图均有PNG和PDF，位于`figures/phase1b/`；内部向量位于两组后续诊断运行的`states/`目录。

规则限定范围依照[NICE肌酐条款](https://www.nice.org.uk/guidance/ng148/chapter/Recommendations)、[NICE血压条款](https://www.nice.org.uk/guidance/ng136/chapter/recommendations)、[NICE DVT路径](https://www.nice.org.uk/guidance/ng158/chapter/recommendations)，具体解释见[来源文件](../protocol/SOURCES.md)。本研究不把限定规则答案扩展为患者的完整诊疗结论。
'''
    (ROOT/'reports/PHASE1B_READ_FIRST.md').write_text(report)
    print('Wrote reports/PHASE1B_READ_FIRST.md')

if __name__=='__main__':main()
