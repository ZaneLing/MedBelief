# 阶段13—21复现

工作目录为项目根目录Seq。沿用已下载的Qwen3-1.7B与DDxPlus；当前推理实现使用MLX Apple GPU，分析环境为原项目Python环境。API费用0。

```bash
python3 MedicalBeliefStudy/src/phase14_prepare.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase13_token_path.py
MedicalBeliefMechanisms/.runtime_mlx/bin/python MedicalBeliefStudy/src/phase14_run.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase14_analyze.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase16_update_analyze.py
MedicalBeliefMechanisms/.runtime_mlx/bin/python MedicalBeliefStudy/src/phase19_presentation.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase19_analyze.py
MedicalBeliefMechanisms/.runtime_mlx/bin/python MedicalBeliefStudy/src/phase15_intervene.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase15_analyze.py
MedicalBeliefMechanisms/.runtime_mlx/bin/python MedicalBeliefStudy/src/phase17_polarity.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase17_analyze.py
MedicalBeliefMechanisms/.runtime_mlx/bin/python MedicalBeliefStudy/src/phase18_run.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase18_analyze.py
MedicalBeliefMechanisms/.runtime_mlx/bin/python MedicalBeliefStudy/src/phase20_prior.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase20_analyze.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase20_score_contrast.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase15_decision_analysis.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase16_attention_analysis.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase16_natural_alignment.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase18_update_alignment.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/render_readable_v2.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/render_model_atlas_v2.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/render_study_design.py
MedicalBeliefMechanisms/.runtime_mlx/bin/python MedicalBeliefStudy/src/verify_presentation_prompts.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/build_v2_delivery.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/verify_belief_v2.py
```

数据：`data/belief_v2`。原始观测与状态：`runs/belief_v2`与`runs/belief_v2_4b`。结果按问题分别位于`results/13_token_path`至`results/21_current_synthesis`。4B条件使用已有8-bit模型，模型文件路径和配置见[模型复核协议](MODEL_REPLICATION_V2.md)。

观测脚本跳过已有完成文件，比较源代码、协议及输入哈希，避免把不同实验版本混写。若改变输入或测量代码，应建立新run而非覆盖旧记录。分析脚本从冻结记录重建表格和图。正式完整运行时使用有限顺序脚本`phase_v2_continue.py`等待阶段14完成，再依次分析、干预和分析；任何子进程失败即停止后续步骤。

主协议：[MECHANISM_CONTINUATION_V2](MECHANISM_CONTINUATION_V2.md)。补充：[干预位置](CAUSAL_POSITION_IMPLEMENTATION.md)、[答案肯否](ANSWER_POLARITY_V2.md)。现有MLX实现不能直接在CUDA服务器运行；迁移需要等价PyTorch前向、缓存与干预实现并重新通过数值对照，不能仅更改device字符串。

其他冻结协议：[呈现追踪](PRESENTATION_FOLLOWUP_V2.md)、[空问卷与候选顺序](TEMPLATE_PRIOR_V2.md)、[事后补充分析登记](POSTHOC_ANALYSES_V2.md)。外部依赖包括同级`ClinicalBelief/data/raw`中的源数据、`MedicalBeliefMechanisms/.models`中的两个模型，以及原有两个Python环境。结果阅读只需本目录；重新准备病例和运行模型需要这些依赖。

原本有限队列由`phase_v2_continue.py`等待800条观测后顺序执行；`phase_v2_finish.py`随后执行阶段20。手动逐条运行上述命令也可以，验证脚本依各阶段完成记录检查，不依赖队列进程。不要同时加载两个GPU模型来抢占设备；分析和绘图可在CPU进行。
