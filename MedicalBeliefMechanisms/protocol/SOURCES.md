# 首轮材料的依据与范围

核查日期：2026-11-17。来源为NICE官方条款。个别网页直接打开返回403；检索索引与官方PDF条款仍可核对。本文件保存来源及本研究采用的限定解释，不复制指南全文。

| 任务 | 来源与条款 | 首轮限定范围 |
|---|---|---|
| AKI肌酐变化 | [NG148 §1.3.1](https://www.nice.org.uk/guidance/ng148/chapter/Recommendations) | 只问48小时内绝对升高至少26 μmol/L这一条标准，未满足此条不能推出没有AKI |
| 高血压确认 | [NG136 §1.2.6、§1.2.8](https://www.nice.org.uk/guidance/ng136/chapter/recommendations) | 成年非孕、规范诊室测量，合格日间ABPM；测量无效或缺失应回答资料不足 |
| DVT初始检查 | [NG158 §1.1.3、§1.1.8](https://www.nice.org.uk/guidance/ng158/chapter/recommendations) | 独立评估的Wells分数已给出，两类检查均可在4小时内完成，只问初始路径 |

每条合成记录带指南来源、可计算事实、期望标签、来源有效性、先前倾向及答案字母映射。撤回报告后没有替代证据，答案是资料不足，不是相反诊断。

病例全部由程序构造；没有调用病人数据，没有独立医生审核。首轮数字范围避开临界值，另用单元检查覆盖边界。按用户2026-11-18明确要求，医生审核不作为继续研究的条件；本项目只对给定规则下的LLM判断作结论。

模型依据：[Qwen3-1.7B官方仓库](https://huggingface.co/Qwen/Qwen3-1.7B)。下载固定提交，实际参数量、层数、版本和精度记录在每次运行元数据。模型名称中的规模不能代替实际参数统计。

方法依据：[模型输出接口](https://huggingface.co/docs/transformers/main_classes/output)、[探针控制任务](https://aclanthology.org/D19-1275/)、[激活替换方法](https://arxiv.org/abs/2309.16042)。

2026-11-18复核：再次核对上述三份NICE官方条款，首轮采用的阈值与检查路径未变。阶段1B确认集包含肌酐恰好升高26 μmol/L的边界题。血压材料明确区分设备测量频率、用于日间均值的有效读数数量，并声明其余质量条件满足；只评估所给规则，不延伸为完整高血压诊断。第二模型采用[Qwen官方Qwen3-4B MLX 8-bit仓库](https://huggingface.co/Qwen/Qwen3-4B-MLX-8bit)，固定提交与权重校验见`qwen3_4b_8bit_snapshot.json`和模型目录中的`verified_download.json`。

2026-11-18阶段2B个案复核：模型在`confirm_dvt_0_initial_no`中额外假设DVT Wells评分不能为负。再次核对[NICE NG158表1](https://www.nice.org.uk/guidance/NG158/chapter/recommendations)，表中“另一个诊断至少同样可能”扣2分，若同时有一个加1分项目，总分可为−1；这是按官方表相加得到的判断。题目中的已核定−1分不因负号而无效。保留模型原始错误，不修改材料将其变成答对。
