# ACL医学信念研究 v0.10 迁移快照

包含当前论文、实验源码、报告、图表、固定病例、v0.8—v0.10的原始模型观测与内部状态、v0.10训练特征及小模块权重。源文件与数据包均有SHA-256清单。

- `current-v010`：最新结构/适配器实验的训练特征和逐层状态，继续当前实验首先恢复此包。
- `acl-evidence-v008-v009`：前两阶段多来源内部机制及结构实验的完整原始观测。
- `source-data`：公开来源数据及旧筛选记录。
- `historical-analysis-arrays`：历史分析用的读出器、数组等。

模型权重从记录的固定Hugging Face版本下载。虚拟环境、凭据、早于v0.8的原始激活缓存及独立ClinicalBelief训练输出不在本快照中；历史论文、报告和相关源码保留。原电脑上的文件不改动。

使用仓库内 `tools/restore_artifacts.py` 下载并逐文件验证。详见根目录HANDOFF.md与artifacts/manifest.json。
