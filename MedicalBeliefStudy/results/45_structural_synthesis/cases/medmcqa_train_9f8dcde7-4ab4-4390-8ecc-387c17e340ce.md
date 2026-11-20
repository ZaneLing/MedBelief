# medmcqa_train_9f8dcde7-4ab4-4390-8ecc-387c17e340ce

来源答案：**Urticaria pigmentosa**；固定错误历史：**Fixed drug eruption**。

候选：1=Fixed drug eruption；2=Lichen planus；3=Urticaria pigmentosa；4=Urticarial vasculitis。

![逐证据轨迹](medmcqa_train_9f8dcde7-4ab4-4390-8ecc-387c17e340ce.png)

![每层与每轮](medmcqa_train_9f8dcde7-4ab4-4390-8ecc-387c17e340ce_layers.png)

曲线颜色代表四种结构，方格颜色及数字代表四个候选。曲线先平均两套代码支持；右侧方格与下表在两套代码不一致时同时列出两个候选编号，方格标灰。统计仍先各映射判定后在病例内平均。逐层图是最终输出头投影；浅灰表示代码总概率不足0.5，深灰表示两映射首选不同，未将这些格子解释为确定的疾病判断。

## 中性历史

| 轮 | 完整模型 | 删除所选MLP | 小型线性替换 | 诊断位置头干预 |
|---:|---|---|---|---|
| 1 | 2 / 3 | 1 / 3 | 3 | 3 |
| 2 | 2 / 3 | 1 / 3 | 3 | 3 |
## 错误历史

| 轮 | 完整模型 | 删除所选MLP | 小型线性替换 | 诊断位置头干预 |
|---:|---|---|---|---|
| 1 | 2 | 1 / 2 | 2 | 2 |
| 2 | 2 | 1 / 2 | 1 / 2 | 2 |

## 新增原文

1. A 5 yr. old male child has multiple hyperpigmented macules over the trunk.
2. On rubbing the lesion with rounded end of pen, he developed urticarial wheal, confined to border of lesion,
