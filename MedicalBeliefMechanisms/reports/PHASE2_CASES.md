# 阶段2：病例到底怎样使用

这些是程序生成的受控医学材料，不是真实患者。正确答案只针对题目明确给出的规则。每一行都对应已经保存的实际模型输出。

## 病例 `belief_aki_0`

当前报告的肌酐从 **111 升到 139**，相隔 **16 小时**。如果报告可用，这个变化达到题目给定标准。旧报告支持相反方向，随后发现旧报告属于另一人。

| 当前报告情况 | 给模型保留什么 | 应有回答 | 实际回答 | 记录ID |
|---|---|---|---|---|
| 当前报告可用 | 只看当前材料 | 达到所给肌酐变化标准 | 达到所给肌酐变化标准 | `belief_aki_0_yes_both_valid_current_only` |
| 当前报告可用 | 保留旧事实 | 达到所给肌酐变化标准 | 达到所给肌酐变化标准 | `belief_aki_0_yes_both_valid_no_old_facts` |
| 当前报告可用 | 再保留自己的旧判断摘要 | 达到所给肌酐变化标准 | 达到所给肌酐变化标准 | `belief_aki_0_yes_both_valid_no_own_judgment_summary` |
| 只撤回无关身高报告 | 只看当前材料 | 达到所给肌酐变化标准 | 达到所给肌酐变化标准 | `belief_aki_0_yes_irrelevant_withdrawn_current_only` |
| 只撤回无关身高报告 | 保留旧事实 | 达到所给肌酐变化标准 | 达到所给肌酐变化标准 | `belief_aki_0_yes_irrelevant_withdrawn_no_old_facts` |
| 只撤回无关身高报告 | 再保留自己的旧判断摘要 | 达到所给肌酐变化标准 | 达到所给肌酐变化标准 | `belief_aki_0_yes_irrelevant_withdrawn_no_own_judgment_summary` |
| 当前关键报告属于别人 | 只看当前材料 | 资料不足 | 资料不足 | `belief_aki_0_yes_relevant_withdrawn_current_only` |
| 当前关键报告属于别人 | 保留旧事实 | 资料不足 | 资料不足 | `belief_aki_0_yes_relevant_withdrawn_no_old_facts` |
| 当前关键报告属于别人 | 再保留自己的旧判断摘要 | 资料不足 | 资料不足 | `belief_aki_0_yes_relevant_withdrawn_no_own_judgment_summary` |

下面是该病例实际使用的一份完整输入，便于检查有没有把答案偷偷写进去。表中的其他条件通过改变来源状态或对话历史构造，完整版本在数据文件。

**user**

```text
Apply the supplied medical rule to the current usable evidence. Report validity and whether a numerical rule is met are separate questions.
RULE
Evaluate only whether the supplied pair meets the absolute creatinine-rise criterion: an increase of at least 26 micromol/L within 48 hours. Compare the observed values at their actual times; do not predict later measurements. Do not evaluate other AKI criteria or diagnose the cause. Both values must be usable measurements from this patient.
CURRENT RECORD
This is a synthetic adult patient aged 59, not pregnant. R0: serum creatinine was 120 and then 123 micromol/L, 16 hours apart. At this initial time, R0 is verified as belonging to this patient; its measurements and assessment are usable.
Interpret the three outcomes precisely: meets = usable required data are present and satisfy the rule; does not meet = usable required data are present and fail the rule; insufficient = the required usable data are missing. Inability to confirm because data are missing belongs to insufficient, not does not meet.
Choose the assessment justified now.
A: The usable pair meets the specified creatinine-rise criterion.
B: The usable pair does not meet that criterion.
C: Insufficient usable measurements to evaluate that criterion.
Think through the current evidence. End your response with a line in the form 'Final answer: X', replacing X with one option letter.
```

**assistant**

```text
My initial assessment based on R0: The usable pair does not meet that criterion.
```

**user**

