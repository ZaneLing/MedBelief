"""Build human-readable synthesis from completed, auditable result files."""
import json,csv,re
from pathlib import Path
from phase41_multisource_analyze import ROOT,DATA,read,fmt,obs,top

R=ROOT/'research_v4';P=ROOT/'acl_paper/v08_multisource'
def percent(s):return f'{s["mean"]*100:.1f}%'
def number(s):return round(s['mean']*s['n'])
def pp(s):return f"{s['mean']*100:.2f}个百分点，95%CI [{s['low']*100:.2f}, {s['high']*100:.2f}]"
def support(q):return '<0.01%' if q<.0001 else f'{q*100:.2f}%'
def main():
 assert read(R/'FINAL_VALIDATION.json')['complete']
 a=read(ROOT/'results/32_multisource_belief/summary.json');b=read(ROOT/'results/34_multisource_depth/summary.json');q=read(ROOT/'results/38_text_quality/summary.json');nc=read(ROOT/'results/41_name_counterbalance/summary.json');mp=read(ROOT/'results/40_final_mlp/summary.json');ng=read(ROOT/'results/40_final_mlp/normalization_summary.json');bh=read(ROOT/'results/37_behavior_checks/summary.json')
 route_text=(R/'ROUTE_FINDING.md').read_text().strip();cases={c['case_id']:c for c in map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines())};c=cases['medqa_train_09811'];alltab=a['tables']['all:all'];strict=q['behavior']['all:all']
 title='模型有医学信念吗？从逐条证据到内部传递，再到诊断形成'
 parts=['# '+title+'\n\n2026-11-20 · 本轮实验结果与论文主线 · 所有计划阶段已完成，API费用 **0美元**。\n']
 parts.append('## 先看一个完整的例子\n\n一位患者逐步提供关节症状、既往情况、查体和化验。原题最终答案是**系统性红斑狼疮**。我们保持患者原文不变，只改变上下文中先前的诊断。\n\n没有先前定论时，模型沿13组输入一直选择红斑狼疮。先前被写成“播散性淋球菌关节炎”时，它第2组一度转回红斑狼疮，第6组后又转回旧病名，直到最后的化验输入仍未改回。\n\n| 原文组 | 中性历史的首选 | 错误历史的首选 | 错误历史下对红斑狼疮的相对支持 |\n|---:|---|---|---:|\n')
 trans={'Systemic lupus erythematosus':'系统性红斑狼疮','Disseminated gonococcal arthritis':'播散性淋球菌关节炎'}
 for t in [1,2,5,6,13]:
  n=obs(c,'neutral',t);w=obs(c,'wrong',t);parts.append(f'| {t} | {trans.get(c["candidates"][top(n)],c["candidates"][top(n)])} | {trans.get(c["candidates"][top(w)],c["candidates"][top(w)])} | {support(w["q_sequence"][c["gold_index"]])} |\n')
 parts.append('\n这里的支持只在本例四个候选里比较。中途没有独立诊断标签，所以只描述模型怎样移动；完整输入才用原题答案评价。[查看该例全部证据、四病名曲线与逐层图](../results/34_multisource_depth/cases/medqa_train_09811.md)。\n\n![四病名与逐层变化](../results/34_multisource_depth/cases/medqa_train_09811_all_candidates.png)\n\n这是一例说明，下面的结论来自全部病例，不按异常大小挑选。\n')
 parts.append('## 数据已经扩到什么程度\n\n| 来源 | 新增病例 | 中性历史答对 | 错误旧诊断答对 | 只提及未采纳病名答对 |\n|---|---:|---:|---:|---:|\n')
 for ds in ['MedQA','MedMCQA','MMLU','all']:
  v=a['tables'][ds+':all'];parts.append(f'| {("合计" if ds=="all" else ds)} | {v["accuracy_neutral"]["n"]} | {number(v["accuracy_neutral"])} | {number(v["accuracy_wrong"])} | {number(v["accuracy_mention"])} |\n')
 parts.append(f'\n这是 **540例、三个公开考试来源**，保留原文、原选项和来源答案；没有让模型编造病例。主模型Qwen3-1.7B。全部540例记录加入最后一组前后的28层；94例展开全部537个累计前缀，并在同94例上复核4B配置。\n\n文字审计标出20例任务尾语或缺失引用材料；严格520例中，中性、错误历史、仅提及分别答对 **{number(strict["accuracy_neutral"])}/{number(strict["accuracy_wrong"])}/{number(strict["accuracy_mention"])}** 例，历史效应保持。内部图谱严格子集为92例；确认内部子集为47例。所有原540例结果仍保留。[数据来源与审计](DATA_CARD.md) · [严格子集结果](../results/38_text_quality/RESULTS.md)。\n')
 parts.append('## 结果一：旧病名会影响判断，即使没有被写成已确定诊断\n\n在540例中，错误历史相对中性历史的完整病名准确率变化为 **'+pp(alltab['wrong_minus_neutral_accuracy'])+'**；仅提及条件相对变化为 **'+pp(alltab['mention_minus_neutral_accuracy'])+'**。实际贪心生成也从 **297/540降至229/540**，因此现象不只出现在候选评分表中。MMLU样本较少，其来源单独估计区间较宽。\n\n为进一步检查病名本身的选择性作用，我们保持字段格式不变，把四个候选轮流放进“未采纳候选”字段；另设同格式空病名。若具体提到哪个病完全不影响输出，每个病被提到时拿到的支持平均应为25%。\n\n| 模型 | 严格病例 | 被提及病名的平均支持，95%CI | 25%基准以上的量 |\n|---|---:|---|---|\n')
 for model in ['1.7b','4b']:
  s=next(r for r in nc['summaries'] if r['model']==model and r['dataset']=='all' and r['strict']);m=s['metrics'];parts.append(f'| {model} | {s["n"]} | {fmt(m["self_mention_support"],True)} | {pp(m["self_mention_excess_over_quarter"])} |\n')
 parts.append('\n![病名轮换](../results/41_name_counterbalance/figures/name_counterbalance.png)\n\n这个追加控制回答的是支持是否跟着未采纳的具体病名走。它不要求模型先明确作出那个诊断。[同格式病名轮换结果](../results/41_name_counterbalance/RESULTS.md)。\n')
 parts.append('## 结果二：答案被带偏，不等于新证据完全失效\n\n同一最后证据组，在中性与错误历史下的作用仍有正相关：MedQA为0.578、MedMCQA为0.716、MMLU为0.649。与此同时，126/540例出现了方向相反且两侧变化均超过预定阈值的更新。\n\n因此要分开看两件事：**旧病名把诊断分布整体推向哪里；新事实又在此基础上推动了多少。** 平均交互接近0不代表每例都相同，单例反向也不代表模型普遍拒绝证据。\n\n在94条完整轨迹中，中性历史有47例全程不换首选，29例曾选中最终来源答案后又离开；错误历史分别为56例和14例。这里保留早改对、晚改对、先选中又离开、始终不变等全部轨迹。\n\n把完整证据组倒序后，总准确率仍为315/540，但 **93例换了诊断**：36例从对变错、36例从错变对，另21例在错误候选之间移动。总分相同会掩盖个体判断的不稳定。\n\n![新增证据作用](../results/32_multisource_belief/figures/evidence_update_pairs.png)\n\n[全部逐组轨迹与顺序控制](../results/37_behavior_checks/RESULTS.md)。\n')
 parts.append('## 结果三：内部影响可以定位到计算位置和信息通路\n\n在原先划定的48例确认队列中，第21层诊断位置的自然状态替换，相对同位置、同范数随机替换，改善来源病相对错误病的分差 **4.55，95%CI [2.51, 6.54]**，并使10/48例换了首选。同层新、旧事实位置替换的作用很小；跨位置自然差的大小不同，因此继续做路径检验。\n\n我们分别阻断历史进入患者事实位置、以及历史直接进入后面的诊断任务/候选/输出位置。每种阻断都重新比较中性与错误/提及历史，并检查正常作答是否受损。\n\n'+route_text+'\n\n![两条路径](../results/36_history_routes/figures/history_paths.png)\n\n[自然位置替换](../results/33_multisource_causality/RESULTS.md) · [未采纳病名的替换](../results/35_unendorsed_name/RESULTS.md) · [完整通路结果](../results/36_history_routes/RESULTS.md)。\n')
 parts.append('## 结果四：概率图上的大跳变，不一定是新的疾病判断形成\n\n同一个病人的每轮输入，我们都保存四个候选的逐层读表；并检查换一套答案代码后，是否还指向同一疾病。1.7B早层大多不能稳定使用这套代码读表，后层才逐渐能稳定区分候选。灰色区域表示两套代码不一致，不给它强行起一个疾病名字。\n\n把末层再拆开，严格47例队列中，最后MLP步骤的历史分差变化为 **−3.47**。看图很容易把它当成关键开关；但换入中性历史的末层MLP后，相对随机扰动的命中率增益只有 **0.53个百分点，95%CI [−3.19, 4.26]**，没有可靠改善。\n\n继续分解输出读表：末层前后的归一化增益约为 **1.85–1.86倍**；上述−3.47变化中，尺度项为 **−3.33**，分子项为 **−0.13**。这里的代数分解说明：**图上的大部分末层跳变，是已有差距被读表放大了。** 它不能直接当作模型在该层突然获得新医学知识的证据。\n\n![模块读表](../results/39_module_readout/figures/module_history_readout.png)\n\n[逐模块结果](../results/39_module_readout/RESULTS.md) · [末层替换的失败检验](../results/40_final_mlp/RESULTS.md) · [尺度分解](../results/40_final_mlp/NORMALIZATION.md)。\n\n每轮变化的是模型激活、注意力和输出支持；模型参数始终冻结，权重文件前后哈希一致。\n')
 parts.append('## 4B提供了什么补充\n\n同94例完整病名评分，中性历史下1.7B答对48例、4B答对71例；错误历史下分别为39例和56例。**4B答题更准，旧诊断的影响仍然存在。** 1.7B为FP16、4B为8-bit，这两种配置不足以单独判断规模规律。\n\n![跨配置内部读表](../results/34_multisource_depth/figures/cross_configuration_readout.png)\n\n[逐层与跨配置结果](../results/34_multisource_depth/RESULTS.md)。\n')
 parts.append('## 论文现在可以怎样讲\n\n题目仍围绕“模型有医学信念吗？”。本轮主线可以写成：**患者事实、历史病名与答案形成共同决定可见的疾病判断；我们追踪新证据怎样改变判断、历史怎样进入计算，以及内部读表怎样放大已有倾向。**\n\n文章从一个患者的疾病转移进入，接着用多来源总体结果建立现象，再拆开证据响应与历史影响，最后用位置替换、通路阻断和末层失败检验区分机制。模型大小和数据来源作为成立范围，而不是把全篇写成弱模型到强模型的排行榜。\n\n临床提示偏差、激活修补和隐状态读出已有直接先例；本轮的实质要放在这些对照共同支持的具体结论上。[论文论证架构](../acl_paper/v08_multisource/ARGUMENT_STRUCTURE.md) · [方法](../acl_paper/v08_multisource/METHODS.md) · [最相关工作](../acl_paper/v08_multisource/RELATED_WORK.md)。\n')
 parts.append('''## 交付目录\n\n[全部94例图谱](../results/34_multisource_depth/CASE_ATLAS.md)包括每例原文、全部四病名曲线、逐轮逐层图；数据导出包含 **240576条层×候选记录**，以及诊断位置的逐层逐头分组注意力。两个有任务尾语的内部病例有明确标记，严格结果排除。\n\n| 问题 | 结果 |
|---|---|
| 540例总体历史与证据影响 | [32](../results/32_multisource_belief/RESULTS.md) |
| 自然状态替换 | [33](../results/33_multisource_causality/RESULTS.md) |
| 全部轨迹与4B | [34](../results/34_multisource_depth/RESULTS.md) |
| 未采纳病名的状态替换 | [35](../results/35_unendorsed_name/RESULTS.md) |
| 历史的两条信息路径 | [36](../results/36_history_routes/RESULTS.md) |
| 实际生成、顺序与转移 | [37](../results/37_behavior_checks/RESULTS.md) |
| 严格文本子集 | [38](../results/38_text_quality/RESULTS.md) |
| attention与MLP阶段读表 | [39](../results/39_module_readout/RESULTS.md) |
| 末层替换和尺度分解 | [40](../results/40_final_mlp/RESULTS.md) |
| 同格式四病名轮换 | [41](../results/41_name_counterbalance/RESULTS.md) |
\n[复现说明](REPRODUCE.md) · [完整交付核验](FINAL_VALIDATION.json)。所有科学图有PNG和PDF。旧的FP16辅助均值溢出已单独用FP32重算，原始记录保留；诊断分数不受该辅助记录问题影响。\n''')
 rendered=re.sub(r'([^\n])\n(#{1,6} )',r'\1\n\n\2',''.join(parts))
 (R/'RESULTS_AND_STORY.md').write_text(rendered)
 short=f'''# 本轮先看这一页

本轮已完成 **三个来源、540个新增病例** 的实验；原文质量严格复核后为520例，核心历史效应保持。主模型1.7B，94例做了完整逐轮逐层分析及4B复核。API费用 **0美元**。

最直接的结果是：同样的病例，中性历史答对 **302/540**，错误旧诊断降到 **232/540**，只提及未采纳病名为 **242/540**。实际生成答案也从297降到229。旧病名可以参与后续判断，并不需要被写成已经确定的诊断。进一步轮流放入四个未采纳候选，在严格47例中，被提及候选拿到的平均支持为1.7B的42.6%和4B的35.9%，均高于无病名选择性影响时的25%。

新证据仍会推动模型，旧病名的影响也可以同时存在。完整证据倒序后，总准确率没变，但 **93例换了诊断**。因此只看最终总分会漏掉判断过程的问题。

内部研究已有两类结果：第21层诊断位置替换能改变疾病分差；另一方面，末层图上的大跳变主要是读表放大已有差距，换掉对应MLP状态并没有可靠改好答案。我们开始区分“图上发生变化”与“真正能控制诊断的环节”。

两个配置的内部通路实验得到一致结果：**旧病名主要经由直接通向诊断作答段的连接影响选择。** 切断这条连接后，历史偏向大幅减弱；只切断它进入患者事实位置的连接，偏向仍然很强。正常中性作答没有随之明显下降。详见[通路结论](ROUTE_FINDING.md)。

**推荐阅读：**

- [完整结果：一个例子讲起，再到总体和内部机制](RESULTS_AND_STORY.md)
- [全部94例图谱：每例四个病名、每轮、每层](../results/34_multisource_depth/CASE_ATLAS.md)
- [论文正文与论证架构](../acl_paper/v08_multisource/PAPER_ZH.md)
- [数据来自哪里、怎样筛选](DATA_CARD.md)

几个容易读懂的例子：[红斑狼疮：先选中又离开](../results/34_multisource_depth/cases/medqa_train_09811.md)、[哮喘：最后一组才转向来源答案](../results/34_multisource_depth/cases/mmlu_professional_medicine_test_0025.md)、[胸腔积液：在几个疾病间切换](../results/34_multisource_depth/cases/medqa_train_01010.md)。这些用于说明；统计包含全部预定病例。
'''
 (R/'START_HERE.md').write_text(short)
 # The paper keeps a substantive introduction and reasoning architecture, with
 # results inserted from the finished report rather than copying old claims.
 intro='''# 模型有医学信念吗？诊断历史如何进入证据更新与答案形成

## 摘要

当新的患者事实到来时，语言模型如何更新其诊断倾向，先前出现的病名又如何参与这一过程？我们在MedQA、MedMCQA和MMLU的540个新增诊断病例上固定患者原文，配对操作中性、错误与未采纳候选历史；对94例展开每个累计证据前缀的28层记录，并在4B配置复核。实验同时测量完整病名评分、真实生成、候选代码投影、内部位置替换与注意力通路。错误历史与未采纳候选均可降低表现，尽管新增证据仍对判断产生影响。两个配置的通路阻断一致显示：历史影响主要经由直接通向诊断作答段的连接传播，阻断其进入患者事实位置的连接并未相应消除影响。末层读表的大变化也不等于一个有效的疾病偏向开关：自然MLP状态替换没有可靠改善，读表增幅主要来自尺度放大。本文以逐病例轨迹和总体配对实验，将医学信念的形成、历史依赖及读出尺度区分开来。

## 1 引言

一份医学病例的最终诊断掩盖了判断的形成过程。模型可能早已选中来源答案，随后又离开；也可能在新事实到来后改变候选支持，却仍被一个旧病名牵引。若只统计完整病例答对多少，这些情况会被混合在同一个总分中。

已有研究已观察到临床模型受到[先前评估](https://aclanthology.org/2026.emnlp-main.2434/)和[叙述方式](https://arxiv.org/abs/2607.27384v3)的影响，并通过[激活干预](https://aclanthology.org/2026.acl-srw.54.pdf)研究医疗模型中的偏差。本文进一步区分同一患者中的几个计算关系：证据怎样推动候选诊断；未采纳病名和先前诊断怎样进入该过程；内部读表中显著的变化是否真的能够改变答案。

我们保持病例事实固定，首先建立患者级配对结果，再沿证据轮次与网络深度追踪状态，最后干预具体位置和信息连接。所有病例均保留原始选项和来源答案，所有内部病例均给出图谱；文本审计和失败检验一并报告。模型参数冻结，“信念更新”指随上下文变化的诊断支持与内部计算变化。

## 2 研究设计

研究采用三个考试来源540例，开发181例、确认359例。主模型Qwen3-1.7B FP16；完整内部轨迹94例，同病例以Qwen3-4B 8-bit复核。除明确提供来源答案的oracle历史正对照外，来源答案用于评分及固定对照选择，不输入患者事实；每轮是重新输入累计原文和固定历史，并非自主回填上一轮答案。运行后按原文进行严格质量审计，形成520例敏感性队列。

输出与内部测量的定义、患者级统计、随机/反向/自身干预、源数据和实现细节见[完整方法](METHODS.md)。最直接的研究先例与贡献边界见[相关工作](RELATED_WORK.md)。

## 3 从患者轨迹到总体结果

'''
 # Rebase the experiment narrative's relative links from research_v4 to paper.
 raw_report=rendered
 narrative=raw_report[raw_report.index('## 先看一个完整的例子'):raw_report.index('## 论文现在可以怎样讲')].replace('](../results/','](../../results/').replace('](DATA_CARD.md)','](../../research_v4/DATA_CARD.md)').replace('](REPRODUCE.md)','](../../research_v4/REPRODUCE.md)').replace('](FINAL_VALIDATION.json)','](../../research_v4/FINAL_VALIDATION.json)').replace('](../acl_paper/v08_multisource/','](')
 for old,new in [('## 先看一个完整的例子','### 3.1 一个患者的诊断轨迹'),('## 数据已经扩到什么程度','### 3.2 多来源总体'),('## 结果一：旧病名会影响判断，即使没有被写成已确定诊断','## 4 历史病名对诊断的选择性作用'),('## 结果二：答案被带偏，不等于新证据完全失效','## 5 证据响应与历史偏移'),('## 结果三：内部影响可以定位到计算位置和信息通路','## 6 内部位置与信息通路'),('## 结果四：概率图上的大跳变，不一定是新的疾病判断形成','## 7 读表放大与因果干预'),('## 4B提供了什么补充','## 8 跨配置复核')]:narrative=narrative.replace(old,new)
 paper=intro+narrative+'''
## 9 讨论与后续检验

本文将可见的诊断支持、患者事实位置的计算状态、诊断位置的状态以及输出读表区分为相联系的测量对象。当前结果支持一个具体关系：新事实仍推动候选判断，旧病名又可经直接通向诊断作答段的连接影响选择。这种影响并不要求先通过患者事实位置传播；同时，单个层的投影跳变可能被尺度放大。完整病例准确率、轨迹稳定性与内部可干预性分别提供不同证据。

现有研究范围是英文考试诊断题、同一模型家族的两个配置和直接作答方式。下一项扩展应在真实纵向临床数据、其他模型家族、医学专用模型及自动传递自产诊断的条件下，检验本轮具体的路径与尺度结论。末层追加实验与病名轮换是在主观察后提出，作为探索性控制；后续独立样本应保持对应操作固定。

## 10 结语

医学判断的变化需要同时从证据、历史与内部计算观察。本文的配对设计和完整图谱把“更新了什么”“历史从哪里进入”和“读表怎样放大变化”变成可复核的问题，为进一步研究模型医学信念提供了具体的机制证据与明确的检验对象。
'''
 (P/'PAPER_ZH.md').write_text(paper)
 (P/'README.md').write_text('# 模型有医学信念吗？v0.8\n\n[中文论文正文](PAPER_ZH.md) · [论证架构](ARGUMENT_STRUCTURE.md) · [方法](METHODS.md) · [相关工作](RELATED_WORK.md)\n\n本轮新增540例、三个来源，正式结果与严格520例复核均已交付。论文依据实际结果动态更新，失败检验和数据审计保留。\n\n[先读一页](../../research_v4/START_HERE.md) · [完整实验报告](../../research_v4/RESULTS_AND_STORY.md) · [全部病例图谱](../../results/34_multisource_depth/CASE_ATLAS.md)\n')
 print(json.dumps(dict(report=str(R/'RESULTS_AND_STORY.md'),paper=str(P/'PAPER_ZH.md'))))
if __name__=='__main__':main()
