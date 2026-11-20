# medmcqa_train_7efe9080-b0da-44c6-a327-ced795f29370

来源：MedMCQA。最终来源答案：**Cutaneous Leishmaniasis**。错误历史预设：Cutaneous tuberculosis。

候选：1. Leprosy；2. Chronic Fungal infections；3. Cutaneous Leishmaniasis；4. Cutaneous tuberculosis

![逐轮变化](../figures/medmcqa_train_7efe9080-b0da-44c6-a327-ced795f29370.png)

实际诊断色块按统一表面写法后的候选身份绘制；逐字输出保留在下表与原文件。上图颜色按候选序号，实线=完整模型、虚线=压缩适配器、点线=第三个冻结方法。序列支持是四个完整字符串归一化后的模型分数，不是临床概率；遇到候选约束模型，则为受约束分布。内部距离只量化表示变化幅度，不能单独说明正朝哪个疾病变化；疾病方向以实际生成和完整候选支持观察。

| 轮次 | 新增事实（保留来源原文） |
|---|---|
| 1 | A 42-year-old Bengali male presents with painless nodules over the face. |
| 2 | The face is erythematous, and the surface of some of the large nodules is discolored. |
| 3 | He gives history of insect bite in past while he went to the jungle for work. |

## 中性历史

| 轮次 | 方法 | 实际诊断 | 最终来源答案支持 | 错误历史诊断支持 |
|---|---|---|---:|---:|
| 1 | 完整模型 | Leprosy | 0.000 | 0.013 |
| 1 | 所选压缩+小适配器16 | Leprosy | 0.000 | 0.078 |
| 1 | 所选压缩+候选约束 | Leprosy | 0.000 | 0.078 |
| 2 | 完整模型 | Leprosy | 0.327 | 0.002 |
| 2 | 所选压缩+小适配器16 | Cutaneous Leishmaniasis | 0.766 | 0.000 |
| 2 | 所选压缩+候选约束 | Cutaneous Leishmaniasis | 0.766 | 0.000 |
| 3 | 完整模型 | Cutaneous Leishmaniasis | 1.000 | 0.000 |
| 3 | 所选压缩+小适配器16 | Cutaneous Leishmaniasis | 1.000 | 0.000 |
| 3 | 所选压缩+候选约束 | Cutaneous Leishmaniasis | 1.000 | 0.000 |

## 错误历史

| 轮次 | 方法 | 实际诊断 | 最终来源答案支持 | 错误历史诊断支持 |
|---|---|---|---:|---:|
| 1 | 完整模型 | Cutaneous tuberculosis | 0.000 | 1.000 |
| 1 | 所选压缩+小适配器16 | Cutaneous tuberculosis | 0.000 | 1.000 |
| 1 | 所选压缩+候选约束 | Cutaneous tuberculosis | 0.000 | 1.000 |
| 2 | 完整模型 | Cutaneous tuberculosis | 0.000 | 0.938 |
| 2 | 所选压缩+小适配器16 | Cutaneous tuberculosis | 0.000 | 0.980 |
| 2 | 所选压缩+候选约束 | Cutaneous tuberculosis | 0.000 | 0.980 |
| 3 | 完整模型 | Cutaneous leishmaniasis | 0.990 | 0.005 |
| 3 | 所选压缩+小适配器16 | Cutaneous Leishmaniasis | 1.000 | 0.000 |
| 3 | 所选压缩+候选约束 | Cutaneous Leishmaniasis | 1.000 | 0.000 |

原始逐轮生成、各层2048维状态和适配器前后向量见[runs轨迹目录](../../../runs/structural_v2/trajectories)。中间前缀没有独立诊断真值；“匹配来源答案”只描述是否提前到达最终答案。