```text
Apply the supplied medical rule to the current usable evidence. Report validity and whether a numerical rule is met are separate questions.
RULE
Evaluate only whether the supplied pair meets the absolute creatinine-rise criterion: an increase of at least 26 micromol/L within 48 hours. Compare the observed values at their actual times; do not predict later measurements. Do not evaluate other AKI criteria or diagnose the cause. Both values must be usable measurements from this patient.
CURRENT RECORD
This is a synthetic adult patient aged 59, not pregnant. The earlier R0 record was found to belong to a different patient. All R0 measurements and assessments are invalid for this patient. Any conclusion based on R0 must be reassessed. Newly arrived report: R1: serum creatinine was 111 and then 139 micromol/L, 16 hours apart. R9: measured standing height 164 cm. Height is not an input to the supplied rule. Source audit: R1 and R9 both belong to this patient and remain usable. There is no other usable evidence for the rule.
Interpret the three outcomes precisely: meets = usable required data are present and satisfy the rule; does not meet = usable required data are present and fail the rule; insufficient = the required usable data are missing. Inability to confirm because data are missing belongs to insufficient, not does not meet.
Choose the assessment justified now.
A: The usable pair meets the specified creatinine-rise criterion.
B: The usable pair does not meet that criterion.
C: Insufficient usable measurements to evaluate that criterion.
Think through the current evidence. End your response with a line in the form 'Final answer: X', replacing X with one option letter.
```

[本运行的全部原始输出](../runs/phase2_pilot_4b/predictions.jsonl)；[实际输入](../data/phase2_pilot_paired.jsonl)。

## 病例 `confirm_aki_0`

当前报告的肌酐从 **147 升到 178**，相隔 **20 小时**。如果报告可用，这个变化达到题目给定标准。旧报告支持相反方向，随后发现旧报告属于另一人。

| 当前报告情况 | 给模型保留什么 | 应有回答 | 实际回答 | 记录ID |
|---|---|---|---|---|
| 当前报告未达到可使用条件 | 只看当前材料 | 资料不足 | 资料不足 | `confirm_aki_0_yes_not_qualified_current_only` |
| 当前报告未达到可使用条件 | 保留旧事实 | 资料不足 | 资料不足 | `confirm_aki_0_yes_not_qualified_no_old_facts` |
| 当前报告未达到可使用条件 | 再保留自己的旧判断摘要 | 资料不足 | 资料不足 | `confirm_aki_0_yes_not_qualified_no_own_judgment_summary` |
| 当前报告未达到可使用条件 | 再保留自己的旧判断原文 | 资料不足 | 资料不足 | `confirm_aki_0_yes_not_qualified_no_own_raw_final` |
| 当前报告可用 | 只看当前材料 | 达到所给肌酐变化标准 | 达到所给肌酐变化标准 | `confirm_aki_0_yes_valid_current_only` |
| 当前报告可用 | 保留旧事实 | 达到所给肌酐变化标准 | 达到所给肌酐变化标准 | `confirm_aki_0_yes_valid_no_old_facts` |
| 当前报告可用 | 再保留自己的旧判断摘要 | 达到所给肌酐变化标准 | 达到所给肌酐变化标准 | `confirm_aki_0_yes_valid_no_own_judgment_summary` |
| 当前报告可用 | 再保留自己的旧判断原文 | 达到所给肌酐变化标准 | 达到所给肌酐变化标准 | `confirm_aki_0_yes_valid_no_own_raw_final` |
| 当前报告属于别人 | 只看当前材料 | 资料不足 | 资料不足 | `confirm_aki_0_yes_wrong_patient_current_only` |
| 当前报告属于别人 | 保留旧事实 | 资料不足 | 资料不足 | `confirm_aki_0_yes_wrong_patient_no_old_facts` |
| 当前报告属于别人 | 再保留自己的旧判断摘要 | 资料不足 | 资料不足 | `confirm_aki_0_yes_wrong_patient_no_own_judgment_summary` |
| 当前报告属于别人 | 再保留自己的旧判断原文 | 资料不足 | 资料不足 | `confirm_aki_0_yes_wrong_patient_no_own_raw_final` |

下面是该病例实际使用的一份完整输入，便于检查有没有把答案偷偷写进去。表中的其他条件通过改变来源状态或对话历史构造，完整版本在数据文件。

**user**

```text
Use the supplied medical rule to assess the current record.
RULE
Evaluate only whether the supplied pair meets the absolute creatinine-rise criterion: an increase of at least 26 micromol/L within 48 hours. Compare the observed values at their actual times; do not predict later measurements. Do not evaluate other AKI criteria or diagnose the cause. Both values must be usable measurements from this patient.
CURRENT RECORD
Current patient: an adult aged 62, not pregnant. Form R0 lists two serum creatinine results: 158 micromol/L followed 20 hours later by 164 micromol/L. R0 is allocated to the current patient. Both laboratory results passed quality checks and were authorised for interpretation.
Interpret the three outcomes precisely: meets = usable required data are present and satisfy the rule; does not meet = usable required data are present and fail the rule; insufficient = the required usable data are missing. Inability to confirm because data are missing belongs to insufficient, not does not meet.
Choose the assessment justified now.
A: Insufficient usable measurements to evaluate that criterion.
B: The usable pair meets the specified creatinine-rise criterion.
C: The usable pair does not meet that criterion.
Think through the current evidence. End your response with a line in the form 'Final answer: X', replacing X with one option letter.
Before the final answer line, write one brief sentence stating the medical assessment supported by this initial report.
```

