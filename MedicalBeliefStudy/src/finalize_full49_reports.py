"""Generate the current synthesis and update the living ACL argument from completed results."""
from pathlib import Path
import json,csv
import numpy as np
import matplotlib.pyplot as plt
from analyze_stages import ROOT,setup,savefig,fmt
def read(path):return json.loads((ROOT/path).read_text())
def main():
    setup();six=read('results/06_full_candidate_trajectories/summary.json');eight=read('results/08_causal_confirmation/summary.json');nine=read('results/09_disease_name_trajectories/summary.json');ten=read('results/10_name_causal_mechanism/summary.json');eleven=read('results/11_disease_information/summary.json');audit=read('results/11_disease_information/text_audit.json')
    dest=ROOT/'results/12_current_synthesis';(dest/'figures').mkdir(parents=True,exist_ok=True);s9=nine['case_weighted'];d9=nine['deep_case_weighted']
    # Figures use the same 24-label comparison for the probe and the native scorer.
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    labels=['初始资料','中间资料','全部资料'];values=[s9[k]['mean'] for k in ['initial_correct','middle_correct','final_correct']]
    axes[0].bar(labels,values,color=['#a9c7dd','#699fc5','#28648c'])
    for i,v in enumerate(values):axes[0].text(i,v+.025,f'{round(v*120)}/120',ha='center')
    axes[0].set(ylim=(0,1.08),ylabel='最终标签命中率',title='49病候选：资料增加后的诊断表现')
    vals=[eleven['native_restricted24_accuracy']['mean'],eleven['layers']['28']['name_to_name']['mean'],eleven['text_accuracy']['mean']]
    axes[1].bar(['模型自身排序','第28层外部读出','病例文本分类'],vals,color=['#b86b4c','#4a8a74','#858585'])
    for i,v in enumerate(vals):axes[1].text(i,v+.025,f'{round(v*120)}/120',ha='center')
    axes[1].set(ylim=(0,1.08),ylabel='未见病例标签命中率',title='公平限定同24病：内部信息与实际输出')
    fig.tight_layout();savefig(fig,dest/'figures/main_findings')
    cid='ddx_validate_0000493';ir=read(f'runs/structured_names_v1/interventions/{cid}.json');ds=read('runs/structured_names_v1/manifest.json')['candidate_diseases'];idx=ds.index('Pulmonary embolism');old=ir['old_q'][idx];current=ir['current_q'][idx];patched=next(v for v in ir['conditions'] if v['layer']==28 and v['condition']=='previous_mlp')['q_sequence'][idx]
    fig,ax=plt.subplots(figsize=(9,4.7));vv=[old,current,patched];ax.bar(['上一轮资料','加入不能活动的病史','保留新资料\n换入旧末层MLP输出'],vv,color=['#9aa6b2','#3c87aa','#ad6544'])
    for i,v in enumerate(vv):ax.text(i,v+.02,f'{v:.1%}',ha='center',fontsize=12)
    ax.set(ylim=(0,1.08),ylabel='肺栓塞的候选相对支持',title='同一病例：换入旧计算，反而更支持新诊断');fig.tight_layout();savefig(fig,dest/'figures/clinical_intervention_example')
    matched=ten['matched_interfaces']['28'];total={'independent_new_cases':120,'new_code_observations':5040,'new_structured_name_observations':538,'model':'Qwen3-1.7B','api_cost_usd':0,
             'primary_sources':['../09_disease_name_trajectories/summary.json','../10_name_causal_mechanism/summary.json','../11_disease_information/summary.json']};(dest/'summary.json').write_text(json.dumps(total,ensure_ascii=False,indent=2)+'\n')
    (dest/'RESULTS.md').write_text(f'''# 医学信念研究：阶段06—11综合结果

**本轮最清楚的结果：模型内部含有可以识别疾病的信息，但它没有同样可靠地把这些信息变成诊断。另一个反直觉结果是：把旧计算放进新上下文，有时反而会加强新诊断。**

本轮完成120个新增模拟病例、24病种、6个疾病组；Qwen3-1.7B，28层、16个注意力头。本机M2 Pro GPU，收费API调用为0。所有实验参数冻结；每轮重新输入累计证据，未把前轮答案喂回。研究的是证据增加后的内部状态与判断变化。

## 1. 先看一个能理解的例子

病例`{cid}`：77岁女性，数据集的最终疾病标签为**肺栓塞**。

模型已看过前几组资料时，更偏向急性肺水肿。新增一条病史：**过去四周内，曾连续三天以上不能活动或起身。** 模型随即转向肺栓塞。

然后做内部实验：新证据仍保留，只将第28层诊断位置的MLP输出换成上一轮对应的数值。MLP是层内的一块计算，不是一个单独的疾病标签。

| 条件 | 肺栓塞的相对支持 | 当时首选 |
|---|---|---|
| 上一轮资料 | {old:.2%} | 急性肺水肿 |
| 加入新病史 | {current:.2%} | 肺栓塞 |
| 保留新病史，换入旧末层MLP输出 | {patched:.2%} | 肺栓塞 |

**换回旧计算，没有恢复旧诊断，反而加强了新诊断。** 这说明一块旧模块输出的作用取决于它与当前状态怎样组合；不能直接把它当成保存着“旧疾病”的容器。该例是说明，下面的总体统计才用于判断规律。

这例后面也没有一直保持正确：第5轮加入胸部疼痛的细节后，模型转向Boerhaave（食管破裂），到终点仍未命中肺栓塞标签。与此同时，第21层外部读出给肺栓塞的排名由第20升到第1。这种“读出由错转对、模型由对转错”的严格交叉，在固定24例178次更新中只出现于1例，作为线索保留，不作为总体规律。[全体相反更新统计](../11_disease_information/OPPOSITE_UPDATES.md)

![具体病例干预](figures/clinical_intervention_example.png)

[该病例每轮证据、疾病支持和内部状态](../09_disease_name_trajectories/cases/{cid}.md)

## 2. 全体病例是否随着证据接近最终疾病

使用49个完整疾病名评分，120例的标签命中为：**初始6例 → 中间27例 → 最终37例**。总体确有改善，但最终仍有83例没有把源标签排在首位。

固定24例的完整轨迹中，**7例曾命中标签又偏离**。相同完整事实仅将新增证据逆序，**12/24例首选改变**；独立乱序改变9/24例。仅反转候选列表也改变12/24例，因此不能将所有摇摆都归因于医学信息本身。

真正的新证据使疾病分布产生的改变量，平均大于行政说明：病例配对JS差为{fmt(ten['content_controls']['real_minus_administrative'],False)}。二者是自然措辞、未严格等长；重复已知证据同样可能引起变化。[详细轨迹与对照](../09_disease_name_trajectories/RESULTS.md)

![总体结果与内部信息](figures/main_findings.png)

## 3. 内部到底测到了什么

我们增加了一个外部线性读出器：只用其他病例训练，再从未见病例的层内状态识别疾病。同一病例的所有轮次都留在同一测试折，避免背题。

为了公平比较，将读出器和模型自身评分都限定到同样24种受试疾病：

| 方法 | 识别正确的病例 |
|---|---|
| 模型自己的疾病名排序 | **45/120，37.5%** |
| 从第21层状态读出 | **92/120，76.7%** |
| 从第28层状态读出 | **93/120，77.5%** |
| 直接用病例文本训练分类器 | **120/120，100%** |

第28层读出与模型自身排序的病例配对差为**40个百分点**，95%区间[30,50]。在24例完整轨迹中，有12例第21层读出已首次命中时，模型自身排序尚未命中过最终标签；3例相反。这里包括模型全程未命中的病例，不为它们虚构一次后来的命中。

**可以下的判断：内部状态保留了可用于区分疾病的信息，最终诊断没有稳定利用这些可读信息。** 但读出器是在其他病例上学习了“状态→疾病”的映射，高分不等于模型原先就按同样方式理解或使用这些信息。

文本基线的100%已独立复核：仅问题文字仍为120/120，仅证据ID为117/120；没有跨折完全重复的病例事实集合。这里“记录了哪些问题”本身携带了症状集合信息。这批模拟病例的标签结构很容易被外部分类器识别，后续必须固定问诊结构，进一步检验对答案内容的处理。

[内部疾病信息报告](../11_disease_information/RESULTS.md) · [文本基线审计](../11_disease_information/TEXT_AUDIT.md)

## 4. 旧的层间机制解释怎样修改

编码实验的120例确认了旧模式：换入上一轮MLP输出，第26、27层平均让最终分布远离旧分布，第28层让它靠近。

但改用完整疾病名后，**第28层的方向反过来了**。这不是仅由病例不同造成：取完全相同24例，第28层相对方向对照效应为：

| 输出设置 | 向旧判断靠近量 [95%区间] |
|---|---|
| 字母编码，两编码在病例内平均 | {fmt(matched['code_effect'],False)} |
| 完整疾病名 | {fmt(matched['name_effect'],False)} |

正数表示拉向旧分布，负数表示进一步远离。两个设置的病例配对差为{fmt(matched['code_minus_name'],False)}。疾病名条件下，7例原本发生首选切换的病例，没有一例因该替换恢复旧首选。

**因此收回“末层MLP保存着能直接恢复的旧医学信念”这一解释。当前支持的是：同一类内部计算对诊断的作用，依赖当前上下文和输出任务。** 输出设置同时改变列表形式、答案形式和自回归路径；下一步要分解这些作用。

补充检查发现，两接口第26—28层都扩大了新旧状态的整体距离。因此，“某层只是在把变化变小”也解释不了诊断方向的翻转，后续必须测疾病相关方向。

[内部干预](../10_name_causal_mechanism/RESULTS.md) · [状态变化幅度检查](../10_name_causal_mechanism/GEOMETRY.md)

## 5. 每层、注意力与真值如何使用

每个观测点保存28层的进入状态、注意力贡献、注意力后状态、MLP贡献、离层状态；每层16个头分别记录它对各组证据的注意力。固定24例另保存逐token注意力、各头输出及证据末位置状态。**变的是计算出来的状态，模型权重没有在这些轮次中重新训练。**

注意力到某个位置不等于那个位置贡献了多少医学信息：模板位置的状态也可能已整合前文。疾病名阶段，晚层状态方向变化与疾病分布改变量的病例内相关系数平均为0.639，95%区间[0.523,0.742]；这提供对应关系，不能代替干预。

120例都有源疾病标签，91例的标签同时也是源参考鉴别分布的首位。49候选完整覆盖参考分布。中间轮没有独立医学标准答案，因此“偏离”指偏离最终标签，不把每次中途改诊都自动叫作医学错误。

## 6. 本轮阶段交付

| 阶段 | 完成内容 | 结果 |
|---|---|---|
| 06 | 120例、49候选、5040个编码观测点，基础与逆序全轨迹 | [报告](../06_full_candidate_trajectories/RESULTS.md) |
| 07 | 28层、16头的状态与证据注意力 | [报告](../07_attention_and_layers/RESULTS.md) |
| 08 | 240个固定中间轮/编码条件，1200个前缀×层干预记录 | [报告](../08_causal_confirmation/RESULTS.md) |
| 09 | 538个完整病名观测点；120例三节点、24例完整轨迹 | [报告](../09_disease_name_trajectories/RESULTS.md) |
| 10 | 24例完整病名干预、内容和候选列表控制、跨接口配对 | [报告](../10_name_causal_mechanism/RESULTS.md) |
| 11 | 120例五折真实疾病读出、跨接口测试、标签置换、文本审计 | [报告](../11_disease_information/RESULTS.md) |

[120例编码轨迹](../06_full_candidate_trajectories/CASE_ATLAS.md) · [24例病名深描](../09_disease_name_trajectories/CASE_ATLAS.md) · [逐层逐轮疾病排名](../11_disease_information/heldout_trajectory_readouts.csv)

## 7. 论文主线与下一阶段

**主问题收敛为：医学证据进入模型后，哪些疾病信息被保留下来，哪些信息真正参与了诊断，二者为什么会分开？**

下一阶段优先做两件事：固定问诊问题与展示顺序，只改变已知答案的揭示；再用独立病例学到的疾病方向做定向干预，测它是否选择性改变对应疾病的完整名称支持。这样才能从“状态能读出来”走到“医学信息被怎样使用”。模型规模和先前诊断历史随后扩展。

当前发现已经把内部可读信息、实际诊断与局部计算作用分开测量。论文的创新性继续以具体可重复机制为依据，不因使用了探针或激活替换就宣称首次发现。

[更新后的ACL主线](../../acl_paper/01_STORY.md) · [下一阶段判据](../../acl_paper/04_NEXT_DECISIONS.md) · [复现步骤](../../protocol/FULL49_REPRODUCE.md)
''')
    verified=ROOT/'protocol/FULL49_DELIVERY_VERIFICATION.json'
    if verified.exists() and json.loads(verified.read_text()).get('passed'):
        v=json.loads(verified.read_text());p=dest/'RESULTS.md';p.write_text(p.read_text()+f'\n## 交付核验\n\n5578个新观测文件全量核验通过；五折读出的24例前缀分数独立重算通过；{v["png_figures"]}张PNG与{v["pdf_figures"]}份PDF已生成，内部链接检查通过。[核验记录](../../protocol/FULL49_DELIVERY_VERIFICATION.json)。\n')
    paper=ROOT/'acl_paper'
    (paper/'01_STORY.md').write_text('''# 论文主线 v0.3

## 一句话

**医学证据进入模型后，可以形成能被外部读出的疾病信息；这些信息是否参与了最终诊断，需要另行验证。**

工作标题：**模型有医学信念吗？——从证据更新到内部疾病信息与诊断选择**

英文工作标题：*Do Language Models Have Medical Beliefs? From Evidence Updates to Internal Disease Information and Diagnostic Choice*

“医学信念”仍是研究对象，不预设模型已有独立、稳定的疾病状态。当前论文研究同一病例在证据增加时的疾病支持、内部信息与实际计算作用。

## 从一个病例进入

77岁女性模拟病例，最终标签肺栓塞。新增“近四周连续三天以上不能活动”的病史后，肺栓塞相对支持由6.35%升到73.01%。保留新资料，只将末层MLP换回前轮输出，支持反而升到93.09%。

该病例后续加入疼痛细节后又转向Boerhaave，终点未命中标签，完整轨迹不截断。外部读出与原生判断在这一轮方向相反的严格交叉仅见于1/24例，因此病例只作引入，不将该稀有交叉包装为总体机制。

读者自然会问：旧计算为什么没有恢复旧诊断？模型内部可以识别的疾病信息，与最终作出的判断是不是同一个东西？案例只负责提出问题，正文随即给出同24例配对及120例总体结果。

## 现在有证据支持的三层论证

1. **证据与判断。** 120例、24病种、6个疾病组中，完整疾病名的最终标签命中从6/120增到37/120；24例完整轨迹中7例曾命中后偏离，12例在相同事实逆序后改变终点首选。更新并非单调，呈现因素也参与结果。
2. **信息与输出。** 公平限定同24类后，未见病例的第28层外部读出为93/120，模型自身名称排序为45/120。内部可读信息与实际输出之间存在显著差距。文本基线120/120、证据ID基线117/120表明输入结构高度可分；不能把外部读出高分直接当成模型已经理解诊断。
3. **计算与上下文。** 同24例的末层旧MLP替换，在编码接口拉向旧分布，在完整病名接口反而远离旧分布。局部旧计算不是可以直接搬运的旧疾病结论；其作用依赖当前上下文及输出任务。整体状态距离的收缩/放大不能解释该方向翻转。

## 核心问题如何继续深入

**输入中的医学信息怎样被编码、保留并用于选择疾病？**

后续先固定问诊结构，以排除“记录了哪些问题”自身的标签线索；然后使用独立病例学习的疾病方向，检验定向改变内部表示是否选择性改变相应疾病支持。将“可以读出”“模型实际使用”“跨表达仍稳定”逐层连起来。

若定向干预在固定问诊结构及独立病例上重复，可把中心结论推进到某种可解释的医学信息利用机制。若只是输出词选择变化，则保留为测量与输出机制结果，继续追踪更早的证据整合过程。

## 当前明确撤回的解释

“中间层一直知道正确疾病，最后层统一压制它”没有跨编码稳定复现；新增120例仍为0例。“第28层保存旧医学信念”受到疾病名条件下相反干预方向的直接挑战。二者不再作为摘要和引言的中心结论。

## ACL定位

论文围绕语言证据如何成为内部疾病信息、这些信息如何进入答案选择展开。输出形式、证据顺序与模型规模是成立条件；研究不缩成一个字母编码问题，也不以病例数量替代机制发现。

当前为单个1.7B模型、模拟问答病例。规模扩展是一个维度；主贡献应来自证据处理与信息利用的机制。已有相关研究覆盖医学更新、内部读出与激活替换，因此不以工具组合宣称新颖。

[本轮综合结果](../results/12_current_synthesis/RESULTS.md) · [证据表](03_EVIDENCE_LEDGER.md) · [相关工作](06_INTRODUCTION_RELATED_WORK.md)
''')
    (paper/'04_NEXT_DECISIONS.md').write_text('''# 下一阶段：从可读信息走向医学信息的因果使用

当前阶段06—11已完成。下一步不继续堆叠同类随机病例，优先解决两个已经由结果暴露的问题。

## 1. 固定问诊结构，让答案内容成为主要变量

同一任务的所有病例使用相同问题面板、相同位置和相同候选。问题面板从训练部分或公开字段字典构建，不能按测试病例的最终疾病临时选题。已知信息按原始来源填入，缺失保持“未知”，不把未记录改成“否”。每轮将若干未知答案替换为源病例已有答案，保留完整面板。

同时保存原始追加式版本作配对比较。病例按症状模板或证据结构分组切分，另设未见来源/模板的测试集。首先检查问题文字和证据ID基线是否降到无区分能力，再比较答案文本基线、模型输出和内部读出。

判据：若疾病信息仍可从内部读出，且更新随具体答案而变，才能将解释推进到医学内容的整合。仅由问题集合识别标签不承担这个结论。

## 2. 干预疾病方向，而不只替换整块旧MLP

从独立训练病例学习疾病对比方向，使用开发集固定层位、强度和读出方法。预留第21层与第28层作为当前结果提示的位置，确认集不得再次用于选层。

在未见病例中，沿目标疾病方向和竞争疾病方向分别改变状态。比较完整49病名称分布、目标疾病的选择性增益，以及其他同首词疾病是否一起上升。对照包括同范数随机方向、非目标疾病方向和不改变状态的自身替换。

完整病名跨多个token：分别干预回答前的诊断位置和名称续写过程，检查效应是否仅来自首词。只把“Acute”等首词变容易生成，不构成某种疾病概念的选择性干预。

判据：相应疾病的信息可读性和实际名称支持一起定向改变，且在固定问诊结构、不同表达和新病例中重复，才支持其被模型用于诊断。

## 3. 连接回医学证据

按当前症状、病史、检查确证等信息分层，使用源病例已有的可对照证据，匹配事实集合、提示长度与揭示位置。逐轮记录疾病排名、完整病名支持、证据位置与诊断位置状态。对诊断中明确提及的既往疾病/治疗单独分层。

DDxPlus的标签与参考鉴别分布继续同时保留。增加具有明确检验或影像确证的另一来源病例时，只使用来源中已有事实和最终诊断，不凭空编造每轮后验。

## 4. 再扩大历史条件和模型规模

在机制测量稳定后，加入无历史、模型自己的旧诊断、受控正确/错误旧诊断；相同新证据配对比较。随后扩展同系列更大模型，比较具体的信息利用与干预效应，不预设更强模型一定更稳定。

## 论文随结果更新

已观察的主结论是“内部可读疾病信息与最终输出存在差距，旧模块干预效应依赖输出设置”。下一阶段要解释差距由什么计算造成。若疾病方向干预没有选择性，继续检查读出和证据整合；不能把旧MLP的输出效应重新命名为医学信念存储。

[当前主线](01_STORY.md) · [阶段06—11总报告](../results/12_current_synthesis/RESULTS.md)
''')
    ledger=paper/'03_EVIDENCE_LEDGER.md';text=ledger.read_text().replace('# 论文证据表 v0.1','# 论文证据表 v0.3')
    start=text.index('## 统一样本口径');end=text.index('## 可供正文使用的证据')
    text=text[:start]+'''## 统一样本口径

历史阶段：12例探索、60例复现、180例读出训练/开发，共252个模拟病例，6600个观测点。新增阶段：独立120例、24病种、6疾病组，5040个编码观测点和538个完整疾病名观测点。总计372个不同模拟病例；新阶段读出五折训练仍使用这120例，不另算新病例。

新增完整病名主分析见阶段09，内部真实疾病读出见阶段11。编码与名称两个任务定义分开，24类读出只与同24类的模型评分直接比较。

'''+text[end:]
    text=text.replace('| P01 | 完整候选与参考鉴别诊断评价后，主要轨迹是否重复？ | 待完成 |','| P01 | 完整候选与参考鉴别诊断评价后，主要轨迹是否重复？ | 已完成新120例；完整病名中仍存在顺序与非单调轨迹 |')
    text=text.replace('| P02 | 对具体证据的逐头注意力，是否对应疾病状态变化？ | 尚未系统采集注意力矩阵 |','| P02 | 对具体证据的逐头注意力，是否对应疾病状态变化？ | 28层16头采集完成；注意力相关不作为因果证据 |')
    text=text.replace('| P03 | 在新患者上冻结检验，层间干预方向模式是否重复？ | 待完成 |','| P03 | 在新患者上冻结检验，层间干预方向模式是否重复？ | 编码任务确认；完整病名下末层方向相反，通用医学解释撤回 |')
    text=text.replace('| P05 | 不同疾病场景和模型规模是否共享该机制？ | 当前主结果为单模型、单组疾病 |','| P05 | 不同疾病场景和模型规模是否共享该机制？ | 已扩到6疾病组24病种；模型仍为1.7B |')
    text=text.replace('| P06 | 内部可读出真实疾病的信息，是否与模型实际使用的信息不同？ | 当前主要训练读出目标为同轮最终模型分布，非真实疾病标签 |','| P06 | 内部可读出真实疾病的信息，是否与模型实际使用的信息不同？ | 完成真实标签的病例隔离读出与文本审计；差距存在，医学方向因果使用待检验 |')
    text=text.replace('“注意力证明模型忽略了反证。”尚未完成相应注意力采集与因果验证。','“注意力证明模型忽略了反证。”已完成采集，仍需区分位置注意力与医学信息的因果贡献。').replace('## 当前尚没有的证据','## 后续问题的当前状态')
    marker='## 阶段06—11新增证据'
    if marker in text:text=text.split(marker)[0]
    text+='''\n## 阶段06—11新增证据

| ID | 结果与分母 | 状态与解释 | 来源 |
|---|---|---|---|
| E11 | 120/120例完整资料下首选随疾病—字母映射改变；跨编码稳定的晚层一致而末层转向为0/120 | 编码接口不作为医学主结果；旧层间压制故事未重复 | [06](../results/06_full_candidate_trajectories/RESULTS.md)、[07](../results/07_attention_and_layers/RESULTS.md) |
| E12 | 完整病名49候选：初始6/120，中间27/120，终点37/120命中标签；同病例编码终点21/120 | 新增总体轨迹，接口差异包含展示与输出方式 | [09](../results/09_disease_name_trajectories/RESULTS.md) |
| E13 | 固定24例：7例命中后偏离；证据逆序12例、乱序9例、候选列表逆序12例改变终点首选 | 顺序与呈现影响仍存在，不能统称医学更新错误 | [09](../results/09_disease_name_trajectories/summary.json) |
| E14 | 同24例第28层相对方向对照效应：编码+0.01719，名称−0.02080；配对差+0.03799 [0.01709,0.06140] | 旧MLP作用不是跨接口稳定的旧诊断恢复机制 | [10](../results/10_name_causal_mechanism/RESULTS.md) |
| E15 | 同24类、120例五折：第21层读出92/120，第28层93/120；模型自身名称评分45/120；第28层配对差40个百分点 [30,50] | 内部可读疾病信息与模型输出表现分离；未等同于模型实际使用 | [11](../results/11_disease_information/RESULTS.md) |
| E16 | 完整文本及仅问题文字120/120，证据ID117/120，年龄性别1/120；无跨折完全相同事实集合 | 数据记录结构高度可分，需要固定问诊结构与语义干预 | [文本审计](../results/11_disease_information/TEXT_AUDIT.md) |
| E17 | 名称条件24例真实新增证据减行政说明的JS变化差0.09779 [0.01647,0.19786] | 内容与行政条件有差异；自然文本长度未严格匹配 | [10](../results/10_name_causal_mechanism/summary.json) |
| E18 | 编码与名称条件的26—28层均扩大新旧状态的整体欧氏距离 | 简单的全局收缩/放大解释不能说明诊断干预方向翻转 | [几何补充](../results/10_name_causal_mechanism/GEOMETRY.md) |

E07在新编码病例中经预定Holm检验得到确认，但E14限制了其医学解释。E15的93/120不能与E12的37/120直接相减：前者24类，后者49候选。E16不证明病例重复或数据泄漏；证据ID本身代表记录的症状集合。
''';ledger.write_text(text)
    log=paper/'05_REVISION_LOG.md';oldlog=log.read_text();addition='''\n## v0.3 · 2026-11-18：新增阶段06—11并重写机制解释

新增120例、24病种的完整候选实验，逐头注意力、旧MLP确认、完整疾病名复查、真实疾病五折读出及文本结构审计。所有新数据均来自固定队列，未为制造机制更换病例。

主要调整：编码接口120例全部映射敏感，降为对照；同24例的末层旧MLP干预在疾病名任务中方向相反，撤回“末层保存旧医学信念”。内部可读信息与实际诊断之间存在40个百分点的同24类差距，但文本/证据ID基线也很高，故将下一步聚焦于固定问诊结构和疾病方向的因果使用。

主线更新为“医学信息如何被编码、保留并参与诊断选择”。保留先前结果作为发现过程，论文不以编码细节作为中心，也不宣称已经找到普遍的医学信念机制。完整证据、失败解释、数值排除和新图见[本轮综合报告](../results/12_current_synthesis/RESULTS.md)。
'''
    if '## v0.3' not in oldlog:log.write_text(oldlog+addition)
    readme=paper/'README.md';s=readme.read_text().replace('版本：v0.1','版本：v0.3');a=s.index('## 当前阶段');b=s.index('## 更新约定')
    s=s[:a]+'''## 当前阶段

阶段06—11已完成。主要新结果是：完整疾病名下的逐轮判断仍受顺序影响；外部读出可从内部识别更多疾病信息；旧MLP干预效应依赖输出设置。文本与证据ID基线暴露了强可分结构，下一阶段固定问诊面板并干预疾病相关方向。

[先读：本轮综合报告](../results/12_current_synthesis/RESULTS.md)。当前不再以“末层保存旧医学信念”作为中心论点。

'''+s[b:];readme.write_text(s)
    outline=paper/'02_PAPER_OUTLINE.md'
    outline.write_text('''# 全文结构 v0.3

论文按科学问题组织，当前实验支持部分论证，机制闭环仍按结果推进。主线是医学信息如何进入内部表示并参与诊断。

| 章节 | 核心问题 | 现有证据与所需补充 |
|---|---|---|
| Introduction | 为什么更多医学信息不保证稳定诊断？内部可读信息与实际使用是否一致？ | 用肺栓塞案例引入旧计算加强新判断，再接总体结果；相关工作见06 |
| Task and Measurement | 什么是本研究所测的疾病支持？真值、候选和病例如何统一？ | 120个新模拟病例、49完整病名、标签与参考分布、病例隔离；编码验证置于附录 |
| Evidence and Diagnostic Updates | 医学证据增加时，诊断如何改变？ | 阶段09的初始/中间/终点和24例完整轨迹，固定事实的顺序对照 |
| Internal Disease Information | 从哪些层可以识别疾病？是否早于最终输出？ | 阶段11五折读出、同24类公平比较、文本及标签置换基线；必须说明问诊结构高度可分 |
| Causal Role of Internal Computation | 改变某块计算是否改变疾病支持？旧状态的作用是否固定？ | 阶段10同病例跨接口替换，输出方向相反；几何补充排除简单全局距离解释 |
| Content-Specific Mechanism | 内部的疾病信息是否被选择性用于诊断？ | 下一阶段固定问诊结构、独立病例疾病方向干预；此节尚无完整结论 |
| Scope and Discussion | 哪些规律受表达、历史和规模影响？ | 已有顺序与输出设置对照；先前回答历史、模型规模和第二病例来源待扩展 |

## 主图

1. 一个病例的新增证据、内部替换与完整疾病名支持；说明问题，不承担总体证明。
2. 120例证据增加后的诊断表现，以及固定24例顺序效应。
3. 未见病例的逐层疾病读出，与同24类原生排序、文本基线和置换标签对照。
4. 同24例跨接口干预方向及区间；明确是完整输出设置的差异。
5. 固定问诊结构后的疾病方向因果检验，留待后续实验。

## 附录

完整病例轨迹与证据；候选概率与名称长度敏感性；源标签/参考鉴别诊断；数值检查和179个编码前缀×层排除记录；代码映射敏感性；注意力与原始层投影；文本结构审计；所有失败假设。

正文不以“中间层知道而末层压制”为既定故事。摘要待第5张图对应实验完成后再决定机制主张的强度。投稿年份、赛道与格式在确定投稿时核对官方要求。

[当前主线](01_STORY.md) · [证据表](03_EVIDENCE_LEDGER.md) · [本轮综合报告](../results/12_current_synthesis/RESULTS.md)
''')
    root=ROOT/'README.md';s=root.read_text().replace('# 医学证据更新的层间分歧','# 医学信念的逐轮与逐层变化')
    if '**当前入口：' not in s:s=s.replace('\n| 阶段 |','\n**当前入口：[阶段06—11综合报告](results/12_current_synthesis/RESULTS.md)**。\n\n| 阶段 |',1)
    insert='''| 06 完整候选 | 49疾病空间中的总体更新与测量可靠性 | [RESULTS](results/06_full_candidate_trajectories/RESULTS.md) |
| 07 层与注意力 | 每层、每头怎样处理证据 | [RESULTS](results/07_attention_and_layers/RESULTS.md) |
| 08 干预确认 | 旧MLP方向模式是否在新病例复现 | [RESULTS](results/08_causal_confirmation/RESULTS.md) |
| 09 疾病全名 | 完整病名的逐轮支持与顺序效应 | [RESULTS](results/09_disease_name_trajectories/RESULTS.md) |
| 10 病名干预 | 旧计算在新上下文中如何影响诊断 | [RESULTS](results/10_name_causal_mechanism/RESULTS.md) |
| 11 疾病信息 | 未见病例的真实疾病读出与文本审计 | [RESULTS](results/11_disease_information/RESULTS.md) |
| 12 综合 | 当前结论、具体病例与论文主线 | [RESULTS](results/12_current_synthesis/RESULTS.md) |
'''
    if '| 06 完整候选' not in s:s=s.replace('\nresults 仅保存','\n'+insert+'\nresults 仅保存')
    s=s.replace('[下一阶段方案](results/05_synthesis/NEXT_EXPERIMENTS.md) · [复现说明](protocol/REPRODUCE.md)',
                '[下一阶段方案](acl_paper/04_NEXT_DECISIONS.md) · [本轮复现](protocol/FULL49_REPRODUCE.md) · [阶段01—05复现](protocol/REPRODUCE.md)')
    root.write_text(s.replace('|\n\n| 06 完整候选','|\n| 06 完整候选'))

if __name__=='__main__':main()
