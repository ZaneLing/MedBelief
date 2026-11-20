# medmcqa_validation_9998be8f-9725-46f3-9891-4ec3f18812ce

来源答案：**Pharyngeal pouch**；固定错误历史：**Diabetes**。

候选：1=Gastrophoresis；2=Achalasia；3=Diabetes；4=Pharyngeal pouch。

![逐证据轨迹](medmcqa_validation_9998be8f-9725-46f3-9891-4ec3f18812ce.png)

![每层与每轮](medmcqa_validation_9998be8f-9725-46f3-9891-4ec3f18812ce_layers.png)

曲线颜色代表四种结构，方格颜色及数字代表四个候选。曲线先平均两套代码支持；右侧方格与下表在两套代码不一致时同时列出两个候选编号，方格标灰。统计仍先各映射判定后在病例内平均。逐层图是最终输出头投影；浅灰表示代码总概率不足0.5，深灰表示两映射首选不同，未将这些格子解释为确定的疾病判断。

## 中性历史

| 轮 | 完整模型 | 删除所选MLP | 小型线性替换 | 诊断位置头干预 |
|---:|---|---|---|---|
| 1 | 2 | 1 / 2 | 2 | 2 / 4 |
| 2 | 2 / 4 | 2 | 2 / 4 | 4 |
## 错误历史

| 轮 | 完整模型 | 删除所选MLP | 小型线性替换 | 诊断位置头干预 |
|---:|---|---|---|---|
| 1 | 3 / 4 | 2 / 3 | 2 | 2 / 4 |
| 2 | 2 / 4 | 4 | 2 / 4 | 2 / 4 |

## 新增原文

1. Babu, a 49-year-old patient, complains of foul breath and regurgitation of food eaten few days back.
2. He also complains of dysphagia.
