# 复现本轮多来源医学信念实验

工作目录为Seq，项目为MedicalBeliefStudy。所有模型推理在本地Apple GPU执行，API费用0美元。

## 冻结输入

使用`data/belief_v4/cases.private.jsonl`中的540例，不重新抽样。SHA256：`f77bacaed2f3217de0916d647c3cf06c8160e7240f0f841794644035028ddd23`。候选、来源答案、固定错误历史、开发/确认分组和内部子集都已写入。公开版本用于不含标签的输入追溯，私有版本供评分。原始来源文件哈希及下载地址见`data/belief_v4/manifest.json`和`raw/download_stage*.json`。

原数据选择脚本phase38保留运行时版本，不因事后审计修改。`text_audit.json`单独标记20例，严格敏感性使用520例；该规则按原文问题筛选，不按模型答对/答错筛选。

## 运行环境

- GPU：`MedicalBeliefMechanisms/.runtime_mlx/bin/python`，Python3.13.2 arm64；mlx0.32.4、mlx-lm0.32.2、transformers5.23.0、tokenizers0.23.3。
- CPU分析：`MedicalBeliefMechanisms/.runtime/bin/python`，需numpy、scipy、scikit-learn、matplotlib。
- 模型：`MedicalBeliefMechanisms/.models/Qwen3-1.7B`与`Qwen3-4B-8bit`。每个权重/配置/分词器文件哈希记录在相应run manifest中。
- 绘图中文字体通过`src/analyze_stages.py`中的setup选择；图同时输出PNG和PDF。

## 依赖顺序

以下均以Seq为当前目录。用上述GPU Python运行推理脚本，用CPU Python运行分析脚本；每个命令的脚本路径前加`MedicalBeliefStudy/src/`。

| 顺序 | 脚本 | 作用 |
|---:|---|---|
| 1 | phase39_multisource_run.py | 540例的6823组正式观测 |
| 2 | phase40_multisource_patch.py | 94例自然状态替换，2444条件 |
| 3 | phase43_multisource_4b.py | 94例4B复核，1034条件 |
| 4 | phase44_layer_trajectories.py | 1960个新增逐轮代码/提及观测，复用376终点 |
| 5 | phase47_mention_patch.py | 48例未采纳病名受体捕捉与960干预 |
| 6 | phase49_history_routes.py --model 1.7b | 48例、1152条通路条件 |
| 7 | phase49_history_routes_native.py --model 4b | 相同48例的4B通路复核 |
| 8 | phase51_mean_repair.py | 1080终点事实均值用FP32重算 |
| 9 | phase58_module_readout.py | 复用376既有状态，拆开attention/MLP读表 |
| 10 | phase60_final_mlp_transfer.py | 940个末层MLP激活干预，不新增整段前向 |

推理阶段可从已完成病例/条件恢复；manifest不符会中止，不能改了代码继续混用旧记录。第58、60阶段只读已有状态，可在主观测完成后运行。追加同格式病名控制运行phase64_name_counterbalance.py --model 1.7b与--model 4b，两个配置各480次输入；CPU分析使用phase65。4B通路原版向量输出头的数值核验失败，使用原生批量输出头版本重新运行，详见MEASUREMENT_NOTES。所有模型参数保持冻结。

完成后按依赖运行CPU分析：phase41、42、45、48、50、52、56、59、61、62。其中phase41必须在phase51修复后运行；phase56须在上述主结果全部就绪后运行；phase62读取phase58结果及原始状态。

## 校验

主记录用phase54校验哈希、每词元分数求和、候选归一化、注意力和、原生前向对照和主状态有限性。主记录6823个中4442个旧`evidence_means`含FP16辅助归约溢出，此字段全部弃用；其他主状态和评分通过检查。正式分析使用`runs/belief_v4/mean_repair`中的1080个FP32 sidecar。修复不改变模型输出。

主观测与干预不同：每层注意力读表不是因果贡献。原生完整病名分数、首代码分数、真实生成和中间层投影分别保存，不混用成一个准确率。

## 服务器迁移

模型、数据、代码、环境依赖和runs要一起考虑；仅复制论文文件夹无法继续实验。现有脚本是MLX实现，不会自动使用CUDA。服务器Codex应先按本文件与`acl_paper/v08_multisource/METHODS.md`实现等价CUDA前向，在固定病例上核对词元、原生logits、候选分数、自身替换和路径遮挡，再扩大运行。不能把CUDA端新结果静默续写到MLX旧manifest目录。

## 汇总与打包

完成上述分析后，用CPU Python运行phase63_final_validation.py；通过后执行phase66_write_synthesis.py生成主报告和中文论文。phase68_atlas_labels.py可单独刷新病例文字表格（不重画图、不调用模型），也已并入phase45的表格生成逻辑。phase67_package.py生成结果与复现代码ZIP，不含模型权重和大体积NPZ激活。ROUTE_FINDING.md是依据完成结果撰写的人工归纳，phase66读取它而不重新推断结论。
