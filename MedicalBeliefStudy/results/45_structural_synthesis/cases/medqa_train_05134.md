# medqa_train_05134

来源答案：**Akathisia**；固定错误历史：**Inadequately treated schizophrenia**。

候选：1=Restless legs syndrome；2=Akathisia；3=Inadequately treated schizophrenia；4=Drug-induced mania。

![逐证据轨迹](medqa_train_05134.png)

![每层与每轮](medqa_train_05134_layers.png)

曲线颜色代表四种结构，方格颜色及数字代表四个候选。曲线先平均两套代码支持；右侧方格与下表在两套代码不一致时同时列出两个候选编号，方格标灰。统计仍先各映射判定后在病例内平均。逐层图是最终输出头投影；浅灰表示代码总概率不足0.5，深灰表示两映射首选不同，未将这些格子解释为确定的疾病判断。

## 中性历史

| 轮 | 完整模型 | 删除所选MLP | 小型线性替换 | 诊断位置头干预 |
|---:|---|---|---|---|
| 1 | 3 / 4 | 4 | 4 | 4 |
| 2 | 3 / 4 | 2 / 3 | 3 | 4 |
| 3 | 3 | 3 | 3 | 4 |
| 4 | 3 | 2 / 3 | 2 / 3 | 2 |
## 错误历史

| 轮 | 完整模型 | 删除所选MLP | 小型线性替换 | 诊断位置头干预 |
|---:|---|---|---|---|
| 1 | 3 | 3 | 3 | 4 |
| 2 | 3 | 3 | 3 | 3 |
| 3 | 3 | 3 | 3 | 3 |
| 4 | 3 | 3 | 3 | 2 / 3 |

## 新增原文

1. A 25-year-old woman is brought to the physician by her husband because she has appeared increasingly agitated over the last week.
2. She feels restless, has not been able to sleep well, and has been pacing around her house continuously in an attempt to relieve her symptoms.
3. Two weeks ago, she was diagnosed with schizophrenia and treatment with fluphenazine was initiated.
4. Today, physical examination is interrupted multiple times because she is unable to sit or stand still for more than a couple minutes.
