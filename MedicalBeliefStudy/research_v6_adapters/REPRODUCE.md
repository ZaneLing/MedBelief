# 复现：结构裁剪、适配器与医学信念更新

所有命令从项目总目录 `Seq` 执行。原模型为 `MedicalBeliefMechanisms/.models/Qwen3-1.7B`。当前实现使用Apple GPU上的MLX，不能原样调用CUDA；服务器迁移时需将实际矩阵裁剪、适配器和缓存生成对应移植为PyTorch，并重新验证数值与速度。数据、选择清单、适配器权重和统计脚本可直接迁移。不要把本机耗时当成服务器耗时。

## 已冻结的数据与方法

- [数据清单](../data/belief_v5/manifest.json)：880例，400训练、80开发、400确认；两个来源各半，与前540例分离。
- [完整协议](PROTOCOL.md)：候选方法、开发选择、确认统计、输入和输出对照。
- [结构选择](../runs/structural_v2/pruning_selection.json)、[训练清单](../runs/structural_v2/adapter_plan.json)、[确认前冻结清单](../runs/structural_v2/confirmation_selection.json)。
- [方法出处](RELATED_METHODS.md)：适配器、结构裁剪、桥接替换与对比解码均有先例。
- [运行中来源复核](SOURCE_AUDIT.md)：原确认400例；文本子集386例；再排除0.80近重复后366例。训练/开发仍按原400/80，不回溯重新选模型。
- [分词修正清单](TOKENIZATION_AMENDMENT.json)：`structure2_compat.py`保留提示词元，仅为一个以单引号开头的候选补充合法续写编码。阶段99—101及原型加载它；原核心与解码器散列不变。已有129例258个回答不受影响。

运行阶段90会拒绝覆盖既有数据；阶段98会拒绝覆盖既有确认选择。复现既有结果不需要重新执行这两步。需要新实验时应复制配置到新版本目录，保留既有原始记录。

## 推断原型

以下命令加载开发集预定的压缩候选，在一个固定病例上实际生成完整候选。无需重新训练；推断不把来源答案交给模型。

```bash
MedicalBeliefMechanisms/.runtime_mlx/bin/python MedicalBeliefStudy/src/structure2_demo.py --candidate compression --condition neutral
```

`--candidate primary` 加载预定主候选；`--candidate baseline` 加载完整原模型。`--case-id` 指定病例，`--round 3` 只给前3组证据，`--condition wrong` 加入固定错误旧诊断。可用 `--output` 另存结果。完整输入渲染和原始生成见 [structure2_core.py](../src/structure2_core.py)，候选约束见 [structure2_decode.py](../src/structure2_decode.py)。原型保留四个来源候选；它不是开放世界临床诊断系统。

小适配器只是原模型上的新增权重。它不能脱离剩余约十多亿参数的模型独立诊断。裁剪在内存中真实缩小矩阵，不是给未删的矩阵乘零；原模型磁盘文件保持不变。

## 实验顺序

GPU脚本使用 `MedicalBeliefMechanisms/.runtime_mlx/bin/python`，CPU脚本使用 `MedicalBeliefMechanisms/.runtime/bin/python`。保留这两个虚拟环境入口路径，不要将其解析为外部解释器路径。GPU任务逐个执行，尤其测速时不要并行跑另一个模型。

| 阶段 | 脚本前缀 | 环境 | 产物 |
|---|---|---|---|
| 90 | phase90_structure2_prepare | CPU | 新数据分组与13个结构候选 |
| 91 | phase91_structure2_calibrate | GPU | 64例训练病例的通道/注意力组排序、数值等效性核验 |
| 92 | phase92_structure2_search | GPU | 13种配置、80例开发的完整名称生成 |
| 93 | phase93_structure2_select_pruning | CPU | 选定压缩结构、冻结适配器训练超参数 |
| 94 | phase94_structure2_features | GPU | 完整/压缩模型的训练和开发冻结状态 |
| 95 | phase95_structure2_train | GPU | 5个小适配器、训练曲线、所选权重 |
| 96 | phase96_structure2_bridge | CPU | 前20层到28层的秩64教师状态桥接 |
| 97 | phase97_structure2_adapter_eval | GPU | 5适配器、桥接、3候选约束的开发结果 |
| 98 | phase98_structure2_freeze | CPU | 7配置、主候选、压缩候选、24例轨迹名单 |
| 99 | phase99_structure2_confirm | GPU | 400例×7配置×2历史，加400例无历史，共6000次生成 |
| 100 | phase100_structure2_timing | GPU | 6例、2历史、2重复，144对耗时记录 |
| 101 | phase101_structure2_trajectories | GPU | 固定24例所有证据前缀、候选分布与各层状态 |
| 102 | phase102_structure2_development_report | CPU | 全部开发尝试及训练报告 |
| 103 | phase103_structure2_confirmation_report | CPU | 配对统计、输入控制、错误可恢复性、耗时图 |
| 104 | phase104_structure2_trajectory_report | CPU | 24例全图谱与内部变化汇总 |
| 105 | phase105_structure2_validate | CPU | 数据、代码、权重、概率、生成与原模型完整性核验 |