**assistant**

```text
My initial assessment based on R0: The usable pair does not meet that criterion.
```

**user**

```text
Use the supplied medical rule to assess the current record.
RULE
Evaluate only whether the supplied pair meets the absolute creatinine-rise criterion: an increase of at least 26 micromol/L within 48 hours. Compare the observed values at their actual times; do not predict later measurements. Do not evaluate other AKI criteria or diagnose the cause. Both values must be usable measurements from this patient.
CURRENT RECORD
Current patient: an adult aged 62, not pregnant. Correction to the earlier record: R0 was filed under the wrong patient and is allocated to someone else. Form R1 lists two serum creatinine results: 147 micromol/L followed 20 hours later by 178 micromol/L. R1 is allocated to the current patient. Both laboratory results passed quality checks and were authorised for interpretation. No other current report is available.
Interpret the three outcomes precisely: meets = usable required data are present and satisfy the rule; does not meet = usable required data are present and fail the rule; insufficient = the required usable data are missing. Inability to confirm because data are missing belongs to insufficient, not does not meet.
Choose the assessment justified now.
A: Insufficient usable measurements to evaluate that criterion.
B: The usable pair meets the specified creatinine-rise criterion.
C: The usable pair does not meet that criterion.
Think through the current evidence. End your response with a line in the form 'Final answer: X', replacing X with one option letter.
```

[本运行的全部原始输出](../runs/phase2b_confirm_4b/predictions.jsonl)；[实际输入](../data/phase2b_current.jsonl)。

## 病例 `confirm_dvt_0`

当前报告填着 **Wells评分 4**。若该评分经过独立评估且可用于本患者，所给路径要求先做超声。旧报告的数值按规则应支持先做D-dimer，但本病例的实际初始回答错误地拒绝了负分，给出资料不足；随后旧报告被判定属于另一人。保留的是这个真实初始回答，不伪造正确旧结论。

| 当前报告情况 | 给模型保留什么 | 应有回答 | 实际回答 | 记录ID |
|---|---|---|---|---|
| 当前报告未达到可使用条件 | 只看当前材料 | 资料不足，不能选定路径 | 资料不足，不能选定路径 | `confirm_dvt_0_yes_not_qualified_current_only` |
| 当前报告未达到可使用条件 | 保留旧事实 | 资料不足，不能选定路径 | 资料不足，不能选定路径 | `confirm_dvt_0_yes_not_qualified_no_old_facts` |
| 当前报告未达到可使用条件 | 再保留自己的旧判断摘要 | 资料不足，不能选定路径 | 资料不足，不能选定路径 | `confirm_dvt_0_yes_not_qualified_no_own_judgment_summary` |
| 当前报告未达到可使用条件 | 再保留自己的旧判断原文 | 资料不足，不能选定路径 | 资料不足，不能选定路径 | `confirm_dvt_0_yes_not_qualified_no_own_raw_final` |
| 当前报告可用 | 只看当前材料 | 先做超声 | 先做超声 | `confirm_dvt_0_yes_valid_current_only` |
| 当前报告可用 | 保留旧事实 | 先做超声 | 先做超声 | `confirm_dvt_0_yes_valid_no_old_facts` |
| 当前报告可用 | 再保留自己的旧判断摘要 | 先做超声 | 先做超声 | `confirm_dvt_0_yes_valid_no_own_judgment_summary` |
| 当前报告可用 | 再保留自己的旧判断原文 | 先做超声 | 先做超声 | `confirm_dvt_0_yes_valid_no_own_raw_final` |
| 当前报告属于别人 | 只看当前材料 | 资料不足，不能选定路径 | 资料不足，不能选定路径 | `confirm_dvt_0_yes_wrong_patient_current_only` |
| 当前报告属于别人 | 保留旧事实 | 资料不足，不能选定路径 | 资料不足，不能选定路径 | `confirm_dvt_0_yes_wrong_patient_no_old_facts` |
| 当前报告属于别人 | 再保留自己的旧判断摘要 | 资料不足，不能选定路径 | 资料不足，不能选定路径 | `confirm_dvt_0_yes_wrong_patient_no_own_judgment_summary` |
| 当前报告属于别人 | 再保留自己的旧判断原文 | 资料不足，不能选定路径 | 资料不足，不能选定路径 | `confirm_dvt_0_yes_wrong_patient_no_own_raw_final` |

