"""Fixed coefficient empty-input subtraction as a diagnostic, not a new method."""
import json
import numpy as np
import matplotlib.pyplot as plt
from phase14_analyze import ROOT,RUN,cases
from analyze_stages import setup,savefig,csvwrite,dump,ci,fmt
def main():
    setup();dest=ROOT/'results/20_template_prior';assert (RUN/'template_prior/completion.json').exists();_,test=cases();ds=json.loads((RUN/'manifest.json').read_text())['candidate_diseases'];rows=[];summary={}
    for c in [c for c in test if c['deep_capture']]:
        cid=c['case_id'];T=len(c['orders']['base']);g=ds.index(c['gold_disease'])
        for view in ['append','panel']:
            full=json.loads((RUN/'observations'/f'{cid}_{view}_base_t{T:02d}.json').read_text());empty=json.loads((RUN/'template_prior'/f'{cid}_empty_{view}.json').read_text());a=np.array(full['log_probability']);b=np.array(empty['log_probability']);d=a-b;p=ds[a.argmax()];new=ds[d.argmax()]
            for j,name in enumerate(ds):rows.append(dict(case_id=cid,view=view,disease=name,is_gold=j==g,full_logp=float(a[j]),empty_logp=float(b[j]),contrast_score=float(d[j]),native_top=p,contrast_top=new,native_correct=p==c['gold_disease'],contrast_correct=new==c['gold_disease']))
    case_rows=[r for r in rows if r['is_gold']];csvwrite(dest/'empty_score_contrast.csv',rows);csvwrite(dest/'empty_score_contrast_cases.csv',case_rows)
    for view in ['append','panel']:
        rr=[r for r in case_rows if r['view']==view];summary[view]={'cases':24,'native_accuracy49':ci([r['native_correct'] for r in rr]),'contrast_accuracy49':ci([r['contrast_correct'] for r in rr]),'paired_accuracy_gain':ci([float(r['contrast_correct'])-float(r['native_correct']) for r in rr]),'native_copd_count':sum(r['native_top']==ds[0] for r in rr),'contrast_copd_count':sum(r['contrast_top']==ds[0] for r in rr),'newly_correct':sum(r['contrast_correct'] and not r['native_correct'] for r in rr),'lost_correct':sum(r['native_correct'] and not r['contrast_correct'] for r in rr)}
    dump(dest/'empty_score_contrast_summary.json',summary);fig,ax=plt.subplots(figsize=(8,5));x=np.arange(2)
    for key,off,label in [('native_accuracy49',-.18,'原病名分数'),('contrast_accuracy49',.18,'减去匹配空输入分数')]:
        rr=[summary[v][key] for v in ['append','panel']];ax.bar(x+off,[r['mean'] for r in rr],width=.34,label=label)
        for xx,r in zip(x+off,rr):ax.text(xx,r['mean']+.025,f"{round(r['mean']*24)}/24",ha='center')
    ax.set(xticks=x,xticklabels=['逐条追加','固定问卷'],ylim=(0,1),ylabel='同24例、49病来源标签命中');ax.legend();fig.tight_layout();savefig(fig,dest/'figures/empty_score_contrast')
    table='\n'.join(f"| {label} | {fmt(summary[v]['native_accuracy49'])} | {fmt(summary[v]['contrast_accuracy49'])} | {fmt(summary[v]['paired_accuracy_gain'],False)} | {summary[v]['native_copd_count']} → {summary[v]['contrast_copd_count']} |" for v,label in [('append','逐条追加'),('panel','固定问卷')])
    (dest/'SCORE_CONTRAST.md').write_text(f'''# 将空输入偏向作为评分对照

阶段20观测前登记的探索性分析，无新增模型调用。对同24例，完整事实病名对数分数减去匹配年龄性别及候选顺序的空输入分数，系数固定为1；不使用测试标签调参。对全部49病重新排序。

| 输入 | 原始命中 | 差值排序命中 | 配对准确率差 | COPD相关选择例数 |
|---|---|---|---|---|
{table}

![空输入分数对照](figures/empty_score_contrast.png)

该操作借鉴已有contextual calibration，不作为新算法。差值排序衡量患者事实相对空输入如何改变字符串支持；它不是临床后验，也没有证明背景和证据能被完全加性分离。[方法先例](https://proceedings.mlr.press/v139/zhao21c.html)

[全部49病分数对照](empty_score_contrast.csv) · [逐病例结果](empty_score_contrast_cases.csv) · [精确汇总](empty_score_contrast_summary.json) · [分析登记](../../protocol/TEMPLATE_SCORE_CONTRAST_V2.md)
''');print(json.dumps(summary,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
