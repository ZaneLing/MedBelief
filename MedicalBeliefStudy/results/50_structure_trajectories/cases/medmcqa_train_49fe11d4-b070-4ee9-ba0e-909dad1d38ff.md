# medmcqa_train_49fe11d4-b070-4ee9-ba0e-909dad1d38ff

来源：MedMCQA。最终来源答案：**Pehes disease**。错误历史预设：Tuberculosis ahritis of hip。

候选：1. Septic ahritis of hip；2. Tuberculosis ahritis of hip；3. Cong dislocation of hip；4. Pehes disease

![逐轮变化](../figures/medmcqa_train_49fe11d4-b070-4ee9-ba0e-909dad1d38ff.png)

实际诊断色块按统一表面写法后的候选身份绘制；逐字输出保留在下表与原文件。上图颜色按候选序号，实线=完整模型、虚线=压缩适配器、点线=第三个冻结方法。序列支持是四个完整字符串归一化后的模型分数，不是临床概率；遇到候选约束模型，则为受约束分布。内部距离只量化表示变化幅度，不能单独说明正朝哪个疾病变化；疾病方向以实际生成和完整候选支持观察。

| 轮次 | 新增事实（保留来源原文） |
|---|---|
| 1 | A 7 year old boy presents to the OPD with a painless limp. |
| 2 | On examination, you observe that abduction and internal rotation of left hip are restricted. |
| 3 | While attempting to flex the hip, the knee goes toward axilla. |

## 中性历史

| 轮次 | 方法 | 实际诊断 | 最终来源答案支持 | 错误历史诊断支持 |
|---|---|---|---:|---:|
| 1 | 完整模型 | Septic arthritis of hip | 0.154 | 0.778 |
| 1 | 所选压缩+小适配器16 | Cong dislocation of hip | 0.070 | 0.102 |
| 1 | 所选压缩+候选约束 | Cong dislocation of hip | 0.070 | 0.102 |
| 2 | 完整模型 | Cong dislocation of hip | 0.153 | 0.043 |
| 2 | 所选压缩+小适配器16 | Cong dislocation of hip | 0.001 | 0.000 |
| 2 | 所选压缩+候选约束 | Cong dislocation of hip | 0.001 | 0.000 |
| 3 | 完整模型 | Cong dislocation of hip | 0.000 | 0.000 |
| 3 | 所选压缩+小适配器16 | Cong dislocation of hip | 0.000 | 0.000 |
| 3 | 所选压缩+候选约束 | Cong dislocation of hip | 0.000 | 0.000 |

## 错误历史

| 轮次 | 方法 | 实际诊断 | 最终来源答案支持 | 错误历史诊断支持 |
|---|---|---|---:|---:|
| 1 | 完整模型 | Tuberculosis ahritis of hip | 0.000 | 0.987 |
| 1 | 所选压缩+小适配器16 | Tuberculosis ahritis of hip | 0.000 | 0.665 |
| 1 | 所选压缩+候选约束 | Tuberculosis ahritis of hip | 0.000 | 0.665 |
| 2 | 完整模型 | Tuberculosis ahritis of hip | 0.000 | 1.000 |
| 2 | 所选压缩+小适配器16 | Tuberculosis ahritis of hip | 0.000 | 1.000 |
| 2 | 所选压缩+候选约束 | Tuberculosis ahritis of hip | 0.000 | 1.000 |
| 3 | 完整模型 | Tuberculosis ahritis of hip | 0.000 | 1.000 |
| 3 | 所选压缩+小适配器16 | Tuberculosis ahritis of hip | 0.000 | 1.000 |
| 3 | 所选压缩+候选约束 | Tuberculosis ahritis of hip | 0.000 | 1.000 |

原始逐轮生成、各层2048维状态和适配器前后向量见[runs轨迹目录](../../../runs/structural_v2/trajectories)。中间前缀没有独立诊断真值；“匹配来源答案”只描述是否提前到达最终答案。
