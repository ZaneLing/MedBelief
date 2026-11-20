# 换一台Apple芯片Mac继续实验

当前阶段已经完成，不需要重新摸索或重新训练这22种配置。先恢复环境，重放一个已知病例，再开下一阶段的新目录。

## 1. 先了解我们做到哪里

按顺序读：

1. [本轮结果](MedicalBeliefStudy/research_v6_adapters/START_HERE.md)。
2. [逐轮病例说明](MedicalBeliefStudy/research_v6_adapters/ONE_CASE_EXPLAINED.md)。
3. [论文三层逻辑](MedicalBeliefStudy/acl_paper/v10_adapters/ARGUMENT_STRUCTURE.md)及[当前正文](MedicalBeliefStudy/acl_paper/v10_adapters/PAPER_ZH.md)。
4. [冻结实验协议](MedicalBeliefStudy/research_v6_adapters/PROTOCOL.md)、[评分修正](MedicalBeliefStudy/research_v6_adapters/SCORING_AUDIT.md)、[运行状态](MedicalBeliefStudy/research_v6_adapters/SESSION_STATUS.json)。

研究对象是**模型的医学信念：每条证据怎样改变候选判断和内部计算**。不改成通用bench排行榜，不把输出写法修复写成医学能力提升。

## 2. 克隆并核对文件

以下命令在新Mac的终端运行。仓库是私有仓库，需要有访问权限的GitHub账号。

```bash
git clone https://github.com/ZaneLing/MedBelief.git
cd MedBelief
python3 tools/check_snapshot.py --profile git
```

从旧电脑拷贝 `MedBelief_ACL_data_20261120.zip`，可放到移动硬盘或新Mac任意位置。无需复制 `.env`、API密钥、虚拟环境或模型缓存。本项目本轮使用本地模型，模型API费用为0。

## 3. 建立两套环境

使用原生Apple Silicon终端，`uname -m` 应输出 `arm64`。如尚未安装所需Python，可用Homebrew：

```bash
brew install python@3.11 python@3.13
python3.11 tools/setup_env.py analysis
python3.13 tools/setup_env.py mlx
```

- CPU统计环境：`MedicalBeliefMechanisms/.runtime/bin/python`。
- Apple GPU推断环境：`MedicalBeliefMechanisms/.runtime_mlx/bin/python`。

保留这些虚拟环境入口，不把它们改成指向旧电脑解释器的绝对路径。CPU统计依赖版本见 `requirements/analysis.txt`；`requirements/mlx.txt`直接使用原GPU环境的完整锁定记录 `MedicalBeliefMechanisms/requirements-mlx-lock.txt`。

检查Apple GPU：

```bash
MedicalBeliefMechanisms/.runtime_mlx/bin/python -c 'import mlx.core as mx; print(mx.device_info())'
```

## 4. 从本地ZIP恢复数据

代码、固定病例、完整生成文本、通道排名和小模块权重已经随Git下载。用户要求大数据不上传GitHub，直接拷贝ZIP；以下操作完全离线。

```bash
# 将示例路径替换为实际ZIP位置；路径包含空格时保留引号。
python3 tools/restore_data.py "/你的拷贝路径/MedBelief_ACL_data_20261120.zip" --profile all
python3 tools/check_snapshot.py --profile all
```

`all`恢复全部已打包的医学研究文件，包括早期原始实验。只想先重放最新阶段，可把两条命令的 `--profile all` 换成 `--profile current`；只提取最新阶段所需文件，但仍需完整拷贝同一个ZIP。工具先检查ZIP完整性，再逐文件核对SHA-256；已经相同的文件会跳过，内容被改过的实验文件不会被覆盖。

[数据包大小与SHA-256](artifacts/LOCAL_DATA_PACKAGE.json) · [所有文件清单](artifacts/manifest.json) · [包含及未包含的内容](docs/SNAPSHOT_SCOPE.md)。

全量恢复建议预留约50GB空闲空间，用于ZIP、解压文件、模型和环境。

不要上传这个ZIP到GitHub，也不要恢复虚拟环境或公共模型缓存。整个文件包是ZIP64格式，可由本工具或macOS归档工具读取；优先使用上述命令，避免解压到错误目录或覆盖后来修改的文件。

## 5. 下载固定版本模型

```bash
MedicalBeliefMechanisms/.runtime/bin/python tools/download_models.py --model 1.7b
```

该命令下载固定revision的Qwen3-1.7B，检查权重和分词器散列，放到 `MedicalBeliefMechanisms/.models/Qwen3-1.7B`。无需模型API。约4.06GB原始模型文件；如已复制相同权重，可加 `--verify-only` 只核验。

需要复核旧4B实验时另外下载 `--model 4b-mlx`；它是旧研究的8-bit MLX配置，不与1.7B FP16混为相同量化设置。

## 6. 先重放一个已知病例

```bash
MedicalBeliefMechanisms/.runtime_mlx/bin/python MedicalBeliefStudy/src/structure2_demo.py --candidate primary --case-id medqa_train_04812 --condition wrong --output new_runs/migration_smoke.json
python3 tools/check_replay.py new_runs/migration_smoke.json
```

原记录最终输出为 `Vascular dementia`。检查器同时核对提示散列、原始完整输出、词元数和参数数。换芯片可能出现数值差异：如果不一致，保留新文件，核查环境和推断路径，不改原答案或删掉检查。

## 7. 下一阶段只保留一个主问题

**局部缩窄是否减弱错误旧诊断的牵引，同时保留正确历史的帮助？**

当前信号：同样候选约束下，完整模型与压缩模型在中性历史为215/400与216/400，在错误历史为168/400与180/400；参数减少13.16%。这是追加解释性对照，尚未由新病例再次确认。

建议下一阶段依次做：

1. 冻结完整模型和当前压缩模型，使用相同输出规则；增加正确旧诊断条件，与中性、错误历史配对。
2. 先准备新的来源病例，核对图像缺失、任务类型、选项写法和近重复；与已有540+880例隔离。新病例先固定，不能看结果再挑。
3. 先小规模验证运行与评分，再扩大。每例同时保存原始文本、严格评分、规范化候选评分及修复/损坏。
4. 在预先固定的轨迹子集逐条给证据，保存各层状态、候选支持、实际答案；分析旧诊断影响是否减弱，以及正确历史是否也被损坏。
5. 每阶段交付结果Markdown、PNG/PDF和原始记录，再更新论文；不要因单个好例子就声称已经发现普遍机制。

原冻结目录只读。新工作建议放在 `new_runs/v011_history_preservation/`、`MedicalBeliefStudy/research_v7_history_preservation/` 和新的阶段结果文件夹。不要重跑阶段90或98来覆盖880例分组和已冻结方法。GPU实验串行运行，尤其测速时不并行跑别的模型。

## 8. 本次迁移已经验证什么

[迁移检查](docs/MIGRATION_VALIDATION.json)记录源文件复制、原始数据包恢复和原型重放检查。本机历史实验的 [最终核验](MedicalBeliefStudy/research_v6_adapters/FINAL_VALIDATION.json) 与 [文档核验](MedicalBeliefStudy/research_v6_adapters/DOCUMENT_VALIDATION.json) 保留原记录；它们不冒充新电脑上的运行记录。
