"""Analyze actual saved predictions. No synthetic model results and no new inference."""
from collections import defaultdict
from pathlib import Path
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT/"runs/phase1_qwen3_1p7b"
FIG = ROOT/"figures/phase1"
FIG.mkdir(parents=True, exist_ok=True)
rows = [json.loads(s) for s in (RUN/"predictions.jsonl").read_text().splitlines()]
meta = json.loads((RUN/"metadata.json").read_text())
completion = json.loads((RUN/"completion.json").read_text())
assert completion["complete"] and len(rows) == 864
assert len({r['record_id'] for r in rows}) == len(rows)
stages = ["initial", "evidence", "confirmed", "withdrawn"]
domains = ["aki", "bp", "dvt"]
names = {"aki":"肌酐变化标准", "bp":"血压确认规则", "dvt":"血栓检查路径"}
stage_names = ["检查未到", "有效检查到达", "再次确认来源", "检查被撤回"]
groups = {}
for d in domains:
    groups[d] = {}
    for s in stages:
        rr = [r for r in rows if r['domain'] == d and r['stage'] == s and r['prior'] == 'none']
        groups[d][s] = {"records": len(rr), "bases": len({r['base_id'] for r in rr}),
            "candidate_accuracy": float(np.mean([r['prediction'] == r['gold'] for r in rr])),
            "unconstrained_first_token_accuracy": float(np.mean([r['unconstrained_top_token_semantic'] == r['gold'] for r in rr])),
            "mean_candidate_mass": float(np.mean([r['candidate_mass'] for r in rr])),
            "mean_correct_probability": float(np.mean([r['semantic_probs'][r['gold']] for r in rr]))}

lookup = {(r['base_id'],r['positive_report'],r['mapping'],r['stage'],r['prior']):r for r in rows}
gaps = {}
rng = np.random.default_rng(20261117)
for d in domains:
    gaps[d] = {}
    for s in stages:
        grouped = defaultdict(list)
        changes = []
        for r in rows:
            if r['domain'] != d or r['stage'] != s or r['prior'] != 'yes':
                continue
            other = lookup[(r['base_id'],r['positive_report'],r['mapping'],s,'no')]
            diff = r['semantic_probs']['yes'] - other['semantic_probs']['yes']
            grouped[r['base_id']].append(diff)
            changes.append(r['prediction'] != other['prediction'])
        base_effect = np.array([np.mean(v) for v in grouped.values()])
        bs = base_effect[rng.integers(0,len(base_effect),(5000,len(base_effect)))].mean(1)
        gaps[d][s] = {"mean_yes_probability_difference": float(base_effect.mean()),
            "base_cluster_bootstrap_ci95": np.quantile(bs,[.025,.975]).tolist(),
            "base_effects": dict(zip(grouped,map(float,base_effect))),
            "paired_decision_disagreement":float(np.mean(changes))}

statefiles = {r['activation_file'] for r in rows}
assert len(statefiles) == 756
assert all((RUN/p).exists() for p in statefiles)
checks = json.loads((RUN/"instrument_checks.json").read_text())
for p in sorted(statefiles)[::97]:
    z=np.load(RUN/p)
    assert z['activations'].shape == (meta['layers'],3,meta['hidden_size'])
    assert np.isfinite(z['activations']).all()
summary = {"scope":"phase 1 instrument validation; not a mechanism finding", "records":len(rows),
    "bases":len({r['base_id'] for r in rows}), "unique_activations":len(statefiles),
    "neutral_accuracy":groups, "paired_supplied_prior_effect":gaps,
    "mean_candidate_mass":float(np.mean([r['candidate_mass'] for r in rows])),
    "candidate_mass_min":float(min(r['candidate_mass'] for r in rows)),
    "first_token_not_an_option":sum(r['unconstrained_top_token_semantic'] is None for r in rows),
    "instrument_checks":checks, "api_cost_usd":0,
    "independent_clinical_review":False, "prior_is_model_generated":False}
(RUN/"analysis.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n")

plt.rcParams.update({"font.family":["Arial Unicode MS","DejaVu Sans"],"font.size":11,
    "axes.spines.top":False,"axes.spines.right":False})
fig,ax=plt.subplots(figsize=(10,5))
colors=['#217b87','#b26c32','#775bab']
for d,c in zip(domains,colors):
    ax.plot(range(4),[100*groups[d][s]['candidate_accuracy'] for s in stages],marker='o',label=names[d],color=c)
ax.set_xticks(range(4),stage_names)
ax.set_ylim(-3,103)
ax.set_ylabel('限定选项下的规则回答正确率（%）')
ax.set_title('阶段1：没有先前判断时，模型能否按当前证据回答？')
ax.legend()
ax.grid(alpha=.18)
fig.text(.5,.015,'Qwen3-1.7B，本地非思考模式；12个病例骨架，仅用于仪器与规则理解检查',ha='center',fontsize=9)
fig.tight_layout(rect=[0,.045,1,1])
for ext in ['png','pdf']: fig.savefig(FIG/f'01_rule_comprehension.{ext}',dpi=180)
plt.close(fig)

fig,axes=plt.subplots(1,3,figsize=(13,4.6),sharey=True)
for ax,d,c in zip(axes,domains,colors):
    vals=[100*gaps[d][s]['mean_yes_probability_difference'] for s in stages]
    err=[[v-100*gaps[d][s]['base_cluster_bootstrap_ci95'][0] for v,s in zip(vals,stages)],
         [100*gaps[d][s]['base_cluster_bootstrap_ci95'][1]-v for v,s in zip(vals,stages)]]
    ax.bar(range(4),vals,color=c,yerr=err,capsize=3)
    ax.axhline(0,color='black',lw=.8)
    ax.set_xticks(range(4),['未到','有效','确认','撤回'])
    ax.set_title(names[d]);ax.grid(axis='y',alpha=.15)
