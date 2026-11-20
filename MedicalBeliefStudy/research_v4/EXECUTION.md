# 本轮实验执行与交付记录

2026-11-20。模型实验、统计分析和最终数据核验已完成。API费用0美元；模型权重哈希保持一致。

| 阶段 | 完成规模 | 结果 |
|---|---|---|
| 多来源主观测 | 540例、6823个输入条件 | results/32_multisource_belief |
| 自然状态替换 | 94例、2444个条件 | results/33_multisource_causality |
| 4B复核及完整逐层图谱 | 4B的1034个条件；1.7B追加1960个逐层条件；94例全部图谱 | results/34_multisource_depth |
| 未采纳病名干预 | 48例、960个条件，另48次受体捕捉 | results/35_unendorsed_name |
| 通路阻断 | 两个模型各1152条件 | results/36_history_routes |
| 输出、顺序与轨迹复核 | 复用540例主观测 | results/37_behavior_checks |
| 事后原文审计 | 严格520例；内部92例、确认内部47例 | results/38_text_quality |
| 模块读表 | 376个既有终点状态 | results/39_module_readout |
| 末层MLP干预与尺度分解 | 940个条件；复用既有状态 | results/40_final_mlp |
| 同格式病名轮换 | 两个模型各480条件 | results/41_name_counterbalance |

共有15525个主输入/状态替换条件，另940个末层替换和960个病名轮换；这些不是独立患者数量。FP32辅助均值额外重算1080个终点，自身/参考状态误差均为0。原均值保留但弃用。

第一版4B通路实现因输出头向量/矩阵数值核验失败，未进入正式病例；使用原生整段输出头重跑。两种模型的通路前向各18次原生检查通过，病名轮换的相同输入重复分数误差为0。详见[测量说明](MEASUREMENT_NOTES.md)。

主观测、冻结病例和原始推理代码不覆盖。运行日志、旧拒绝manifest和全部质量标记保留。phase68仅修正病例表格的展示：两映射不一致时不命名疾病，并增加错误历史和代码全词表概率总量；没有新增模型调用或改变分数。

[先读结果](START_HERE.md) · [全部论据](EVIDENCE_LEDGER.md) · [最终核验](FINAL_VALIDATION.json) · [复现顺序](REPRODUCE.md)。
