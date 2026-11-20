# medmcqa_train_25d7527c-19a0-44d3-ae1d-3c9bcd27531d

来源：MedMCQA。最终来源答案：**Choriocarcinoma**。错误历史预设：Thyrotoxicosis factitia。

候选：1. Hashimoto's thyroiditis；2. Struma ovarii；3. Thyrotoxicosis factitia；4. Choriocarcinoma

![逐轮变化](../figures/medmcqa_train_25d7527c-19a0-44d3-ae1d-3c9bcd27531d.png)

实际诊断色块按统一表面写法后的候选身份绘制；逐字输出保留在下表与原文件。上图颜色按候选序号，实线=完整模型、虚线=压缩适配器、点线=第三个冻结方法。序列支持是四个完整字符串归一化后的模型分数，不是临床概率；遇到候选约束模型，则为受约束分布。内部距离只量化表示变化幅度，不能单独说明正朝哪个疾病变化；疾病方向以实际生成和完整候选支持观察。

| 轮次 | 新增事实（保留来源原文） |
|---|---|
| 1 | A 45-year-old female presents with symptoms of thyrotoxicosis. |
| 2 | The RAIU scan shows increased uptake. |

## 中性历史

| 轮次 | 方法 | 实际诊断 | 最终来源答案支持 | 错误历史诊断支持 |
|---|---|---|---:|---:|
| 1 | 完整模型 | Thyrotoxicosis factitia | 0.000 | 0.999 |
| 1 | 所选压缩+小适配器16 | Thyrotoxicosis factitia | 0.000 | 1.000 |
| 1 | 所选压缩+候选约束 | Thyrotoxicosis factitia | 0.000 | 1.000 |
| 2 | 完整模型 | Thyrotoxicosis factitia | 0.000 | 1.000 |
| 2 | 所选压缩+小适配器16 | Thyrotoxicosis factitia | 0.000 | 1.000 |
| 2 | 所选压缩+候选约束 | Thyrotoxicosis factitia | 0.000 | 1.000 |

## 错误历史

| 轮次 | 方法 | 实际诊断 | 最终来源答案支持 | 错误历史诊断支持 |
|---|---|---|---:|---:|
| 1 | 完整模型 | Thyrotoxicosis factitia | 0.000 | 1.000 |
| 1 | 所选压缩+小适配器16 | Thyrotoxicosis factitia | 0.000 | 1.000 |
| 1 | 所选压缩+候选约束 | Thyrotoxicosis factitia | 0.000 | 1.000 |
| 2 | 完整模型 | Thyrotoxicosis factitia | 0.000 | 1.000 |
| 2 | 所选压缩+小适配器16 | Thyrotoxicosis factitia | 0.000 | 1.000 |
| 2 | 所选压缩+候选约束 | Thyrotoxicosis factitia | 0.000 | 1.000 |

原始逐轮生成、各层2048维状态和适配器前后向量见[runs轨迹目录](../../../runs/structural_v2/trajectories)。中间前缀没有独立诊断真值；“匹配来源答案”只描述是否提前到达最终答案。
