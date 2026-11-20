# medmcqa_train_d69f4de3-e358-4335-af72-b0d95fb9d515

来源：MedMCQA。最终来源答案：**Amyotrophic lateral sclerosis**。错误历史预设：Subacute combined degeneration。

候选：1. Multiple Sclerosis；2. Amyotrophic lateral sclerosis；3. Subacute combined degeneration；4. Progressive spinal muscular atrophy

![逐轮变化](../figures/medmcqa_train_d69f4de3-e358-4335-af72-b0d95fb9d515.png)

实际诊断色块按统一表面写法后的候选身份绘制；逐字输出保留在下表与原文件。上图颜色按候选序号，实线=完整模型、虚线=压缩适配器、点线=第三个冻结方法。序列支持是四个完整字符串归一化后的模型分数，不是临床概率；遇到候选约束模型，则为受约束分布。内部距离只量化表示变化幅度，不能单独说明正朝哪个疾病变化；疾病方向以实际生成和完整候选支持观察。

| 轮次 | 新增事实（保留来源原文） |
|---|---|
| 1 | A middle aged man presents with progressive atrophy & weakness of hand & forearms. |
| 2 | On examination he is found to have slight spasticity of the leg, genera-lized hyperreflexia and increased signal in the coico-spinal tracts on T2 weighted MRI. |

## 中性历史

| 轮次 | 方法 | 实际诊断 | 最终来源答案支持 | 错误历史诊断支持 |
|---|---|---|---:|---:|
| 1 | 完整模型 | Amyotrophic lateral sclerosis | 0.972 | 0.000 |
| 1 | 所选压缩+小适配器16 | Amyotrophic lateral sclerosis | 0.993 | 0.000 |
| 1 | 所选压缩+候选约束 | Amyotrophic lateral sclerosis | 0.994 | 0.000 |
| 2 | 完整模型 | Amyotrophic lateral sclerosis | 0.933 | 0.000 |
| 2 | 所选压缩+小适配器16 | Amyotrophic lateral sclerosis | 0.990 | 0.000 |
| 2 | 所选压缩+候选约束 | Amyotrophic lateral sclerosis | 0.992 | 0.000 |

## 错误历史

| 轮次 | 方法 | 实际诊断 | 最终来源答案支持 | 错误历史诊断支持 |
|---|---|---|---:|---:|
| 1 | 完整模型 | Amyotrophic lateral sclerosis | 0.989 | 0.001 |
| 1 | 所选压缩+小适配器16 | Amyotrophic lateral sclerosis | 1.000 | 0.000 |
| 1 | 所选压缩+候选约束 | Amyotrophic lateral sclerosis | 1.000 | 0.000 |
| 2 | 完整模型 | Progressive spinal muscular atrophy | 0.030 | 0.003 |
| 2 | 所选压缩+小适配器16 | Progressive spinal muscular atrophy | 0.400 | 0.000 |
| 2 | 所选压缩+候选约束 | Progressive spinal muscular atrophy | 0.461 | 0.000 |

原始逐轮生成、各层2048维状态和适配器前后向量见[runs轨迹目录](../../../runs/structural_v2/trajectories)。中间前缀没有独立诊断真值；“匹配来源答案”只描述是否提前到达最终答案。
