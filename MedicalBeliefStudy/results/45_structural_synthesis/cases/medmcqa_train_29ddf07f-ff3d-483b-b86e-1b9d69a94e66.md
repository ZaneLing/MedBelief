# medmcqa_train_29ddf07f-ff3d-483b-b86e-1b9d69a94e66

来源答案：**Cluster headache**；固定错误历史：**Tension headache**。

候选：1=Migraine headache；2=Tension headache；3=Cluster headache；4=Brain tumour。

![逐证据轨迹](medmcqa_train_29ddf07f-ff3d-483b-b86e-1b9d69a94e66.png)

![每层与每轮](medmcqa_train_29ddf07f-ff3d-483b-b86e-1b9d69a94e66_layers.png)

曲线颜色代表四种结构，方格颜色及数字代表四个候选。曲线先平均两套代码支持；右侧方格与下表在两套代码不一致时同时列出两个候选编号，方格标灰。统计仍先各映射判定后在病例内平均。逐层图是最终输出头投影；浅灰表示代码总概率不足0.5，深灰表示两映射首选不同，未将这些格子解释为确定的疾病判断。

## 中性历史

| 轮 | 完整模型 | 删除所选MLP | 小型线性替换 | 诊断位置头干预 |
|---:|---|---|---|---|
| 1 | 1 | 1 / 3 | 1 / 2 | 2 / 3 |
| 2 | 3 | 1 / 3 | 3 | 3 |
| 3 | 3 | 1 / 3 | 3 | 3 |
| 4 | 3 | 1 / 3 | 3 | 3 |
| 5 | 3 | 1 / 3 | 3 | 3 |
| 6 | 3 | 1 / 3 | 3 | 3 |
## 错误历史

| 轮 | 完整模型 | 删除所选MLP | 小型线性替换 | 诊断位置头干预 |
|---:|---|---|---|---|
| 1 | 1 | 1 / 3 | 2 | 2 |
| 2 | 1 | 1 / 3 | 1 | 1 / 2 |
| 3 | 3 | 1 / 3 | 3 | 3 |
| 4 | 3 | 3 | 3 | 3 |
| 5 | 3 | 3 | 3 | 3 |
| 6 | 3 | 1 / 3 | 3 | 3 |

## 新增原文

1. A 35-year-old man presents with daily headache.
2. He describes two attacks per day over the last 3 weeks.
3. Each attack lasts about an hour and awakens him from sleep.
4. The patient has noticed associated tearingand reddening of the right eye as well as nasal stuffness.
5. The pain's deep, excruciating, and limiting to the right side of the head.
6. The neurological examination is normal.
