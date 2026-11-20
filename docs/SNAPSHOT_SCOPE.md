# 这个独立目录包含什么

根目录保留原项目相对路径，避免冻结代码、病例和结果链接失效。

| 内容 | 存放位置 |
|---|---|
| 当前ACL论文、方法和历史稿 | MedicalBeliefStudy/acl_paper |
| 医学信念实验代码、结果、全部阶段报告 | MedicalBeliefStudy/src、results、research_*、protocol |
| 固定来源病例、划分、原题答案、评分审计 | MedicalBeliefStudy/data |
| 当前22配置与400例完整生成、通道排名、小适配器权重 | MedicalBeliefStudy/runs/structural_v2，随Git提供 |
| 当前训练特征、逐层状态 | Release current-v010，默认恢复 |
| v0.8—v0.9多来源机制和结构实验完整原始记录 | Release acl-evidence-v008-v009 |
| 全量来源文件、早期分析数组 | Release source-data、historical-analysis-arrays |
| 原模型下载记录与环境锁定 | MedicalBeliefMechanisms/protocol、requirements* |
| 早期数据准备的源码依赖 | ClinicalBelief、MedicalBelief1_7B、MedicalBeliefTrajectories |

本快照纳入 **35,667** 个原科学文件。随Git复制的源文件合计约 **468.2 MB**；15个数据包合计约 **9.46 GB**。每个文件和数据包均在[清单](../artifacts/manifest.json)记录字节数与SHA-256。

## 有意不复制的部分

- 公共模型权重：按固定Hugging Face revision重新下载，并检查原散列。
- 虚拟环境、平台工具、缓存、`.env`和凭据：新电脑重新安装。
- 重复的旧交付ZIP：论文、图和源码已分目录保存。
- v0.8之前的全部原始激活缓存、前身项目原始运行缓存，以及独立ClinicalBelief模型/训练输出：不是当前ACL续跑所需，仍保留在原电脑。相应历史报告、科学源码和固定病例保留。本快照不能冒称整个Seq目录的逐字全备份。
- 非医学的摸球/随机性等早期项目：不属于本次ACL医学信念迁移。

这些排除项不影响最新v0.10恢复、阶段102—106统计、结构原型重放或继续新病例实验。完整恢复v0.8/v0.9原始观测使用 `--profile acl`。

## 为什么把大状态放Release

GitHub普通Git不接受超过100MiB的单文件，并建议仓库保持较小；官方支持用Release分发大二进制文件。[GitHub说明](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)。本项目以代码和科学结果为Git主内容，原始内部状态以数据包恢复；所有资产继承当前私有仓库的访问权限。

原数据来源和模型遵循各自原有许可，本次整理不另行替第三方数据授予许可。原题及来源索引保留在病例字段、数据manifest和既有相关工作中。
