"""Describe template-induced preferences without a clinical prior interpretation."""
import collections,json
import numpy as np
import matplotlib.pyplot as plt
from phase14_analyze import ROOT,RUN,cases
from analyze_stages import setup,savefig,ci,fmt,csvwrite,dump,js
def main():
    setup();run=RUN/'template_prior';assert (run/'completion.json').exists();dest=ROOT/'results/20_template_prior';(dest/'figures').mkdir(parents=True,exist_ok=True);_,test=cases();test=[c for c in test if c['deep_capture']];ds=json.loads((RUN/'manifest.json').read_text())['candidate_diseases'];copd=ds.index('Acute COPD exacerbation / infection');rows=[]
    for c in test:
        cid=c['case_id'];T=len(c['orders']['base']);base=json.loads((RUN/'observations'/f'{cid}_panel_base_t{T:02d}.json').read_text());bq=np.array(base['q_sequence'])
        for cond in ['empty_panel','empty_append','reverse_candidates','rotate_candidates']:
            r=json.loads((run/f'{cid}_{cond}.json').read_text());q=np.array(r['q_sequence']);pred=ds[q.argmax()];rows.append(dict(case_id=cid,condition=cond,prediction=pred,copd=pred==ds[copd],copd_support=float(q[copd]),picked_first_candidate=pred==r['presented_diseases'][0],changed_from_full_panel=bool(q.argmax()!=bq.argmax()),js_from_full_panel=float(js(q,bq)),correct=None if cond.startswith('empty') else pred==c['gold_disease'],input_tokens=r['input_tokens'],generated_disease=r['generated_disease']))
    summary={'cases':24,'conditions':{},'scope':'Empty conditions measure conditional output preferences, not disease prevalence or diagnostic accuracy.'}
    for cond in ['empty_append','empty_panel','reverse_candidates','rotate_candidates']:
        rs=[r for r in rows if r['condition']==cond];summary['conditions'][cond]={k:ci([r[k] for r in rs if r[k] is not None]) for k in ['copd','copd_support','picked_first_candidate','changed_from_full_panel','js_from_full_panel','correct']};summary['conditions'][cond]['prediction_counts']=dict(collections.Counter(r['prediction'] for r in rs))
    lookup={(r['case_id'],r['condition']):r for r in rows};summary['empty_panel_minus_empty_append_copd_support']=ci([lookup[c['case_id'],'empty_panel']['copd_support']-lookup[c['case_id'],'empty_append']['copd_support'] for c in test]);dump(dest/'summary.json',summary);csvwrite(dest/'case_results.csv',rows)
    fig,ax=plt.subplots(figsize=(9,5));labels=['无症状、无问卷','无症状、完整空问卷','有完整事实、候选反转','有完整事实、候选轮换'];keys=list(summary['conditions']);x=np.arange(4)
    ax.bar(x,[summary['conditions'][k]['copd_support']['mean'] for k in keys]);ax.set(xticks=x,xticklabels=labels,ylim=(0,1),ylabel='慢阻肺急性加重/感染的平均相对支持');ax.tick_params(axis='x',labelrotation=15);fig.tight_layout();savefig(fig,dest/'figures/template_preferences')
    table='\n'.join(f"| {label} | {fmt(summary['conditions'][k]['copd'])} | {fmt(summary['conditions'][k]['copd_support'])} | {fmt(summary['conditions'][k]['picked_first_candidate'])} |" for k,label in zip(keys,labels))
    (dest/'RESULTS.md').write_text(f'''# 阶段20：共同答案来自空问卷，还是候选首位？

## 方法

由固定问卷输出集中触发的探索性追踪，全部预定24例。空问卷与无问题列表均只保留年龄性别和49候选，不包含患者症状事实。另两条件保留完整事实，只反转或固定轮换候选表。所有分数还原到统一疾病顺序。

## 结果

| 条件 | 首选COPD相关诊断比例 | 该病平均支持 | 选择当前列表第一项比例 |
|---|---|---|---|
{table}

![问卷与候选位置](figures/template_preferences.png)

空问卷减无问题列表的COPD支持差为{fmt(summary['empty_panel_minus_empty_append_copd_support'],False)}。完整事实下，反转候选的标签命中为{fmt(summary['conditions']['reverse_candidates']['correct'])}；固定轮换为{fmt(summary['conditions']['rotate_candidates']['correct'])}。

空条件不计算准确率，也不把模型输出叫作人群患病概率。该对照检验提示文本和候选位置如何形成条件输出偏向；其结果不能自动说明真实医疗记录中的普遍偏差。

[全部病例](case_results.csv) · [精确汇总](summary.json)
''');print(json.dumps(summary,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
