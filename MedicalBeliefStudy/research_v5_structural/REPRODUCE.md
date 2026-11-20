# 复现本轮结构与医学判断实验

在项目Seq目录执行。数据沿用`MedicalBeliefStudy/data/belief_v4`；模型在`MedicalBeliefMechanisms/.models/Qwen3-1.7B`。运行使用Apple M2 Pro、MLX、FP16主模型；低秩小模块计算为FP32，输出转回主模型精度。API费用0美元。

```bash
MedicalBeliefMechanisms/.runtime_mlx/bin/python MedicalBeliefStudy/src/phase70_structural_screen.py
MedicalBeliefMechanisms/.runtime_mlx/bin/python MedicalBeliefStudy/src/phase79_structural_queue.py
MedicalBeliefMechanisms/.runtime_mlx/bin/python MedicalBeliefStudy/src/phase80_structural_trajectories.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase77_structural_holdout_analyze.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase81_structural_trajectory_analyze.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase82_structural_validate.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase83_structural_dynamics.py
MedicalBeliefMechanisms/.runtime_mlx/bin/python MedicalBeliefStudy/src/phase86_structural_head_followup.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase87_structural_head_analyze.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase89_structural_followup_details.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase84_structural_report.py
```

队列脚本依次执行定位分析、拟合样本整理、线性拟合、27例组合开发、冻结配置、345例留出、60例病名生成和计时。不要并行启动多个GPU实验，以免干扰计时并占用显存。现有记录逐文件断点续跑；清空输出或更改配置前先复制研究目录，避免覆盖既有冻结结果。

`selected.json`保存最终配置；`linear/rank_16.npz`、`rank_64.npz`保存小模块参数；`structural_v1_variants.py`中的`materialize`将配置装入新加载的原模型。部署模型仍需其余原权重；7万参数的小模块不能单独诊断。

复跑单个既有病例可调用`structural_predict.py --case-id 病例标识 --configuration linear_mlp_2_r16 --round 3 --condition wrong`，使用GPU环境解释器；可用配置见`selected.json`。该工具返回四个原候选的支持、实际首选、最终来源答案与真实参数数。

| 路径 | 内容 |
|---|---|
| `runs/structural_v1/screen` | 18例单组件干预，均匀词元训练向量，数值对照 |
| `runs/structural_v1/linear` | 训练/开发锚点、低秩参数与拟合误差 |
| `runs/structural_v1/tune` | 27例×16种结构 |
| `runs/structural_v1/selected.json` | 留出前冻结的9个配置 |
| `runs/structural_v1/test` | 345例、两历史、两代码映射 |
| `runs/structural_v1/generation` | 60例实际完整候选文本生成 |
| `runs/structural_v1/timing` | 同步计时、交错顺序与实际参数数 |
| `runs/structural_v1/trajectories` | 47例每轮、每层、4个结构，完整模型逐头注意力 |
| `runs/structural_v1/followup` | 130例同层头对照、正确历史对照、首步及持续生成 |
| `results/42_structural_localization` 至 `46_structural_head_followup` | 分阶段表、PNG/PDF图、病例图谱与结论 |

CPU分析环境与GPU推理环境不同。必须直接调用各自venv里的解释器；不要将解释器符号链接展开成系统Python。服务器CUDA迁移需用等价PyTorch实现Qwen3的Q/K归一化、RoPE、GQA、残差及最终归一化；先复核完整模型和自身干预，再对比改结构结果。当前代码不会自动转成CUDA。

每个阶段写入源码、配置、病例等散列；最终核验检查数量、概率有效性、开发/留出分离、生成解析、轨迹终点重复误差及原模型文件不变。`FINAL_VALIDATION.json`是已完成检查的机器可读入口。

130例追加复核的冻结集合在`runs/structural_v1/followup/spec.json`，方案与发生顺序见[FOLLOWUP_HEAD_CONTROLS](FOLLOWUP_HEAD_CONTROLS.md)。复现报告脚本会等待phase87成功写入的完成标记。按上述顺序运行即可；最后可运行phase88_structural_delivery_check.py核对文档链接与原权重未变。
