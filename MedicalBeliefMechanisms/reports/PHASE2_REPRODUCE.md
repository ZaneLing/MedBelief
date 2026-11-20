# 阶段2的设计修订、复现与审计说明

这份文件说明怎样复现，以及哪些改动发生在看到结果之前或之后。最终条数、词元数与文件校验，以生成后的`protocol/phase2_delivery.json`为准；统计表由`src/summarize_phase2.py`生成。

## 不混淆各批数据

| 批次 | 材料 | 用途 | 输出前确定的内容 |
|---|---|---|---|
| 2A | 12个数值病例骨架；24条初始题、360条后续题 | 自己的旧判断、来源更正与内部读出 | 原事实冻结；先规定肌酐/DVT为主要分析，血压单列；规定配对及读出划分 |
| 血压开发 | 4个新骨架，80条 | 比较五种说明 | 所有说明、确认材料和选择规则均先冻结 |
| 血压确认 | 另4个骨架，80条 | 新病例验证 | 开发基线全对，按原规则运行全部五种方法 |
| 2B | 8个新骨架；16条初始题、288条后续题 | 更简洁的来源表述、新失效原因、实际旧判断原文 | 病例与生成配置先冻结；初始回答格式修订发生在任何2B输出前 |
| 2C | 8个新骨架，64条 | 用替代报告拆开“R1可用性”和“最终是否资料不足” | 在任何2C输出前冻结材料、主要读出及修正读出方案 |
| 2D | 6个新骨架，48条 | 正确局部数字说明在肌酐/DVT中是否同样出问题 | 观察到血压个案后设计，自己的输入和对照在输出前冻结；属于探索性跨任务复查 |

这些是程序生成的数值骨架，很多共享题面结构。总记录数不能当成独立患者数，也不代表已经覆盖广泛医学决策。阶段1B已经通过的基础任务不保证新题面一定通过，因此2B继续单列无历史的基础表现。

## 模型、采样和内部记录

统一使用固定提交的Qwen3-4B官方MLX 8-bit权重。具体提交、权重哈希与版本在`protocol/qwen3_4b_8bit_snapshot.json`和各运行的`metadata.json`。没有调用收费模型API，没有修改Qwen权重。

运行入口是`src/mlx_experiment_v2.py`，原阶段1B引擎`src/mlx_experiment.py`没有改动。新入口只增加配对随机数流、输入长度和历史消息处理；过滤顺序沿用本机MLX-LM实现，top-p 0.95、top-k 20、温度0.6。每条最多生成2048词元，批量16；2A初始题沿用旧入口及其已保存配置。

配对条件共享等生成步数的随机抽样流，不表示它们生成相同文字，也不能消除所有采样波动。只有一个本轮主随机种子；不能将变体数量当成多种子复现。

记录每层最后一个输入词元的状态，尚未生成新思考。4B每条为36×2560，位于层输出、最终归一化之前。保存精确输入词元和ID，用真实聊天模板核对。前一阶段已验证手工采集前向与正常前向一致；本阶段没有用生成解释文字替代内部向量。

## 旧判断的来源

2A先让模型实际判断，再把其选择变成语义一致的简短摘要放回历史。2B增加实际生成的医学判断句：只去掉独立的选项字母行，不人工编写它“应该想什么”，也不回放思考块。

2A的6条初始输出只有答案字母。为使2B的原文条件包含医学判断而非只复制字母，在2B任何输出前，给初始问题增加“一句医学判断”的格式要求；旧版协议、初始输入及源码快照保留为`phase2b_preformat_v1.json`、`phase2b_initial_preformat_v1.jsonl`及`runs/code_snapshots/`。

2B实际初始判断15/16正确。`confirm_dvt_0_initial_no`额外假设负Wells评分不合法，输出资料不足；这个真实回答进入了历史，没有被替换成正确答案。原文分支是按**旧报告数值与当前数值相反**来分配，因此其中3条分支的实际旧判断并非相反的确定判断。主统计保留全部分支，另增加初始判断正确的敏感性统计；新增统计发生在看到这个初始错误之后，不能伪称完全事前分析。

确认该病例标准答案的来源见[来源复核](../protocol/SOURCES.md)。全部原始输出保留。

## 内部读出的修订顺序

1. 2A主要分析中，病例索引0、1训练，2、3测试；同一病例所有变体在同一侧。四个目标分别是当前报告数值方向、当前报告可用性、旧报告数值方向、仅保留旧事实时的旧方向。不能把后两者直接叫作旧信念。
2. 原始词分词器丢弃单个数字，补充了保留数字/负号的词组与字符片段对照；旧结果没有删除。
3. 发现固定C文字分类器会只猜多数类，又增加类别平衡、只在训练病例内部选择C的版本。这是2A方法开发，保留`lexical_controls_v2.json`和`strong_text_controls.json`全部结果。
4. 在2B固定所有读出选择：训练只用2A，测试新2B病例。隐藏状态C=1，显示全部36层；最后一层为事先指定的数字摘要。文字对照继承2A训练病例内部选出的C，不用2B调参。
5. 2A→2B来源读出的平衡正确率降到68.4375%之后，在2C任何输出前另行冻结两种探索修正：使用2A+2B训练，在2C测试；或只用一半2C数值病例训练、另一半测试。原始迁移结果仍作为主要测量结果保留。后一种同模板数值留出不能当作跨模板验证。
6. 2C的主要读出仍按原协议只用2A训练，另做只用2A无历史条件训练的检查。所有方案都分别报告有替代报告和无替代报告；修正读出不能替换主要失败结果。

