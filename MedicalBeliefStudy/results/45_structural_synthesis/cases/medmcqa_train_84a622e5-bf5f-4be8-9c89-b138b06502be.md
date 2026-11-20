# medmcqa_train_84a622e5-bf5f-4be8-9c89-b138b06502be

来源答案：**Ruptured aneurysm**；固定错误历史：**Meningitis**。

候选：1=Meningitis；2=Ruptured aneurysm；3=Hypertensive bleed；4=Stroke。

![逐证据轨迹](medmcqa_train_84a622e5-bf5f-4be8-9c89-b138b06502be.png)

![每层与每轮](medmcqa_train_84a622e5-bf5f-4be8-9c89-b138b06502be_layers.png)

曲线颜色代表四种结构，方格颜色及数字代表四个候选。曲线先平均两套代码支持；右侧方格与下表在两套代码不一致时同时列出两个候选编号，方格标灰。统计仍先各映射判定后在病例内平均。逐层图是最终输出头投影；浅灰表示代码总概率不足0.5，深灰表示两映射首选不同，未将这些格子解释为确定的疾病判断。

## 中性历史

| 轮 | 完整模型 | 删除所选MLP | 小型线性替换 | 诊断位置头干预 |
|---:|---|---|---|---|
| 1 | 3 | 3 | 3 | 3 |
| 2 | 3 | 3 | 3 | 3 |
| 3 | 3 | 3 | 3 | 3 |
## 错误历史

| 轮 | 完整模型 | 删除所选MLP | 小型线性替换 | 诊断位置头干预 |
|---:|---|---|---|---|
| 1 | 2 | 2 / 4 | 2 / 4 | 3 |
| 2 | 2 / 3 | 2 / 4 | 2 | 3 |
| 3 | 3 | 3 | 3 | 3 |

## 新增原文

1. A 45-years old hypertensive male presented with sudden onset most severe headache, vomiting and neck stiffness.
2. On examination he didn't have any focal neurological deficit.
3. His CT scan shoed blood in the Sylvain fissure.
