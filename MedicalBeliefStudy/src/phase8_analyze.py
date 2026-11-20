"""Prespecified confirmation plus descriptive content/interface controls."""
import json
from pathlib import Path
from collections import defaultdict
import numpy as np
from scipy.stats import ttest_1samp
import matplotlib.pyplot as plt
from analyze_stages import ci, fmt, js, winner, changed, setup, savefig, csvwrite, dump
ROOT=Path(__file__).resolve().parents[1]
def main():
    setup();run=ROOT/'runs/full49_v1';dest=ROOT/'results/08_causal_confirmation';(dest/'figures').mkdir(parents=True,exist_ok=True)
    assert (run/'depth_interventions/completion.json').exists();assert (run/'content_controls/completion.json').exists()
    cases={r['case_id']:r for r in map(json.loads,(ROOT/'data/full49_v1/cases.private.jsonl').read_text().splitlines())};diseases=json.loads((run/'manifest.json').read_text())['candidate_diseases']
    rows=[json.loads(p.read_text()) for p in sorted((run/'depth_interventions').glob('ddx*.json'))];assert len(rows)==1200
    effects=[];excluded=[]
    for r in rows:
        if not r['numerically_stable']:excluded.append({k:r[k] for k in ['job_id','layer','sham_max_candidate_logit_error']});continue
        old=np.array(r['previous_q']);cur=np.array(r['current_q']);pq=np.array(r['q']);baseline=float(js(cur,old));gain=baseline-js(pq,old)
        oldtop=int(winner(old));curtop=int(winner(cur));sw=bool(changed(old,cur));y=diseases.index(cases[r['case_id']]['gold_disease'])
        e={k:r[k] for k in ['job_id','case_id','family','rotation','layer']};e.update(old_current_js=baseline,old_current_switch=sw,previous_label_correct=oldtop==y,current_label_correct=curtop==y)
        for j,name in enumerate(r['components']):
            e[name+'_gain']=float(gain[j]);e[name+'_candidate_mass']=r['candidate_mass'][j]
            e[name+'_recovery']=bool(sw and winner(pq[j])==oldtop)
            e[name+'_label_support_change']=float(pq[j,y]-cur[y])
        e['mlp_minus_direction']=float(gain[2]-gain[4]);e['attention_minus_direction']=float(gain[1]-gain[3]);effects.append(e)
    csvwrite(dest/'intervention_events.csv',effects);dump(dest/'numerical_exclusions.json',excluded)
    bycase=[]
    for layer in range(24,29):
        for cid,c in cases.items():
            rr=[r for r in effects if r['layer']==layer and r['case_id']==cid]
            if not rr:continue
            keys=[k for k in rr[0] if k.endswith('_gain') or k.endswith('_direction') or k.endswith('_label_support_change')]
            r={'case_id':cid,'family':c['family'],'layer':layer,'valid_mappings':len(rr),**{k:float(np.mean([v[k] for v in rr])) for k in keys}}
            switched=[v for v in rr if v['old_current_switch']]
            for k in ['previous_mlp','shifted_mlp_difference','previous_attention','shifted_attention_difference']:
                r[k+'_recovery']=float(np.mean([v[k+'_recovery'] for v in switched])) if switched else None
            bycase.append(r)
    csvwrite(dest/'case_interventions.csv',bycase)
    summaries={}
    for layer in range(24,29):
        rr=[r for r in bycase if r['layer']==layer];keys=[k for k in rr[0] if k.endswith('_gain') or k.endswith('_direction') or k.endswith('_label_support_change')]
        summaries[str(layer)]={k:ci([r[k] for r in rr]) for k in keys}
        for k in ['previous_mlp_recovery','shifted_mlp_difference_recovery','previous_attention_recovery','shifted_attention_difference_recovery']:
            summaries[str(layer)][k]=ci([r[k] for r in rr if r[k] is not None])
    tests=[]
    for l in [26,27,28]:
        vals=[r['mlp_minus_direction'] for r in bycase if r['layer']==l];t=ttest_1samp(vals,0.)
        tests.append({'layer':l,'n_cases':len(vals),'expected_sign':-1 if l<28 else 1,'mean':float(np.mean(vals)),'t':float(t.statistic),'p_two_sided':float(t.pvalue)})
    rank=sorted(range(3),key=lambda i:tests[i]['p_two_sided']);last=0
    for j,i in enumerate(rank):last=max(last,min(1.,(3-j)*tests[i]['p_two_sided']));tests[i]['p_holm']=last
    for t in tests:t['direction_confirmed']=bool(np.sign(t['mean'])==t['expected_sign'] and t['p_holm']<.05)
    # Nonclinical controls are naturally worded, with lengths reported rather than assumed matched.
    content=[json.loads(p.read_text()) for p in sorted((run/'content_controls').glob('ddx*.json'))];assert len(content)==240
    cr=[]
    for r in content:
        old=np.array(r['previous_q']);real=np.array(r['real_q']);y=diseases.index(cases[r['case_id']]['gold_disease'])
        row={'case_id':r['case_id'],'family':r['family'],'rotation':r['rotation'],'real_js':float(js(real,old)),
             'real_flip':bool(changed(real,old)),'real_delta_gold':float(real[y]-old[y]),'real_added_tokens':r['real_tokens']-r['previous_tokens']}
        for c in r['conditions']:
            q=np.array(c['q']);name=c['condition'];row.update({name+'_js':float(js(q,old)),name+'_flip':bool(changed(q,old)),
              name+'_delta_gold':float(q[y]-old[y]),name+'_added_tokens':c['input_tokens']-r['previous_tokens'],
              'real_minus_'+name+'_js':float(js(real,old)-js(q,old))})
        cr.append(row)
    csvwrite(dest/'content_events.csv',cr);content_cases=[]
    for cid,c in cases.items():
        rr=[r for r in cr if r['case_id']==cid];content_cases.append({'case_id':cid,'family':c['family'],**{k:float(np.mean([r[k] for r in rr])) for k in rr[0] if k not in ['case_id','family','rotation']}})
    csvwrite(dest/'content_case_metrics.csv',content_cases);content_summary={k:ci([r[k] for r in content_cases]) for k in content_cases[0] if k not in ['case_id','family']}
    sensitivity={}
    for layer in [26,27,28]:
        byid=defaultdict(list)
        for r in rows:
            if r['layer']==layer:byid[r['case_id']].append(float(js(r['q'][4],r['previous_q'])-js(r['q'][2],r['previous_q'])))
        sensitivity[str(layer)]=ci([np.mean(v) for v in byid.values()])
    summary={'planned_prefix_depth_records':1200,'valid_prefix_depth_records':len(effects),'numerically_excluded':len(excluded),'layers':summaries,
             'unfiltered_relative_effect_sensitivity':sensitivity,
             'primary_tests':tests,'three_layer_pattern_confirmed':all(t['direction_confirmed'] for t in tests),'content':content_summary}
    dump(dest/'summary.json',summary)
    fig,axes=plt.subplots(1,2,figsize=(12,4.6));ls=list(range(24,29))
    for k,label in [('previous_mlp_gain','Previous MLP'),('shifted_mlp_difference_gain','Direction control')]:
        vals=[summaries[str(l)][k] for l in ls];axes[0].errorbar(ls,[v['mean'] for v in vals],yerr=[[v['mean']-v['low'] for v in vals],[v['high']-v['mean'] for v in vals]],marker='o',capsize=3,label=label)
    axes[0].axhline(0,color='gray',lw=.8);axes[0].set(xlabel='Intervened layer',ylabel='JS movement toward previous round');axes[0].legend()
    ks=['real_js','administrative_js','repeat_initial_js'];vals=[content_summary[k] for k in ks]
    axes[1].bar(range(3),[v['mean'] for v in vals],yerr=[[v['mean']-v['low'] for v in vals],[v['high']-v['mean'] for v in vals]],capsize=4)
    axes[1].set(xticks=range(3),xticklabels=['New evidence','Administrative text','Repeated evidence'],ylabel='JS change from previous round');fig.tight_layout();savefig(fig,dest/'figures/causal_and_content')
    tab='\n'.join(f'| {l} | {fmt(summaries[str(l)]["previous_mlp_gain"],False)} | {fmt(summaries[str(l)]["mlp_minus_direction"],False)} |' for l in ls)
    testtab='\n'.join(f'| {t["layer"]} | {"负" if t["expected_sign"]<0 else "正"} | {t["mean"]:+.6f} | {t["p_holm"]:.5g} | {"确认" if t["direction_confirmed"] else "未确认"} |' for t in tests)
    verdict='三个预定层的方向模式在新病例中得到确认。' if summary['three_layer_pattern_confirmed'] else '此前的三个层方向模式没有完整复现，应从论文的已确认机制中移除。'
    (dest/'RESULTS.md').write_text(f'''# 阶段08：旧计算是否推动模型回到前轮判断

## 方法

120例的固定中间轮、两个编码，共240个前缀。分别在24—28层替换诊断位置的注意力增量或MLP增量，替换来源为同病例前轮。方向对照将相同差向量沿隐藏维度循环移位257位，保留范数；自身替换检查数值误差。其他输入事实保持当前轮不变，计算后续层输出。

主要指标：JS(当前分布,前轮分布) − JS(干预分布,前轮分布)。正值表示向前轮靠近，负值表示远离；前轮不一定正确。报告原替换效应和减去方向对照后的效应。先病例内平均编码，再计算病例bootstrap区间。26、27、28层三个预定检验使用双侧t检验与Holm校正。

## 干预结果

| 层 | 旧MLP替换：向前轮靠近量 [95%区间] | 减去方向对照后的效应 [95%区间] |
|---|---|---|
{tab}

| 层 | 预定方向 | 相对方向对照的均值 | Holm校正p | 结论 |
|---|---|---|---|---|
{testtab}

**{verdict}** 共1200个前缀×层记录，{len(excluded)}个未通过自身替换数值检查，被排除于效应分析；原始记录全部保留。每层有效病例数和编码数在数据表中单列。

探索性敏感性分析保留所有记录：第26、27、28层相对方向对照效应分别为{fmt(sensitivity['26'],False)}、{fmt(sensitivity['27'],False)}、{fmt(sensitivity['28'],False)}。它用于判断数值排除的影响，不替代预定主要分析。

## 非医学新增内容

同一前轮分别追加真实新证据、行政记录说明或重复初始证据；后两者不增加新的临床事实。其疾病分布变化JS为：

| 追加内容 | 改变量 [95%区间] | 首选改变率 [95%区间] | 平均新增token |
|---|---|---|---|
| 真实新证据 | {fmt(content_summary['real_js'],False)} | {fmt(content_summary['real_flip'])} | {content_summary['real_added_tokens']['mean']:.1f} |
| 行政说明 | {fmt(content_summary['administrative_js'],False)} | {fmt(content_summary['administrative_flip'])} | {content_summary['administrative_added_tokens']['mean']:.1f} |
| 重复初始证据 | {fmt(content_summary['repeat_initial_js'],False)} | {fmt(content_summary['repeat_initial_flip'])} | {content_summary['repeat_initial_added_tokens']['mean']:.1f} |

真实减行政的JS差为{fmt(content_summary['real_minus_administrative_js'],False)}，真实减重复的差为{fmt(content_summary['real_minus_repeat_initial_js'],False)}。自然文本长度未严格匹配，因此这些对比测量不同输入条件的敏感性，不单独分离语义与长度。

![干预与内容](figures/causal_and_content.png)

## 解释范围

本轮确认的是冻结1.7B模型、49疾病编码接口中诊断位置的局部计算作用。替换具有因果意义，但跨轮状态替换并非自然医学证据编辑；恢复前轮也不等于改善诊断。是否能用疾病名及更自然的证据干预复现，将决定它能否上升为医学信念机制。

[干预逐病例数据](case_interventions.csv) · [内容逐病例数据](content_case_metrics.csv) · [精确结果](summary.json) · [数值排除记录](numerical_exclusions.json)
''')
    if (run/'name_controls/completion.json').exists():analyze_names(run,dest,cases,diseases)
    print(json.dumps(summary,ensure_ascii=False),flush=True)

