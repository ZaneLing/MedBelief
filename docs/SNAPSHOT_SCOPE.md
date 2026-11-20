# 交接范围

**GitHub存代码和论文；完整研究数据用本地ZIP拷贝，不上传GitHub。**

| 内容 | 位置 |
|---|---|
| 当前ACL论文、相关工作、方法及历史稿 | MedicalBeliefStudy/acl_paper |
| 源码、阶段报告、统计表图、固定病例和最新生成 | GitHub已有对应目录 |
| 最新训练特征、每层状态、全部早期医学实验原始记录 | 本地ZIP，恢复后回到原相对路径 |
| 前身项目的数据、原始运行和ClinicalBelief训练产物 | 本地ZIP中的MedicalBeliefMechanisms、MedicalBelief1_7B、MedicalBeliefTrajectories、ClinicalBelief |
| 固定公共模型版本与环境配置 | MedicalBeliefMechanisms/protocol、requirements和根目录tools |

本地ZIP覆盖上述五个医学研究项目的77,004个科学文件，包括早期原始运行和ClinicalBelief已有训练产物。ZIP为20,734,524,357字节（约20.73GB），解压内容约22.01GB。原电脑的研究文件不修改。

准确文件数、大小和ZIP校验码见 [LOCAL_DATA_PACKAGE.json](../artifacts/LOCAL_DATA_PACKAGE.json)。[manifest.json](../artifacts/manifest.json)逐文件记录路径、字节数、SHA-256和恢复分组；ZIP内部也包含同一份清单。打包后重新读取每个ZIP条目，核对解压后的SHA-256。

不包含公共基础模型权重、虚拟环境、平台工具和缓存、`.env`及凭据、重复的旧交付压缩包，以及非医学项目。小适配器和ClinicalBelief已有训练产物属于实验结果，已经包含。公共基础模型按固定revision下载并校验。

源码中的原数据来源和许可信息保持原样，本次整理不改变第三方数据许可。