axes[0].set_ylabel('先前倾向“是”减去倾向“否”\n对“是”选项的概率影响（百分点）')
fig.suptitle('相同医学事实下，提供的先前判断怎样影响当前输出？')
fig.text(.5,.012,'每域仅4个骨架；区间按骨架重采样。此处是上下文影响，尚不是内部信念机制。',ha='center',fontsize=9)
fig.tight_layout(rect=[0,.06,1,.95])
for ext in ['png','pdf']:fig.savefig(FIG/f'02_supplied_prior_effect.{ext}',dpi=180)
plt.close(fig)

lines=["# 阶段1交付：规则理解与内部采集验证", "",
"本阶段已经运行本地开放权重模型。以下数值来自保存的真实模型输出；没有人工填充结果。研究目标仍是医学信念机制，本阶段只验证实验仪器与基础能力。", "",
f"模型：`{meta['model']}`；固定提交`{meta['revision']}`；{meta['layers']}层，隐藏维度{meta['hidden_size']}；本地{meta['device']}、{meta['dtype']}、非思考模式。", "",
"**完成了什么。** 12个病例骨架、216条配对轨迹、864条阶段记录，共756个不同提示。三类任务分别是肌酐变化标准、血压确认规则和血栓初始检查路径。每条轨迹比较检查未到、有效检查到达、来源再次确认及报告撤回。", "",
"**先看一道真实跑过的题。** 给定规则：48小时内肌酐升高至少26 μmol/L满足这条标准。病例`aki_00`的有效报告写着：24小时内从70升到100。报告撤回时，题目明确说明它属于其他患者，而且没有替代报告。下面固定展示无旧判断、选项轮换0的这一个预定病例；它不是从错误案例里挑选出来的。", "",
"| 证据到了哪一步 | 按题目规则应回答 | 模型在限定选项中选择 |", "|---|---|---|"]
words = {"yes":"满足这条标准", "no":"不满足这条标准", "unknown":"资料不足"}
for s,label in zip(stages,stage_names):
    r = lookup[("aki_00",True,0,s,"none")]
    lines.append(f"| {label} | {words[r['gold']]} | {words[r['prediction']]} |")
lines += ["",
"**没有先前判断时的基础结果。** 下表是限定A/B/C候选中的最高分答案；完整词表质量检查另列。每域只有4个骨架，多种选项轮换不算独立病例。", "",
"| 任务 | 检查未到 | 有效检查 | 来源确认 | 报告撤回 |", "|---|---:|---:|---:|---:|"]
for d in domains:
    lines.append('| '+names[d]+' | '+' | '.join(f"{100*groups[d][s]['candidate_accuracy']:.1f}%" for s in stages)+' |')
lines += ["", "![基础理解](../figures/phase1/01_rule_comprehension.png)", "",
"**先前判断的影响。** 在相同事实下，把提供的旧判断从“否”改为“是”，观察模型对“是”的输出概率变化。这个差值测的是上下文中的先前判断影响；本阶段没有让模型自然形成并保存初始医学判断。", "",
"![先前判断影响](../figures/phase1/02_supplied_prior_effect.png)", "",
"**内部数据已经取得。** 每个不同提示都保存全部解码层、3个预定义位置的输出向量，位置包括读完提示处、报告结尾和最新来源说明结尾。初始阶段不存在的报告/来源位置带缺失标记，不把占位向量用于分析。", "",
f"每份激活数组形状为`{meta['layers']} × 3 × {meta['hidden_size']}`，共{len(statefiles)}份；本轮采集没有训练或修改模型权重。被动采集对照的最大答案logit差为{max(c['capture_vs_plain_max_logit_difference'] for c in checks):.8g}。", "",
f"**答案格式检查。** 候选字母在完整词表中的平均概率质量为{summary['mean_candidate_mass']:.4f}，最小值为{summary['candidate_mass_min']:.4f}；{summary['first_token_not_an_option']}/{len(rows)}条记录的完整词表首选词元不是有效选项。条件化候选分数不能直接当作真实患病概率。", "",
"**现在能够说到哪里。** 可以评价采集流程、这组限定规则题的基础理解和提供旧判断的影响。不能宣布发现医学信念、证明某种内部机制，也不能据此推广到大型模型或实际诊疗。尚未开展独立医学审核、跨模板验证、训练读出器或有科学对照的因果干预。", "",
"**下一阶段。** 根据各域的基础理解表现，优先修正任务理解与表达问题，补充新模板和专业审核；随后在严格留出的病例上测量事实、证据条件和判断倾向。词面基线和随机标签对照同时运行，再决定哪些位置值得因果干预。", "",
"**复现与文件。** [论文逻辑](../paper/PAPER_LOGIC.md)、[分阶段计划](../protocol/STAGES.md)、[规则来源](../protocol/SOURCES.md)、[完整统计](../runs/phase1_qwen3_1p7b/analysis.json)、[逐条输出](../runs/phase1_qwen3_1p7b/predictions.jsonl)、[采集代码](../src/run_phase1.py)、[分析代码](../src/analyze_phase1.py)。激活在运行目录的`states/`中。", "",
"本轮收费API支出0美元，本地电力未计量。"]
(ROOT/'reports/PHASE1.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({"neutral_accuracy":groups,"mean_candidate_mass":summary['mean_candidate_mass'],
    "first_token_not_an_option":summary['first_token_not_an_option']},ensure_ascii=False,indent=2))
