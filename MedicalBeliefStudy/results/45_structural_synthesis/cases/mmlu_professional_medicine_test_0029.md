# mmlu_professional_medicine_test_0029

来源答案：**uninhibited neurogenic bladder**；固定错误历史：**motor paralytic bladder**。

候选：1=autonomic neurogenic bladderv；2=motor paralytic bladder；3=reflex neurogenic bladder；4=uninhibited neurogenic bladder。

![逐证据轨迹](mmlu_professional_medicine_test_0029.png)

![每层与每轮](mmlu_professional_medicine_test_0029_layers.png)

曲线颜色代表四种结构，方格颜色及数字代表四个候选。曲线先平均两套代码支持；右侧方格与下表在两套代码不一致时同时列出两个候选编号，方格标灰。统计仍先各映射判定后在病例内平均。逐层图是最终输出头投影；浅灰表示代码总概率不足0.5，深灰表示两映射首选不同，未将这些格子解释为确定的疾病判断。

## 中性历史

| 轮 | 完整模型 | 删除所选MLP | 小型线性替换 | 诊断位置头干预 |
|---:|---|---|---|---|
| 1 | 2 / 4 | 2 / 4 | 2 / 4 | 3 / 4 |
| 2 | 2 | 1 / 2 | 1 / 2 | 3 |
| 3 | 2 | 2 | 2 | 3 |
## 错误历史

| 轮 | 完整模型 | 删除所选MLP | 小型线性替换 | 诊断位置头干预 |
|---:|---|---|---|---|
| 1 | 2 | 2 | 1 / 2 | 2 |
| 2 | 2 | 2 | 2 | 2 |
| 3 | 2 | 2 | 2 | 2 |

## 新增原文

1. A 65-year-old female is admitted to the hospital after experiencing aphasia and right-sided hemiparesis.
2. She subsequently develops urinary incontinence.
3. There is no evidence of urinary tract infection and no prior history of urinary pathology.
