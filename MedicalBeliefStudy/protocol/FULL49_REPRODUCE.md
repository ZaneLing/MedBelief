# 阶段06—11复现说明

## 环境与输入

本轮推理实际使用本机 Apple M2 Pro GPU、MLX、Qwen3-1.7B，BF16权重加载后统一转FP16，参数冻结，未量化。未调用付费API。每个运行目录的manifest记录依赖、源代码与模型文件哈希。

推理解释器：`../MedicalBeliefMechanisms/.runtime_mlx/bin/python`；分析解释器：`../MedicalBeliefMechanisms/.runtime/bin/python`。以下命令从项目根目录Seq执行。推理实现依赖Apple Silicon上的MLX；迁往CUDA服务器时需移植前向采集并复核数值，不能将本轮称为CUDA实验。NPZ/JSON/CSV和分析代码可直接跨平台使用。

原始DDxPlus文件来自`ClinicalBelief/data/raw/`。模型位于`MedicalBeliefMechanisms/.models/Qwen3-1.7B/`。本研究目录并未复制这两份大型来源，迁移需同时提供数据和模型，或调整路径。

## 执行顺序

```bash
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase6_prepare.py
MedicalBeliefMechanisms/.runtime_mlx/bin/python MedicalBeliefStudy/src/phase6_measure.py
MedicalBeliefMechanisms/.runtime_mlx/bin/python MedicalBeliefStudy/src/phase6_name_control.py
MedicalBeliefMechanisms/.runtime_mlx/bin/python MedicalBeliefStudy/src/phase8_validate.py
MedicalBeliefMechanisms/.runtime_mlx/bin/python MedicalBeliefStudy/src/phase8_intervene.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase67_analyze.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase8_analyze.py
MedicalBeliefMechanisms/.runtime_mlx/bin/python MedicalBeliefStudy/src/phase9_names.py
MedicalBeliefMechanisms/.runtime_mlx/bin/python MedicalBeliefStudy/src/phase10_names_intervene.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase910_analyze.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase10_geometry.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase11_probe.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase11_text_audit.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/phase11_update_divergence.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/render_probe_figures.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/finalize_full49_reports.py
MedicalBeliefMechanisms/.runtime/bin/python MedicalBeliefStudy/src/verify_full49_delivery.py
```

已存在的原始观测会跳过；源代码、模型或冻结输入变化时manifest不一致会报错。修订测量方法应另设运行版本，不能覆盖原数据。分析脚本可从原始记录重新生成报告和图。

## 输出与统计口径

- `runs/full49_v1/`：5040次编码接口观测、24例无候选名称控制、240个固定中间轮/编码条件的内容控制、1200个前缀×层干预记录。
- `runs/structured_names_v1/`：538次完整疾病名观测；24例候选列表逆序、24例深层干预、行政说明和重复证据控制。
- 原始状态保存28层五处诊断锚点状态；每层16个注意力头聚合到证据组。预定24例另保存逐token注意力、逐头输出及证据末位置状态。
- 统计先在病例内汇总；区间通常为2000次病例bootstrap，固定随机种子20261119。全0/全1二元结果使用精确二项边界区间。JS使用自然对数。NLL计算以1e-30作为数值下限，原始概率不改写。
- 阶段08确认检验为第26/27/28层旧MLP相对移位对照效应的双侧t检验，三比较Holm校正。阶段09—10是观察编码问题后的探索性修正，不称为独立确认。
- 阶段11在固定五折中以病例隔离训练真实疾病读出器，100次训练标签置换。读出器是外部线性分类器，未更新语言模型参数；完整病名原生评分限制到同24类后进行公平比较。文本结构审计在观察到100%基线后追加。

## 工程修订记录

无候选名称控制首次启动时，MLX没有`mx.log_softmax`接口，在任何观测写入前终止。改为先减最大值再用`logsumexp`的稳定实现；失败manifest保留在`runs/full49_v1/name_controls/failed_api_manifest.json`。随后24例正常完成。

阶段06曾短暂停止进程，让预定名称检查和疾病名接口的少量数值检查独占GPU，之后恢复；输入、权重、观测代码未改变。观测进程的总elapsed包含这些暂停，不能直接当作纯推理耗时；逐条记录有实际观测耗时。

更细的冻结方案与适应性补充见同目录：`FULL49_PHASES_6_8.md`、`FULL49_ANALYSIS_ADDENDUM.md`、`STRUCTURED_NAME_ADAPTATION.md`、`STRUCTURED_NAME_CANDIDATE_ORDER.md`和`NAME_CONTENT_CONTROLS.md`。

交付数值复核：FP16批量逐层投影与单点末层概率并非逐位相等；沿用原观测脚本预定的logit容差，并另报告全量最大概率差与首选差异。最大候选支持差0.007628，5040次首选差异为0，原始观测未改变。图形后处理单独使用`render_probe_figures.py`修正层号为1—28并将色条移到面板外，不重训读出器。
