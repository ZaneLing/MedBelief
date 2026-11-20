# 当前论文：v0.10 医学信念与计算取舍

[整合中文论文](v10_adapters/PAPER_ZH.md) · [三层论证架构](v10_adapters/ARGUMENT_STRUCTURE.md) · [用人话读结果](../research_v6_adapters/START_HERE.md) · [病例解释](../research_v6_adapters/ONE_CASE_EXPLAINED.md)

从同一事实下的判断变化，深入历史利用的内部路径，再以真实结构裁剪和小适配器检验计算能否替代。新增880例、22配置开发、400例独立确认及匹配输出对照；24例逐轮逐层轨迹。保留局部压缩的成本收益、适配器和大幅删层的失败，以及严格字符串评分夸大收益的发现。没有将方法本身或格式修复作为新医学机制。

当前为随实验更新的中文研究稿；早期英语排版文件不自动包含本轮结果。[完整新增实验](../research_v6_adapters/RESULTS_AND_STORY.md) · [全部阶段](v10_adapters/README.md)。

---

# 历史论文：v0.9 医学信念与结构取舍

[整合中文论文](v09_structure/PAPER_ZH.md) · [由表及里的论证架构](v09_structure/ARGUMENT_STRUCTURE.md) · [全部阶段索引](v09_structure/README.md) · [用人话解释结果](../research_v5_structural/START_HERE.md)

沿着证据更新、历史利用、内部定位与结构替换展开。新增Qwen3-1.7B的28层、448头定位；45例开发，345例结构验证与另外130例复核。小模块、同层头对照、正确历史对照、完整名称生成及47例全部轮次共同检验机制解释。模型结构与实际生成之间的成功、失败和差异均保留。

[新增测量方法](../research_v5_structural/MEASUREMENT.md) · [直接相关工作](../research_v5_structural/RELATED_WORK.md) · [总体实验报告](../research_v5_structural/RESULTS_AND_STORY.md)。旧版实验、论文与原始数据保留在下方；v0.9为历史中文研究稿。

---

# 历史论文：v0.8 多来源与通路机制

[中文论文正文](v08_multisource/PAPER_ZH.md) · [由表及里的论证架构](v08_multisource/ARGUMENT_STRUCTURE.md) · [方法](v08_multisource/METHODS.md) · [相关工作](v08_multisource/RELATED_WORK.md)

本轮以三个来源540例、94例完整内部轨迹及两个模型配置的路径干预，进一步区分新证据响应、旧病名影响和输出读表放大。实际结果、失败检验、严格文本子集及全部病例图谱见[综合报告](../research_v4/RESULTS_AND_STORY.md)。这是随实验更新的中文论文稿，早期版本保留在下方。

---

# 历史论文主线：v0.7研究重构

[主线与分层架构](v07_reframing/START_HERE.md) · [下一轮区分实验](v07_reframing/EXPERIMENT_DESIGN.md) · [证据审计](v07_reframing/EVIDENCE_AUDIT.md)

当前中心问题：同样的当前医学事实，为什么会因为先前诊断不同而产生不同结论——变化发生在证据处理还是答案输出？已有实验尚未完成机制区分。下面的v0.6与v0.5保留为历史稿，不能以“完整正文”推断机制已得到完整证明。

[v0.6中文稿](v06_building/PAPER_ZH.md) · [v0.6英文PDF](v06_building/main.pdf)

# 历史ACL论文 v0.5：完整正文与病例附录

[可编译ACL源码包](ACL_medical_beliefs_v05.zip)（含PDF、图表、数据表、BibTeX）

优先阅读：[中文完整稿](10_FULL_PAPER_ZH.md) · [文章论证架构](11_ARGUMENT_ARCHITECTURE.md) · [英文ACL完整PDF](submission/main.pdf) · [全部24例的新汇总](../results/22_paper_case_synthesis/RESULTS.md)。

本版新增全病例六类轨迹、120例读出—输出四格统计、10个对照例子及24例完整证据表；没有新增患者。旧07稿保留为v0.4历史论述，最新完整论述以10稿和submission为准。

---

# ACL论文工作区：模型有医学信念吗？

v0.4 · 2026-11-19。

**当前主线：医学信息可以进入内部并推动输出，但这种作用未必足以决定最终诊断；输入呈现和生成位置影响了两者之间的联系。**

研究定位是医学证据更新及内部作用分析。简单分类器高分分支单独保留，不将本文改成分类器新方法或bench排行榜。

## 阅读入口

| 文件 | 内容 |
|---|---|
| [完整中文论文稿](07_MANUSCRIPT.md) | 从中耳炎实例进入，逐步给出总体结果、内部分析、干预和成立条件 |
| [当前综合报告](../results/21_current_synthesis/RESULTS.md) | 以直接语言解释实验怎样做、看到了什么，附主要图表 |
| [01_STORY.md](01_STORY.md) | 文章中心论点及证据如何逐层展开 |
| [02_PAPER_OUTLINE.md](02_PAPER_OUTLINE.md) | 章节、主图与附录安排 |
| [03_EVIDENCE_LEDGER.md](03_EVIDENCE_LEDGER.md) | 每个结果的分母、解释范围和原始来源 |
| [04_NEXT_DECISIONS.md](04_NEXT_DECISIONS.md) | 下一版自然中介、来源泛化与模型设置的研究决策 |
| [05_REVISION_LOG.md](05_REVISION_LOG.md) | 旧解释如何被新结果修改；失败假设保留 |
| [06_INTRODUCTION_RELATED_WORK.md](06_INTRODUCTION_RELATED_WORK.md) | 46项相关工作记录及原始定位引言 |
| [08_MECHANISM_RELATED_WORK_ADDENDUM.md](08_MECHANISM_RELATED_WORK_ADDENDUM.md) | 本轮机制解释与直接先例的补充比较 |
| [09_MEASUREMENT_APPENDIX.md](09_MEASUREMENT_APPENDIX.md) | 评分、读出、干预、层与头、统计及数据口径 |

## 当前实验规模

旧120例训练读出，新120例测试；24疾病、6疾病组。预定24例完整轨迹覆盖17疾病、184次更新。1.7B完成28层观测、672个方向干预及48个零干预；4B 8-bit完成36层与同病例复核，未运行方向干预。全部实验为本地运行，API费用0美元。

## 图与原始证据

- [同24例的两种输入轨迹](../results/14_fixed_panel/CASE_ATLAS.md)
- [同24例的两模型轨迹](../results/18_model_replication/CASE_ATLAS.md)
- [120例全部层、全部头的组注意力](../results/16_update_mechanism/ATTENTION_ATLAS.md)
- [方向有效但没有新增正确诊断的分差分析](../results/15_disease_directions/DECISION_GAPS.md)
- [复现与验证](../protocol/BELIEF_V2_REPRODUCE.md)

所有图提供PNG和PDF。本文为具有完整实验与论证结构的中文研究稿，尚未转换为特定ACL赛道的最终英语投稿格式。具体结论限定于现有病例来源、模型配置和直接作答方式；相关工作不以工具组合宣称独占创新。
