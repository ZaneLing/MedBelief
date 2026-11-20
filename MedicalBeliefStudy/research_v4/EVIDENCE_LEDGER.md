# 本轮论据及其原始出处

统计单位始终是病例。两种代码映射、多个前缀、网络层和干预条件不重复计成独立病例。表中“确认”指运行前划分的病例队列；后追加的分析仍标明为探索性。

| 论文要回答的问题 | 样本与比较 | 结果文件 | 可据此下的判断 |
|---|---|---|---|
| 旧诊断是否影响相同患者事实的判断 | 新增540例；中性/错误/仅提及历史，完整候选字符串评分 | [总体](../results/32_multisource_belief/RESULTS.md)、[逐病例表](../results/32_multisource_belief/patient_results.csv) | 中性302例答对，错误历史232例，仅提及242例；来源分开报告 |
| 是否只是候选评分方式造成的 | 同540例，实际贪心生成与按词元数标准化评分 | [输出检查](../results/37_behavior_checks/RESULTS.md) | 实际生成297→229，现象跨测量方式存在 |
| 新证据是否还在起作用 | 同540例，加入最后原文组前后、历史之间配对 | [新增证据](../results/32_multisource_belief/RESULTS.md) | 更新仍有关联，126例出现方向相反；不能把平均交互接近0当作没有个体交互 |
| 是否逐渐接近来源答案 | 预定94例、537个累计前缀，全部轨迹 | [轨迹统计](../results/37_behavior_checks/RESULTS.md)、[全部图谱](../results/34_multisource_depth/CASE_ATLAS.md) | 存在不换首选、选中后离开、反复变化等多种轨迹；中间轮没有额外真值 |
| 同样的事实换顺序是否稳定 | 同540例，无历史、原序/倒序 | [顺序结果](../results/37_behavior_checks/RESULTS.md) | 总命中数315不变，但93例换诊断 |
| 内部哪个位置能改变诊断倾向 | 94例、2444个自然状态替换；确认48例独立报告 | [位置干预](../results/33_multisource_causality/RESULTS.md) | 第21层诊断位置相对同范数随机方向能改变分差；命中率改善未得到可靠支持 |
| 未采纳病名是否也进入内部 | 原确认48例、960个干预 | [提及干预](../results/35_unendorsed_name/RESULTS.md) | 诊断位置的自然状态替换也能改变分差 |
| 历史影响经过哪条路 | 原确认48例，两个配置、三历史、两映射、四种通路，共2304条件 | [路径实验](../results/36_history_routes/RESULTS.md)、[严格47例](../results/38_text_quality/RESULTS.md) | 同时报告历史效应的衰减与中性历史正常作答，结论见[通路归纳](ROUTE_FINDING.md) |
| 图中大变化是否代表关键开关 | 376个既有终点状态读表、940个末层MLP替换 | [模块](../results/39_module_readout/RESULTS.md)、[替换](../results/40_final_mlp/RESULTS.md)、[尺度分解](../results/40_final_mlp/NORMALIZATION.md) | 末层投影明显放大，但自然MLP替换没有可靠胜过随机干预；大部分读表变化来自尺度项 |
| 是否具体提到哪个病就偏向哪个病 | 原确认48例，同格式四候选轮换加空病名，两个配置共960条件；追加控制 | [轮换结果](../results/41_name_counterbalance/RESULTS.md) | 严格47例中，被提及候选获得42.6%/35.9%支持，高于无选择性效应的25%基准 |
| 是否依赖一个模型配置 | 同94例，1.7B FP16与4B 8-bit | [配置复核](../results/34_multisource_depth/RESULTS.md) | 4B总体更准，历史效应仍在；不能把大小与精度的影响分开 |
| 是否依赖文本筛选错误 | 原文审计严格520例、内部92例、确认内部47例 | [严格复核](../results/38_text_quality/RESULTS.md)、[审计](../data/belief_v4/text_audit_review.json) | 主结果与严格子集并列，原记录保留，按文本而非模型表现标记 |

全部评分、映射、代码总概率和完整病名评分分别保存。逐层图使用原模型输出头投影，灰色表示两种映射不能一致指向疾病；不把早层未校准投影直接命名为真实诊断。注意力记录为诊断位置到五类词元的逐层逐头权重，不是所有位置的完整注意力矩阵。

数据哈希、原生前向核验、随机/自身对照、FP32辅助均值重算、模型权重一致性见[最终核验](FINAL_VALIDATION.json)与[测量说明](MEASUREMENT_NOTES.md)。
