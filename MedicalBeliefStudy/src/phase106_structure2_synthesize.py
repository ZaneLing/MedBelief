"""Create result-grounded plain-language delivery and the updated paper narrative."""
from structure2_analysis import *

def pp(s):return f'{100*s["mean"]:+.2f}个百分点，95%区间[{100*s["low"]:+.2f}, {100*s["high"]:+.2f}]'

def main():
    assert read(DOC/'FINAL_VALIDATION.json')['complete'];s=read(ROOT/'results/49_structure_confirmation/summary.json');t=read(ROOT/'results/50_structure_trajectories/summary.json');dev=read(ROOT/'results/47_structure_search/summary.json');train=read(ROOT/'results/48_adapter_training/summary.json');p=s['primary_candidate'];prune=read(RUN/'pruning_selection.json')['selected']['name'];params=s['parameters'];base=params['baseline']['parameters'];reduction=100*(1-params[p]['parameters']/base);pc=next(r for r in s['primary_comparisons'] if r['candidate']==p)
    def row(n,co):return next(r for r in s['per_method'] if r['candidate']==n and r['dataset']=='all' and r['condition']==co)
    def counts(n):return [row(n,co)['correct'] for co in ['neutral','wrong']]
    def timer(n,k):return next(r['ratio'] for r in s['timing'] if r['candidate']==n and r['metric']==k)
    pre=timer(p,'prefill_seconds');decode=timer(p,'fixed12_decode_seconds');wall=timer(p,'actual_answer_seconds');bcounts=counts('baseline');pcounts=counts(p);rcompose=counts(prune);acounts=counts('full_adapter16');deepcounts=counts('exit20_adapter16');bridgecounts=counts('exit20_bridge64');strict={r['candidate']:r for r in s['source_sensitivity'] if r['filter']=='strict_source_and_similarity_keep'};nstrict=strict[p]['n'];none=round(s['input_control'][0]['none_accuracy']['mean']*400)
    ns=s['normalized_scoring'];npc=next(r for r in ns['comparisons'] if r['candidate']==p);nby={r['candidate']:r for r in ns['per_method']};none=ns['no_history_correct'];acounts=[nby['full_adapter16'][k] for k in ['neutral_correct','wrong_correct']]
    verdict='这轮选出了可运行的压缩路线：保留层数、缩窄后半段；实际模型更小，回答耗时更短。'
    verdict+='所选方案实际减少了'+f'{reduction:.2f}%'+'参数。严格字符串评分显示的准确率收益，在清理空格、冠词和标点差异后明显缩小。'
    scoring=f'相对原自由生成模型，原预定逐字评分的平均增益为{pp(pc)}，Holm p={pc["p_holm"]:.4g}；统一表面写法后为{pp(npc)}，敏感性六项内Holm p={npc["p_holm"]:.4g}。同一压缩模型加候选约束的{ns["constraint_repairs"]}个严格评分修复中，{ns["constraint_repairs_already_correct"]}个原回答已经写出了正确候选的规范化名称。评分规范化是在主结果后增加的敏感性检查，原方案选择及原评分结果均保留。'
    matched=s['matched_output_control'];mct=matched['difference'];matchedtext='补充同样输出规则的完整模型后，压缩模型相对它的平均差为'+pp(mct)+'。'
    if mct['low']>0:matchedtext+='这项追加解释性对照出现小幅优势，主要在错误历史条件；需要新增病例确认，尚不足以宣布医学能力普遍提高。'
    elif mct['high']<0:matchedtext+='这项对照显示压缩付出了准确率代价。'
    else:matchedtext+='这项对照尚未确认裁剪本身额外提高准确率；区间跨0也不等于已证明两者等效。'
    mpre=next(r['ratio'] for r in matched['timing'] if r['metric']=='prefill_seconds');mwall=next(r['ratio'] for r in matched['timing'] if r['metric']=='actual_answer_seconds');matchedspeed='在两者使用相同候选约束的直接配对中，读取病例耗时比为'+fmt(mpre)+'，实际回答耗时比为'+fmt(mwall)+'（压缩/完整）。'
    table='| 方法 | 规范化中性命中/400 | 规范化错误历史命中/400 | 参数数 |\n|---|---:|---:|---:|\n'
    for n in ['baseline',prune,'full_adapter16','baseline_constrained',p]:
        a,b=nby[n]['neutral_correct'],nby[n]['wrong_correct'];table+=f'| {LABELS[n]} | {a} | {b} | {params[n]["parameters"]:,} |\n'
    fulltable='| 方法 | 规范化中性/错误历史 | 逐字中性/错误历史 | 逐字合法中性/错误历史 | 参数减少 |\n|---|---:|---:|---:|---:|\n'
    for cfg in read(RUN/'confirmation_selection.json')['configurations']+[matched['control']]:
        n=cfg['name'];a,b=counts(n);fulltable+=f'| {LABELS[n]} | {nby[n]["neutral_correct"]}/{nby[n]["wrong_correct"]} | {a}/{b} | {row(n,"neutral")["listed"]}/{row(n,"wrong")["listed"]} | {100*(1-params[n]["parameters"]/base):.2f}% |\n'
    speed=f'读取完整病例的耗时比为{fmt(pre)}；固定生成12个词元为{fmt(decode)}；实际生成完整答案为{fmt(wall)}。比值低于1表示更快。这是Apple M2 Pro上6例的交错配对实测，区间按病例估计。'
    nsp,nsb=nby[p]['strict_subset'],nby['baseline']['strict_subset'];stricttext=f'严格文本与近重复子集保留{nstrict}例。规范化评分下，主方案中性/错误历史答对{nsp["neutral_correct"]}/{nsp["wrong_correct"]}例，原模型为{nsb["neutral_correct"]}/{nsb["wrong_correct"]}例；两种历史平均差为{pp(nsp["difference"])}。'
    output=''
    for r in s['output_control']:output+=f'- {r["condition"]}：相对同样的压缩骨干，约束将{r["repaired_from_invalid"]}个非法名称修复为正确答案，将{r["repaired_from_listed_wrong"]}个合法错误候选改成正确答案，损坏{r["damaged"]}个原本正确的答案。原本合法时，有{r["changed_when_raw_listed"]}例换了病名。\n'
    trajectory='| 方法 | 历史 | 最终同原模型/24 | 每轮都同原模型/24 | 最终同但中途不同/24 |\n|---|---|---:|---:|---:|\n'
    for r in t['aggregate']:trajectory+=f'| {LABELS[r["candidate"]]} | {r["condition"]} | '+ ' | '.join(str(round(24*r[k]['mean'])) for k in ['normalized_final_agreement','normalized_entire_path_agreement','normalized_same_final_different_earlier'])+' |\n'
    eq=t['output_rule_state_equivalence'];eqtext=f'对同一压缩骨干的{eq["prefix_conditions"]}个前缀条件，增加输出约束前后，读完证据时全部层状态最大绝对差为{eq["all_layer_max_abs"]:.6g}，输出端向量最大差为{eq["readout_max_abs"]:.6g}，原始病名有{eq["changed_actual_names"]}个条件不同，规范化候选身份有{eq["changed_normalized_choices"]}个条件不同，其中{eq["normalized_invalid_to_valid"]}个是无法匹配变为合法候选，仅{eq["normalized_valid_choice_changed"]}个是在两个合法候选间改变。这里检验的是开始续写前的状态，后续生成状态可能分岔。约束还改变了分数归一化；这类分数变化不能单独当作内部医学信念更新。'
    top=f'''# 这轮实验回答了什么

**{verdict}**

实际完成了22种配置的开发比较，并将7种配置放到固定的400例上确认。新收集到本实验的880例来自MedQA与MedMCQA：400例训练、80例选方案、400例确认。模型是Qwen3-1.7B，实际生成完整候选名称。这里统计的是诊断相关考试题；少数来源答案为检查特征或病理机制，已单列做[答案类型敏感性](ANSWER_SCOPE.md)。

之后补充了开发阶段已有的完整模型候选约束配置作为解释性对照，形成同病例的2×2比较。它不是重新选择主方法的步骤。**{matchedtext}**

{table}

开发集预先选定的方案是：**{LABELS[p]}**。它保留28层，把后12层MLP的通道从6144减为3072，再用候选列表约束输出。参数从{base:,}降到{params[p]['parameters']:,}。它仍是约15亿参数的模型，小适配器不能单独替代整个模型。

**评分核查：**{scoring}

例如来源答案末尾多一个空格，模型正确写出病名也会被原评分算错。现在正文优先使用统一写法后的候选命中率。[具体规则与原文](SCORING_AUDIT.md)。{stricttext}

**速度：**{speed}

{matchedspeed} 同规则的读取病例及固定长度解码区间较宽；约15%的实际回答耗时下降仅代表这6例本机测量。

**适配器没有成为这轮的解决办法。** 完整模型加67600参数的小适配器，规范化命中数为{acounts[0]}/{acounts[1]}；压缩骨干的适配器在开发阶段越训练越差，最终按规则退回零初始化。删掉8层后加小适配器，中性和错误历史分别答对{deepcounts[0]}/400、{deepcounts[1]}/400；状态桥接两条件分别为{bridgecounts[0]}/400、{bridgecounts[1]}/400。这里评价的是本轮训练设置下的输出端模块，不能推广为所有适配器都无效。

**错误也受到输入和输出的影响。** 原模型完全去掉旧诊断历史后，规范化命中{none}/400。对相同压缩结构增加候选约束，修复情况如下：

{output}
上述修复按原逐字评分计算，其中18/28是写法差异。它们支持把“知识不够”“历史牵引”“输出失败”分开研究。可压缩不等于原部件有害；修改后偶尔答对也不等于已经证明模型原先掌握了完整医学推理。

先看[一个病例的逐轮中文解释](ONE_CASE_EXPLAINED.md)，再看[完整分析与论文主线](RESULTS_AND_STORY.md)，需要逐个数字时看[400例结果](../results/49_structure_confirmation/RESULTS.md)。[22种配置](../results/47_structure_search/RESULTS.md)和[全部24例轨迹](../results/50_structure_trajectories/RESULTS.md)保留失败例。API费用：**0美元**。
'''
    (DOC/'START_HERE.md').write_text(top)
    story=f'''# 医学信念：输入、结构、输出分别影响什么

## 1 本轮判断

{verdict}

{scoring} 单纯通道压缩与输出约束的效果必须分开；本轮没有得到“只要增加适配器就显著提升诊断”的结果。

用户提出的解释是：模型的错误可能来自输入、输出或内部多余计算，而不完全是不会诊断。本轮实际修改这些环节，比较哪些错误被修复、哪些原正确答案被损坏，以及计算量是否下降。

## 2 数据和操作

新增880个原题病例，两个来源各440。400训练、80开发、400确认，病例ID与前540例分离；数据集原始划分与本实验分组不是一回事。这里是诊断相关医学考试题，最终答案来自源题库；不是模型编造病例，也不是临床随访。

每例四个原始候选、同一组患者事实。中性历史写“尚未确定”，错误历史固定放入一个错误候选。每轮重新输入累计证据和固定历史，不将模型上一轮回答自动回填。中间前缀没有独立唯一诊断真值；最终完整材料才按来源答案评分。

模型训练参数不会随每条证据到来自动变化。逐轮记录的是激活、候选支持和实际诊断；本轮结构裁剪或小模块训练是在测试前完成的。

题干含“诊断”不保证选项都是病名，例如ASCA positivity是检查特征，另有题干与分子机制选项不吻合。已将9个明确条目单列，并在366例基础上另做来源答案类型敏感性；不将400例全部称为纯疾病命名。[范围审计](ANSWER_SCOPE.md)。

初始筛选漏检了28例来源问题，后续只根据原文复核，原训练和方案选择保留。原400例确认、386例来源文本子集、366例再去除近重复子集分别报告。[源文本审计与分词修正](SOURCE_AUDIT.md)。

## 3 试过哪些结构与小模块

22种配置覆盖整层截断、局部删层、删MLP、全层/晚层通道裁剪、注意力头组裁剪、旧两MLP线性替换、晚层贡献缩放、层间对比解码、5个输出端适配器、前20层到28层的教师状态桥接，以及3个候选约束对照。只用80例开发结果选择方法，随后冻结7个确认配置。

开发比较中，全层MLP保留75%通道削减15.36%参数，中性/错误历史仅答对33/18例；后12层MLP通道减半削减13.16%，答对54/43例。相近的参数节省，不同位置的代价明显不同。直接前20层的合法输出为0/160；强制它在候选中输出以后答对22/19例，仍远低于完整模型55/39例。

这支持优先研究**保留深度、局部缩窄**，而不能把大量尾层直接视为无用。以上是开发结果，最终确认如下。

## 4 独立400例的真实名称生成

每个格子均以400例为分母。规范化仅清理表面写法，要求唯一匹配四个原候选之一，不采用同义词模型或真值驱动解析。[评分核查](SCORING_AUDIT.md)。

{fulltable}

![两种评分](../results/49_structure_confirmation/figures/scoring_audit.png)

最后一行完整模型候选约束是主结果之后追加的解释性对照，前七项为冻结的确认配置。{matchedtext}

![原逐字评分与成本](../results/49_structure_confirmation/figures/confirmation_overview.png)

{stricttext}

原逐字评分中，原模型与纯压缩的两条件答对数分别为{bcounts[0]}/{bcounts[1]}和{rcompose[0]}/{rcompose[1]}；规范化数值见上表。这表明削减计算会同时修复和损坏病例，不能只统计改善例子。每种方法的修复、损坏、来源分层、配对区间与多重校正见[确认报告](../results/49_structure_confirmation/RESULTS.md)。

## 5 小模块为什么没有直接变成更强的诊断器

4096参数的逐维适配器将开发损失从2.178降到1.649，但中性答对从55/80降到50/80，错误历史仍39/80。67600参数适配器选择第100步；更大264256参数版本与压缩骨干上的67600参数版本均退回第0步。退回零初始化意味着没有生效的训练改动，不能称为适配器修复成功。

前20层的适配器使开发损失从11.161降到4.699；266240参数桥接使内部状态均方误差从8.588降到2.281。两者都没有恢复到原模型的完整诊断表现。**拟合答案文字更容易、内部向量更像原模型，与真实诊断更准，是不同的成功标准。**

所有骨干权重冻结；完整与压缩骨干使用相同400例、相同67600参数模块、相同更新设置。最终直接比较见[训练与结构配对图](../results/49_structure_confirmation/figures/training_vs_structure.png)。本轮训练仍含9例后续标记的来源问题，数据规模和当前训练目标限制了对适配器的广泛判断。[训练细节与曲线](../results/48_adapter_training/RESULTS.md)。

## 6 哪些错误来自输入或输出

![结构与输出规则分开](../results/49_structure_confirmation/figures/matched_output_control.png)

{matchedtext} 同400例的四格为完整/压缩骨干×自由/约束生成，进一步区分裁剪效应与输出约束效应。追加对照单独登记，未混入原六项确认检验。

去掉所有旧诊断历史，原模型答对{none}/400；同患者事实下，规范化评分的错误历史条件为{nby['baseline']['wrong_correct']}/400。这里改变了历史内容及对应消息，不能单独称为一种纯内部知识测量。

相同压缩骨干增加输出约束，以下按原逐字评分统计：

{output}
约束只使用已给出的四个候选，不使用哪个正确；它可能修复拼写、JSON及表外病名。其中18/28个严格修复原本已有正确的规范化名称。其余10个仍包含错拼、简称和疾病用词变化，不能全称为医学推理被纠正。未做监督权重更新的变换能改变对错，说明最终错误对输入和计算路径敏感；所有方法仍答错也不能证明模型内部绝对没有相关信息。

将“任一方法答对”的病例合并，需要知道真值后选择方法，仅用于错误可恢复性分析，不能宣称实际系统准确率。结构选型本身用了80例来源答案，因此也不将整个流程称为无监督。

## 7 参数与真实速度

{speed}

{matchedspeed}

参数减少{reduction:.2f}%，主要来自真实切除MLP矩阵通道。保留28层意味着注意力层数和KV缓存层数不变。读取病例、固定长度缓存生成、实际回答分别测量；无效答案过长也会增加实际回答时间。全部测速明细见[确认报告](../results/49_structure_confirmation/RESULTS.md)。

## 8 最终相同，判断过程是否也相同

[血管性痴呆病例的逐轮解释](ONE_CASE_EXPLAINED.md)用同一评分公式比较两种结构：完整模型曾经选对，后来离开；缩窄模型在后续证据后重新回来。它是结果后挑出的说明例，以下用全部预定病例汇总。

确认前固定24例，两个来源各12；共{t['prefixes']}个累计证据前缀，3种配置×2种历史，记录{t['observations']}个轮次条件。来源与近重复严格子集保留{t['strict_cases']}例。

以下一致性以规范化候选身份计算。

{trajectory}

![终点与全过程](../results/50_structure_trajectories/figures/trajectory_preservation.png)

每轮保存实际名称、完整候选序列支持、长度归一化敏感性分数、每层输出位置的2048维向量，以及输出适配器前后向量。向量距离只告诉我们改变多大；疾病方向要结合候选支持和实际名称。两个无效回答不算诊断一致，也不直接算疾病改变；过程不同要求至少一轮两个合法候选实际不同。[全部病例与原始数据](../results/50_structure_trajectories/RESULTS.md)。

{eqtext}

## 9 放回论文的三层逻辑

第一层观察同一患者事实如何受旧诊断影响，结合证据增加与顺序改变。第二层通过逐层测量、激活与通路干预区分证据处理和作答位置。第三层真正改变模型，检验可压缩性、答案恢复与证据更新路径是否一致。

上一轮所选注意力头在错误历史的编码选择中有益，正确历史利用却受损，完整名称生成没有同样改善。本轮又看到训练损失和状态拟合不能替代实际诊断检验。两轮共同要求把“内部可读”“计算有作用”“最终答对”和“过程保留”分别测量，而非只用一张读出图证明医学信念。

适配器、剪枝和线性替层均有直接先例；本研究的论证应围绕医学证据、旧诊断利用和实际作答之间的关系。[相关方法](RELATED_METHODS.md) · [三层论证架构](../acl_paper/v10_adapters/ARGUMENT_STRUCTURE.md) · [整合中文稿](../acl_paper/v10_adapters/PAPER_ZH.md)。

## 10 复现与核验

[复现命令](REPRODUCE.md) · [冻结配置](../runs/structural_v2/confirmation_selection.json) · [最终运行核验](FINAL_VALIDATION.json)。原模型权重散列保持不变；所有失败配置、原始生成与来源审计保留。本轮模型API费用0美元。
'''
    (DOC/'RESULTS_AND_STORY.md').write_text(story)
    paperdir=ROOT/'acl_paper/v10_adapters';paperdir.mkdir(exist_ok=True)
    paper=f'''# 模型有医学信念吗？从证据更新到诊断计算的可压缩性

## 摘要

模型给出错误诊断，可能涉及知识、历史利用和输出过程。本研究沿累计医学证据追踪候选支持与内部计算，并用实际干预和结构改造检验这些环节。前期在MedQA、MedMCQA与MMLU的540题中观察历史效应，并在94例与两个模型配置上展开内部分析。新增研究从前期病例之外选取880题，400训练、80开发、400确认；对Qwen3-1.7B比较22种开发配置并冻结7种确认配置。预定主方案{LABELS[p]}使参数减少{reduction:.2f}%。逐字评分初见准确率增益，但写法核查发现其中包含空格、冠词及标点错误；规范化后相对完整模型的平均差为{pp(npc)}，敏感性六项内Holm p={npc['p_holm']:.4g}，未确认医学候选选择改善。补充相同输出约束后，压缩减完整的配对差为{pp(mct)}（追加解释性对照）。训练损失下降及教师状态拟合改善未自动恢复完整诊断生成。固定24例的全部证据前缀进一步区分终点保持和更新过程保持。结果将医学信念的证据响应、历史利用、作答转换与计算可替代性联系起来。

## 1 引言

一个患者逐步提供关节症状、既往情况、查体和化验，原题答案是系统性红斑狼疮。中性历史下，模型一直选择这一诊断；加入“播散性淋球菌关节炎”的旧判断后，它第2组事实一度转回红斑狼疮，第6组后又离开，最后仍选择旧病名。完整病例只记录一个错误，逐轮轨迹却显示了接近、离开和保持的过程。[完整示例](../../results/34_multisource_depth/cases/medqa_train_09811.md)。

本文将医学信念操作性地定义为：模型对候选诊断随上下文改变的支持，以及参与形成这种支持的内部计算。我们依次追问：证据与旧诊断怎样改变选择；影响通过什么内部位置和连接传播；改变这些计算后，能否保持或改善诊断，同时缩减成本。

这一顺序使内部观察接受行为检验。能读出疾病并不充分证明模型可靠输出该疾病；局部干预提高一种选择分数，也不充分证明完整病名生成改善。结构修改进一步检验计算可替代性，但不能预设复杂部件必然有害。

## 2 数据与测量

前期540题来自三个公开考试来源，保留原文、原选项与来源答案；旧版文本审计形成520题敏感性队列。新增880题来自MedQA和MedMCQA各440题，分为400训练、80开发、400确认，与旧540题ID分离。本轮运行中扩大源文本复核，得到386题文本确认子集、366题再排除0.80近重复的子集。训练和开发仍保留最初分组，新增审计不重新选型；旧版520题不冒称已经通过本轮新审计。

病例筛选依据诊断问题，但部分来源候选是检查特征、病原体或分子机制。9个明确条目单列，366例之上再做来源答案类型敏感性；该审计不等同于完整医学本体标注。

每题四个候选；每轮输入累计来源证据并重新前向传播。历史保持固定，不自动回填模型上一轮输出。中性历史与错误历史保持同一消息格式，另测试完全去除历史。最终来源答案用于评分；中间前缀没有独立唯一真值。新增预定指标为实际生成完整候选名称的逐字命中，无法解析或表外名称计错。结果后发现该指标将部分正确病名的表面写法差异计错，因此另登记统一规范化敏感性：清理大小写、冠词、空格和表面标点，并要求唯一匹配全部四候选之一；不做医学同义词或模糊匹配。正文区分两种评分。序列分数仅在给定候选中归一化，不解释为临床概率。

独立统计单位是病例。每病例先平均两种历史的正确性，再对400病例做配对bootstrap与符号随机化检验；六项相对完整模型比较做Holm校正。三项训练/结构比较单独构成Holm组。来源质量子集为运行后源文本敏感性分析。详细提示、数据划分、训练参数和代码见[复现方法](../../research_v6_adapters/REPRODUCE.md)。

## 3 表层：证据响应与历史牵引

前期540题的完整候选评分，中性历史答对302例，错误历史232例，未采纳病名242例；实际名称生成分别为297与229例。病名轮换控制显示，未采纳病名的具体内容也会影响候选支持。最后一组证据在两种历史下的作用仍有正相关，同时126/540题出现预定阈值以上的反向更新。两者应分开：旧病名改变分布的位置，新事实仍可在其上继续推动判断。

证据组倒序后，总准确数仍为315/540，但93题改变了首选，包含36题对转错、36题错转对。总分不能代替病例层面的诊断过程。[行为、顺序与全轨迹](../../results/37_behavior_checks/RESULTS.md)。

## 4 内部：读出、通路和实际作用

前期研究区分患者事实位置、诊断作答位置和最终词表输出。路径干预支持历史病名可通过直接通向作答位置的连接影响选择；部分读出跳变又可由尺度变化放大。因此，内部读数的变化要与真实输出干预配对。[内部分析与跨配置复核](../../results/34_multisource_depth/RESULTS.md)。

在另130题中，固定8个头的干预使错误历史的编码选择命中从35.00%提高到42.69%，优于三个同层对照；当历史直接给出来源答案时，却从81.92%降至75.77%。完整候选生成在同130题的错误历史下由54题降至48题。延长头干预没有恢复名称收益。由此，这组计算参与历史使用，作用取决于历史内容与作答接口；不能简单标记为无用。[匹配对照与实际生成](../../results/46_structural_head_followup/RESULTS.md)。

旧两MLP的小型线性替换曾减少4.38%参数并补回直接删除失去的部分诊断功能。新增研究扩大到多种删减与训练方式，同时将实际名称生成作为确认指标。

## 5 结构检验：局部宽度与尾部深度

开发阶段比较整层截断、局部删层、删MLP、MLP通道裁剪、注意力组裁剪、线性替换、晚层贡献缩放、静态层间对比解码、5个小适配器、尾层桥接和候选约束，共22配置。

相近压缩比例下，全部MLP保留75%通道减少15.36%参数，开发中性/错误历史答对33/18题；后12层MLP通道减半减少13.16%，答对54/43题。仅前20层无法生成合法候选；加候选约束后为22/19题，完整模型为55/39题。这一开发比较支持优先选择保留深度、局部缩窄的路线。它不证明其他位置或其他剪枝算法普遍不可行。

确认前冻结的主候选为{LABELS[p]}；固定包含完整模型、原压缩骨干、完整/压缩骨干相同小适配器、前20层适配器、前20层桥接及开发最优其余方法。原型为本机MLX实现，MLP矩阵被真实切小，原模型文件保持不变。[全部开发尝试](../../results/47_structure_search/RESULTS.md)。

## 6 实际诊断、训练与成本

{fulltable}

最后一行为主结果后追加的匹配输出对照；原先冻结的七项及六项Holm检验保持不变。

![独立确认](../../results/49_structure_confirmation/figures/confirmation_overview.png)

{verdict}

{scoring}

![评分审计](../../results/49_structure_confirmation/figures/scoring_audit.png)

{stricttext}

{matchedtext} 完整/压缩骨干与自由/约束生成形成2×2分析；追加完整模型约束对照在原主结果产生后登记，属于解释性估计。[四格比较](../../results/49_structure_confirmation/figures/matched_output_control.png)。

完整骨干和压缩骨干的67600参数输出适配器使用相同训练病例和优化设置。完整模型确认答对{acounts[0]}/{acounts[1]}题；压缩适配器按开发损失退回零初始化，不能称为训练修复。较大264256参数适配器也退回第0步。4096参数逐维模块虽降低开发损失，却没有提高开发准确率。尾层适配器确认答对{deepcounts[0]}/{deepcounts[1]}题，状态桥接为{bridgecounts[0]}/{bridgecounts[1]}题。[训练曲线](../../results/48_adapter_training/RESULTS.md)。

去除历史后，完整模型答对{none}/400。对相同压缩骨干增加候选约束，原逐字评分的修复来源分解如下：

{output}
其中18/28个严格修复在规范化后已正确匹配候选，不能当成新获得的疾病判断能力。

未进行监督权重更新的变换仍能改变对错，说明最终表现对输入和计算路径敏感；结构选型使用了开发答案，整个流程并非无监督。学习适配器后的变化还可能包含新学到的医学对应关系。

{speed} 不能仅凭参数量推断实际回答更快，也不能将较短的错误回答当作有用的诊断加速。配对统计、输入控制、全部速度与来源子集见[确认结果](../../results/49_structure_confirmation/RESULTS.md)。

{matchedspeed}

## 7 过程检验：终点与更新路径

在确认结果产生前固定24题，逐组提供全部{t['prefixes']}个累计前缀。每轮记录完整名称、候选序列支持、各层输出位置状态和输出适配前后向量。三种配置与两种历史共{t['observations']}个条件；文本与相似度严格子集为{t['strict_cases']}题。

以下一致性以规范化候选身份计算。

{trajectory}

![更新过程](../../results/50_structure_trajectories/figures/trajectory_preservation.png)

最终答案一致与每轮判断一致是不同要求。中途变化既可能纠正先前判断，也可能离开最终来源答案；缺少独立中间真值时，不将所有变化标成医学错误。内部余弦距离量化改动幅度，疾病方向由候选支持和实际生成共同呈现。全部病例和状态文件均保留。[24题全图谱](../../results/50_structure_trajectories/RESULTS.md)。

{eqtext}

## 8 讨论

本研究给出一个分层解释框架。证据与旧诊断共同塑造候选支持；特定连接参与历史利用；作答形式决定内部改动能否成为可观察的正确答案。缩减某些计算可能保留相近终点，但不能据此将原部件称为有害，或认定内部更新过程完全相同。

新增结构结果必须同时通过实际名称、严格来源子集、病例层面的修复与损坏、以及真实时延检验。内部拟合误差和训练损失是中间指标，不能替代实际诊断。将所有方法正确题取并集只是知道真值后的可恢复性上界，不是一个可运行系统。

范围限定在英文考试诊断题与当前训练设置。新增裁剪和适配器仅在Qwen3-1.7B测试；前期4B证据对应历史与路径实验，不证明本轮压缩规律跨规模成立。源文本复核发生在确认运行中，原训练保留来源问题；子集结果用于检验敏感性，不掩盖这一先后关系。

## 9 相关工作与贡献定位

瓶颈适配器已有[Houlsby等](https://proceedings.mlr.press/v97/houlsby19a.html)，低秩更新已有[LoRA](https://arxiv.org/abs/2106.09685)，结构裁剪和修复已有[LLM-Pruner](https://arxiv.org/abs/2305.11627)。[ReplaceMe](https://arxiv.org/abs/2505.02819)已有用线性操作替层的研究，[DoLa](https://arxiv.org/abs/2309.03883)已有层间对比解码。本文使用这些方法脉络作为机制检验工具，不宣称首次提出小适配器、剪枝或线性替层。

本文的论证集中于医学证据、旧诊断利用、内部计算与实际作答之间的联系，以及结构简化对终点和更新过程的不同影响。医学信念相关研究的完整比较见[既有相关工作](../v08_multisource/RELATED_WORK.md)，新增方法的实现边界见[本轮相关方法](../../research_v6_adapters/RELATED_METHODS.md)。

## 10 可复现材料

[协议](../../research_v6_adapters/PROTOCOL.md)、[代码与命令](../../research_v6_adapters/REPRODUCE.md)、[源文本审计](../../research_v6_adapters/SOURCE_AUDIT.md)、[数据与权重核验](../../research_v6_adapters/FINAL_VALIDATION.json)。本轮全部使用本地Apple GPU，模型API费用0美元。本稿是随实验更新的中文研究稿；前期英文排版稿不自动包含本轮结果。
'''
    (paperdir/'PAPER_ZH.md').write_text(paper);(paperdir/'README.md').write_text('# v0.10 医学信念、结构裁剪与小适配器\n\n[整合中文研究稿](PAPER_ZH.md) · [三层论证架构](ARGUMENT_STRUCTURE.md) · [用人话读结果](../../research_v6_adapters/START_HERE.md) · [完整实验](../../research_v6_adapters/RESULTS_AND_STORY.md)\n\n新增880例、22种开发配置、7种固定确认配置，另补1种匹配输出对照；400例确认、366例严格敏感性；24例全部证据轮次。所有模型API费用0美元。旧稿与全部失败结果保留。\n')
    print(json.dumps(dict(complete=True,primary=p,parameter_reduction=reduction,strict_primary_difference=pc['mean'],normalized_primary_difference=npc['mean'],files=['START_HERE.md','RESULTS_AND_STORY.md','PAPER_ZH.md','README.md']),ensure_ascii=False))
if __name__=='__main__':main()
