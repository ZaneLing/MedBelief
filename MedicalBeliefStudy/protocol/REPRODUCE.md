# 复现

当前后端：Apple MLX，Qwen3-1.7B原始权重转FP16；GPU为Apple M2 Pro。模型、包版本与文件哈希见 ../runs/expanded_v1/manifest.json。

在Seq目录运行：

```bash
MedicalBeliefMechanisms/.runtime_mlx/bin/python MedicalBeliefStudy/src/run_observations.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/readouts.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/affine_readout.py
MedicalBeliefMechanisms/.runtime_mlx/bin/python MedicalBeliefStudy/src/intervene_and_names.py
MedicalBeliefMechanisms/.runtime_mlx/bin/python MedicalBeliefStudy/src/content_and_depth.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/analyze_stages.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/summarize_mechanisms.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/summarize_controls.py
```

已有模型观察及干预支持续跑，不重新覆盖完成点；生成来源配置变化应使用新run ID。分析和图表可从冻结原始数据重建。summarize_mechanisms先生成基础报告，summarize_controls再加入内容与深度部分；重建时按此顺序执行。

data中的公开输入和私有评估标签已经复制，可直接携带本目录迁移。仅重新选病例时依赖相邻ClinicalBelief原始数据。Linux/NVIDIA服务器需要PyTorch后端，不能直接执行MLX推理；沿用本目录输入和指标，重新核验正常前向、采集前向和干预前向一致性，另开run ID。Mac虚拟环境不作为Linux环境迁移。