def analyze_names(run,dest,cases,diseases):
    rows=[]
    for p in sorted((run/'name_controls').glob('ddx*.json')):
        r=json.loads(p.read_text());c=cases[r['case_id']];T=len(c['orders']['base']);fq=np.mean([json.loads((run/'observations'/f'{r["case_id"]}_base_t{T:02d}_m{m}.json').read_text())['q'] for m in [0,16,32]],axis=0)
        q=np.array(r['q_sequence']);qm=np.array(r['q_token_mean']);y=diseases.index(c['gold_disease']);w=int(winner(q));wm=int(winner(qm));wc=int(winner(fq))
        rows.append({'case_id':r['case_id'],'gold':c['gold_disease'],'code_top':diseases[wc] if wc>=0 else 'TIED','name_top':diseases[w] if w>=0 else 'TIED',
          'length_mean_top':diseases[wm] if wm>=0 else 'TIED','free_text':r['free_text'],'free_stop':r['free_stop'],'free_exact_canonical_match':r['exact_canonical_match'],
          'code_correct':wc==y,'name_correct':w==y,'token_mean_correct':wm==y,'code_name_agreement':wc==w and w>=0,
          'name_length_agreement':w==wm and w>=0,'free_exact_label_match':r['exact_canonical_match']==c['gold_disease']})
    csvwrite(dest/'name_interface_cases.csv',rows)
    summary={k:ci([r[k] for r in rows]) for k in ['code_correct','name_correct','token_mean_correct','code_name_agreement','name_length_agreement','free_exact_label_match']}
    summary['unmatched_free_text']=sum(r['free_exact_canonical_match'] is None for r in rows);dump(dest/'name_interface_summary.json',summary)
    table='\n'.join(f'| {r["case_id"]} | {r["gold"]} | {r["code_top"]} | {r["name_top"]} | {r["free_text"].replace(chr(10)," ").replace("|","/")} |' for r in rows)
    (dest/'NAME_INTERFACE.md').write_text(f'''# 疾病名与自由诊断控制：预定24例

病例在观察模型结果之前按哈希选定，使用基础顺序终点。移除候选列表，评分49个规范疾病名加EOS的完整序列概率，并单列每token平均分；另贪心生成最多64token的自由诊断。每例用完整前向核对一条候选的缓存序列分数。

| 指标 | 病例比例 [95%区间] |
|---|---|
| 编码接口命中标签 | {fmt(summary['code_correct'])} |
| 完整疾病名序列评分命中标签 | {fmt(summary['name_correct'])} |
| 每token平均评分命中标签 | {fmt(summary['token_mean_correct'])} |
| 编码与完整疾病名首选一致 | {fmt(summary['code_name_agreement'])} |
| 完整序列与每token平均首选一致 | {fmt(summary['name_length_agreement'])} |

自由输出有{summary['unmatched_free_text']}/24未严格匹配规范疾病名；未匹配不自动算医学错误，以下保留完整文本。两个接口还同时改变候选列表与输出形式，因此测量的是接口稳健性，并非只隔离字母效应。

| 病例 | 标签 | 编码首选 | 名称序列首选 | 自由诊断 |
|---|---|---|---|---|
{table}

[完整表](name_interface_cases.csv) · [精确结果](name_interface_summary.json)
''')

if __name__=='__main__':main()
