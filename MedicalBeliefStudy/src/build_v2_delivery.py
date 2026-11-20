"""Compose the current synthesis from completed, frozen stage summaries."""
import csv,json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from analyze_stages import ROOT,setup,savefig,fmt
def main():
    for run in ['belief_v2','belief_v2/disease_interventions','belief_v2/polarity','belief_v2/presentation','belief_v2/template_prior','belief_v2_4b']:assert (ROOT/'runs'/run/'completion.json').exists()
    setup();dest=ROOT/'results/21_current_synthesis';(dest/'figures').mkdir(parents=True,exist_ok=True)
    def read(folder,name='summary.json'):return json.loads((ROOT/'results'/folder/name).read_text())
    small=read('14_fixed_panel');causal=read('15_disease_directions');gap=read('15_disease_directions','decision_summary.json');alignment=read('16_update_mechanism','natural_alignment_summary.json');polarity=read('17_answer_polarity');big=read('18_model_replication');presentation=read('19_presentation_mechanism');prior=read('20_template_prior');contrast=read('20_template_prior','empty_score_contrast_summary.json')
    n=lambda x,N=120:round(x['mean']*N)
    rows=[('1.7B FP16：逐条追加',small['endpoints']['append']['native24'],small['endpoints']['append']['layers']['28']),('1.7B FP16：固定问卷',small['endpoints']['panel']['native24'],small['endpoints']['panel']['layers']['28']),('4B 8-bit：逐条追加',big['native24'],big['layers_accuracy']['36'])]
    fig,ax=plt.subplots(figsize=(10,5));x=np.arange(3)
    for j,label,color in [(1,'模型自身病名评分','#2878b5'),(2,'独立患者训练的最后层读出','#e07b21')]:
        rr=[v[j] for v in rows];xx=x+(-.18 if j==1 else .18);ax.bar(xx,[v['mean'] for v in rr],width=.34,color=color,label=label,yerr=[[v['mean']-v['low'] for v in rr],[v['high']-v['mean'] for v in rr]],capsize=3)
        for a,v in zip(xx,rr):ax.text(a,v['high']+.018,f'{n(v)}/120',ha='center',fontsize=10)
    ax.set(xticks=x,xticklabels=[v[0] for v in rows],ylim=(0,1.12),ylabel='同24病的独立新病例准确率');ax.legend(loc='upper left',fontsize=9);fig.tight_layout();savefig(fig,dest/'figures/central_comparison')
    main_table='\n'.join(f"| {label} | {n(native)}/120 | {n(probe)}/120 |" for label,native,probe in rows)
    primary='\n'.join(f"| {'追加' if r['view']=='append' else '问卷'} | {'回答前' if r['site']=='anchor' else '全部续写'} | {r['layer']} | {r['target_minus_random_logodds']['mean']:.3f} | {r['target_minus_random_same_first']['mean']:.3f} | {r['p_holm_8']:.5f} |" for r in causal['contrasts'])
    template='\n'.join(f"| {label} | {n(prior['conditions'][key]['copd'],24)}/24 | {prior['conditions'][key]['copd_support']['mean']:.3f} | {n(prior['conditions'][key]['picked_first_candidate'],24)}/24 |" for key,label in [('empty_append','无症状、无问卷'),('empty_panel','无症状、空问卷'),('reverse_candidates','完整资料、候选反转'),('rotate_candidates','完整资料、候选轮换')])
    strata=list(csv.DictReader((ROOT/'results/14_fixed_panel/stratified_metrics.csv').open()));family_names={'respiratory':'呼吸系统','cardiovascular':'心血管','digestive':'消化系统','neurologic':'神经系统','ent':'耳鼻喉','systemic':'全身性疾病'};family=[]
    for name,label in family_names.items():
        a=next(r for r in strata if r['grouping']=='family' and r['group']==name and r['view']=='append');b=next(r for r in strata if r['grouping']=='family' and r['group']==name and r['view']=='panel');N=int(a['cases']);family.append(f"| {label} | {N} | {round(float(a['native24_accuracy'])*N)} → {round(float(b['native24_accuracy'])*N)} | {round(float(a['probe28_accuracy'])*N)} → {round(float(b['probe28_accuracy'])*N)} |")
    text=f'''# 医学信念：从信息进入模型，到影响诊断

## 核心结论

**模型能保留疾病相关信息，这些信息也能推动诊断分数；但分数被推动，并不等于最后会选对。输入呈现会改变信息可读性及它与输出更新的联系。**

本轮沿原论文主线完成新病例、逐层读出、自然更新、疾病方向干预、肯否、呈现与候选顺序，以及另一模型配置复核。简单分类器高分分支保持独立，不作为本文的新诊断方法。

## 一个例子说明问题

同一份来源标签为急性中耳炎的模拟病例，包含右耳痛、近期针对耳部感染使用口服抗生素、发热等资料。逐条追加时，模型在抗生素病史加入后转向中耳炎，并保持到终点。相同事实填入固定问卷，其余项目明确为未知，模型却一直选择慢阻肺相关诊断；后层外部读出仍识别中耳炎。

![同一病例的两种轨迹](../14_fixed_panel/cases/ddx_test_0041136.png)

上排看模型实际支持什么病，黑线是来源标签。下排看每层内部状态经独立读出后，来源标签排第几；黄色越多，越容易读出来。下排不是模型自己的患病概率。[每轮新增事实与完整数值](../14_fixed_panel/cases/ddx_test_0041136.md)

## 一、实际怎样做

| 项目 | 本轮设计 |
|---|---|
| 病例来源 | 已有DDxPlus模拟病例；旧validate 120例训练读出，新test 120例测试 |
| 范围 | 24病种各5例、6疾病组；与此前病例无完全相同事实集合 |
| 完整轨迹 | 预定24例，覆盖17病种；每例4—15次新增证据，共184次更新 |
| 每轮资料 | 累积来源事实，症状及病史按固定顺序揭示；不输入前轮模型诊断 |
| 模型 | Qwen3-1.7B FP16、Qwen3-4B 8-bit；直接作答、关闭显式thinking |
| 模型自身判断 | 49个完整病名的序列相对支持；另存实际续写 |
| 内部测量 | 1.7B全部28层、4B全部36层的attention/MLP前后状态与诊断位置注意力 |
| 内部读出 | 仅用旧120例训练24类线性读出器，新病例不参与训练 |
| 真值 | 终点对照来源标签，同时保留参考鉴别诊断；早期各轮没有唯一标准后验 |
| 成本 | 全部本地GPU运行，API费用0美元 |

模型权重始终不变。变化的是每轮计算得到的状态、注意力与输出。新test与旧训练虽隔离，仍来自同一合成生成来源。

## 二、总体结果：能读出，不代表会选对

以下统一比较24病，避免把24类读出与49类诊断混为同一任务。原模型未经过外部读出器的标签适配。

| 配置与输入 | 模型自己排名正确 | 最后层外部读出正确 |
|---|---:|---:|
{main_table}

![主结果](figures/central_comparison.png)

1.7B中，固定问卷使内部末层读出从100例提高到112例，原生24病排名却从56例降到14例。完整49病命中由44/120降至10/120；105/120例终点首选随呈现改变。问卷条件85/120例选择慢阻肺相关诊断。

只取来源标签同时为参考鉴别诊断首位的79例，差距仍存在：追加式原生42/79、读出67/79；问卷原生10/79、读出77/79。

### 不同疾病组

表中箭头为“逐条追加→固定问卷”，均为24类命中数。

| 疾病组 | 病例数 | 原模型命中 | 第28层读出命中 |
|---|---:|---:|---:|
{chr(10).join(family)}

总体差异不要求每个疾病组同向。小组结果保留原分母，不把单病5例当成稳定疾病级结论。[阶段14全部结果](../14_fixed_panel/RESULTS.md)

## 三、每条证据进入后，是慢慢变化还是突然转向

| 相同24例、184次更新 | 首选切换次数（49病） | 单病支持变化至少50个百分点 |
|---|---:|---:|
| 1.7B逐条追加 | 77 | 69 |
| 1.7B固定问卷 | 23 | 21 |
| 4B逐条追加 | {big['deep']['switch_events']} | {big['deep']['big_events']} |

两种变化都存在，且大幅转向并不少见。少改口不意味着更好：1.7B问卷中切换少，终点却更差。最终标签不等于每轮唯一合理答案，因此“曾对后来错”是轨迹描述，不自动判为医学更新错误。

输出与内部也不是完全无关：第28层读出分差与原输出分差的自然变化，1.7B追加式病例平均相关0.575、约73.9%同向；固定问卷相关0.319、约62.6%同向。相同患者的相关差为{fmt(alignment['paired_panel_minus_append']['28']['spearman'],False)}。首选可以不同步，连续分数仍可有联系。

[自然更新与内部计算](../16_update_mechanism/RESULTS.md) · [连续变化的逐层关系](../16_update_mechanism/NATURAL_ALIGNMENT.md) · [逐层逐头注意力](../16_update_mechanism/ATTENTION_ATLAS.md) · [24例两模型完整轨迹](../18_model_replication/CASE_ATLAS.md)

## 四、内部方向真的能影响模型自己的回答

用旧病例学到的“目标病减竞争病”方向，轻推新病例的内部状态；比较反向、随机及零干预。只改回答前位置与同时改续写位置分开。标签用于离线靶向实验，不是可部署诊断时已知的输入。

48/48零干预与原记录一致。672个干预条件中，8项预定主对比全部显示目标方向优于随机方向（Holm p≤0.00065）。以下增益为完整病名对数比，不是准确率或患病概率。

| 呈现 | 干预位置 | 层 | 目标减随机增益 | 同首词元选择性增益 | Holm p |
|---|---|---:|---:|---:|---:|
{primary}

第21层锚点在追加式中能区分部分共享病名开头的疾病；最后层锚点只能改变第一个输出词元，同首词元选择性精确为零。覆盖续写位置后，可产生后续病名词元的选择性。这表明干预放在哪里，会决定它能改变哪一部分诊断生成。

**分数拉动了，正确诊断没有增加。** 当前8种主条件均无由错转对病例。第21层全续写干预中，原本错误病例的落后分差中位数，追加式10.681、问卷22.119；干预带来的分差增益中位数只有1.166和1.516。局部方向有输出作用，当前强度却不足以跨过诊断决策边界。

[方向干预](../15_disease_directions/RESULTS.md) · [决策边界与全部病例](../15_disease_directions/DECISION_GAPS.md) · [首词元机制](../13_token_path/RESULTS.md)

## 五、为什么问卷会改变判断

在同24例、同token长度下，把已知资料从问卷前面移到后面，后层对资料的注意力从2.05%升至3.99%；49病命中却从7/24降至2/24，慢阻肺相关选择从17/24升至22/24。准确率配对检验p=0.0634，按未通过0.05阈值报告；标签支持平均下降0.2185，探索性p=0.0070。注意力增加没有带来诊断改善。

删除Unknown行、保留全部已知事实，命中从原公开字段顺序问卷的3/24提高至12/24。只改变一个Yes/No答案时，5/24例改变首选，第21层读出7/24例改变。这说明模型并非完全不看患者答案，但答案内容、背景问卷与输出竞争共同影响结果。

### 空问卷与候选顺序

| 条件 | 选择慢阻肺相关诊断 | 该病平均相对支持 | 选择当前列表第一项 |
|---|---:|---:|---:|
{template}

空问卷减无问卷的该病支持差：{fmt(prior['empty_panel_minus_empty_append_copd_support'],False)}。有完整事实时，候选反转命中{n(prior['conditions']['reverse_candidates']['correct'],24)}/24，候选轮换命中{n(prior['conditions']['rotate_candidates']['correct'],24)}/24。无症状条件只测输出偏向，不计诊断准确率，也不称人群患病先验。

[呈现分解](../19_presentation_mechanism/RESULTS.md) · [肯否对照](../17_answer_polarity/RESULTS.md) · [空问卷与候选控制](../20_template_prior/RESULTS.md)

将完整事实分数减去匹配空输入分数、固定系数1重新排序，追加式命中由{n(contrast['append']['native_accuracy49'],24)}/24变为{n(contrast['append']['contrast_accuracy49'],24)}/24，固定问卷由{n(contrast['panel']['native_accuracy49'],24)}/24变为{n(contrast['panel']['contrast_accuracy49'],24)}/24。**慢阻肺偏向在没有问卷时就已存在；扣除空输入偏向后，集中选择慢阻肺的现象消失了，但问卷诊断仍只对5/24例。去掉共同偏向，没有自动恢复正确诊断。** 这是借鉴已有contextual calibration的诊断性对照，不提出新算法，也不把差值当成临床后验。[空输入评分对照](../20_template_prior/SCORE_CONTRAST.md)

## 六、4B配置复核

同新120例，4B的49病命中{n(big['native49'])}/120，同24病命中{n(big['native24'])}/120，最后层外部读出{n(big['layers_accuracy']['36'])}/120。固定24例的4B完整问卷命中{n(big['fixed_panel_followup']['panel_accuracy49'],24)}/24，追加式为{n(big['fixed_panel_followup']['append_accuracy49_same_cases'],24)}/24。

4B和1.7B同时改变了参数规模与量化精度；这是跨配置复核，不是只改变规模的因果实验。4B未运行本轮方向干预，主因果结论仍来自1.7B。

[4B总体结果](../18_model_replication/RESULTS.md) · [全部24例对照图](../18_model_replication/CASE_ATLAS.md) · [信息可读与输出更新的深度](../18_model_replication/NATURAL_ALIGNMENT.md)

## 七、论文现在怎样收束

论文由一个病例进入，按“判断变化→内部信息→自然更新联系→干预作用→输入条件→模型复核”推进。核心不是发现一个分类器能高分，而是把**信息存在、能影响输出、能否改变诊断**拆开并放回同一条证据轨迹验证。

本轮已形成完整中文研究稿、相关工作、测量附录、证据表和全病例图谱。最明确的判断是：模型中存在可读、可扰动的疾病相关信息，但其对诊断的作用受呈现和生成位置限制，不能仅凭读出高分或注意力图推断模型有一个可靠统一的诊断状态。具体模板偏向是否推广到其他模型家族、真实病历及显式推理，属于后续外推范围。

简单文本分类器120/120的结果单独保留：它揭示这套模拟资料的记录模式高度可学习，尚不构成无需推理即可普遍诊断的新方法。[保留分支](../11_disease_information/FOLLOWUP_RESERVED.md)

## 交付与追溯

新增1488组自然/输入对照观测，另672个内部干预条件、48个零干预；这些是观测条件，不是独立患者数。本轮新增患者120例，读出训练另用旧120例。原始记录、状态、候选完整分数和哈希均保留；全部图提供PNG和PDF。API费用0美元。

[完整论文稿](../../acl_paper/07_MANUSCRIPT.md) · [论文主线](../../acl_paper/01_STORY.md) · [证据表](../../acl_paper/03_EVIDENCE_LEDGER.md) · [复现步骤](../../protocol/BELIEF_V2_REPRODUCE.md) · [数值与文件验证](../../protocol/BELIEF_V2_DELIVERY_VERIFICATION.json)
'''
    (dest/'RESULTS.md').write_text(text)
    (dest/'summary.json').write_text(json.dumps({'new_patients':120,'readout_training_patients':120,'deep_patients':24,'deep_unique_diseases':17,'diseases':24,'disease_families':6,'updates_per_view':184,'new_observation_records':1488,'active_interventions':672,'zero_interventions':48,'api_cost_usd':0,'causal_primary_positive_holm':sum(r['p_holm_8']<.05 and r['target_minus_random_logodds']['mean']>0 for r in causal['contrasts']),'stage_sources':['13_token_path','14_fixed_panel','15_disease_directions','16_update_mechanism','17_answer_polarity','18_model_replication','19_presentation_mechanism','20_template_prior']},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'report':str(dest/'RESULTS.md'),'complete_stage_summaries':True}),flush=True)
if __name__=='__main__':main()
