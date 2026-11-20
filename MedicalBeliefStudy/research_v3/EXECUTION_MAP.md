# 本轮实验的执行图

本轮核心对象：同一患者的证据逐条进入后，模型内部疾病信息与最终诊断的关系。使用本地M2 Pro GPU；Qwen3-1.7B为主要对象，已有Qwen3-4B 8-bit为配对复核。没有调用付费模型API，费用0美元。

## 队列与实际规模

下表为冻结输入对应的有限任务数。完成状态由各目录completion.json及最终validation.json确认，不以本表代替完成记录。

| 模块 | 新患者/题目 | 模型观测或干预条件 | 输出位置 |
|---|---:|---:|---|
| DDxPlus新患者、全轨迹、顺序/重复/历史对照 | 240；其中72例全轨迹 | 1359 | runs/belief_v3 |
| 自然更新分量干预，首批 | 24（上述患者子集） | 288 | runs/belief_v3/natural_interventions |
| 外部MedQA诊断题，逐句、顺序、错误历史 | 87；84种来源答案 | 954 | runs/belief_v3_medqa |
| 4B配置复核 | 相同240；其中24例全轨迹 | 424 | runs/belief_v3_4b |
| 完整病例逐一删证据组 | 相同24 | 208 | runs/belief_v3/evidence_context |
| 完整事实下正确历史的配对补充 | 相同24 | 24 | runs/belief_v3/history_matched |
| 自然更新分量独立患者复核 | 另外48（上述72例子集） | 576 | runs/belief_v3/natural_interventions_replication |
| 外部MedQA自然状态作用 | 上述全部87题 | 783 | runs/belief_v3_medqa/natural_interventions |
| 事实角色绑定，结果驱动的解释检验 | 上述72例 | 216 | runs/belief_v3/role_binding |
| 合计 | **327个新患者/题目，不重复计算模型与条件** | **4832** | 各阶段独立保存 |

DDxPlus完整轨迹72例，共567次新增证据；MedQA 87题，共606次新增原文片段。主要1.7B轨迹共159条、1173次证据更新。4B另外测量同24例的184次更新，属于配置复核，不算新患者。

## 数据覆盖

DDxPlus是模拟记录，24病×10例；研究分组为呼吸60例、神经40例、心血管40例、消化40例、耳鼻喉30例、全身性30例。各组名称是研究组织方式。全部患者18–90岁、至少5个证据组。旧病例事实集合与新病例无完全相同记录；读出器仍使用旧120例训练头。

DDxPlus的“反序”保持初始问题组，反转其后证据；MedQA“反序”反转全部事实片段。两者均只在完整信息终点评价顺序对照。自然轨迹使用固定原始片段，不把问诊顺序当成真实疾病发生时间。

MedQA从1273道四选项测试题中按直接诊断、可分段、无外部图片依赖等规则得到87题。规则修复发生于该模块推理前，两个弃用清单及原因均保留；最终版本通过原文逐字内容重建（忽略空白差异），没有重新生成病例内容。含列表的原文片段整体保留，故一轮不一定等于一条独立临床事实。

## 每轮存什么

- 完整候选病名的log条件概率、候选内相对支持、每个词元的log概率、规范病名总概率质量；自然观测另存模型贪心续写。
- 所有层的入层状态、注意力增量、注意力后状态、前馈增量、离层状态，均在固定诊断锚点采集。
- 所有层、所有查询头从锚点指向证据/候选/格式等组的注意力。深度自然轨迹另存逐token注意力、头输出和证据组末尾状态。
- 输入token、提示哈希、状态文件哈希、候选续写token及数值校验。推理中不训练或更改模型参数。

## 统计与证据位置

患者是抽样及区间单位。逐轮先患者内汇总，避免长病例获得更多权重。所有28层/36层均报告，主读出固定在旧患者训练的alpha=0.1，不在新队列上重新挑最佳层。三层自然干预分别做目标与等范数随机对照，首批24与复核48分开做20000次符号置换、三层Holm校正。

主因果试验协议为[NATURAL_UPDATE_PROTOCOL.md](NATURAL_UPDATE_PROTOCOL.md)，独立复核为[NATURAL_REPLICATION_PROTOCOL.md](NATURAL_REPLICATION_PROTOCOL.md)。历史补充和证据上下文分析分别见[HISTORY_MATCHED_PROTOCOL.md](HISTORY_MATCHED_PROTOCOL.md)、[EVIDENCE_CONTEXT_PROTOCOL.md](EVIDENCE_CONTEXT_PROTOCOL.md)。

## 复现顺序

在项目根目录使用现有.runtime_mlx/bin/python运行模型采集，.runtime/bin/python运行CPU分析。已完成观测按job_id跳过，manifest要求源码和输入保持一致；改变条件必须建新目录。

```text
phase23_prepare.py
phase23_run.py
phase24_natural_intervene.py
phase25_external_prepare.py  # 需要已校验的公开原始test.jsonl
phase25_external_run.py
phase23_run.py --model 4b
phase26_evidence_context.py
phase27_history_matched.py
phase24_natural_intervene.py --replication
phase28_external_natural.py
phase29_roles.py

phase23_analyze.py
phase24_analyze.py
phase25_analyze.py
phase23_analyze.py --model 4b
phase26_analyze.py
phase24_analyze.py --replication
phase28_external_analyze.py
phase29_roles_analyze.py
phase30_measurement_audit.py
phase31_export_scores.py
phase32_auxiliary.py
verify_belief_v3.py
phase33_paper.py
phase34_manuscript.py
# 在acl_paper/v06_building中使用项目.tools/tectonic编译main.tex
# 完成PDF视觉检查并写入qa/visual_review.json后：
phase35_release.py
```

本地模型路径和MLX适配位于phase6_measure.py。它们是本机Metal GPU脚本；迁移CUDA服务器时应保留数据、评分和干预定义，另做后端适配，不能把本机命令说成CUDA命令。