脚本均在 `MedicalBeliefStudy/src/`。阶段102须等阶段98，阶段103须等阶段100，阶段104须等阶段101，最终核验须在全部推断结束后执行。已有逐病例结果可断点续跑，但冻结清单和代码散列不匹配会报错，不应通过删掉核验绕过。

## 数据字段怎么读

`cases.private.jsonl` 保留来源、原文证据句、四候选、最终来源答案、分组。`wrong_disease` 是通过病例散列从三个错误候选中固定选的历史干扰；它不是模型自己上一轮生成的答案。

病例ID里的 `train` / `dev` / `validation` 表示原题库的来源划分；本实验另外用 `cohort` 划成400/80/400。400例确认是本实验留出集，不称为原题库的官方测试集，也不据此宣称基础模型预训练从未接触过相关题目。

生成JSON中的 `text` 是原始续写，`generated_disease` 是解析后的完整名称，`correct` 与来源最终答案严格比对。不能解析、名称不属于原四候选均计错。候选约束只依赖给出的四个候选，不依赖哪个正确；它保证名称格式，不保证选对。

轨迹JSON中的 `q_sequence` 是四个完整候选序列分数归一化后的支持，`q_token_mean` 是除以序列长度后再归一化的敏感性指标。普通方法使用完整词表概率；候选约束方法使用前缀树约束后的条件概率，两者要分开解释。都不是校准后的临床疾病概率。

轨迹NPZ保存每轮所有层、输出位置的2048维状态，以及最终归一化后适配器之前/之后的向量。相邻证据轮的向量变化衡量内部改动幅度；疾病方向要结合候选序列支持和实际生成，不能单凭余弦距离命名疾病。推断时模型权重固定，改变的是上下文激活与输出；注意力权重也不等于模型训练参数发生变化。

## 统计

独立单位是病例。主准确率差先将同病例的两种历史平均，再做400病例配对bootstrap区间与配对随机符号检验；六项相对完整模型比较采用Holm校正。三项训练/结构差异使用单独的三项Holm组。输入控制、来源分层、错误可恢复性及轨迹为解释性分析，不再用于选方法。

测速先在每病例内平均对数耗时比，再跨6病例估计几何比和区间。“任一方法答对”的并集需要知道正确答案后选择，是oracle错误分析，不能作为部署成绩。本轮没有预定非劣界值，未显著变差不能直接宣称证明不损失性能。

本轮模型API费用：**0美元**。

## 追加的匹配输出对照

阶段107 `phase107_structure2_matched_output.py` 在原GPU阶段99—101结束后运行：开发阶段已有的完整模型候选约束，400例×2历史=800次生成；与压缩候选约束在同6例上另做24对测速。阶段103汇总会等待该对照完成。它是主结果产生后的解释性对照，登记与代码散列见[MATCHED_OUTPUT_CONTROL.json](MATCHED_OUTPUT_CONTROL.json)，结果置于 `runs/structural_v2/output_matched_control/`。原定6000次确认生成单独保留，追加对照不进入原六项Holm组。

## 结果后的评分敏感性修正

原逐字命中会因来源候选的末尾空格、冠词及标点把部分正确病名计错。追加统一写法规范化，唯一匹配全部四个候选之一；没有医学模糊匹配或真值驱动解析。原主方法、原始输出及原Holm组保留，规范化六项比较单独报告。方法登记与全部28个输出修复见[评分审计](SCORING_AUDIT.md)。阶段103同时输出两套指标；阶段104的轨迹一致性主表改用规范化候选身份，原逐字指标保留；阶段105独立重算两套数值。

阶段106 `phase106_structure2_synthesize.py` 在105核验完成后生成读者入口和中文论文稿；最后运行 `structure2_validate_documents.py` 核对文档链接、图像与代码语法。

## 已实测的原型重放

以下在项目根目录运行，加载原始1.7B权重后在内存中真实裁剪，不覆盖模型文件。

```bash
MedicalBeliefMechanisms/.runtime_mlx/bin/python MedicalBeliefStudy/src/structure2_demo.py --candidate primary --case-id medqa_train_04812 --condition wrong
```

该病例已重放并与原确认的完整输出、词元数和提示散列逐项核对，见[DEMO_VALIDATION.json](DEMO_VALIDATION.json)。`--round 9` 可只看到第9轮证据；`--candidate baseline` 可改回完整模型。[中文解释](ONE_CASE_EXPLAINED.md)。演示耗时不混入交错配对测速。
