# MedBelief：模型有医学信念吗？

这是 ACL 医学信念研究的独立续跑目录。当前研究稿为 **v0.10**，从逐条医学证据下的判断变化，深入模型内部，再检验结构裁剪与小适配器能否改变诊断。

**换电脑后先读 [HANDOFF.md](HANDOFF.md)。给另一台电脑的 Codex 复制 [这一句话](docs/CODEX_PROMPT.md)。**

| 想看什么 | 入口 |
|---|---|
| 本轮结论，用人话解释 | [START_HERE](MedicalBeliefStudy/research_v6_adapters/START_HERE.md) |
| 一个病例如何选对、转错、再转回来 | [病例解释与图](MedicalBeliefStudy/research_v6_adapters/ONE_CASE_EXPLAINED.md) |
| 当前论文与三层论证 | [中文稿](MedicalBeliefStudy/acl_paper/v10_adapters/PAPER_ZH.md) · [论证架构](MedicalBeliefStudy/acl_paper/v10_adapters/ARGUMENT_STRUCTURE.md) |
| 全部新增实验 | [结果与论文主线](MedicalBeliefStudy/research_v6_adapters/RESULTS_AND_STORY.md) |
| 相关工作 | [医学信念相关工作](MedicalBeliefStudy/acl_paper/v08_multisource/RELATED_WORK.md) · [结构与适配器](MedicalBeliefStudy/research_v6_adapters/RELATED_METHODS.md) |
| 数据、评分与异常核查 | [数据审计](MedicalBeliefStudy/research_v6_adapters/SOURCE_AUDIT.md) · [评分审计](MedicalBeliefStudy/research_v6_adapters/SCORING_AUDIT.md) · [答案范围](MedicalBeliefStudy/research_v6_adapters/ANSWER_SCOPE.md) |
| 每阶段的完整记录 | [实验总索引](MedicalBeliefStudy/README.md) |

当前已完成：Qwen3-1.7B，新增880例（400训练、80开发、400确认），22种开发配置、7种冻结确认配置及1个匹配输出对照；24例147个证据阶段、882次逐轮内部观测。模型API费用0美元。

局部缩窄减少13.16%参数；同输出规则下，在错误历史条件出现小幅改善，需新病例确认。大幅删层和本轮输出端适配器恢复失败。严格字符串评分会夸大部分收益，正文保留规范化检查，不能把格式修复写成医学能力提升。

## 代码与本地数据包

论文、代码、报告、表图、固定病例和最新原始生成已经推送到GitHub。**完整数据通过本地 `MedBelief_ACL_data_20261120.zip` 拷贝，不上传GitHub。** ZIP同时保留早期医学实验的原始运行、逐层状态和前身项目结果；准确大小与校验码见[数据包记录](artifacts/LOCAL_DATA_PACKAGE.json)。

```bash
git clone https://github.com/ZaneLing/MedBelief.git
cd MedBelief
python3 tools/check_snapshot.py --profile git
python3 tools/restore_data.py /你的拷贝路径/MedBelief_ACL_data_20261120.zip --profile all
python3 tools/check_snapshot.py --profile all
```

克隆私有仓库需要有权限的GitHub账号；恢复本地ZIP不需要网络或GitHub登录。模型权重与虚拟环境按固定版本重新安装。[迁移步骤](HANDOFF.md) · [文件范围](docs/SNAPSHOT_SCOPE.md)。

旧科学脚本、数据、选择清单和结果按字节保留。新的迁移工具集中在 `tools/`，新实验写到 `new_runs/`，不覆盖冻结记录。本次交接目标为Apple芯片Mac，沿用原来的MLX显卡后端。NVIDIA/CUDA并未在本次交接中移植。
