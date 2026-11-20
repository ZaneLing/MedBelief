# 模型有医学信念吗？v0.9

本版沿着“证据进来后，模型怎样形成、维持和改变诊断”展开，在既有证据更新与历史影响实验之后，加入实际结构替换。

[先读结果解释](../../research_v5_structural/START_HERE.md) · [整合论文稿](PAPER_ZH.md) · [论证架构](ARGUMENT_STRUCTURE.md) · [结构实验完整报告](../../research_v5_structural/RESULTS_AND_STORY.md)

[具体病例：内部从哪个病转向哪个病](../../research_v5_structural/ONE_CASE_EXPLAINED.md)。这页用中文逐轮、逐层解释一个例子，再链接全部病例和总体检验。

## 本版要回答的问题

1. 哪些层里的状态已经接近最终诊断？
2. 哪些部件对形成该诊断有实际作用？
3. 同一个部件何时帮助诊断，何时传播错误历史？
4. 缩小部件之后，总体正确率、每例判断和逐证据变化是否都保留？

这些问题依次需要观察、干预、方向对照和实际替换。与原模型一致和答对来源答案分别统计。结构实验使用Qwen3-1.7B；既有4B实验用于历史通路复核，没有测试本版压缩结构。

## 结果索引

| 阶段 | 病例与测量 | 结果 |
|---|---|---|
| 定位 | 18例；28层、448个查询头，组件删除；既有92例逐层投影 | [42：内部位置与实际作用](../../results/42_structural_localization/RESULTS.md) |
| 开发 | 另27例比较16种结构，冻结9种检验配置 | [43：结构与小模块](../../results/43_structural_development/RESULTS.md) |
| 首批验证 | 345例；9种结构；其中60例实际候选生成、6例配对计时 | [44：诊断保持与正确性](../../results/44_structural_holdout/RESULTS.md) |
| 完整过程 | 其中47例、289个前缀、4种结构、28层投影 | [45：逐证据过程](../../results/45_structural_synthesis/RESULTS.md) · [全部病例](../../results/45_structural_synthesis/CASE_ATLAS.md) |
| 第二批验证 | 另130例；同层头对照、正确历史对照及持续生成干预 | [46：头的具体作用](../../results/46_structural_head_followup/RESULTS.md) |

345例和130例相互独立，也均不参与18例定位、27例结构开发；总计520个独立题目。60例与47例是345例的子集，不能重复计为新增病例。

[测量细节](../../research_v5_structural/MEASUREMENT.md) · [直接相关工作](../../research_v5_structural/RELATED_WORK.md) · [复现](../../research_v5_structural/REPRODUCE.md) · [数据与运行核验](../../research_v5_structural/FINAL_VALIDATION.json)

保留[v0.8全文](../v08_multisource/PAPER_ZH.md)及其方法、数据卡和原始记录。本版新增结构证据，不重写旧实验的结果。
