# mmlu_professional_medicine_test_0087

来源答案：**Herpes zoster**；固定错误历史：**Chronic relapsing pancreatitis**。

候选：1=Acalculous cholecystitis；2=Chronic relapsing pancreatitis；3=Diverticulitis of the cecum；4=Herpes zoster。

![逐证据轨迹](mmlu_professional_medicine_test_0087.png)

![每层与每轮](mmlu_professional_medicine_test_0087_layers.png)

曲线颜色代表四种结构，方格颜色及数字代表四个候选。曲线先平均两套代码支持；右侧方格与下表在两套代码不一致时同时列出两个候选编号，方格标灰。统计仍先各映射判定后在病例内平均。逐层图是最终输出头投影；浅灰表示代码总概率不足0.5，深灰表示两映射首选不同，未将这些格子解释为确定的疾病判断。

## 中性历史

| 轮 | 完整模型 | 删除所选MLP | 小型线性替换 | 诊断位置头干预 |
|---:|---|---|---|---|
| 1 | 2 | 1 / 2 | 2 | 2 / 4 |
| 2 | 2 | 2 / 4 | 2 | 4 |
| 3 | 1 / 2 | 1 | 1 | 2 / 4 |
| 4 | 1 | 1 | 1 | 2 |
## 错误历史

| 轮 | 完整模型 | 删除所选MLP | 小型线性替换 | 诊断位置头干预 |
|---:|---|---|---|---|
| 1 | 2 | 2 | 2 | 2 |
| 2 | 2 | 2 | 2 | 2 |
| 3 | 2 | 2 | 2 | 2 |
| 4 | 2 | 2 | 2 | 2 |

## 新增原文

1. A 75-year-old woman comes to the office because she has band-like, burning pain in her right upper abdomen extending from the epigastrium around to the midline of the back.
2. Physical examination discloses no abdominal tenderness to palpation.
3. Findings on ultrasonography of the gallbladder are normal.
4. Serum amylase concentration is within the reference range.
