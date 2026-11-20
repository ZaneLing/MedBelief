"""Numerical report and manuscript section from completed structural results."""
from structural_v1_analysis import *
from phase77_structural_holdout_analyze import LABELS
DOC=ROOT/'research_v5_structural';PAPER=ROOT/'acl_paper/v09_structure'

def main():
    import time
    while not (DOC/'head_followup_complete.json').exists():time.sleep(10)
    audit=read(DOC/'FINAL_VALIDATION.json');assert audit['complete'];s=read(ROOT/'results/44_structural_holdout/summary.json');d=read(ROOT/'results/45_structural_synthesis/dynamics_summary.json');p=read(ROOT/'results/44_structural_holdout/paired_contrasts.json');sel=read(RUN/'selected.json')
    def row(name,cond):return next(r for r in s['code_summaries'] if r['candidate']==name and r['condition']==cond and r['dataset']=='all')
    def dyn(name,cond):return next(r for r in d['summary'] if r['candidate']==name and r['condition']==cond)
    def val(name,cond,key):return row(name,cond)[key]['mean']*100
    def gen(name,cond):return next(r for r in s['generation'] if r['candidate']==name and r['condition']==cond)
    def tim(name):return next(r for r in s['timing'] if r['candidate']==name)
    def contrast(left,right,cond,key):return next(r for r in p['contrasts'] if r['left']==left and r['right']==right and r['condition']==cond)[key]
    names=[c['name'] for c in sel['candidates']]
    table='| 结构 | 参数减少 | 中性：正确率 / 原诊断一致率 | 错误历史：正确率 / 原诊断一致率 |\n|---|---:|---:|---:|\n'
    for name in names:
        v=next(r for r in s['verdicts'] if r['candidate']==name)
        table+=f'| {LABELS[name]} | {100*v["parameter_reduction"]:.2f}% | {val(name,"neutral","accuracy"):.2f}% / {val(name,"neutral","fidelity"):.2f}% | {val(name,"wrong","accuracy"):.2f}% / {val(name,"wrong","fidelity"):.2f}% |\n'
    n,w=row('linear_mlp_2_r16','neutral'),row('linear_mlp_2_r16','wrong');cn=contrast('linear_mlp_2_r16','drop_mlp_2','neutral','fidelity');cw=contrast('linear_mlp_2_r16','drop_mlp_2','wrong','fidelity')
    facts=f'''## 1. 什么最接近最终诊断，什么真正影响诊断

在严格92例、521个累计前缀的投影中，第25层与同轮最终诊断已达到93.5%／94.3%的一致率（中性／错误历史）。但18例穷尽定位显示，第3层MLP和第20层注意力仍对最终诊断有强作用：分别删除它们，改变69.4%／72.2%及61.1%／44.4%的首选。**答案在后面变得容易读出来，前面的计算仍可能是形成答案所必需的。**

注意力大也不自动意味着作用大：448个头的历史注意力与删除后分布变化的描述性Spearman相关为0.285／0.272。我们依据实际重算后的答案变化定位部件。[每层、每头定位与数值对照](../results/42_structural_localization/RESULTS.md)。

## 2. 真正改结构以后发生了什么

定位18例、组合开发27例、结构留出345例互不重叠。留出来源为MedQA194、MedMCQA125、MMLU26。首批结构实验的独立病例总数为390，60例生成与47例轨迹均为345例的子集；另130例用于随后冻结的注意力头复核，见第7节。

{table}

两套代码映射先在同病例内平均。正确率检查来源答案；一致率检查是否保留原模型答案，二者不能互换。完整病例级95%区间和分来源表见[留出结果](../results/44_structural_holdout/RESULTS.md)。

**只运行前27层**，中性与错误历史分别保留{val('early_exit','neutral','fidelity'):.2f}%、{val('early_exit','wrong','fidelity'):.2f}%的原诊断。准确率相对完整模型变化为{fmt(row('early_exit','neutral')['accuracy_change'],True)}、{fmt(row('early_exit','wrong')['accuracy_change'],True)}（差值按百分点解释）。整模型参数减少2.93%。

**删除第25、26层MLP**，准确率变化为{fmt(row('drop_mlp_2','neutral')['accuracy_change'],True)}／{fmt(row('drop_mlp_2','wrong')['accuracy_change'],True)}；但{100-val('drop_mlp_2','neutral','fidelity'):.2f}%／{100-val('drop_mlp_2','wrong','fidelity'):.2f}%的原诊断发生变化。总体分数接近，不能据此说这两处没有作用。

**用小模块替代这两处MLP**，每处由37,748,736参数变为69,632参数。相对直接删除，原诊断一致率分别提高{fmt(cn,True)}和{fmt(cw,True)}。这直接量化小模块补回了多少功能。与完整模型相比，来源答案命中变化为{fmt(n['accuracy_change'],True)}／{fmt(w['accuracy_change'],True)}。模块用18例内部向量拟合，没有以疾病标签作为拟合目标；开发阶段的结构选择使用了答案评分。

替换后完整模型为1,645,216,768参数，整体减少4.38%。7万参数仅是一个替换部件的大小，并不是完整诊断模型大小。[开发选择与拟合](../results/43_structural_development/RESULTS.md)。

## 3. 错误历史是否随简化而消失

完整模型中，中性与错误历史正确率相差{val('baseline','neutral','accuracy')-val('baseline','wrong','accuracy'):.2f}个百分点；秩16替换后仍相差{val('linear_mlp_2_r16','neutral','accuracy')-val('linear_mlp_2_r16','wrong','accuracy'):.2f}个百分点。局部计算可以简化，旧病名的牵引仍然存在。可压缩性与去偏能力需要分别解释。

诊断位置8个头的固定干预，相对完整模型的准确率变化为{fmt(row('anchor_heads_8','neutral')['accuracy_change'],True)}／{fmt(row('anchor_heads_8','wrong')['accuracy_change'],True)}。它只在输入最后位置移除这些头的贡献，参数数没有减少。其两历史间的配对作用差以及修复/损坏均保留在[配对对照](../results/44_structural_holdout/paired_contrasts.json)。

## 4. 最后答得一样，中间会不会走不同的路

全部47例、289个累计证据前缀，比较完整模型、删MLP、小模块替换与8头干预。每个条件保留28层投影，完整模型保留28×16头的注意力。图谱涵盖全部病例。

| 结构 | 历史 | 最终与原模型一致 | 各轮与原模型一致 | 最终一致、但中间曾改变 |
|---|---|---|---|---|
'''
    for name in ['drop_mlp_2','linear_mlp_2_r16','anchor_heads_8']:
        for cond in ['neutral','wrong']:
            r=dyn(name,cond);facts+=f'| {LABELS[name]} | {"中性" if cond=="neutral" else "错误历史"} | {fmt(r["endpoint_fidelity"],True)} | {fmt(r["all_round_fidelity"],True)} | {fmt(r["same_final_changed_earlier"],True)} |\n'
    facts+='\n![终点和过程](../results/45_structural_synthesis/figures/endpoint_vs_path.png)\n\n读图：前两组柱子越高，保留原判断越多；第三组专门数“最后相同、但前面至少一次选了不同疾病”的轨迹。中间轮没有独立的唯一诊断标签，这里衡量路径改变，不自动将所有中途变化叫作错误。\n\n[47例完整原文、逐轮候选与逐层图](../results/45_structural_synthesis/CASE_ATLAS.md) · [总体动态结果](../results/45_structural_synthesis/RESULTS.md)。\n'
    facts+='\n## 5. 实际病名与实际速度\n\n代码选择之外，另在固定60例上实际生成完整候选文本；未解析或不在候选中的输出计错。\n\n| 结构 | 中性答对/60 | 错误历史答对/60 | 相对预填充耗时，95%CI |\n|---|---:|---:|---|\n'
    for name in names:
        t=tim(name) if name!='baseline' else None;ts=f'{t["geometric_ratio"]:.3f} [{t["ratio_low"]:.3f}, {t["ratio_high"]:.3f}]' if t else '1.000'
        facts+=f'| {LABELS[name]} | {gen(name,"neutral")["correct"]} | {gen(name,"wrong")["correct"]} | {ts} |\n'
    facts+='\n耗时<1表示更快。计时为Apple M2 Pro上6例、两历史、3次交错配对重复的同步预填充与最终词表输出，不包含分词、模型加载和持续生成。参数减少与速度提升分别核实。\n\n## 6. 对照怎样约束结论\n\n'
    for left,right,title,key in [('linear_mlp_2_r16','linear_mlp_2_r64','秩16相对秩64的原诊断一致率差','fidelity'),('drop_mlp_2','depth_matched_random_mlp_2','所选MLP删除相对深度匹配随机删除的一致率差','fidelity')]:
        facts+=title+'：中性'+fmt(contrast(left,right,'neutral',key),True)+'；错误历史'+fmt(contrast(left,right,'wrong',key),True)+'。差值按百分点解释。\n\n'
    facts+='开发集上“小模块比大模块更忠实”的现象没有在345例复现：秩64的原诊断一致率点估计在两种历史下都更高，中性条件的差异区间不跨0。两种秩的正确率差异则都没有明确方向。因此不能把开发阶段的反常现象写成已确认发现。相关比较为探索性区间，不按留出表现重新选层或挑秩。\n\n线性替换、删层和医学内部定位都有直接先例。本研究应将贡献放在证据更新、历史竞争、内部计算与结构取舍之间的关系；[同类工作比较](RELATED_WORK.md)列出LASER、ReplaceMe、医学transcoder及PH3等具体研究。\n'
    followup=read(ROOT/'results/46_structural_head_followup/summary.json')
    facts+='\n## 7. 在另外130例上复核注意力头作用\n\n这批MedQA82、MedMCQA48未参与本轮结构选择及首批345例检验。固定两个同层随机集合与一个同层高历史注意力集合，保持每层头数相同；另测试来源答案被明确写为旧诊断的oracle正对照。\n\n| 结构 | 历史 | 来源答案命中 | 相对完整模型变化，95%CI |\n|---|---|---|---|\n'
    from phase87_structural_head_analyze import LABELS as HEAD_LABELS
    for r in followup['code_summaries']:
        if r['dataset']=='all':facts+=f'| {HEAD_LABELS[r["candidate"]]} | {r["condition"]} | {fmt(r["accuracy"],True)} | {fmt(r["accuracy_change"],True)} |\n'
    facts+='\n[第二批完整结果、同层对照与实际候选生成](../results/46_structural_head_followup/RESULTS.md)。两批结构验证合计475例，加上45例定位/开发，共覆盖严格520例。第二批由第一批结果触发，报告保留这个先后关系，不称一次性事先设计的全部实验。\n'
    facts+='''
## 8. 同一部件的作用，取决于历史内容与作答接口

所选8头干预在另外130例的错误历史代码选择中，从35.00%提高到42.69%，配对差7.69个百分点，95%CI [2.69, 13.08]。同层随机集合1、2及高历史注意力集合分别达到35.38%、32.69%、28.46%；所选头相对三个对照的配对检验经Holm校正均小于0.01。三个对照均排除所选头。**看历史更多并不意味着关闭后更能改善诊断，必须直接检验该计算的作用。**

当历史明确给出来源答案时，同样的8头干预使代码命中从81.92%降至75.77%，差−6.15个百分点，95%CI [−11.15, −1.15]。干预在错误历史下的作用比正确历史下高13.85个百分点，[7.69, 20.38]。这一oracle对照支持这组头参与旧诊断利用的解释；它们既可能传递帮助，也可能传递误导，并非普遍无用的组件。

![历史方向与实际生成](../results/46_structural_head_followup/figures/history_and_generation.png)

同130例错误历史下，完整候选生成中原模型答对54例，首步关头和持续关头都答对48例；两者相对原模型差均为−4.62个百分点，[−10.00, 0.77]。中性条件分别为70、66、65例。延长同一干预没有改善完整生成。代码收益减去名称生成收益的同病例配对差为12.31个百分点，[5.38, 20.00]；该比较包含两映射代码接口与原顺序名称接口的设计差异，尚未单独分离编码和顺序。**这组部件改变了特定作答过程，代码选择的改善不能直接解释为医学知识增强。**

首批60例也保留在报告中；在同60例上代码与名称干预收益的差异区间跨0。130例配对结果提供了更清楚的接口差异，但不删除第一批结果。[同病例接口统计](../results/46_structural_head_followup/INTERFACE_AND_HISTORY.md)。

具体到导管内乳头状瘤病例，干预使最后一组事实后两套编码均转回来源答案，第23—28层的投影也一致改变；早期轮次仍有编码分歧。小MLP替换并未修好这个病例，而是在总体上恢复直接删除所丢失的功能。这说明“替代计算”和“减轻旧诊断牵引”是不同目标。[逐轮、逐层中文解释](ONE_CASE_EXPLAINED.md)。

据此，下一阶段应检验条件性地调节历史通路，以及用完整名称与逐证据过程共同约束小模块拟合。本轮没有训练这样的条件门控，也没有把两种改动组合成已验证成品。
'''
    ending='''
## 复核与交付

完整模型28层、448个查询头；定位包含6048次全输入组件删除、38304次最后位置组件删除及2016次自身对照。27例比较16个开发配置；345例比较9个冻结配置，共12,420个代码提示条件。60例完成1080次完整文本生成；47例完成4624个逐证据结构条件。每个病例与其来源答案、四候选均能追溯。

[测量定义](MEASUREMENT.md) · [实验协议](PROTOCOL.md) · [复现命令](REPRODUCE.md) · [最终机器核验](FINAL_VALIDATION.json) · [论文论证结构](../acl_paper/v09_structure/ARGUMENT_STRUCTURE.md)。全部使用本地GPU，API费用0美元。
'''
    title='# 医学判断中的关键计算，能否用更小结构保留\n\n本轮已完成从全部层定位、实际结构替换，到留出病例与完整更新轨迹的检验。研究对象是Qwen3-1.7B在三来源诊断类题目上的计算。\n\n**小模块能够补回部分诊断功能；所选注意力头对旧诊断的作用具有方向性和接口依赖；最终判断保持也可能掩盖中间过程改变。** 共520个独立题目，其中45例用于定位/开发、475例分两批验证。[先读中文解释](START_HERE.md)。\n\n'
    (DOC/'RESULTS_AND_STORY.md').write_text(title+facts+ending)
    # A new integrated paper draft, retaining earlier empirical chapters.
    old=(ROOT/'acl_paper/v08_multisource/PAPER_ZH.md').read_text()
    old=old.replace('## 8 跨配置复核','## 9 跨配置复核').replace('## 9 讨论与后续检验','## 10 讨论与后续检验').replace('## 10 结语','## 11 结语')
    section='## 8 从内部机制到结构取舍\n\n'+facts.replace('../results/','../../results/').replace('](RELATED_WORK.md)','](../../research_v5_structural/RELATED_WORK.md)').replace('](ONE_CASE_EXPLAINED.md)','](../../research_v5_structural/ONE_CASE_EXPLAINED.md)')
    # Keep the chapter hierarchy clear inside the integrated manuscript.
    for k in range(1,9):section=section.replace(f'## {k}. ',f'### 8.{k} ')
    old=old.replace('## 9 跨配置复核',section+'\n## 9 跨配置复核')
    abstract=f'在此基础上，我们进一步定位全部层与注意力头，使用18例拟合小型替换模块、27例选择结构，并在345例上检验。第25、26层MLP的秩16替换使整模型参数减少4.38%，相对直接删除恢复了{cn["mean"]*100:.2f}／{cw["mean"]*100:.2f}个百分点的原诊断一致率；47例逐证据复核进一步区分终点保持与过程保持。'
    old=old.replace('本文以逐病例轨迹和总体配对实验，将医学信念的形成、历史依赖及读出尺度区分开来。','本文以逐病例轨迹和总体配对实验，将医学信念的形成、历史依赖及读出尺度区分开来。'+abstract)
    old=old.replace('输出与内部测量的定义、患者级统计、随机/反向/自身干预、源数据和实现细节见[完整方法](METHODS.md)。','输出与内部测量的定义、患者级统计、随机/反向/自身干预、源数据和实现细节见[v0.8方法](../v08_multisource/METHODS.md)；新增结构实验见[测量与设计](../../research_v5_structural/MEASUREMENT.md)。')
    old=old.replace('见[相关工作](RELATED_WORK.md)','见[v0.8相关工作](../v08_multisource/RELATED_WORK.md)及[新增结构相关工作](../../research_v5_structural/RELATED_WORK.md)')
    old=old.replace('每轮变化的是模型激活、注意力和输出支持；模型参数始终冻结，权重文件前后哈希一致。','每轮变化的是模型激活、注意力和输出支持；原模型权重文件保持不变。下一节另拟合小型替换模块并改变运行时结构。')
    old=old.replace('完整病例准确率、轨迹稳定性与内部可干预性分别提供不同证据。','完整病例准确率、轨迹稳定性与内部可干预性分别提供不同证据。新增结构实验进一步把这些区别变成可操作的检验：小模块能补回部分诊断功能，局部简化仍保留明显的历史影响。评价结构不能只看总体分数，还要检查同一病例的终点与逐证据过程。')
    old=old.replace('# 模型有医学信念吗？诊断历史如何进入证据更新与答案形成','# 模型有医学信念吗？证据更新、历史利用与诊断计算的可替代性')
    abstract='''当患者事实逐步增加时，语言模型的诊断倾向怎样更新，哪些内部计算决定了这种变化？我们在MedQA、MedMCQA与MMLU的540个诊断类题目上配对操作事实与历史，对94例展开内部轨迹，并在严格520例中进行结构研究。研究依次比较候选支持、逐层投影、实际干预与计算替换。两个模型配置中的路径实验显示，旧病名可直接通过诊断作答段影响选择；内部读表的大变化也可能来自尺度放大。进一步在1.7B模型中定位全部层与头：固定8头干预在345例与另130例上提高错误历史下的代码选择正确率，但损害正确历史利用，且未改善完整候选生成。同层高历史注意力头的干预反而降低表现。第25、26层MLP的小型替换使整模型参数减少4.38%，并恢复直接删除丢失的部分诊断功能；47例逐证据复核显示，约19%—24%的轨迹最终判断相同，中途仍发生改变。结果将医学信念的证据响应、历史利用、作答接口与结构保持联系起来，并说明这些能力需要分别检验。'''
    start=old.index('## 摘要');end=old.index('## 1 引言');old=old[:start]+'## 摘要\n\n'+abstract+'\n\n'+old[end:]
    old=old.replace('## 2 研究设计','''内部分析进一步面临一个检验：如果我们找到了真正参与诊断的计算，能否减少它的规模，或减弱其中传播错误历史的作用？我们同时检查来源答案正确率、与原模型的个体诊断一致率以及逐证据更新路径。一个部件可能可替代，却仍影响中间判断；同一组头可能传递正确历史，也可能传递错误历史。代码选择与完整候选生成的配对实验进一步检验这种作用能否跨作答形式保持。

## 2 研究设计''',1)
    old=old.replace('## 3 从患者轨迹到总体结果','''新增结构实验在严格520例中分离18例定位与拟合、27例组合开发、345例首批结构验证、130例随后冻结的复核。后两批未用于本轮位置选择和模块拟合；它们已有旧版原模型记录，不称全新收集的数据。60例名称生成与47例逐层结构轨迹是345例的子集，不重复计入病例数。结构改动仅在Qwen3-1.7B验证；4B结果对应前述历史通路实验。

## 3 从患者轨迹到总体结果''',1)
    old=old.replace('## 10 讨论与后续检验','''## 10 讨论与后续检验

结构结果提供了两种不同的证据。小MLP替换表明部分计算可以用简单映射近似，同时保留大部分原选择；它没有证明模型的全部医学判断都能压缩到这个小模块。头干预的正确/错误历史对照表明，同一计算的作用会随内容改变；完整名称生成又显示，这种改善依赖当前作答接口。因而本研究对医学信念的解释需要同时指定输入证据、历史与输出任务，不能仅将一个高支持读数或一组头当作独立的疾病信念本体。

只测终点还会低估结构改变的作用。小模块替换在47例中保留约92%的最终选择，但全部轨迹中仍有约19%—24%出现最终相同、中途不同。对医疗证据更新的结构优化，应同时衡量终点、个体判断和更新过程；当前实验尚未区分所有中途改变是否有益，因为中间轮没有独立唯一真值。
''',1)
    (PAPER/'PAPER_ZH.md').write_text(old)
    write(DOC/'report_complete.json',dict(complete=True))
    print(json.dumps(dict(complete=True,report=str(DOC/'RESULTS_AND_STORY.md'),paper=str(PAPER/'PAPER_ZH.md'))))

if __name__=='__main__':main()
