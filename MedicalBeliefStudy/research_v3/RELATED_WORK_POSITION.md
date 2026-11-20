# 新实验的文献位置：医学信念怎样成为诊断

检索核对日期：2026-11-19。下表用于调整论文的贡献位置；“差别”不等于已经证明全球首次。

| 已有研究 | 他们已经做了什么 | 本轮实验要继续回答什么 |
|---|---|---|
| [Probabilistic Coherence of Stated Diagnostic Beliefs](https://www.mdpi.com/2504-4990/8/11/369)，2026 | 在DDxPlus上大规模检验证据顺序、重复、更新方向与自报概率一致性；诊断名称与自报概率也会不一致。 | 我们不以“换顺序会改诊断”为核心创新，而测量每条证据到来后所有层中的疾病信息，与原模型完整病名评分的关系，再删除实际发生的内部更新分量。 |
| [Large language models exhibit unreliable updating of clinical judgment as patient evidence evolves](https://arxiv.org/abs/2610.02684)，2026 | 用ICU纵向记录研究先前判断对当前风险估计的影响、恶化/改善证据的不对称更新。 | 历史判断影响本身已有先例。本轮将同样的历史对照与逐层疾病读出配对，区分内部疾病信息改变和最终选择改变。 |
| [When Correct Beliefs Collapse](https://aclanthology.org/2026.acl-long.395/)，ACL 2026 | MED-STRESS研究临床对话中的社会压力及正确诊断动摇，测试9个模型并提出防御与微调。 | 本轮没有把用户施压作为新机制；研究真实来源证据逐步加入时的内部状态，以及固定事实下先前诊断的影响。 |
| [MedEinst](https://aclanthology.org/2026.acl-long.1847/)，ACL 2026 | 49种疾病、5383对反事实病例，改变鉴别证据形成诊断陷阱，研究固有模式与病例证据冲突。 | 不把“医学模型依赖捷径”重新包装为发现。重点是同一患者的内部更新是否被输出采用，以及局部更新移除后的反应。 |
| [Medical Interpretability and Knowledge Maps](https://proceedings.iclr.cc/paper_files/paper/2026/hash/17aa70697d6cd35835f201c6fb0a2fd5-Abstract-Conference.html)，ICLR 2026 | 用激活投影、梯度显著性、层移除和激活修补描绘医学概念的层间分布，并发现非单调表示。 | “医学信息分布在不同层”不是空白。我们的分析单位是同一个病人的相邻证据轮次，将自然变化、冻结的独立读出、原生输出与干预连在一起。 |
| [Sequential diagnosis with language models](https://pubmed.ncbi.nlm.nih.gov/42912144/)，Science 2026 | 研究主动获取信息、更新鉴别诊断、准确率及检查成本。 | 本轮固定证据获取过程，主要研究内部计算怎样变化，不宣称率先做序贯诊断。 |
| [DERELAB](https://aclanthology.org/2026.emnlp-main.1625/)，EMNLP 2026 | 对可撤销推理和确认偏差进行生成式基准评估。 | 医学患者来源事实与模型内部因果测量构成本轮对象；不以正反证据选择游戏或通用确认偏差bench作为论文核心。 |

## 更合适的中心问题

进一步检索还找到更直接的近邻：[Large Language Models Develop Belief State Geometry In-Context](https://arxiv.org/abs/2609.17376)已在HMM控制环境用线性读出和干预检验belief state；[MedEVM](https://arxiv.org/abs/2609.35627)研究动态医学证据的价值、诊断提交与顺序影响；[Probing conflict resolution between contextual and parametric knowledge in medical language models](https://www.sciencedirect.com/science/article/pii/S095741742602628X)的出版商摘要及引言检索内容明确介绍MinPairProbe：最小对比上下文、答案位置读出、内部检测与外部行为分离，以及上下文替换/steering。作者为Zhengqiu Yu、Yueping Ding、Xiangrong Liu；2026年已在线，正式卷期为Expert Systems with Applications 332 (2027), 133720。直接正文接口返回403，本次已核对出版商摘要与可检索引言/章节片段，没有声称读完全文。因此“对医学信念做探针或steering”本身也不能作为新贡献。需用新病例的**自然逐条证据更新、内部—输出配对，以及目标/随机的自然分量移除**形成具体可检验的结论。

**同一份医学证据进入模型后，形成的疾病信息、随证据发生的更新、以及最终诊断，是怎样联系又怎样分开的？**

这句话比“模型也有偏见”具体，也比“某层准确率更高”完整。文章需要连续跨过四个证据门槛：

1. 新病例中复现内部可读信息与最终诊断的差距，明确两个测量接口。
2. 逐条证据到来后，确定内部更新与诊断更新是否同步，展示各种患者轨迹而非只挑异常。
3. 同样当前事实下，改变先前判断，比较内部与输出的反应。
4. 删除真实发生的内部更新分量，与等范数随机改动比较，判定读出方向是否参与当前输出变化。

证据顺序、重复、外部来源与不同模型配置用于检验上述关系的成立条件。它们增加解释力，但不各自包装为独立“首次发现”。

## 引用更新

旧论文将Medical Interpretability列为预印本；正式ICLR 2026论文已可核对，后续稿件应更新。MED-STRESS、MedEinst和Science序贯诊断研究需加入新稿。旧稿v0.5保留作为历史版本，不静默替换其中结论。
