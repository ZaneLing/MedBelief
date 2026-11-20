"""Post-hoc continuous natural-update alignment, beyond whether argmax switches."""
import json
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from phase14_analyze import ROOT,RUN,cases
from analyze_stages import setup,savefig,csvwrite,dump,ci,fmt
def main():
    setup();dest=ROOT/'results/16_update_mechanism';scores=np.load(ROOT/'results/14_fixed_panel/prefix_readout_scores.npz');classes=scores['classes'].tolist();ds=json.loads((RUN/'manifest.json').read_text())['candidate_diseases'];sub=[ds.index(d) for d in classes];_,test=cases();rows=[];caserows=[];summary={}
    for c in [c for c in test if c['deep_capture']]:
        cid=c['case_id'];T=len(c['orders']['base']);gi=ds.index(c['gold_disease']);yi=classes.index(c['gold_disease'])
        for view in ['append','panel']:
            logs=np.array([json.loads((RUN/'observations'/f'{cid}_{view}_base_t{t:02d}.json').read_text())['log_probability'] for t in range(T+1)]);s=scores[f'{cid}_{view}'];xx=[];yy=[]
            for t in range(1,T+1):
                co=max((j for j in range(24) if j!=yi),key=lambda j:logs[t-1,sub[j]]);cg=sub[co];dx=(s[t,:,yi]-s[t,:,co])-(s[t-1,:,yi]-s[t-1,:,co]);dy=(logs[t,gi]-logs[t,cg])-(logs[t-1,gi]-logs[t-1,cg]);xx.append(dx);yy.append(dy)
                for l in range(28):rows.append(dict(case_id=cid,view=view,round=t,layer=l+1,gold=c['gold_disease'],competitor=classes[co],readout_margin_change=float(dx[l]),native_margin_change=float(dy),same_direction=bool(dx[l]*dy>0)))
            X=np.array(xx);Y=np.array(yy)
            for l in range(28):
                valid=(abs(X[:,l])>1e-8)&(abs(Y)>1e-8);rho=float(spearmanr(X[:,l],Y).statistic) if np.ptp(X[:,l])>1e-8 and np.ptp(Y)>1e-8 else None
                caserows.append(dict(case_id=cid,view=view,layer=l+1,updates=T,spearman=rho,nonzero_updates=int(valid.sum()),same_direction=float(np.mean((X[:,l]*Y>0)[valid])) if valid.any() else None))
    for view in ['append','panel']:
        summary[view]={str(l):{key:ci([r[key] for r in caserows if r['view']==view and r['layer']==l and r[key] is not None]) for key in ['spearman','same_direction']} for l in range(1,29)}
    lookup={(r['case_id'],r['view'],r['layer']):r for r in caserows};ids=[c['case_id'] for c in test if c['deep_capture']]
    summary['paired_panel_minus_append']={str(l):{key:ci([lookup[cid,'panel',l][key]-lookup[cid,'append',l][key] for cid in ids if lookup[cid,'panel',l][key] is not None and lookup[cid,'append',l][key] is not None]) for key in ['spearman','same_direction']} for l in range(1,29)}
    csvwrite(dest/'natural_alignment_updates.csv',rows);csvwrite(dest/'natural_alignment_cases.csv',caserows);dump(dest/'natural_alignment_summary.json',summary)
    fig,axs=plt.subplots(1,2,figsize=(11,4.6))
    for ax,key,title in zip(axs,['spearman','same_direction'],['每例内部变化与输出变化的相关性','内部与输出朝同一疾病方向变化的比例']):
        for view,label,color in [('append','逐条追加','#2878b5'),('panel','固定问卷','#e07b21')]:
            rr=[summary[view][str(l)][key] for l in range(1,29)];ax.plot(range(1,29),[r['mean'] for r in rr],label=label,color=color);ax.fill_between(range(1,29),[r['low'] for r in rr],[r['high'] for r in rr],alpha=.15,color=color)
        ax.set(title=title,xlabel='层',ylim=(-1,1) if key=='spearman' else (0,1),xticks=[1,7,14,21,28]);ax.axhline(0 if key=='spearman' else .5,color='gray',ls='--',lw=1);ax.legend()
    fig.tight_layout();savefig(fig,dest/'figures/natural_alignment')
    table='\n'.join(f"| {label} | {l} | {fmt(summary[v][str(l)]['spearman'],False)} | {fmt(summary[v][str(l)]['same_direction'])} |" for v,label in [('append','逐条追加'),('panel','固定问卷')] for l in [21,28])
    (dest/'NATURAL_ALIGNMENT.md').write_text(f'''# 内部与输出不同步，是否意味着完全无关？

## 方法

事后连续量分析，沿用全部24例、每种呈现184次自然证据更新。对一次更新固定“来源标签病—前轮24类中最强非标签病”，分别计算外部读出分差与原模型完整序列对数分差的变化。先在每例内部计算相关及同方向比例，再按病例汇总；竞争病可以在不同事件间变化，但一次事件前后固定。近零变化不进入同方向比例，病例分母和有效事件数均保存。

## 结果

| 呈现 | 层 | 病例平均Spearman相关 | 同方向变化比例 |
|---|---:|---|---|
{table}

![连续更新关系](figures/natural_alignment.png)

首选是否更换与连续分数是否一起移动回答不同问题。前者受排名交叉影响，后者描述变化的方向与幅度关联；内部首选保持，仍可能发生与输出一致的分差变化。相关性不估计自然更新的因果中介比例，也不把两个不同评分系统校准为同一疾病概率。图中0.5仅为同向比例参考线，不是经置换得到的统计零假设。

同病例固定问卷减追加式的第28层相关差为{fmt(summary['paired_panel_minus_append']['28']['spearman'],False)}，同向比例差为{fmt(summary['paired_panel_minus_append']['28']['same_direction'],False)}。这是事后配对描述，不对所有层重复进行显著性筛选。

[每次更新](natural_alignment_updates.csv) · [病例统计](natural_alignment_cases.csv) · [精确汇总](natural_alignment_summary.json)
''');print(json.dumps({v:{l:summary[v][l] for l in ['21','28']} for v in summary},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
