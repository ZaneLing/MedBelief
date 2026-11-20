# mmlu_professional_medicine_test_0267

来源答案：**amyotrophic lateral sclerosis**；固定错误历史：**progressive multifocal leukoencephalopathy**。

候选：1=amyotrophic lateral sclerosis；2=Friedreich ataxia；3=Pick disease；4=progressive multifocal leukoencephalopathy。

![逐证据轨迹](mmlu_professional_medicine_test_0267.png)

![每层与每轮](mmlu_professional_medicine_test_0267_layers.png)

曲线颜色代表四种结构，方格颜色及数字代表四个候选。曲线先平均两套代码支持；右侧方格与下表在两套代码不一致时同时列出两个候选编号，方格标灰。统计仍先各映射判定后在病例内平均。逐层图是最终输出头投影；浅灰表示代码总概率不足0.5，深灰表示两映射首选不同，未将这些格子解释为确定的疾病判断。

## 中性历史

| 轮 | 完整模型 | 删除所选MLP | 小型线性替换 | 诊断位置头干预 |
|---:|---|---|---|---|
| 1 | 1 / 4 | 1 / 4 | 1 / 4 | 4 |
| 2 | 1 / 4 | 1 / 2 | 1 / 4 | 2 / 4 |
| 3 | 1 / 2 | 1 / 2 | 1 / 2 | 1 / 2 |
| 4 | 2 | 1 / 2 | 1 / 2 | 2 |
| 5 | 2 | 1 / 2 | 1 / 2 | 2 |
## 错误历史

| 轮 | 完整模型 | 删除所选MLP | 小型线性替换 | 诊断位置头干预 |
|---:|---|---|---|---|
| 1 | 4 | 4 | 4 | 4 |
| 2 | 4 | 4 | 4 | 4 |
| 3 | 4 | 2 / 4 | 4 | 4 |
| 4 | 4 | 2 / 4 | 4 | 2 / 4 |
| 5 | 2 / 4 | 2 / 4 | 2 / 4 | 2 |

## 新增原文

1. A 64-year-old female presents to the office with the complaint of difficulty swallowing saliva for about 6 months.
2. She has slurred speech.
3. Examination of the tongue reveals wasting and fasciculation.
4. Decreased deep tendon reflexes and fasciculation are noted in the left lower extremity.
5. The deep tendon reflexes of the left upper extremity are hyperactive.
