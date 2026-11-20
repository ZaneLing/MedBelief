# 本轮证据应放在什么已有研究之后

核对日期：2026-11-20。本文的题目仍可用“模型有医学信念吗？”，但贡献必须落到能由实验区分的机制上。

## 最直接的近邻

| 工作 | 已有结论/设计 | 本文需要额外回答什么 |
|---|---|---|
| [How Cognitive Biases Propagate in LLM Clinical Differential Diagnosis](https://aclanthology.org/2026.emnlp-main.2434/)，EMNLP 2026 | 在686条MIMIC-IV患者时间线上，让先前评估随步骤传递，并比较错误诊断进入上下文的四种渠道；模型自身先前评估被改动时影响最大。 | 本文不能把“旧诊断影响后续判断”当首创。我们的固定历史对照进一步区分仅提及、证据增量、内部位置和注意力通路；并明确当前实验不是自主回填答案的真实病程回放。 |
| [Probing Bias Formation in Medical LLMs through Activation Steering](https://aclanthology.org/2026.acl-srw.54.pdf)，ACL SRW 2026 | 在MedGemma-27B和BiasMedQA上研究错误提示；使用SAE、逐层干预和分簇steering定位/减轻偏差。论文表1列1273题、135次正确转向偏置答案的事件。 | “医学偏差存在内部方向”“可以找到干预层”均已有先例。本轮使用预先选定病例，不只保留发生翻转的患者；比较未采纳病名和旧诊断，并在同患者上拆分历史经过事实位置与直接进入诊断段的两条路。 |
| [The strength of clinical evidence is recoverable from language model representations but not from their stated grades](https://arxiv.org/abs/2606.29034)，2026 | 在六来源临床论断与22个模型中比较证据强度读出和自报等级；可读信号很大程度上与词汇有关，跨主题/框架转移有限。 | 读出器好于输出不等于模型内部已正确理解。本文避免用旧DDxPlus探针给新病例“判病”，使用原生候选评分、映射检验和干预交叉核对。 |
| [Elucidating Mechanisms of Demographic Bias in LLMs for Healthcare](https://aclanthology.org/2025.findings-emnlp.789/)，EMNLP Findings 2025 | 对医疗语境下的性别/种族表示做激活修补，影响病例生成与相关预测。 | 激活修补医疗模型本身不是贡献；本文研究同一患者的诊断历史与逐组证据更新，而非人口学标签生成。 |
| [Scale-Invariant Normalization Hides Activation Scaling](https://aclanthology.org/2026.blackboxnlp-1.66/)，BlackboxNLP 2026 | 复核医疗人口学偏差干预，指出归一化前后干预位置会改变“局部/分布式”解释。 | 对我们是直接的方法要求：准确记录残差/MLP干预位置、正常作答能力和随机对照。单次补丁失败不能证明该位置没有信息。 |
| [Same Illness, Different Voice](https://arxiv.org/abs/2607.27384v3)，2026-11-03版 | 对1000个MedQA病例做不同说话方式的改写并比较12个模型；发现语言呈现影响诊断，文本改写有一定补救效果。 | 本文固定当前患者原文，以历史变化和内部通路为自变量。检索索引仍显示旧标题“Same Facts, Different Diagnosis”，引用采用v3的正式标题。 |
| [LLM Sensitivity Evaluation Framework for Clinical Diagnosis](https://aclanthology.org/2025.coling-main.207/)，COLING 2025 | 通过关键医学信息扰动检验诊断敏感性。 | “改证据会改答案”不是空白。本轮的问题是同一证据的作用是否依赖先前判断，以及这种依赖经过哪个计算环节。 |
| [Can LLMs Replace Clinical Doctors?](https://aclanthology.org/2024.findings-emnlp.814/)，EMNLP Findings 2024 | 在大规模临床记录中研究疾病预测偏差，并报告对病历中既有病名的重复倾向。 | 因此仅提及效应也不能泛化宣传为“首次发现病名会影响模型”。更有价值的是未采纳条件、证据更新和内部通路之间的联合结果。 |

## 更合适的引言逻辑

患者的新检查并不是模型看到的唯一信息：它也会看到一个先前的病名。新证据进入后，诊断改变可以来自三件不同的事：患者事实改变了，先前病名改变了事实的处理，或者先前病名直接影响最终答案的形成。最终答对率只能看到这些过程混合后的结果。

已有研究已充分说明临床模型会受历史、错误提示和表述影响。内部探针与steering又说明这些影响可以在激活中测量或操纵。接下来的具体问题是：**在保持患者事实相同的条件下，如何把“看到一个病名”“已经给出这个诊断”“根据新事实更新”和“最后输出这个诊断”拆开？**

本轮以相同病例的配对操作回答这一问题：先比较不同历史下的外部判断与逐证据更新，再追踪逐层状态，最后对事实位置、诊断位置以及两类信息路径做干预。贡献应写成这组实验得到的实质结论，而不是把数据来源数量、探针或干预工具排列成创新点。

## 引用边界

上述前五项与本文关系最直接，应进入Introduction/Related Work。其他既有调研保留在[上一版文献位置](../../research_v3/RELATED_WORK_POSITION.md)。本次核对SRW论文正文的任务、样本与研究问题，并核对其他论文的官方页面/摘要；没有把未读完的出版商全文当作已全面比较。本轮没有做全球首次证明，不使用“此前无人研究医学信念/内部医学偏差”的表述。
