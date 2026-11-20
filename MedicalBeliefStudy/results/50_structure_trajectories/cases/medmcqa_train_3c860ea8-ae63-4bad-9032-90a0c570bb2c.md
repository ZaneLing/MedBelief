# medmcqa_train_3c860ea8-ae63-4bad-9032-90a0c570bb2c

来源：MedMCQA。最终来源答案：**Senile immature cataract**。错误历史预设：Mucopurulent conjunctivitis。

候选：1. Acute congestive glaucoma；2. Open angle glaucoma；3. Senile immature cataract；4. Mucopurulent conjunctivitis

![逐轮变化](../figures/medmcqa_train_3c860ea8-ae63-4bad-9032-90a0c570bb2c.png)

实际诊断色块按统一表面写法后的候选身份绘制；逐字输出保留在下表与原文件。上图颜色按候选序号，实线=完整模型、虚线=压缩适配器、点线=第三个冻结方法。序列支持是四个完整字符串归一化后的模型分数，不是临床概率；遇到候选约束模型，则为受约束分布。内部距离只量化表示变化幅度，不能单独说明正朝哪个疾病变化；疾病方向以实际生成和完整候选支持观察。

| 轮次 | 新增事实（保留来源原文） |
|---|---|
| 1 | A 60-year-old male presents with coloured halos. |
| 2 | On Fincham&;s test, the halos split and then reunite. |

## 中性历史

| 轮次 | 方法 | 实际诊断 | 最终来源答案支持 | 错误历史诊断支持 |
|---|---|---|---:|---:|
| 1 | 完整模型 | Acute congestive glaucoma | 0.000 | 0.000 |
| 1 | 所选压缩+小适配器16 | Acute congestive glaucoma | 0.000 | 0.000 |
| 1 | 所选压缩+候选约束 | Acute congestive glaucoma | 0.000 | 0.000 |
| 2 | 完整模型 | Acute congestive glaucoma | 0.000 | 0.000 |
| 2 | 所选压缩+小适配器16 | Acute congestive glaucoma | 0.000 | 0.000 |
| 2 | 所选压缩+候选约束 | Acute congestive glaucoma | 0.000 | 0.000 |

## 错误历史

| 轮次 | 方法 | 实际诊断 | 最终来源答案支持 | 错误历史诊断支持 |
|---|---|---|---:|---:|
| 1 | 完整模型 | Acute congestive glaucoma | 0.000 | 0.385 |
| 1 | 所选压缩+小适配器16 | Acute congestive glaucoma | 0.000 | 0.042 |
| 1 | 所选压缩+候选约束 | Acute congestive glaucoma | 0.000 | 0.042 |
| 2 | 完整模型 | Mucopurulent conjunctivitis | 0.000 | 0.951 |
| 2 | 所选压缩+小适配器16 | Mucopurulent conjunctivitis | 0.000 | 0.877 |
| 2 | 所选压缩+候选约束 | Mucopurulent conjunctivitis | 0.000 | 0.877 |

原始逐轮生成、各层2048维状态和适配器前后向量见[runs轨迹目录](../../../runs/structural_v2/trajectories)。中间前缀没有独立诊断真值；“匹配来源答案”只描述是否提前到达最终答案。
