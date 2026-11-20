# 当前研究：v0.10 医学信念、结构裁剪与小适配器

[先读：本轮结果](research_v6_adapters/START_HERE.md) · [一个病例的逐轮中文解释](research_v6_adapters/ONE_CASE_EXPLAINED.md) · [完整实验与论文主线](research_v6_adapters/RESULTS_AND_STORY.md) · [整合中文论文](acl_paper/v10_adapters/PAPER_ZH.md)

2026-11-20。Qwen3-1.7B完成22种开发配置，880个新增来源病例分为400训练、80开发、400确认；7个冻结确认配置，另补1个相同输出约束对照。24例、147个累计证据前缀、882次逐轮观测，保存28层状态。全部使用本地Apple GPU，模型API费用0美元。

保留全部28层、将后12层MLP通道减半，参数减少13.16%。同候选输出规则下，完整/压缩模型中性答对215/216例，错误历史答对168/180例（各400例）；这是结果后追加对照中的小幅优势。6例直接配对的实际回答耗时约少15%。原自由生成参照下，严格字符串评分的增益被空格等写法差异放大，规范化后未确认稳健显著改善；不将格式修复称为医学能力提升。直接删8层的小模块恢复失败，输出端适配器没有成为本轮有效方案。

[47 全部尝试](results/47_structure_search/RESULTS.md) · [48 训练](results/48_adapter_training/RESULTS.md) · [49 400例确认](results/49_structure_confirmation/RESULTS.md) · [50 全部轨迹](results/50_structure_trajectories/RESULTS.md)

[评分审计](research_v6_adapters/SCORING_AUDIT.md) · [数据审计](research_v6_adapters/SOURCE_AUDIT.md) · [来源答案范围](research_v6_adapters/ANSWER_SCOPE.md) · [复现与原型](research_v6_adapters/REPRODUCE.md) · [运行核验](research_v6_adapters/FINAL_VALIDATION.json) · [原型重放](research_v6_adapters/DEMO_VALIDATION.json)

---

# 历史研究：v0.9 医学判断的关键计算与结构替换

[先读：本轮发现了什么](research_v5_structural/START_HERE.md) · [一个病例的逐轮逐层中文解释](research_v5_structural/ONE_CASE_EXPLAINED.md) · [完整结果](research_v5_structural/RESULTS_AND_STORY.md) · [整合论文](acl_paper/v09_structure/PAPER_ZH.md)

2026-11-20。本轮结构实验全部完成：三个来源严格520例，45例定位/开发、345例首批结构验证、130例复核；47例展开全部证据轮次和28层。原模型为Qwen3-1.7B，本地Apple GPU运行，API费用0美元。

小MLP替换使整模型参数减少4.38%，补回直接删除丢失的部分诊断功能；固定8头干预的代码改善在两批复现，但正确历史利用受损，完整候选生成也未改善。约19%—24%的小模块轨迹最终判断相同、中途仍改变。总体正确率、个体选择、更新过程及作答接口分别报告。

[全部47例图谱](results/45_structural_synthesis/CASE_ATLAS.md) · [测量与结构](research_v5_structural/MEASUREMENT.md) · [相关工作](research_v5_structural/RELATED_WORK.md) · [复现](research_v5_structural/REPRODUCE.md) · [运行核验](research_v5_structural/FINAL_VALIDATION.json) · [交付核验](research_v5_structural/DOCUMENT_VALIDATION.json)

分阶段结果：[42 定位](results/42_structural_localization/RESULTS.md) · [43 开发](results/43_structural_development/RESULTS.md) · [44 345例验证](results/44_structural_holdout/RESULTS.md) · [45 更新过程](results/45_structural_synthesis/RESULTS.md) · [46 130例头对照](results/46_structural_head_followup/RESULTS.md)。

---

# 历史研究：v0.8 多来源实验与内部通路

[先读这一页](research_v4/START_HERE.md) · [完整结果与论文主线](research_v4/RESULTS_AND_STORY.md) · [中文论文](acl_paper/v08_multisource/PAPER_ZH.md) · [全部94例图谱](results/34_multisource_depth/CASE_ATLAS.md)

2026-11-20。本轮新增MedQA 300例、MedMCQA 200例、MMLU 40例；严格文本敏感性520例。540例配对记录最后证据组前后，94例展开全部轮次与28层，并用4B配置复核。全部运行与最终核验完成，API费用0美元。

主要结果：中性历史302/540答对，错误历史232/540，仅提及242/540；新证据仍推动诊断，历史影响在两个配置上主要经直接通向诊断作答段的连接传播。末层大读表跳变经干预与尺度分解核查，未被当作已经找到疾病判断开关。

