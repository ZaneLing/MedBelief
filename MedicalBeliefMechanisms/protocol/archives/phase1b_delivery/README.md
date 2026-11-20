# 医学信念机制研究

研究主线：模型如何在内部形成医学判断，如何接受、使用和撤回证据，以及哪些内部状态实际影响后续判断与调查。

按2026-11-18讨论，研究对象是LLM医学信念；以明确指南、程序标签与受控对照进行机制研究，不设医生审核门槛。

这是独立研究目录。旧ClinicalBelief和此前探索保留为参考，不把旧模型的概率当成大模型内部信念。

**先读：[论文逻辑线](paper/PAPER_LOGIC.md)。** 实验问题、竞争解释和主要图的论点对应关系都写在其中。

最新交付：[阶段1B易读报告与结果图](reports/PHASE1B_READ_FIRST.md)。648条核心确认和诊断记录，另有开发排查；保存162份4B内部状态。数值题和来源题分别正确，最终判断仍可能错误；目前是行为线索，尚未确立内部机制。

此前交付：[阶段0](reports/PHASE0.md)、[阶段1先读这个](reports/PHASE1_READ_FIRST.md)、[阶段1详细结果与图](reports/PHASE1.md)。内部数据的测量与解释见[内部表示说明](protocol/INTERNAL_MEASUREMENTS.md)。

**阶段状态**

| 阶段 | 当前状态 | 交付 |
|---|---|---|
| 0：论文定位与首轮设计 | 已完成 | [论文逻辑](paper/PAPER_LOGIC.md)、[阶段计划](protocol/STAGES.md)、[冻结配置](protocol/phase1.json) |
| 1：测量可行性与规则理解 | 已交付；工程采集通过，基础能力校准未通过 | [易读结论](reports/PHASE1_READ_FIRST.md)、[完整结果与两张图](reports/PHASE1.md)、756份激活；另完成39条排查记录 |
| 1B：校准修订及分解诊断 | 已交付；4B思考配置的肌酐、DVT通过，血压未通过；三域未整体通过 | [结果与图](reports/PHASE1B_READ_FIRST.md)、[开发与执行记录](reports/PHASE1B_AUDIT.md)、[交付校验清单](protocol/phase1b_delivery.json) |
| 2—6 | 正式实验未开始 | 阶段2已有准备代码和材料，但未运行；按[阶段计划](protocol/STAGES.md)递进 |

**目录**

- `paper/`：论文逻辑与后续主张记录。
- `protocol/`：冻结设计、指南来源、模型版本、成本与分阶段安排。
- `src/`、`tests/`：可复现代码与有意义的规则边界检查。
- `data/`：合成病例及校验清单。
- `runs/`：运行日志、原始输出、内部激活和元数据。
- `reports/`、`figures/`：逐阶段报告与真实数据图。
- `.runtime/`：本项目执行入口，继承已存在的本机依赖，未修改原环境；版本见`protocol/runtime.json`。
- `.models/`：固定提交的公开权重，不打包分发。早先`.venv/`安装已停止，不用于本轮结果。

**首轮材料**

12个病例骨架，分属三类规则明确的任务。216条配对轨迹展开为864条阶段记录，共756个不同提示。临床来源见[依据与范围](protocol/SOURCES.md)。独立医学审核尚未完成，不能把程序检查称为专家验证。

**复现命令，工作目录为本项目目录**

```bash
.runtime/bin/python src/download_model.py
.runtime/bin/python src/cases.py
.runtime/bin/python -m pytest tests -q
.runtime/bin/python src/run_phase1.py
.runtime/bin/python src/analyze_phase1.py
# 以下为首轮结果之后的追加排查，单独保存
.runtime/bin/python src/diagnose_phase1.py
```

模型由`protocol/model_snapshot.json`中的固定提交决定，权重按官方SHA256校验。下载程序可恢复已完成分段，请勿同时启动两个下载进程。复现依赖以`protocol/runtime.json`与`requirements-local-lock.txt`中的实际版本为准，后者对应Python 3.11环境；`requirements.txt`是新建环境的参考要求。下载与环境日志在`runs/`。采集可按已完成提示恢复；模型或数据改变时必须使用新的运行ID。

首轮及阶段1B均为本地推理，收费API实际支出0美元。首轮无旧判断的有效报告题正确率50%，尚未达到机制研究的基础能力要求；完整解释见阶段1易读结论。阶段1B新增的4B思考配置在肌酐、DVT域通过校准，血压域仍未通过。目前没有确立医学信念机制。

阶段1B采用本机原生ARM64 Python 3.13与MLX运行，隔离环境为`.runtime_mlx/`，包版本在`requirements-mlx-lock.txt`。模型固定提交、精度、采样和代码快照均保存在各运行目录的`metadata.json`与`source_snapshot.py`。图与主报告可从保存的原始记录重新生成：

```bash
python3 src/analyze_calibration.py phase1b_confirm_1p7b
python3 src/analyze_calibration.py phase1b_confirm_4b
python3 src/analyze_calibration.py phase1b_confirm_4b_direct
python3 src/analyze_evidence_diagnosis.py
python3 src/write_phase1b_report.py
.runtime/bin/python src/plot_current_stages.py
.runtime_mlx/bin/python src/verify_phase1b_delivery.py
```

完整推理入口为`src/mlx_experiment.py`。例如4B思考确认使用`--data data/phase1b_confirmation.jsonl --run-id phase1b_confirm_4b --max-tokens 2048 --model-dir .models/Qwen3-4B-8bit --model-manifest protocol/qwen3_4b_8bit_snapshot.json`；直接作答另加`--no-thinking`，第二种子复测使用对应54条数据和`--seed 20261119 --capture`。同机重新采集需换运行ID以保留原结果。
