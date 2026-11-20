"""Post-hoc: distinguish causal score movement from crossing a diagnostic decision boundary."""
import json
import numpy as np
import matplotlib.pyplot as plt
from analyze_stages import ROOT,setup,savefig,csvwrite,dump
def main():
    setup();dest=ROOT/'results/15_disease_directions';rows=[]
    for p in sorted((ROOT/'runs/belief_v2/disease_interventions').glob('ddx*.json')):
        r=json.loads(p.read_text());g=r['gold_index49'];others=[i for i in range(49) if i!=g];bl=np.array(r['baseline']['log_probability']);bm=bl[g]-bl[others].max()
        for v in r['conditions']:
            if v['condition'] not in ['toward','toward_small','random','away']:continue
            ll=np.array(v['log_probability']);mm=ll[g]-ll[others].max()
            rows.append(dict(case_id=r['case_id'],view=r['view'],layer=v['layer'],site=v['site'],condition=v['condition'],baseline_margin=float(bm),intervened_margin=float(mm),margin_gain=float(mm-bm),baseline_correct=bool(bm>0),intervened_correct=bool(mm>0),newly_correct=bool(bm<0 and mm>0),lost_correct=bool(bm>0 and mm<0)))
    csvwrite(dest/'decision_margins.csv',rows);summary={};fig,axs=plt.subplots(1,2,figsize=(10,5))
    for ax,view in zip(axs,['append','panel']):
        rr=[r for r in rows if r['view']==view and r['layer']==21 and r['site']=='all_answer_positions' and r['condition']=='toward'];wrong=[r for r in rr if not r['baseline_correct']]
        summary[view]={'cases':len(rr),'baseline_correct':sum(r['baseline_correct'] for r in rr),'intervened_correct':sum(r['intervened_correct'] for r in rr),'newly_correct':sum(r['newly_correct'] for r in rr),'lost_correct':sum(r['lost_correct'] for r in rr),'initially_wrong_cases':len(wrong),'median_deficit_initially_wrong':float(np.median([-r['baseline_margin'] for r in wrong])),'median_margin_gain_initially_wrong':float(np.median([r['margin_gain'] for r in wrong]))}
        x=np.array([r['baseline_margin'] for r in rr]);y=np.array([r['intervened_margin'] for r in rr]);ax.scatter(x,y,c=np.where(x>0,'#2878b5','#c43b37'));limits=[min(x.min(),y.min())-1,max(x.max(),y.max(),1)+1];ax.plot(limits,limits,'--',color='gray',lw=1);ax.axvline(0,color='gray',lw=.7);ax.axhline(0,color='gray',lw=.7);ax.set(xlim=limits,ylim=limits,title={'append':'逐条追加','panel':'固定问卷'}[view],xlabel='干预前：标签病减最强其他病的对数分差',ylabel='干预后：同一分差');ax.set_aspect('equal',adjustable='box')
    fig.suptitle('第21层、全部续写位置、5%目标方向：分数移动，是否越过零线？');fig.tight_layout();savefig(fig,dest/'figures/decision_boundary');dump(dest/'decision_summary.json',summary)
    table='\n'.join(f"| {label} | {summary[v]['baseline_correct']}/24 | {summary[v]['intervened_correct']}/24 | {summary[v]['newly_correct']} | {summary[v]['median_deficit_initially_wrong']:.3f} | {summary[v]['median_margin_gain_initially_wrong']:.3f} |" for v,label in [('append','逐条追加'),('panel','固定问卷')])
    (dest/'DECISION_GAPS.md').write_text(f'''# 方向有效，为什么没有新增正确诊断？

阶段15完成后的事后分解。原主检验检验目标/预定竞争病分数是否定向改变；这里另计算标签病与每个条件下49病最强其他病的分差。分差大于0才表示标签病成为首选。该阈值是当前字符串排序的决策边界，不是临床概率阈值。

## 第21层、全部续写位置、5%方向增量

| 呈现 | 原始命中 | 干预后命中 | 由错转对 | 原本错误病例的落后幅度中位数 | 这些病例的分差增益中位数 |
|---|---:|---:|---:|---:|---:|
{table}

![决策边界](figures/decision_boundary.png)

高于斜虚线表示标签病相对最强其他病得到了加强；越过水平零线才会从错变对。目标方向造成可测量的输出作用，却没有在当前强度下新增正确诊断。8种主条件均未出现由错转对，也未出现由对转错；少数首选变化发生在错误病之间。

这将结论具体化为：**这些方向有影响输出的能力，但在当前病例和干预强度下，没有取得足以改变诊断正确性的影响。** 未运行更强剂量的剂量扫描，不推断增加强度一定能修复诊断。

[全部条件分差](decision_margins.csv) · [精确汇总](decision_summary.json) · [主检验](RESULTS.md)
''')
    print(json.dumps(summary,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
