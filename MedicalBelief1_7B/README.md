# 1.7B 医学信念逐层轨迹

目标：同一个病例，每来一组证据，观察模型的最终疾病选择以及每一层的疾病支持如何变化。

首轮使用已有的 12 例 DDxPlus 模拟病例、131 个累计证据时间点。疾病标签仅在分析端使用。模型为 Qwen3-1.7B，28 层；本机 Apple M2 Pro GPU、MLX、FP16 推理，不调用收费 API。

本目录复制并冻结了本轮输入数据，原项目保持原样。原始设计见 [测量合同](protocol/MEASUREMENT_DESIGN.original.md)。本阶段的调整与预先规定见 [执行协议](protocol/PHASE1.md)。

运行命令（在 Seq 目录执行）：

```bash
MedicalBeliefMechanisms/.runtime_mlx/bin/python MedicalBelief1_7B/src/run_direct.py --run-id phase1_direct_v2
MedicalBeliefMechanisms/.runtime/bin/python MedicalBelief1_7B/src/analyze.py --run-id phase1_direct_v2
```

可通过 `--model-dir` 指定权重目录。数据已复制到本目录，运行时不再依赖旧病例准备代码。当前运行器依赖 MLX；Linux/NVIDIA 服务器需实现 PyTorch 捕捉适配，不能把这条 Mac 命令直接当作 CUDA 实验。

第一阶段完成后阅读 [中文结果报告](reports/PHASE1_RESULTS.md)。R/P 思考分支、独立病例校准读出、顺序对照和因果替换属于后续阶段，不会被记为本轮完成。
