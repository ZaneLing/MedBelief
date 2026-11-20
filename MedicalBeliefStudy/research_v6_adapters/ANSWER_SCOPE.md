# 候选答案的医学范围

来源题干经“诊断”关键词筛选，但这不保证选项全是疾病名。复核400例最终来源标签后，将9个明确属于检查特征、病原体、机制、影像描述或组合答案的条目单列。疾病、综合征、缺乏症、损伤和正常状态鉴别仍保留。此表是窄范围的来源答案审计，不冒充完整疾病本体标注。

原400例结果保留；原文本与近重复严格366例也保留。在其上再排除本表条目，作为附加敏感性分析，不重新训练或选型。原始字段名gold_disease沿用代码历史，不能据字段名假定每项一定是疾病。

| 病例 | 来源答案 | 单列原因 |
|---|---|---|
| medqa_dev_00157 | ASCA positivity | 检查特征：ASCA positivity，不是疾病名称 |
| medqa_train_03655 | Environmental allergen | 致病因素：Environmental allergen |
| medqa_train_01986 | Calcification of valve leaflets | 病理描述：Calcification of valve leaflets |
| medmcqa_train_1bba25d9-7512-458e-b47c-65a5a78c975f | CMV | 病原体简称：CMV |
| medqa_dev_00294 | Parvovirus B19 | 病原体名称：Parvovirus B19 |
| medmcqa_train_202cb4ea-c9ef-4e19-868c-eaae7fca2262 | Consolidation | 影像/体征描述：Consolidation |
| medmcqa_train_27f22bd6-be02-4c94-bbd5-deb82ef5a018 | c abd b | 组合选项c abd b，不能作为单一疾病名 |
| medmcqa_train_fba4477b-e045-47e8-a48b-d0856f57ccc9 | LDL receptor mutation | 分子机制：LDL receptor mutation |
| medqa_dev_00834 | Intrinsic apoptotic pathway | 分子机制：Intrinsic apoptotic pathway；题干要求诊断与选项类型不吻合 |

[结构化记录](ANSWER_SCOPE_AUDIT.json) · [确认结果](../results/49_structure_confirmation/RESULTS.md)。医学信念的疾病示例使用明确疾病候选；全部统计准确表述为诊断相关医学题的候选判断。
