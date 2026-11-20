# 医学信念更新：Introduction、Related Work 与逐篇对照

版本：v0.2；原综述检索日期：2026-11-18，本轮补充核查：2026-11-19。服务于[当前论文主线](01_STORY.md)，随实验和文献更新。

**核心定位：把“医学证据怎样改变诊断”与“这个改变怎样在模型内部发生”连接起来，并通过干预解释具体的更新机制。**

本文整合项目已有的两份调研，并新增医学内部表示、跨语言医学知识访问、信念状态几何及干预方法研究。共列出 46 条工作记录，其中访问或出版状态不完整的条目明确标注。它是围绕本项目的定向综述，不宣称穷尽全部相关论文。

## 阅读导航

1. [最接近我们的工作](#closest)：先判断重合在哪里。
2. [Introduction 中文工作稿](#introduction)：可继续打磨成论文引言。
3. [Related Work 中文工作稿](#related-work)：按研究问题组织的正文。
4. [逐篇工作对照](#catalog)：研究什么、怎样做、与我们如何对应。
5. [对当前论文和实验的影响](#implications)：哪些主张已有人做，下一步需要什么证据。
6. [核查范围与版本记录](#verification)：区分正文核查、摘要核查与待核查。

文中“我们的差异”表示研究目标或设计比较；是否成为贡献，取决于完成实验后的结果。“输入干预”指改变提示、旧判断或证据；“内部干预”指改变模型激活等计算。两者都能用于因果问题，但回答的层次不同。

<a id="closest"></a>
## 一、最接近我们的工作

**真正需要重点对照的不只有 DeReLab。医学更新、医学内部解释、内部信念动态都已有直接先例。**

下表比较各工作的主要研究对象，不用简单的勾叉表把其他论文尚未核查的内容写成“没有做”。编号对应后面的原文与阅读记录。

| 工作 | 已覆盖的核心问题 | 与我们最直接的重合 | 我们需要额外回答的问题 |
|---|---|---|---|
| A03：医学诊断概率一致性 | DDxPlus、证据顺序、冗余、更新方向、模型规模 | 同数据来源、逐步证据、诊断支持与顺序对照 | 哪些内部计算造成更新，以及干预能否定向改变它 |
| A01：临床判断纵向更新 | 病情变化时，旧评估怎样影响新风险判断 | 医学信念更新、历史依赖 | 将输入层面的历史效应连接到层、头或模块的计算 |
| C01：医学知识地图 | 医学概念的内部表示、层删除和激活替换 | 医学内部机制与跨模型分析 | 同一患者逐条证据到来时，竞争诊断怎样被重新组织 |
| C02：TLoRA 医学跨语言研究 | 中间表示与最终回答的差异，读出和激活替换 | “内部已有信息但输出未体现”的表象和工具 | 解释证据累积中的更新规律，而不是复述知识访问失败 |
| B05：Same Answer, Different Future | 当前预测相同，后续更新是否相同；文本与激活形成状态 | 内部信念、读出、状态干预、更新动态 | 在多疾病竞争中找到经验证的证据整合机制 |
| B01：DeReLab | 多轮支持/反对证据，逐轮形式真值 | 先判断、再给证据、观察撤回或坚持 | 内部状态如何转化为判断；医学的不确定参照如何评价 |
| B03：BayesBench | 多轮证据下的信念轨迹、潜变量推断与预测 | 过程评价、多环境、规模比较 | 自然医学证据与内部因果计算之间的联系 |
| A02：脚本一致性测试 | 新线索怎样改变医学诊断或处置的合理性 | 评价一次医学更新，而非只看终点 | 连续多轮与内部变化，而非仅判断一条线索的影响 |
| C09：信念状态几何 | 用可计算生成过程检验内部信念表示 | 内部“信念”能否被读出和量化 | 从可计算状态扩展到医学证据时，哪些机制仍成立 |

上述问题有交叉，但“把几种已有工具放在一起”本身也不是机制发现。我们最终需要一个清楚、可重复的新解释，例如某类证据如何在特定计算过程中被保留、抵消或覆盖，并给出成立条件。现在保留这些候选解释，尚不指定最终答案。

<a id="introduction"></a>
## 二、Introduction 中文工作稿

以下保留最初的定位引言；当前基于完成实验的正文已写入[完整论文稿](07_MANUSCRIPT.md)。新增方法重合与测量差异见[机制补充](08_MECHANISM_RELATED_WORK_ADDENDUM.md)。

一个模型最初怀疑某种疾病，随后收到新的症状、病史或检查信息。它可能转向另一种诊断，也可能坚持原判，甚至在曾经命中最终疾病后再次偏离。只观察最后一次回答，我们无法知道哪些信息改变了它的判断，也无法区分一次合理的修正与一次由无关因素引起的转向。本文关注的正是这个过程：**医学证据如何成为模型当前的疾病判断，以及这种判断如何随着新证据更新。** 此处的场景是研究问题的示意，不是新增实验结果。

这一问题已有重要的行为研究基础。脚本一致性测试考察新线索对医学判断的影响；纵向临床研究分析先前评估对当前预测的作用；诊断概率研究则直接检查证据排列与更新一致性。这些工作表明，评价过程不能只依赖终点答案，同时也使“研究医学信念更新”本身不再足以构成新的贡献。[SCT](https://doi.org/10.1056/AIdbp2500120)、[纵向临床更新](https://arxiv.org/abs/2610.02684)、[诊断概率一致性](https://www.mdpi.com/2504-4990/8/11/369)

内部解释研究进一步提供了分析这一过程的工具与先例。医学知识地图已经结合表示分析和内部干预；跨语言医学研究也已检验中间层信息与最终回答之间的差异。因此，我们的问题需要从“内部有没有医学知识”推进到“新证据到来后，这些信息如何参与竞争诊断的更新”。[医学知识地图](https://arxiv.org/html/2510.11390v2)、[医学跨语言访问](https://arxiv.org/pdf/2608.00207v2)

我们将医学信念操作化为与疾病判断有关、能够被重复测量并接受干预检验的模型状态。研究同时追踪三个层次：输出端对竞争疾病的相对支持、内部各层可读出的疾病信息，以及特定计算对最终诊断的实际作用。仅有某个概率或一张聚类图不足以完成这条论证；状态还应通过新证据下的变化和干预效应得到检验。相关的受控研究已经说明，当前回答一致并不保证未来更新一致。[状态与后续更新](https://arxiv.org/html/2611.07913v2)

据此，我们对同一患者逐组揭示证据，在每个前缀记录诊断支持与模型内部状态，并通过事实集合相同的顺序对照、输出格式对照及模块替换来区分不同解释。最终疾病标签用于判断终点命中，参考鉴别诊断用于描述合理候选范围；不将最终标签直接当作每轮唯一合理答案。数据选择与参照定义遵循所用数据的实际字段，而非由被测模型自行生成答案。[DDxPlus 数据说明](https://github.com/mila-iqia/ddxplus/blob/main/README.md)

当前探索已在 Qwen3-1.7B 上完成逐轮、逐层观测与部分干预：诊断对排列和输出设置有明显依赖。旧MLP替换在编码与完整病名条件下方向不同，不能解释为可直接搬运的旧疾病结论。新增词元分解表明，最后层回答前位置的干预只改变首个输出词元。固定问卷、独立新病例和疾病方向干预现已完成：内部信息可读性与诊断表现分离，方向干预有输出作用，但当前剂量未新增正确诊断。[现有证据表](03_EVIDENCE_LEDGER.md)、[输出路径分解](../results/13_token_path/RESULTS.md)

**写成投稿引言时：**前五段压缩成问题、已有覆盖、具体未解决问题与研究路线；最后一段替换为最终确认的主结果。不要保留实验日记式措辞，也不要在结果尚未完成时写“本文首次揭示了普遍机制”。

<a id="related-work"></a>
## 三、Related Work 中文工作稿

### 3.1 医学证据更新与交互诊断

医学推理研究已从单次答题扩展到新信息的利用和交互过程。SCT 通过专家参考评价新增线索的方向与强度；纵向临床更新工作研究旧评估如何影响后续预测。OncoRounds 关注主动索取信息，MTDiag 构建多来源的多轮诊断材料。这些路线分别提供更新质量、历史依赖、信息获取及交互任务的参照。我们的分析重点放在同一病例证据更新的内部计算解释；固定证据揭示与主动问诊是不同实验设置，应分别比较。[A02](https://doi.org/10.1056/AIdbp2500120)、[A01](https://arxiv.org/abs/2610.02684)、[A04](https://arxiv.org/abs/2607.10275)、[A05](https://arxiv.org/abs/2608.25085)

### 3.2 信念修正、先前判断与证据选择

Belief-R 和 DeReLab 将新信息下的结论修正构造成可评估任务，BayesBench 进一步比较多轮推断与预测。Competing Biases 区分旧答案的支持效应与相反建议的权重；主动规则发现和搜索代理研究则将偏差定位到证据选择、检索和使用等环节。我们据此区分“资料变化”“资料排列”“先前回答可见”三种因素，而不将所有转向统称为确认偏误。[B02](https://aclanthology.org/2024.emnlp-main.586/)、[B01](https://aclanthology.org/2026.emnlp-main.1625/)、[B03](https://arxiv.org/abs/2606.30850)、[B04](https://doi.org/10.1038/s42256-026-01217-9)、[B06](https://arxiv.org/abs/2604.02485)、[B07](https://arxiv.org/abs/2611.05720)

### 3.3 医学知识表示与内部信念

医学知识地图与 TLoRA 已表明，医学任务可以结合层内读出和干预开展分析。另一方面，Latent Taxonomies 和事实学习动力学通过控制训练数据追踪表示形成；信念状态几何则在已知生成过程中连接理论状态与激活。本文借鉴其“明确问题—量化表示—检验作用”的路径，但当前研究是冻结模型在推理时的证据更新，不声称解释了医学知识在预训练中的形成。[C01](https://arxiv.org/html/2510.11390v2)、[C02](https://arxiv.org/pdf/2608.00207v2)、[C04](https://arxiv.org/html/2610.15836v1)、[C05](https://arxiv.org/html/2503.21676v2)、[C09](https://arxiv.org/abs/2405.15943)

### 3.4 如何读取和验证模型状态

Tuned Lens 将中间状态映射到预测分布，潜在知识与真值表示研究则考察读出、泛化及输出干预。它们支持区分“能够从状态中读出的信息”与“模型最终表达的内容”，但读出目标不同会带来不同解释。Same Answer 工作进一步提醒我们，单次输出的匹配不足以证明状态等价。我们的读出训练目标、评估病例与干预检验因此分别定义。[D01](https://arxiv.org/abs/2303.08112)、[C06](https://arxiv.org/abs/2212.03827)、[C07](https://arxiv.org/abs/2310.06824)、[C08](https://arxiv.org/abs/2306.03341)、[B05](https://arxiv.org/html/2611.07913v2)

### 3.5 呈现方式与因果解释的检验

选项偏差和上下文位置研究说明，输出变化可能包含与任务内容无关的因素。注意力解释的讨论要求根据具体模型和对照检验图中权重的意义；激活替换研究也指出测量指标、替换方式及组件交互会改变结论。因此，本文将编码与顺序控制、读出验证及因果干预作为同一证据链的一部分。[D06](https://arxiv.org/abs/2309.03882)、[D07](https://aclanthology.org/2024.tacl-1.9/)、[D04](https://aclanthology.org/N19-1357/)、[D05](https://aclanthology.org/D19-1002/)、[D02](https://arxiv.org/abs/2309.16042)、[D09](https://arxiv.org/abs/2606.27510)

这五节为可压缩正文。最终篇幅取决于主发现：若证据整合成为核心，增加医学更新与证据选择；若内部状态机制成为核心，增加表示与干预，减少一般人机协作背景。

<a id="catalog"></a>
## 四、逐篇工作对照

每条的“比较”是本项目的分析，不是原作者对我们的评价。未读到完整方法的条目只概括作者明确报告的内容，不能据此证明某个实验未被做过。

### A. 医学信念、诊断更新与数据

#### A01｜临床判断的纵向更新

Zeng、Zhang，2026，arXiv。*Large language models exhibit unreliable updating of clinical judgment as patient evidence evolves*。[原文 v1](https://arxiv.org/html/2610.02684v1)

**研究与方法：**使用纵向 ICU 资料，比较只看当前信息与同时看到旧评估；控制当前证据或提供的旧风险，测后续估计变化。作者报告历史评估可能增加预测误差，且对改善和恶化的响应不对称。

**比较：**这是医学信念更新的直接前例。它操纵上下文中的评估；我们需要进一步定位内部计算。当前实验没有旧回答历史，不能冒充已经复现该设置。核查：正文相关设计与作者摘要。

#### A02｜脚本一致性测试 SCT

McCoy 等，2025，NEJM AI。*Assessment of Large Language Models in Clinical Reasoning: A Novel Benchmarking Study*。[出版原文](https://doi.org/10.1056/AIdbp2500120)

**研究与方法：**750 道题测试新线索对诊断或处置的影响，用专家组答案分布计分。作者报告模型与资深临床人员存在差距，部分推理模型倾向极端影响评分。

**比较：**“新证据应如何改变判断”已有成熟医学任务。可借鉴其允许合理分歧的参照；专家一致性分数不等于精确疾病后验。核查：正文方法与结果。

#### A03｜诊断概率的一致性

Arun、George、Bhasuran，2026，Machine Learning and Knowledge Extraction。*Probabilistic Coherence of Stated Diagnostic Beliefs in Large Language Models: Anchored Tests on a Synthetic Clinical Corpus*。[出版页面](https://www.mdpi.com/2504-4990/8/11/369)

**研究与方法：**在 DDxPlus 上检验顺序、更新、冗余和位置，使用重复测量等参照。作者报告口头诊断与所报概率排序存在差异，原始与归一化指标可能给出不同规模趋势。

**比较：**与我们的行为设置高度接近。“换证据顺序”不能单独作为创新。下一步应核对其评分接口，并比较我们测得的输出支持与内部因果效应。核查：本轮出版摘要；PDF接口未成功解析，细节沿用旧笔记前须复核。

#### A04｜OncoRounds：主动调查失败

Braitsch 等，2026，arXiv。*Information-seeking failures of large language models in agentic clinical reasoning*。[作者摘要](https://arxiv.org/abs/2607.10275)

**研究与方法：**在分阶段肿瘤病例中让模型主动索取资料，再提交诊断和治疗。作者发现信息利用与表现相关，推理文字评分不能充分反映最终结论质量。

**比较：**主动取证、过早停止已有直接医学研究；我们的固定揭示实验控制所见证据，回答的是后续整合。核查：本轮摘要；具体病例构建参见历史阅读记录，投稿前复核正文。

#### A05｜MTDiag：多来源多轮诊断

Chouayfati 等，2026，arXiv。*MTDiag: A Multi-Turn Diagnostic Dataset Towards Clinically Meaningful LLM Evaluation*。[作者摘要](https://arxiv.org/abs/2608.25085)

**研究与方法：**结合 DDxPlus、MIMIC-IV 与病例报告，使用统一医学概念/诊断编码及对话生成流程，构建多轮诊断材料。

**比较：**它覆盖“多病例、多轮、统一疾病概念”的数据路线。可作为数据扩展候选；需要核查授权、可见资料与诊断泄露。核查：摘要；尚未完成数据下载审计。

#### A06｜BELIEF：用信念更新改进医学模型

Guo 等，2026，EMNLP。*Trustworthy Medical LLMs via Bayesian Belief Updating*。[正式页面](https://aclanthology.org/2026.emnlp-main.1678/)

**研究与方法：**结合显式候选信念更新与不确定性驱动的医学证据检索，作者报告多个数据集上的表现改善。

**比较：**这是构建改进框架；我们研究冻结模型原有计算。人为规定的更新模块不能直接当作模型自然实现的贝叶斯机制。核查：本轮正式摘要；训练奖励和推理接口以论文 PDF 为准，不能只据名称推断。

#### A07｜医学多轮迎合

Kim 等，2026，HeaLing Workshop。*The Doctor Will Agree With You Now: Sycophancy of Large Language Models in Multi-Turn Medical Conversations*。[正式页面](https://aclanthology.org/2026.healing-1.2/)

**研究与方法：**逐步加强用户质疑，测量多个模型在医学问题上的立场保持与改变；作者报告任务之间的抵抗程度不同。

**比较：**用户施压与新增医学事实应分开。坚持初始错误不代表更可靠；未来加入回答历史时需同时记录真值。核查：正式摘要；评分定义见已存历史笔记，使用具体数值前复核正文。

#### A08｜患者主张的分级影响

Manoranjan 等，2026，arXiv。*The Patient Is Always Right? Evaluating Sycophancy in Medical Diagnosis with Graded Patient Beliefs*。[作者摘要](https://arxiv.org/abs/2610.34013)

**研究与方法：**改变患者坚持的疾病与病例证据的相符程度及表达角色，检查模型是否接受该诊断；部分条件包含虚构疾病。

**比较：**直接覆盖“非证据性的他人信念改变诊断”。我们的历史条件需区分患者意见、医生意见与模型自己的旧答案。核查：摘要。

#### A09｜医生意见的帮助与误导

Lopez 等，2026，arXiv。*Clinician input steers AI toward accurate and harmful recommendations*。[当前作者页面](https://arxiv.org/abs/2603.14158)

**研究与方法：**比较正确专家内容和误导性医生内容进入上下文后的诊断与建议变化，并研究多轮分歧。

**比较：**医生信息的影响已有直接研究。内容有用性、身份和表达信心需独立控制；与医生一致不等于正确。核查：当前摘要。旧笔记标题对应早期版本，此处采用本轮页面标题。

#### A10｜ChronoEvo：指南修订的落实

Zeng 等，2026，arXiv。*Large language models show systematic failures in incorporating evolving medical knowledge*。[作者摘要](https://arxiv.org/abs/2610.30631)

**研究与方法：**从新旧指南构建建议变更，分开评估识别变化和实际落实。作者报告两者存在缺口。

**比较：**“承认变化却未改变建议”已经被研究。指南适合扩展知识更新，不应与同一患者的新症状简单合并。核查：当前摘要；本项目尚未运行指南轨道。

#### A11｜医学错误信息的接受

Omar 等，2026，The Lancet Digital Health。*Mapping the susceptibility of large language models to medical misinformation across clinical notes and social media: a cross-sectional benchmarking analysis*。[出版原文](https://doi.org/10.1016/j.landig.2025.100949)

**研究与方法：**在病历、社交材料及模拟病例中呈现错误医学内容，比较修辞包装；多数被测谬误包装并未增加接受程度。

**比较：**证据来源与表述本身已有影响研究。跨材料差异不能直接归因为文风，需同一事实配对。核查：出版摘要及索引正文片段。

#### A12｜DDxPlus：病例和参考分布来源

Tchango 等，2022，NeurIPS Datasets and Benchmarks。*DDXPlus: A New Dataset For Automatic Medical Diagnosis*。[论文](https://proceedings.neurips.cc/paper_files/paper/2022/hash/cae73a974390c0edd95ae7aeae09139c-Abstract.html)、[数据文档](https://github.com/mila-iqia/ddxplus)

**研究与方法：**模拟患者数据同时给出疾病标签、症状/病史与鉴别诊断，支持自动诊断和信息收集。

**比较：**它提供病例世界，不提供本研究每个任意揭示前缀的精确后验。必须报告参考候选覆盖与模拟数据属性。核查：论文摘要、官方字段说明及本地源数据。

### B. 一般信念更新、证据权重与主动调查

#### B01｜DeReLab

Sadhu 等，2026，EMNLP。*DERELAB: Probing Defeasible Reasoning and Confirmation Bias in LLMs with a Generative Benchmark*。[正式页面](https://aclanthology.org/2026.emnlp-main.1625/)、[方法 v1](https://arxiv.org/html/2608.30413v1)

**研究与方法：**从规则图生成多轮可撤回推理，每轮有形式化真值，比较支持和削弱信息的处理。

**比较：**与“先判断、再给正反证据、观察跳变”直接重合。我们的新增结论需要具体内部机制，而非只把规则实体换成疾病。核查：正式摘要与原文相关方法。

#### B02｜Belief-R

Wilie 等，2024，EMNLP。*Belief Revision: The Adaptability of Large Language Models Reasoning*。[正式页面](https://aclanthology.org/2024.emnlp-main.586/)

**研究与方法：**用信念修正任务评价新信息下结论的适应能力；作者同时发现，善于改变的模型也可能在无需修改时表现较差。

**比较：**撤回旧答案是已有评估对象。医学资料存在多种合理诊断，不能直接套用形式推理的唯一标签逻辑。核查：正式摘要；详细任务类型在最终使用前复核 PDF。

#### B03｜BayesBench

Samanta 等，2026，arXiv。*BayesBench: Evaluating LLM Belief Trajectories Under Multi-Turn Evidence Accumulation*。[作者摘要](https://arxiv.org/abs/2606.30850)

**研究与方法：**用多种模拟环境区分潜变量估计与结果预测，并改变互动框架；作者报告规模带来的推断改善未必传递到预测。

**比较：**多环境信念轨迹和规模分析已有先例。我们的受控参照轨道要说明它为哪项医学机制检验服务。核查：摘要及历史原文阅读；不同环境的真值条件不可混称精确贝叶斯后验。

#### B04｜旧选择与相反建议的竞争

Kumaran 等，2026，Nature Machine Intelligence。*Competing Biases underlie Overconfidence and Underconfidence in LLMs*。[出版页面](https://doi.org/10.1038/s42256-026-01217-9)

**研究与方法：**控制旧答案是否可见及建议方向/可靠性，结合行为模型，解释坚持旧答案和对反对意见过度更新的并存。

**比较：**不能把“固执”和“轻易改口”当作同一机制。我们可将其作为历史条件的行为对照，再检查内部实现。核查：出版社索引的摘要及方法内容，不将行为计算模型等同于神经机制。

#### B05｜同一个当前答案，不同的后续更新

Li 等，2026，arXiv。*Same Answer, Different Future: Dissociating Belief Content and Evidence Weight in Language Models*。[阅读版本 v2](https://arxiv.org/html/2611.07913v2)

**研究与方法：**在可计算概率任务中，通过记录、摘要、陈述和激活干预形成状态，再追加相同证据；比较当前读出与后续改变。

**比较：**这是内部信念动态的重要邻近工作。一次干预改对答案还不够；我们也应检查后续更新是否保持。核查：v2 正文相关设计。检索摘要另有不同标题和实验范围，本文不拼接版本数值。

#### B06｜主动寻找反例

Jhaveri 等，2026，arXiv。*Failing to Falsify: Evaluating and Mitigating Confirmation Bias in Language Models*。[作者页面](https://arxiv.org/abs/2604.02485)

**研究与方法：**通过交互式数字规则发现任务，记录模型提出的测试是否试图推翻当前假设，并研究提示和训练干预。

**比较：**“模型偏好验证自己”已有主动实验。若增加问诊选择，必须把查什么与如何使用查到的信息分开。核查：当前摘要，历史方法笔记。

#### B07｜搜索过程中偏差出现在哪一步

Xiao、Yu，2026，arXiv。*Cognitive Bias Signatures in Search-Equipped LLM Agents: A Stage-Resolved Analysis*。[作者页面](https://arxiv.org/abs/2611.05720)

**研究与方法：**固定问题和合成文档库，操纵顺序、过去工作和初始假设，追踪查询、检索、打开与最终答案。

**比较：**阶段分析与长度控制已有先例。我们需要把外部过程进一步接到内部计算，而不只增加日志层级。核查：摘要及历史方法笔记。

#### B08｜相信或怀疑如何改变联网研究

Vohra、Xu，2026，REALM Workshop。*Research Agents Feed Doubts, Not Beliefs: Auditing Belief Framing in Live-Web Search*。[正式页面](https://aclanthology.org/2026.realm-1.45/)

**研究与方法：**对健康主张改变用户立场，并交叉重放检索证据，区分获取与解释证据的作用。

**比较：**输入立场对取证和解读的分解已有直接先例。可以借鉴同证据重放，但不能把程度偏移写成普遍真假翻转。核查：正式摘要及历史方法记录。

#### B09｜用鞅性质检测信念固化

He 等，2025，arXiv。*Martingale Score: An Unsupervised Metric for Bayesian Rationality in LLM Reasoning*。[作者页面](https://arxiv.org/abs/2512.02914)

**研究与方法：**以统计回归衡量当前信念是否系统预测未来更新，在开放问题中研究信念固化。

**比较：**“越推理越确信”及过程合理性已有量化。鞅参照依赖信息与抽样假设，不能直接套在被刻意排序的医学证据上。核查：摘要；指标假设使用前复核。

#### B10｜识别筛选偏差，却没有数值纠正

Deng、Yan，2026，SSRN 工作论文。*Large Language Models Can Recognize Evidence Selection Yet Fail to Correct Numerical Advice*。[作者论文入口](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7066638)

**研究与方法：**区分识别证据经过筛选和利用被省略信息作数值纠正，使用受控选择规则。

**比较：**口头承认信息有偏不代表判断已改。我们的证据选择实验也需要行为分数，而不只分析解释文字。核查：作者页面搜索索引中的摘要；直接全文访问未成功，不据此宣称精确划界。

### C. 医学内部表示、信念形成与因果读出

#### C01｜医学知识地图

Marinescu、Gruber、Fajardo，2025 预印本，公开会议稿标注 ICLR 2026。*Medical Interpretability and Knowledge Maps of Large Language Models*。[阅读版本 v2](https://arxiv.org/html/2510.11390v2)

**研究与方法：**结合中间激活投影、权重梯度、层删除和激活替换，比较人口资料、疾病与药物信息在多模型中的表示。

**比较：**医学概念的多层测量与因果定位已经有人做。我们应把研究单位落在“同一患者的新证据怎样重组疾病竞争”，而非再画一套静态知识地图。核查：正文方法；正式最终引用元数据仍以会议记录为准。

#### C02｜TLoRA：医学知识出现，却未成为答案

Abouzahir 等，2026，本文依据 arXiv v2。*Bridging the English-Arabic Medical Knowledge Gap: Targeted Low-Rank Adaptation via Causal Layer Selection*。[原文 PDF](https://arxiv.org/pdf/2608.00207v2)

**研究与方法：**用逐层读出和跨语言激活替换分析医学回答差距，据此选择局部适配层。

**比较：**这是“中间层有正确信息、输出未体现”故事的直接医学邻近工作；我们的初始现象不能据此单独主张新颖性。下一步应提出证据更新特有、可复验的机制。核查：正文第3节与方法相关内容。

#### C03｜EHR 基础模型中的临床特征

*Probing Clinical Concepts in an EHR Foundation Model via Sparse Autoencoders*。[公开 OpenReview 稿件](https://openreview.net/pdf/f12a4065d09c871d753df647d05fbf17306bceb3.pdf)

**研究与方法：**公开稿描述在 MIMIC-IV 事件序列模型上训练稀疏自编码器，分析临床特征并进行跨层激活替换。

**比较：**结构化临床序列的特征与内部干预也有先例，不能声称所有医学内部研究都是静态问答。其模型输入与聊天 LLM 不同。核查：原稿索引的摘要与方法片段；作者匿名、正式出版状态未核实，暂作重要线索，不填造作者或录用信息。

#### C04｜Latent Taxonomies

Sobotka 等，2026，arXiv。*Latent Taxonomies: How Property Induction Develops in Language Model Pre-training*。[阅读版本 v1](https://arxiv.org/html/2610.15836v1)

**研究与方法：**控制虚构实体及共享属性的训练经历，测属性归纳和内部分类结构；固定注入预算下，规模与归纳表现的关系不简单单调。

**比较：**我们借鉴受控经历与表示测量的研究方式。目前推理实验没有操纵预训练，不能解释医学预期最初如何形成。核查：v1正文；未将第三方转载的评审回复当作新版结果。

#### C05｜事实学习动力学

Zucchet 等，2025，COLM。*How do language models learn facts? Dynamics, curricula and hallucinations*。[阅读版本 v2](https://arxiv.org/html/2503.21676v2)

**研究与方法：**在受控人物事实数据上追踪训练，并通过注意力替换研究表面成绩平台期中的内部变化。

**比较：**表面输出不变不代表内部不变。这是我们同时追踪概率与表示的动机；训练阶段机制不直接移植为推理时机制。核查：正文设计与干预部分。

#### C06｜无监督提取潜在知识 CCS

Burns 等，2022 预印本。*Discovering Latent Knowledge in Language Models Without Supervision*。[原文入口](https://arxiv.org/abs/2212.03827)

**研究与方法：**利用肯定/否定等一致性结构，从激活中提取回答信息，区分内部可读知识与生成输出。

**比较：**“模型知道什么”和“说了什么”的分离已有基础。我们的疾病读出仍要验证迁移和因果使用。核查：作者摘要。

#### C07｜真值表示的几何与干预

Marks、Tegmark，2023 预印本。*The Geometry of Truth: Emergent Linear Structure in Large Language Model Representations of True/False Datasets*。[原文入口](https://arxiv.org/abs/2310.06824)

**研究与方法：**在真假命题上结合表示可视化、跨数据集探针迁移和激活干预，分析真值方向。

**比较：**读出、泛化与因果作用应一起检验。二元真假方向不是多疾病概率分布的现成替代。核查：作者摘要；本文按预印本年标注。

#### C08｜Inference-Time Intervention

Li 等，2023。*Inference-Time Intervention: Eliciting Truthful Answers from a Language Model*。[原文入口](https://arxiv.org/abs/2306.03341)

**研究与方法：**识别注意力头中的方向并在推理时调整激活，改善 TruthfulQA 表现，同时观察其他性能权衡。

**比较：**内部方向干预改变回答已有先例；干预后变好不自动证明该方向就是自然医学信念。核查：作者摘要与论文方法片段。

#### C09｜信念状态几何

Shai 等，2024，NeurIPS；arXiv 后续修订。*Transformers represent belief state geometry in their residual stream*。[作者页面](https://arxiv.org/abs/2405.15943)

**研究与方法：**在已知隐状态生成过程中训练模型，将理论信念几何与残差流中的可读表示比较。

**比较：**“模型内部存在可量化信念状态”不是未经探索的命题。它为精确参照轨道提供方法背景，医学自然资料则需要额外检验。核查：会议稿开篇和作者摘要。

#### C10｜上下文学习与隐式贝叶斯推断

Xie 等，2021 预印本，ICLR 2022。*An Explanation of In-context Learning as Implicit Bayesian Inference*。[原文入口](https://arxiv.org/abs/2111.02080)

**研究与方法：**在混合隐马尔可夫模型等假设下解释上下文学习，并用受控数据检验。

**比较：**提供规范与理论背景，不证明任意医学聊天模型都在精确计算后验。核查：作者摘要及理论设置概述。

### D. 测量、顺序与内部干预方法

#### D01｜Tuned Lens

Belrose 等，2023。*Eliciting Latent Predictions from Transformers with the Tuned Lens*。[原文](https://arxiv.org/abs/2303.08112)

逐层训练映射以读取中间预测，并检验其可靠性与因果相关性。**对我们：**读出方法是已有工具；当前六维分数校正不应直接命名为完整 Tuned Lens。核查：作者摘要及既有方法记录。

#### D02｜激活替换的指标与方法

Zhang、Nanda，2023 预印本，ICLR 2024。*Towards Best Practices of Activation Patching in Language Models: Metrics and Methods*。[原文](https://arxiv.org/abs/2309.16042)

系统比较替换设置和评价量对定位结果的影响。**对我们：**同时保存分数差、分布距离和输出有效性；局部效应要经配对及方向控制。核查：会议稿/作者摘要与方法内容。

#### D03｜如何解释激活替换

Heimersheim、Nanda，2024。*How to use and interpret activation patching*。[原文](https://arxiv.org/abs/2404.15255)

讨论替换方向、实验问题和结果解释的对应关系。**对我们：**恢复旧诊断、破坏当前诊断、恢复正确诊断是不同实验，不混成一个成功率。核查：作者摘要及项目既有方法记录。

#### D04｜注意力权重不自动构成解释

Jain、Wallace，2019，NAACL。*Attention is not Explanation*。[原文](https://aclanthology.org/N19-1357/)

在所测任务中比较注意力与其他重要性度量，并研究不同权重产生相似预测的情况。**对我们：**热图不能替代因果实验；不将其结论扩大成所有注意力研究都无意义。核查：正式摘要。

#### D05｜注意力解释需要具体检验

Wiegreffe、Pinter，2019，EMNLP-IJCNLP。*Attention is not not Explanation*。[原文](https://aclanthology.org/D19-1002/)

针对注意力解释提出均匀权重、随机种子等对照。**对我们：**将注意力作为可检验的证据，而不是先验接受或否定其解释价值。核查：正式摘要和方法概述。

#### D06｜选择题编码偏差

Zheng 等，2023 预印本，ICLR 2024。*Large Language Models Are Not Robust Multiple Choice Selectors*。[原文](https://arxiv.org/abs/2309.03882)

研究选项位置、答案编码 token 偏好及去偏方法。**对我们：**目前编码敏感性与这条已有研究直接相关；轮换平均是控制手段，不是新机制。核查：作者摘要与会议稿元数据。

#### D07｜上下文位置效应

Liu 等，2024，TACL。*Lost in the Middle: How Language Models Use Long Contexts*。[原文](https://aclanthology.org/2024.tacl-1.9/)

改变相关信息在上下文中的位置，测问答与检索表现。**对我们：**需要区分信息内容、文本位置与真实事件时间；顺序变化本身不是首次发现。核查：正式摘要。

#### D08｜模型对自身正确性的评估

Kadavath 等，2022。*Language Models (Mostly) Know What They Know*。[原文](https://arxiv.org/abs/2207.05221)

研究回答正确性的自我评价及模型是否知道答案的预测。**对我们：**自报把握、答案 token 概率、疾病相对支持是不同量，不混称为校准的医学后验。核查：作者摘要。

#### D09｜替换效应中的组件交互

Vaidyanathan 等，2026，arXiv。*The Curse of Multiple Mediators: Hidden Interaction Effects in Activation Patching*。[原文](https://arxiv.org/abs/2606.27510)

从因果中介角度分析组件替换与其他状态的交互。**对我们：**不同层作用符号相反，可能包含上下游交互；应检查配对与联合干预，而非仅按效应排行命名功能。核查：作者摘要，作为待深入的方法比较。

#### D10｜干预得到正确答案，也可能走了别的路径

Liu、Chen，2026，arXiv。*Right Answer, Wrong Mechanism: Detecting Pernicious Divergence in Causal Interventions*。[原文](https://arxiv.org/abs/2609.39243)

通过植入隐藏路径，研究干预成功是否反映自然计算。**对我们：**关注替换后的异常激活和自然配对；不能把该受控结果写成所有常规模型干预都失效。核查：作者摘要，尚未复现。

### E. 人类医学信念：背景参照，不作为模型机制证据

#### E01｜医生使用模型的随机试验

Goh 等，2024，JAMA Network Open。*Large Language Model Influence on Diagnostic Reasoning: A Randomized Clinical Trial*。[原文](https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2825395)

比较医生使用模型加常规资源与仅用常规资源；试验未显示明确的组间诊断推理收益。**比较：**可用于说明模型独立能力与协作效果不同，不能据此推断医生或模型内部偏差。核查：正文设计与结果。

#### E02｜AI 建议与医生自动化偏差

Qazi 等，2026，历史调研记录为 NEJM AI。*Automation Bias in Large Language Model–Assisted Diagnostic Reasoning among Physicians Trained in AI Literacy — A Randomized Clinical Trial*。[出版入口](https://doi.org/10.1056/AIoa2501001)

**保留为待复核条目。**本轮出版正文返回访问限制；不重复旧笔记的具体样本数与效应量。若用于引言，只能在重新核对作者摘要或正文后描述其结果。与当前模型内部实验属于不同研究对象。

#### E03｜医生锚定：看见与使用信息

Mamede 等，2026，Diagnosis。*Cognitive mechanisms underlying anchoring bias in diagnosis: a randomized controlled experiment*。[原文入口](https://doi.org/10.1515/dx-2025-0181)

比较病例干扰线索及其位置，结合眼动与回忆分析医生诊断。**比较：**启发我们区分接触、保留与使用信息，但人类认知测量不能直接替代模型注意力解释。核查：作者摘要及出版方法片段。

#### E04｜来源身份与公众健康信念

Ballot 等，2026，Scientific Reports。*Chatbots reduce health-related conspiracy beliefs not because of but despite being perceived as AI*。[出版原文](https://www.nature.com/articles/s41598-026-66242-5)

随机改变对话对象被标为人类还是 AI，测公众健康阴谋论信念的前后变化。**比较：**可作为来源身份控制的背景；被测信念属于人，不属于模型。核查：出版方法及摘要。

<a id="implications"></a>
## 五、这份调研如何改变我们的论文与实验

### 5.1 可以继续做，但贡献要落在具体发现上

| 原本容易写出的主张 | 文献对照后的判断 | 更具体的研究落点 |
|---|---|---|
| 医学模型会随证据改变信念 | A01—A03、B01—B03已有覆盖 | 解释哪类内部计算使更新发生或失败 |
| 多轮诊断不同于单轮诊断 | A04—A05已有直接路线 | 固定信息集合，定位历史与内部整合的作用 |
| 医学知识能从中间层读出 | C01—C03已有直接先例 | 跟踪同一患者在连续证据下的疾病竞争 |
| 中间有正确信息，最后却回答错 | C02与一般潜在知识研究接近 | 证明特定更新中的信息如何被覆盖，并用干预复验 |
| 读出概率就测到了内部信念 | B05、C09、D01要求更强验证 | 同时看读出稳定性、后续更新与实际因果使用 |
| 更大模型一定更合理 | A03、B03、C04提示指标与任务依赖 | 比较同一机制效应与相同参照，而非只排规模榜 |

### 5.2 v0.1提出的待检验问题（保留发现过程）

**同一条医学证据的作用，是否会在模型内部被不同阶段的计算重新分配，以至于最终疾病排序无法从某一中间层的支持直接预测？**

这是结合现有实验提出的候选问题，不是已确认的独占空白。它需要同时面对 A03 的行为过程研究、C01/C02 的医学内部研究、B05 的状态动态研究和 D09 的组件交互解释。

要把它变成论文贡献，至少需要三步：

1. 在候选覆盖更完整、参考定义清楚的多个疾病场景中重复总体更新现象。
2. 用经验证的读出定位具体变化，并把证据内容与位置、编码、历史因素分开。
3. 在新病例上通过自然配对与内部干预检验同一机制，给出其效应和成立条件。

若最后发现主要是一般上下文处理机制，论文就解释它如何在医学竞争诊断中表现；不能为了标题强行命名为医学专属模块。

### 5.3 文献对应的实验要求

| 要补的实验或分析 | 直接相关文献 | 用途 |
|---|---|---|
| 完整候选、口头回答与原始输出分数分开评价 | A03、A12、D08 | 明确“信念”测量接口 |
| 局部线索作用与终点标签正确性分开 | A02、B01、B03 | 避免把合理中间不确定性当成错误 |
| 当前资料固定，改变旧答案可见性 | A01、B04、A07—A09 | 隔离先前判断的影响 |
| 编码轮换、疾病名称及位置对照 | D06、D07、A03 | 排除呈现方式造成的假象 |
| 判断读出与真实疾病标签读出分开训练 | D01、C06、C07 | 分开准备说什么与哪些信息可被读出 |
| 干预后继续给相同的新证据 | B05、C09 | 检验状态动态，而不止当下答案 |
| 自身替换、方向控制、自然配对与联合干预 | D02、D03、D09、D10 | 增强机制解释的可信度 |
| 跨医学场景及非医学同结构对照 | C01、B03、C09 | 判断机制范围及医学特征 |

### 5.4 正文优先引用顺序

直接行为对照：A03、A01、A02、B01、B03。

直接内部对照：C01、C02、B05、C09；C03在元数据补齐后重新评估优先级。

形成过程与研究风格：C04、C05。

方法依据：D01—D07及C06—C08；D09/D10在涉及组件交互或分布外干预时使用。

其他医学交互与人类工作用于相应研究分支或简短背景，不必把所有条目都堆入最终正文。

<a id="verification"></a>
## 六、核查范围、检索记录与更新规则

### 6.1 本轮检索范围

来源优先级：论文出版页面与 ACL Anthology、arXiv 作者版本、NeurIPS/OpenReview 公开稿、官方数据仓库。项目历史笔记提供检索线索，不单独充当新结论的证据。未使用第三方自动总结来确立核心方法或创新性。

检索组合包括：`medical diagnosis belief updating`、`clinical belief hidden states`、`medical activation patching`、`medical logit lens`、`belief state geometry`，以及旧笔记内各论文的准确标题；沿医学知识地图的参考文献追查内部医学工作。未设只保留支持本项目创新的结果筛选。

“核查正文”指读取了相关方法或结果部分，不等于通读所有附录或复现代码。“摘要核查”只支持作者明确报告的研究范围，不支持断言全文未做某项实验。

### 6.2 需要保留的访问与版本差异

- A03：出版页面及摘要已读；本轮 PDF 返回不支持的内容类型。当前比较足以认定行为设置接近，评分细节还需全文复核。
- B05：本文采用v2正文标题；当前检索摘要呈现不同标题和更窄的实验描述。不得将两个版本的模型数、规模和结论混写。
- A09：论文标题发生版本变化；本文使用当前作者摘要页标题，旧调研原样保留。
- C01：原始预印本2025、所读v2为2026；公开会议PDF标注ICLR2026，正式参考文献导出时再次核对。
- C02：已读取arXiv v2 PDF的方法；第三方提及会议归属，但本文件不据第三方填写正式发表状态。
- C03：公开匿名稿和方法片段已定位，作者与最终出版信息未核实。
- B10：作者页面搜索索引的摘要可读，直接全文访问未成功。
- E02：本轮出版接口受限，只保留待复核记录，不将旧摘要数值写进本轮论证。

### 6.3 历史资料与当前材料

- [此前一般信念调研](../../paper/RELATED_WORK_GUIDE_20261117.md)
- [此前医学信念调研](../../paper/MEDICAL_BELIEF_RELATED_WORK_20261117.md)
- [现有实验事实与口径](03_EVIDENCE_LEDGER.md)
- [统一测量设计](../protocol/MEDICAL_BELIEF_MASTER_DESIGN.md)

原有调研保留其阅读版本；新论文优先使用本文明确核查的原文和版本。发表年份、作者、标题及会议信息进入正式 BibTeX 前逐条从权威页面导出核对，不手工补猜。

### 6.4 每阶段如何更新

完成一个实验阶段后，更新对应论文的比较结论：我们具体新增了哪种证据；是否已有相同因果实验；结论的条件是否不同；是否足以改写引言里的问题和贡献。新增最接近论文时，先更新本文件，再同步主线与修订记录，不通过删除重合工作来维持原叙述。

原v0.1综述本身没有运行模型。v0.2将阶段13—20实验解释接入当前论文，并保留原始文献核查范围；完整实验结果以[当前证据表](03_EVIDENCE_LEDGER.md)和[论文稿](07_MANUSCRIPT.md)为准。