[数据卡](research_v4/DATA_CARD.md) · [论据出处](research_v4/EVIDENCE_LEDGER.md) · [复现](research_v4/REPRODUCE.md) · [最终核验](research_v4/FINAL_VALIDATION.json) · [结果与代码ZIP](deliverables/medical_beliefs_v08_results.zip)

以下保留更早研究记录；v0.8为本轮结构研究的既有证据。

---

# 历史研究主线（v0.7重构）

[先读：论文到底要解释什么](acl_paper/v07_reframing/START_HERE.md) · [实验设计](acl_paper/v07_reframing/EXPERIMENT_DESIGN.md) · [证据与相关工作审计](acl_paper/v07_reframing/EVIDENCE_AUDIT.md)

当前判断：已有结果说明内部疾病读出、证据更新与最终答案可能不同步，但尚未区分知识不足、先前诊断改变证据处理、输出环节受影响这三种解释。v0.7以并列解释和逐层验证重新组织研究；保留全部旧记录。新增24例历史配对重分析，没有新增模型推理，API费用0美元。v0.6的篇幅与实验完成情况不等于中心机制已经得到完整证明。

# 历史论文与实验结果（v0.6）

[先读这一页：用人话解释](research_v3/START_HERE.md) · [完整中文论文](acl_paper/v06_building/PAPER_ZH.md) · [英文论文PDF](acl_paper/v06_building/main.pdf) · [分阶段完整结果](research_v3/RESULTS_AND_STORY.md)

本轮新增327个患者/题目，159条完整证据轨迹、1173次证据更新；含4B配对复核、历史与证据背景、自然内部更新干预及独立48例复核。4832个观测/干预条件全部完成核验。API费用0美元。旧v0.5及此前结果保留在下方。

# 历史论文交付（v0.5）

[完整中文论文](acl_paper/10_FULL_PAPER_ZH.md) · [英文ACL论文与附录](acl_paper/submission/main.pdf) · [论证架构](acl_paper/11_ARGUMENT_ARCHITECTURE.md) · [全病例分析](results/22_paper_case_synthesis/RESULTS.md)

# 医学信念的逐轮与逐层变化

**先读：[当前综合报告](results/21_current_synthesis/RESULTS.md)**。完整论证见[中文论文稿](acl_paper/07_MANUSCRIPT.md)。

当前结论：疾病信息能够被读出，也能影响输出；但推动分数不等于改变诊断。新120例、24病种、1.7B与4B配置的结果按阶段保存。简单分类器高分分支另行保留。

2026-11-19追加：[DDxPlus分类器扩大验证](results/22_ddx_classifier_expansion/RESULTS.md)。已扩至全部49类、134,529例官方测试病例：问题文字Ridge 98.23%，证据出现位置逻辑回归99.18%，保留答案值逻辑回归99.67%；包含重复审计、学习曲线、相同问题不同疾病的成对反例。此分支不改变前述模型内部机制结论。

同日深入审计：[生成规则、短证据证明与同问题条件挑战](results/23_ddx_generator_audit/RESULTS.md)。无需患者训练的官方目录排除，在 test / validation 分别唯一覆盖 92.47% / 92.42%，覆盖部分全部命中；同问题条件挑战中，validation 问题身份逻辑回归 48.98%，加入回答值 75.58%。该分支不将分类器高分宣称为首次发现，并量化生成标签与参考鉴别诊断的目标差异；此前的疾病读出结果不能单独解释为一般医学推理能力。

2026-11-20：[轻量模型五数据集扩展](results/24_lightweight_multidataset/RESULTS.md)。新增 DXY、MZ-4、MZ-10、MedQA 和 MedMCQA 单选子集；全资料准确率分别为 81.73%、74.49%、67.45%、36.14%、42.58%。DXY 弃答模型覆盖 60/104、答对 58，已导出 7.28 KB 标准库可运行参数。[后续复核与公开 GPT-6 调研](results/24_lightweight_multidataset/GPT6_PUBLIC_BENCHMARKS.md)：关掉同模型筛选后 DXY/MZ-4/MZ-10 为 79.81%/74.20%/64.49%；已校验作者公开 MedQA 逐题输出与本地完全相同的测试文件，重算 GPT-6.1 Sol Low 为 96.86%，本轮未调用 GPT API。知识库零患者训练、普通分类器与置信度弃答均已有先例，保留为基线，不再当作创新方向。

