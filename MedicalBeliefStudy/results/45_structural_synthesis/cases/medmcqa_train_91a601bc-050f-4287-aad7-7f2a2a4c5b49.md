# medmcqa_train_91a601bc-050f-4287-aad7-7f2a2a4c5b49

来源答案：**Ostium primum atrial septal defect.**；固定错误历史：**Tricuspid atresia.**。

候选：1=Total anomalous pulmonary venous drainge；2=Tricuspid atresia.；3=Ostium primum atrial septal defect.；4=Ventricular septal defect with pulmonary aerial hypeension.。

![逐证据轨迹](medmcqa_train_91a601bc-050f-4287-aad7-7f2a2a4c5b49.png)

![每层与每轮](medmcqa_train_91a601bc-050f-4287-aad7-7f2a2a4c5b49_layers.png)

曲线颜色代表四种结构，方格颜色及数字代表四个候选。曲线先平均两套代码支持；右侧方格与下表在两套代码不一致时同时列出两个候选编号，方格标灰。统计仍先各映射判定后在病例内平均。逐层图是最终输出头投影；浅灰表示代码总概率不足0.5，深灰表示两映射首选不同，未将这些格子解释为确定的疾病判断。

## 中性历史

| 轮 | 完整模型 | 删除所选MLP | 小型线性替换 | 诊断位置头干预 |
|---:|---|---|---|---|
| 1 | 1 / 4 | 1 / 4 | 2 / 4 | 2 / 4 |
| 2 | 1 / 2 | 1 / 2 | 1 / 2 | 1 |
| 3 | 1 | 1 / 2 | 1 | 1 |
## 错误历史

| 轮 | 完整模型 | 删除所选MLP | 小型线性替换 | 诊断位置头干预 |
|---:|---|---|---|---|
| 1 | 1 / 3 | 1 / 3 | 1 | 3 |
| 2 | 1 / 2 | 1 / 2 | 1 | 2 / 3 |
| 3 | 1 | 1 / 2 | 1 | 1 |

## 新增原文

1. A young female presents with history of dyspnoea on exeion.
2. On examination, she has wide, fixed split S2 with ejection systolic murmur (IIINI) in left second intercostal space.
3. Her ECG shows left axis detion.
