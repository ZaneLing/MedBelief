# 与结构简化、医学内部机制工作的关系

检索日期：2026-11-20。下表依据论文原文、作者摘要或正式出版页。创新性判断是研究定位，不是保证不存在任何同类工作。

| 工作 | 已研究什么 | 本研究需要怎样区别与比较 |
|---|---|---|
| [Medical Interpretability and Knowledge Maps of Large Language Models](https://arxiv.org/abs/2510.11390) | 医学概念的层内表示，结合投影、参数显著性、删层和激活替换；比较多种模型 | 医学内部定位本身已有先例。我们追踪同一病例的逐证据更新，配对操纵旧诊断，并检验结构改变是否保留整条判断轨迹 |
| [Efficient Transcoder Adaptation for Fine-Tuned Models](https://ojs.aaai.org/index.php/AAAI/article/view/40604) | 在Gemma2-2B及医学微调变体上，以transcoder替代MLP做特征归因，分析模式匹配和多步推理 | “替换MLP来理解医学推理”也不是空白。本轮小模块用于计算替代和行为检验，尚未形成可命名的稀疏医学特征图；后续做transcoder需直接对照该工作 |
| [ShortGPT](https://aclanthology.org/2025.findings-acl.1035/) | 用输入输出相似程度衡量层影响并删层 | 本轮加入相同定义的Block Influence两层删除对照；它是对照指标实现，不宣称完整复现全部论文配置 |
| [Are Sixteen Heads Really Better Than One?](https://proceedings.neurips.cc/paper_files/paper/2019/hash/2c601ad9d2ff9bc8b282670cdd54f69f-Abstract.html) | 研究注意力头冗余及剪枝 | 注意力头可删除已有研究。我们区分对原诊断的贡献、对正确性的贡献、以及错误历史下的副作用；本轮最后位置门控不构成实际头压缩 |
| [Cutting Off the Head Ends the Conflict / PH3](https://aclanthology.org/2024.findings-acl.70/) | 定位内部记忆与外部上下文的冲突头，并通过头干预改变模型依赖哪种知识 | 与“删头减少旧诊断牵引”直接相关，必须作为主要先例。医学应用本身不够证明新机制；本轮更应检验同一病例逐证据更新、历史正误与部件作用的关系。没有将本轮零消融排名称作PH3完整复现 |
| [LASER: The Truth is in There](https://arxiv.org/abs/2312.13558) | 对特定层权重做秩截断，部分任务性能反而提高 | “简化模型可能改善答案”已有先例。不能将任何删改后的增益自动当作新发现；需要解释它改变的是医学证据处理还是历史诱导 |
| [ReplaceMe](https://arxiv.org/abs/2505.02819) | 用小校准集估计线性映射来近似被裁掉的Transformer块 | 线性近似计算本身不是创新。我们拟合的是特定MLP输出，同时检查同病例终点、逐证据路径、错误历史效应和输出接口 |
| [Half the Nonlinearity Is Wasted](https://arxiv.org/abs/2603.03459) | 系统研究用线性替代MLP及上下文门控，报告架构差异与部分非线性的负作用 | 与本轮简化思路直接重叠；不能声称首次发现非线性可省。我们的待检验问题是医学更新保持与忠实性、正确性是否分离 |
| [Compact Language Models via Pruning and Knowledge Distillation](https://proceedings.neurips.cc/paper_files/paper/2024/hash/4822991365c962105b1b95b1107d30e5-Abstract-Conference.html) | 联合结构剪枝与知识蒸馏得到较小模型 | 本轮只有局部线性拟合，参数压缩幅度有限；若要提出新压缩方法，需要在同等压缩率和训练预算上直接比较 |
| [Eliciting Latent Predictions from Transformers with the Tuned Lens](https://arxiv.org/abs/2303.08112) | 用学习的仿射读出改善中间层预测解释 | 中间层直连输出头可能存在读出失配。我们同时看代码覆盖和实际干预；当前读表不能等同于已恢复每层完整医学信念 |

## 论文的贡献应放在哪里

目前最合适的主线是：**同一份患者事实，如何在旧诊断背景下变成不同答案；哪些内部计算维持或改变这种偏向；改变结构后，终点分数是否掩盖了更新路径的变化。**

结构简化是对机制解释的压力测试。如果一个部件被称为“多余”，就同时检查终点和中间过程；如果被称为“有害”，就同时检查修好的病例与损坏的病例，以及中性与错误历史。如果只剩参数更少、总体答题率差不多，应该将它写成应用结果，不能代替医学信念的机制结论。

本轮深度匹配随机删除及Block Influence用于防止把普通冗余误认成医学专有机制。更强的工程方法比较（LASER、ReplaceMe、transcoder）仍需独立预算与相同条件实现；本轮没有运行这些方法，不用综述文字充当实验对照。