| 阶段 | 研究问题 | 结果 |
|---|---|---|
| 01 探索 | 新证据是否使不同层朝不同疾病移动？ | [RESULTS](results/01_pilot/RESULTS.md) |
| 02 独立复现 | 在新增病例中有多常见？跨答案映射是否稳定？ | [RESULTS](results/02_replication/RESULTS.md) |
| 03 证据顺序 | 同一证据集合，不同排列是否改变疾病判断？ | [RESULTS](results/03_evidence_order/RESULTS.md) |
| 04 内部机制 | 读出是否可靠？不同层的attention或MLP是否促成转向？ | [RESULTS](results/04_internal_mechanism/RESULTS.md) |
| 05 综合 | 多阶段证据支持什么总体结论？ | [RESULTS](results/05_synthesis/RESULTS.md) |
| 06 完整候选 | 49疾病空间中的总体更新与测量可靠性 | [RESULTS](results/06_full_candidate_trajectories/RESULTS.md) |
| 07 层与注意力 | 每层、每头怎样处理证据 | [RESULTS](results/07_attention_and_layers/RESULTS.md) |
| 08 干预确认 | 旧MLP方向模式是否在新病例复现 | [RESULTS](results/08_causal_confirmation/RESULTS.md) |
| 09 疾病全名 | 完整病名的逐轮支持与顺序效应 | [RESULTS](results/09_disease_name_trajectories/RESULTS.md) |
| 10 病名干预 | 旧计算在新上下文中如何影响诊断 | [RESULTS](results/10_name_causal_mechanism/RESULTS.md) |
| 11 疾病信息 | 未见病例的真实疾病读出与文本审计 | [RESULTS](results/11_disease_information/RESULTS.md) |
| 12 综合 | 当前结论、具体病例与论文主线 | [RESULTS](results/12_current_synthesis/RESULTS.md) |
| 13 输出路径 | 最后层锚点为何只能影响首词元 | [RESULTS](results/13_token_path/RESULTS.md) |
| 14 新病例与问卷 | 新120例；信息可读性与原生诊断表现 | [RESULTS](results/14_fixed_panel/RESULTS.md) |
| 15 疾病方向 | 672干预、随机/反向/零对照及诊断边界 | [RESULTS](results/15_disease_directions/RESULTS.md) |
| 16 自然更新 | 输出切换、连续关联、模块与逐头注意力 | [RESULTS](results/16_update_mechanism/RESULTS.md) |
| 17 答案肯否 | 同问题Yes/No/Unknown如何影响状态 | [RESULTS](results/17_answer_polarity/RESULTS.md) |
| 18 4B配置 | 同患者逐轮、逐层复核与固定问卷终点 | [RESULTS](results/18_model_replication/RESULTS.md) |
| 19 呈现分解 | 同长度已知资料位置、删Unknown、实际24候选 | [RESULTS](results/19_presentation_mechanism/RESULTS.md) |
| 20 背景偏向 | 空输入、候选顺序及空输入评分对照 | [RESULTS](results/20_template_prior/RESULTS.md) |
| 21 当前综合 | 完成结果、统一论文主线、全部交付入口 | [RESULTS](results/21_current_synthesis/RESULTS.md) |
| 22 分类器扩大 | 全部49类、全量测试；问题身份、答案值与相似度分类 | [RESULTS](results/22_ddx_classifier_expansion/RESULTS.md) |
| 23 生成规则审计 | 零患者训练、目录证明、同问题原始病例挑战与评测目标 | [RESULTS](results/23_ddx_generator_audit/RESULTS.md) |

results 仅保存论文式方法、结果、表格、图及必要边界。执行协议在 protocol，原始模型记录在 runs；数据和代码分别在 data、src。

本研究使用模拟病例的证据逐组揭示，模型参数冻结。研究对象是模型的疾病支持如何更新，不将模型分数解释为患者患病的真实概率。

[下一版研究决策](acl_paper/04_NEXT_DECISIONS.md) · [本轮复现](protocol/BELIEF_V2_REPRODUCE.md) · [阶段06—11复现](protocol/FULL49_REPRODUCE.md) · [阶段01—05复现](protocol/REPRODUCE.md)

[医学信念统一设计：逐轮判断、病例汇总、真值与内部机制](protocol/MEDICAL_BELIEF_MASTER_DESIGN.md) · [最终标签与参考鉴别诊断审计](protocol/ground_truth_audit.json)

[ACL 论文工作区：主线、全文结构、证据与迭代记录](acl_paper/README.md)


当前图谱：[同24例两种输入](results/14_fixed_panel/CASE_ATLAS.md) · [同24例两模型](results/18_model_replication/CASE_ATLAS.md) · [逐层逐头注意力](results/16_update_mechanism/ATTENTION_ATLAS.md)。所有图同时保存PNG和PDF，全部疾病分数和状态保留在runs。模型参数冻结；API费用0美元。

[本轮文件与数值验证](protocol/BELIEF_V2_DELIVERY_VERIFICATION.json)。当前执行使用MLX Apple GPU；迁移至CUDA需要等价实现与数值复核，见复现说明。
