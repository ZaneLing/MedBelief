"""Paired interface and decode-coverage analysis; no new model selection."""
import csv
import matplotlib.pyplot as plt
from structural_v1_analysis import *
from analyze_stages import setup,savefig

OUT=ROOT/'results/46_structural_head_followup'

def main():
    s=read(OUT/'summary.json');assert read(ROOT/'research_v5_structural/head_followup_complete.json')['complete'];setup()
    with (OUT/'patient_code_results.csv').open() as f:code=list(csv.DictReader(f))
    with (OUT/'patient_generation_results.csv').open() as f:gen=list(csv.DictReader(f))
    contrasts=[]
    for cond in ['neutral','wrong']:
        cc={r['case_id']:float(r['accuracy_change']) for r in code if r['candidate']=='anchor_heads_8' and r['condition']==cond}
        pp={r['case_id']:float(r['accuracy_change']) for r in gen if r['candidate']=='anchor_heads_8' and r['condition']==cond}
        aa={r['case_id']:float(r['accuracy_change']) for r in gen if r['candidate']=='anchor_heads_8_all_answer_tokens' and r['condition']==cond}
        assert set(cc)==set(pp)==set(aa) and len(cc)==130
        contrasts.append(dict(condition=cond,code_minus_prefill_name_effect=stat([cc[c]-pp[c] for c in cc]),code_minus_sustained_name_effect=stat([cc[c]-aa[c] for c in cc]),sustained_minus_prefill_name_accuracy=stat([aa[c]-pp[c] for c in cc])))
    write(OUT/'paired_interface_contrasts.json',dict(cases=130,contrasts=contrasts,interpretation='Same patients, paired differences. Code scores average two mappings; name generation has one canonical candidate order. Exploratory intervals; no new structure selected.'))
    fig,axs=plt.subplots(1,2,figsize=(11,4.8),layout='constrained')
    rr=[next(r for r in s['code_summaries'] if r['candidate']=='anchor_heads_8' and r['dataset']=='all' and r['condition']==c)['accuracy_change'] for c in ['neutral','wrong']]
    rr.append(next(r for r in s['oracle_gold'] if r['candidate']=='anchor_heads_8')['accuracy_change'])
    means=np.array([r['mean'] for r in rr])*100;lo=np.array([r['low'] for r in rr])*100;hi=np.array([r['high'] for r in rr])*100
    axs[0].bar(range(3),means,color=['#317f9e','#bc534c','#61a17e'],width=.6);axs[0].errorbar(range(3),means,yerr=[means-lo,hi-means],fmt='none',color='#333333',capsize=3)
    axs[0].set(xticks=range(3),xticklabels=['中性历史','错误旧诊断','正确旧诊断\n（故意提供答案）'],ylabel='相对完整模型：正确率变化（百分点）',title='同一组头，历史内容改变后作用如何')
    for cond,c,off in [('neutral','#317f9e',-.12),('wrong','#bc534c',.12)]:
        rr=[next(r for r in s['generation'] if r['candidate']==n and r['condition']==cond)['accuracy_change'] for n in ['anchor_heads_8','anchor_heads_8_all_answer_tokens']]
        m=np.array([r['mean'] for r in rr])*100;lo=np.array([r['low'] for r in rr])*100;hi=np.array([r['high'] for r in rr])*100
        axs[1].errorbar(np.arange(2)+off,m,yerr=[m-lo,hi-m],fmt='o',color=c,capsize=3,label='中性历史' if cond=='neutral' else '错误历史')
    axs[1].set(xticks=range(2),xticklabels=['只改输入末位置','持续到全部答案词元'],ylabel='相对完整模型：正确率变化（百分点）',title='同130例：真正生成完整候选名称');axs[1].legend()
    for ax in axs:ax.axhline(0,color='gray',lw=.8)
    fig.suptitle('固定8头；病例级配对95%区间',fontsize=11);savefig(fig,OUT/'figures/history_and_generation')
    lines=['# 同一批病例：历史方向与实际生成\n\n![历史与生成](figures/history_and_generation.png)\n\n左图在同一批130例上改变历史内容；正确旧诊断明确写入来源答案，仅为机制对照。右图实际生成完整候选，比较只干预首步与持续干预每个答案词元。\n\n## 接口与干预持续时间的配对比较\n\n| 历史 | 代码收益减去首步生成收益 | 代码收益减去持续生成收益 | 持续生成减去首步生成的正确率 |\n|---|---|---|---|\n']
    for r in contrasts:lines.append('| '+('中性' if r['condition']=='neutral' else '错误旧诊断')+' | '+' | '.join(fmt(r[k],True) for k in ['code_minus_prefill_name_effect','code_minus_sustained_name_effect','sustained_minus_prefill_name_accuracy'])+' |\n')
    lines.append('\n数值为百分点及病例级95%区间。比较使用同130例；代码结果先平均两映射，名称生成使用原候选顺序，因此接口差异也包含编码与顺序设计差异。此分析在冻结结构后解释结果，没有用它重新挑头。[全部结果](RESULTS.md) · [可复算配对统计](paired_interface_contrasts.json)。\n')
    (OUT/'INTERFACE_AND_HISTORY.md').write_text(''.join(lines))
    print(json.dumps(dict(complete=True,contrasts=contrasts),ensure_ascii=False))

if __name__=='__main__':main()