查看2B完整层曲线后，第26层来源读出达到96.25%，高于预定末层。我们额外固定第26层用于2C验证，见`phase2c_layer_candidate.json`；选择发生在2C生成已经开始、但任何2C读出成绩尚未产生时。它是用2B选择的候选，不能将2B峰值当作无偏验证成绩；预定第36层结果仍全部报告。

分类器训练和缩放只使用对应训练数据；同病例不跨训练/测试。每层都有五组病例内打乱标签的对照。分类器读出的是可恢复信息，不是已验证的因果变量；输入文字本身也含有信息，文字基线必须一起看。

## 统计与判分

保留所有完成记录，停止原因、生成长度和解析失败单列。只有输出正常结束且满足答案格式，才赋予yes/no/unknown；达到预算但没有完成的回答不偷填答案。

比较历史或说明条件时，按病例、数值方向及来源逐条配对，报告变好和变坏的数量。区间按病例骨架重采样5000次，不把同一病例变体当独立样本。只有3—8个骨架时，区间不可靠地代表总体；全部配对差为零时，零宽度区间也不能证明总体等效。

血压始终保持诊断域身份。补充说明、原文历史与中性条件没有做到严格的词元长度匹配，因此差异还可能来自措辞、复述与长度；不能仅凭这些对照唯一归因于模型维护旧判断。

## 从保存数据重新生成分析与图

工作目录为项目根目录。下面都是对已有输出做分析，不会调用模型API：

```bash
.runtime/bin/python src/analyze_phase2.py --run-id phase2_pilot_4b
.runtime/bin/python src/analyze_phase2.py --run-id phase2b_confirm_4b
.runtime/bin/python src/analyze_bp_repairs_phase2.py
.runtime/bin/python src/probe_phase2.py --scope primary
.runtime/bin/python src/probe_phase2.py --scope diagnostic_bp
.runtime/bin/python src/strong_text_controls_phase2.py
.runtime/bin/python src/transfer_phase2.py
.runtime/bin/python src/analyze_answer_control_phase2.py
.runtime/bin/python src/probe_answer_control_phase2.py
.runtime/bin/python src/repair_source_readout_phase2.py
.runtime/bin/python src/plot_phase2.py
.runtime/bin/python src/plot_answer_control_phase2.py
.runtime/bin/python src/plot_readout_repairs_phase2.py
.runtime/bin/python src/analyze_partial_fact_phase2.py
.runtime/bin/python src/summarize_phase2.py
.runtime/bin/python src/write_phase2_casebook.py
.runtime_mlx/bin/python src/verify_phase2_delivery.py
```

重新生成图会更新文件时间或PDF元数据；原交付哈希用于确认交付时的具体文件，不代表每次渲染的PDF字节必须一致。

若要重新推理，用新运行ID，保留现有原始数据。例如：

```bash
.runtime_mlx/bin/python src/mlx_experiment_v2.py \
  --data data/phase2b_current.jsonl \
  --run-id phase2b_reproduction_20261118 \
  --model-dir .models/Qwen3-4B-8bit \
  --model-manifest protocol/qwen3_4b_8bit_snapshot.json \
  --max-tokens 2048 --batch-size 16 --capture
```

这个命令重跑的是**已冻结历史内容**下的当前判断。如果也要重新生成旧判断，应另建初始运行和对应的数据版本再组装历史；不能将新旧结果混接后当成同一条轨迹。

## 历史与交付文件

阶段1、1B原始输入、引擎、结果和图不覆盖。阶段1B交付时的README、论文逻辑、阶段计划、内部测量说明已按原哈希归档到`protocol/archives/phase1b_delivery/`，当前入口文档可以更新到新阶段。

`protocol/phase2_delivery.json`由最终校验脚本生成，记录每个实际运行的条数、正确数、生成词元数、输入和代码哈希、精确词元一致性、内部状态形状及历史文件完整性。它是最终完成状态的依据，不用正在运行的日志代替完成记录。

## 本轮追加的阶段3小型预试验

2C的32条有替代报告记录提供实际当前回答。阶段3首次32条撤回R2，随后完整32条换第二随机种子复测；另外三种修正各32条，共160次后续生成。三种修正为：更清楚的更新句、明确重申R1既有状态、删除前一个assistant回答。修正方案在看过首次3条错误之后冻结，不能称作独立确认。没有新增病例骨架。

预测器只用当前输入、当前实际回答和当前生成前状态；未来输入及未来回答不进入预测特征。训练与测试各4个数值骨架、16条轨迹。预测目标为实际未来回答是否改变，不是预设应改答案。隐藏状态固定C=1；文字C只在训练骨架内选；第36层为主要摘要，第26层是此前选定的次要检查。所有层显示，不按未来测试成绩选层。

第一次分析的病例bootstrap抽样偶尔只含一个目标类别，二分类平衡正确率在这种样本中不适用。发现sklearn警告后排除了这些抽样，并记录排除数；原分析输出及源码均归档。修订见`protocol/phase3_analysis_amendment.json`。主要点估计和测试预测没有变化；仅4个留出骨架的区间不能作可靠总体推断。

```bash
.runtime/bin/python src/analyze_phase3_future.py
.runtime/bin/python src/analyze_phase3_repairs.py
.runtime_mlx/bin/python src/verify_phase2_delivery.py
```

最后一个校验入口的名称沿用阶段2，但交付清单包含本轮阶段2以及阶段3预试验的全部11次运行。阶段3第二种子只改变后续生成，复用同一份当前回答和状态；不把它说成从头独立复现整条轨迹。
