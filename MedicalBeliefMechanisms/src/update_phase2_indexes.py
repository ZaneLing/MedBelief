"""Update live navigation after completed runs; historical snapshots remain intact."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=json.loads((ROOT/'runs/phase3_followup_summary.json').read_text());assert p['records']==160
    readme=ROOT/'README.md';s=readme.read_text()
    start=s.index('当前新增：');end=s.index('\n\n此前交付：',start)
    s=s[:start]+'''当前交付：[本轮易读报告与结果图](reports/PHASE2_READ_FIRST.md)。阶段2A—2D、测量修正、阶段3更新预试验及其复测已完成，新增1120条实际输出、42个数值病例骨架、752份内部快照、12组PNG/PDF图，收费API支出0美元。旧判断维护没有稳定成立；内部读出迁移不稳；撤回证据后出现更新错误，已进行整组第二采样、措辞与历史对照。仍未确立独有医学信念机制。

[病例怎样使用](reports/PHASE2_CASES.md) · [内部怎样测量](reports/PHASE2_METHODS_PLAIN.md) · [阶段3后续更新](reports/PHASE3_PILOT_READ_FIRST.md) · [复现与修订](reports/PHASE2_REPRODUCE.md) · [交付校验清单](protocol/phase2_delivery.json)'''+s[end:]
    s=s.replace('| 2：本轮探索 | 2A已完成；血压修正及2B新病例确认正在运行 | [2A结果](reports/PHASE2A_READ_FIRST.md)、[当前设计](protocol/PHASE2_EXECUTION.md) |','| 2：行为与表示探索 | 2A—2D及测量修正完成；跨模板稳定性要求仍未达到 | [本轮结果](reports/PHASE2_READ_FIRST.md)、[详细表](reports/PHASE2_TABLES.md) |')
    s=s.replace('| 3—6 | 尚未执行 | 按[阶段计划](protocol/STAGES.md)及前置证据递进 |','| 3：未来更新 | 160条预试验、复测和修正完成；未显示内部状态超越文字的预测增益；完整阶段未完成 | [预试验报告](reports/PHASE3_PILOT_READ_FIRST.md) |\n| 4—6 | 内部因果、第二模型复现及论文定稿尚未完成 | 按[阶段计划](protocol/STAGES.md)及前置证据递进 |')
    readme.write_text(s)
    f=ROOT/'protocol/STAGES.md';s=f.read_text();start=s.index('2026-11-18交付更新：');end=s.index('\n\n| 阶段',start)
    s=s[:start]+'''2026-11-18交付更新：阶段0、1、1B的历史结果保留。本轮完成阶段2A—2D及读出修正，共960条生成；另完成阶段3预试验、整组第二种子和三种修正，共160条。详见[本轮易读报告](../reports/PHASE2_READ_FIRST.md)。完成了这些运行不等于原阶段2所有科学门槛通过：42个数值骨架不等于原计划60个多结构骨架，跨新表述的内部读出不稳定，完整阶段3也未显示相对文字的增量解释。阶段4内部干预未开始。不能将探索完成写成机制证明完成。'''+s[end:]
    s+='''
## 下一交付单元：建立可迁移的医学证据关系测量

本轮没有稳定旧判断维护，后续先检验“模型如何保留结论和依据的对应关系”，而不是继续为预设结论寻找孤例。

1. 将报告身份、可使用条件、独立替代支持分别改变。使用来源状态明确、无“未修改”歧义的新病例和新表达；保持数字及正确结论可配对。
2. 整条轨迹包括原判断、证据变化、依据撤回；保留无先前回答、真实先前回答、等长中性历史。多个种子估计反应分布，不能只找一次错误。
3. 在回答前、思考结束和来源说明之后分别记录状态。所有确认模板完全留出；开发阶段固定读出与候选位置。
4. 控制当前答案及其分数、可见文字特征后，再检验内部状态的增量预测。若仍无增益，收缩测量结论，不称隐藏信念。
5. 只有出现跨表述复现的行为差异及可用候选测量，才进入阶段4的自身、同条件、随机、双向替换等因果对照。若不满足，继续报告行为和测量边界。

研究质量、患者适用性与第二模型是后续广度维度；本轮只验证局部规则下的证据处理，不将它们写成已覆盖内容。以上是下一单元的设计要求，尚未运行，也不是结果。
''';f.write_text(s)
    f=ROOT/'paper/PAPER_LOGIC.md';s=f.read_text();start=s.index('当前实证进展（2026-11-18）：');end=s.index('**与已有工作的关系。**',start)
    s=s[:start]+'''当前实证进展（2026-11-18）：[本轮报告](../reports/PHASE2_READ_FIRST.md)新增1120条实际输出、42个数值骨架和752份内部快照。2A和2B没有建立稳定的旧判断维护；血压中“正确局部数字说明使整体判断变差”的个例在肌酐/DVT复查中没有复现。内部来源信息可读出，但跨表述迁移不稳定，第26层在2B的选后高分没有迁移到2C。

最接近论文入口的实际例子是：模型先正确指出R1不能用，并用R2作出正确判断；R2撤回后，它却重新使用R1。首次3条错误，整组第二采样4条错误；完整措辞、明确状态和删除旧回答对照见[更新试验](../reports/PHASE3_PILOT_READ_FIRST.md)。这些失败集中于一类措辞，尚不能归因于自我辩护或稳定信念。未来改口的预测中，预定内部末层与文字基线都为86.4%，没有观察到内部增益。当前未做内部因果干预。

论文主问题继续锚定：**它是否知道医学结论依赖什么，以及依据改变后能否保持正确的证据关系？** 不能用当前准确率替代这个问题，也不能把一个易歧义句子当成新机制。首先在新模板、不同证据资格与替代支持下找到稳定现象；再用回答前／思考后测量和增量预测，最后用选择性干预检验内部作用。

现阶段可写的是受控探索和测量失败边界，不能写成“发现了一种全新医学信念机制”。原计划的广泛结构病例确认、当前答案概率控制、内部因果和第二模型仍欠缺。这里的信念是研究问题，尚非已经被验证的内部变量。

'''+s[end:]
    s+='''
本轮新增的直接竞争解释包括上下文干扰、语句或答案词复用、临床关键信息扰动和其他患者信息误归属。具体原论文链接与重合边界见[本轮新颖性核查](../reports/PHASE2_NOVELTY_BOUNDARY.md)。核查是针对当前现象的原始来源查阅，不是穷尽检索；不声称“别人从未做过”。
''';f.write_text(s)
    f=ROOT.parent/'paper/README.md';s=f.read_text();start=s.index('新的独立执行目录：');end=s.index('\n\n医学研究的前期讨论稿：',start)
    s=s[:start]+'''新的独立执行目录：[MedicalBeliefMechanisms](../MedicalBeliefMechanisms/README.md)。最新为[本轮医学信念实验报告](../MedicalBeliefMechanisms/reports/PHASE2_READ_FIRST.md)：完成阶段2A—2D、测量修正和阶段3小型预试验及复测，新增1120条输出、752份内部快照、12组结果图。未建立稳定旧判断维护；发现依据撤回后的更新错误，已追加措辞与历史对照；内部预测未超过文字基线。仍未确立独有机制。研究定位保持为医学信念机制分析，不设医生审核门槛。此前[阶段1B](../MedicalBeliefMechanisms/reports/PHASE1B_READ_FIRST.md)、[阶段1](../MedicalBeliefMechanisms/reports/PHASE1_READ_FIRST.md)和前期探索全部保留。'''+s[end:];f.write_text(s)
    f=ROOT/'protocol/PHASE2_WORKING_STATUS.md';s=f.read_text();s+='''
最终交付：2A—2D全部运行完成；追加阶段3首次32条、第二采样32条、措辞及历史修正96条也全部完成。最终结果以`reports/PHASE2_READ_FIRST.md`、`reports/PHASE3_PILOT_READ_FIRST.md`和`protocol/phase2_delivery.json`为准。此前“正在运行”“尚未查看”描述是当时的过程记录，不是当前状态。未完成完整阶段3及内部因果阶段。
''';f.write_text(s)
    for name in ['PHASE2A_READ_FIRST.md','PHASE2B_READ_FIRST.md','PHASE2_BP_READ_FIRST.md']:
        f=ROOT/'reports'/name;s=f.read_text();s+='\n后续批次现已结束，本文中的后续计划属于当时状态；最终汇总见[本轮完整报告](PHASE2_READ_FIRST.md)。\n';f.write_text(s)
    print('Updated live indexes; phase1B document snapshots retained')
if __name__=='__main__':main()