下面是该病例实际使用的一份完整输入，便于检查有没有把答案偷偷写进去。表中的其他条件通过改变来源状态或对话历史构造，完整版本在数据文件。

**user**

```text
Use the supplied medical rule to assess the current record.
RULE
An adult with suspected DVT has had no investigations. Both ultrasound and D-dimer are available within 4 hours. A usable independently assessed two-level DVT Wells score >=2 calls for proximal leg-vein ultrasound first; a score <=1 calls for D-dimer first. If no usable score is available, the pathway is undetermined.
CURRENT RECORD
Current patient: an adult aged 62, not pregnant. DVT is suspected, no tests have been done, and both initial tests can be completed within 4 hours. Form R0 has the two-level DVT Wells score field filled with -1. R0 is allocated to the current patient. The score was independently assessed for this patient and signed off for use.
Interpret the three outcomes precisely: meets = usable required data are present and satisfy the rule; does not meet = usable required data are present and fail the rule; insufficient = the required usable data are missing. Inability to confirm because data are missing belongs to insufficient, not does not meet.
Choose the assessment justified now.
A: Proximal leg-vein ultrasound first.
B: D-dimer first.
C: Insufficient usable information to choose either pathway.
Think through the current evidence. End your response with a line in the form 'Final answer: X', replacing X with one option letter.
Before the final answer line, write one brief sentence stating the medical assessment supported by this initial report.
```

**assistant**

```text
My initial assessment based on R0: Insufficient usable information to choose either pathway.
```

**user**

```text
Use the supplied medical rule to assess the current record.
RULE
An adult with suspected DVT has had no investigations. Both ultrasound and D-dimer are available within 4 hours. A usable independently assessed two-level DVT Wells score >=2 calls for proximal leg-vein ultrasound first; a score <=1 calls for D-dimer first. If no usable score is available, the pathway is undetermined.
CURRENT RECORD
Current patient: an adult aged 62, not pregnant. DVT is suspected, no tests have been done, and both initial tests can be completed within 4 hours. Correction to the earlier record: R0 was filed under the wrong patient and is allocated to someone else. Form R1 has the two-level DVT Wells score field filled with 4. R1 is allocated to the current patient. The score was independently assessed for this patient and signed off for use. No other current report is available.
Interpret the three outcomes precisely: meets = usable required data are present and satisfy the rule; does not meet = usable required data are present and fail the rule; insufficient = the required usable data are missing. Inability to confirm because data are missing belongs to insufficient, not does not meet.
Choose the assessment justified now.
A: Proximal leg-vein ultrasound first.
B: D-dimer first.
C: Insufficient usable information to choose either pathway.
Think through the current evidence. End your response with a line in the form 'Final answer: X', replacing X with one option letter.
```

[本运行的全部原始输出](../runs/phase2b_confirm_4b/predictions.jsonl)；[实际输入](../data/phase2b_current.jsonl)。

## 本轮所有错误，全部保留

### phase2_pilot_4b：1条

- `belief_aki_1_no_both_valid_no_own_judgment_summary`：应答“未达到这条变化标准”，实际“资料不足”；旧判断方向为`no`，当前数值方向为`no`。
### phase2b_confirm_4b：4条

- `confirm_aki_1_no_wrong_patient_yes_own_judgment_summary`：应答“资料不足”，实际“未达到这条变化标准”；旧判断方向为`yes`，当前数值方向为`no`。
- `confirm_aki_3_no_wrong_patient_no_own_judgment_summary`：应答“资料不足”，实际“未达到这条变化标准”；旧判断方向为`no`，当前数值方向为`no`。
- `confirm_dvt_0_no_valid_no_own_judgment_summary`：应答“先做D-dimer”，实际“资料不足，不能选定路径”；旧判断方向为`unknown`，当前数值方向为`no`。
- `confirm_dvt_0_no_valid_no_old_facts`：应答“先做D-dimer”，实际“资料不足，不能选定路径”；旧判断方向为`unknown`，当前数值方向为`no`。
