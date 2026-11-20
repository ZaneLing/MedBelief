"""Analyze the development-motivated unendorsed-name causal follow-up."""
import json
import numpy as np
import matplotlib.pyplot as plt
from phase41_multisource_analyze import ROOT,DATA,RUN,read,write,csvwrite,stat,fmt,holm,SOURCES
from analyze_stages import setup,savefig

def main():
    src=RUN/'mention_patches';assert read(src/'completion.json')['complete'];dest=ROOT/'results/35_unendorsed_name';(dest/'figures').mkdir(parents=True,exist_ok=True);setup()
    cases={c['case_id']:c for c in map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines())};rows=[]
    for cid,c in cases.items():
        if not c['mechanism_capture'] or c['cohort']!='confirmation':continue
        z=read(src/(cid+'.json'));g,w=c['gold_index'],c['wrong_index']
        def m(v):return v[g]-v[w]
        neutral=m(z['neutral_log_probability']);base=m(z['mention_log_probability']);baseline_correct=int(np.argmax(z['mention_log_probability'])==g)
        for layer in [14,21]:
            for site in ['new','old','anchor']:
                a={r['condition']:r for r in z['conditions'] if r['layer']==layer and r['site']==site};target=m(a['target']['log_probability']);random=np.mean([m(a[k]['log_probability']) for k in ['random_0','random_1']]);newcorrect=int(np.argmax(a['target']['log_probability'])==g)
                rows.append(dict(case_id=cid,dataset=c['dataset'],layer=layer,site=site,neutral_margin=neutral,mention_margin=base,target_margin=target,random_mean_margin=random,target_minus_random=target-random,target_change=target-base,accuracy_change=newcorrect-baseline_correct,target_correct=newcorrect,baseline_correct=baseline_correct,neutral_correct=int(np.argmax(z['neutral_log_probability'])==g),prediction_changed=int(np.argmax(a['target']['log_probability'])!=np.argmax(z['mention_log_probability'])),distance_to_neutral_improvement=abs(base-neutral)-abs(target-neutral),delta_norm=a['target']['delta_norm'],token_count=a['target']['token_count']))
    csvwrite(dest/'patient_interventions.csv',rows);summaries=[]
    for ds in SOURCES+['all']:
        group=[]
        for layer in [14,21]:
            for site in ['new','old','anchor']:
                rr=[r for r in rows if r['layer']==layer and r['site']==site and (ds=='all' or r['dataset']==ds)];s=dict(dataset=ds,layer=layer,site=site,**stat([r['target_minus_random'] for r in rr],pvalue=True))
                for key in ['target_change','accuracy_change','target_correct','baseline_correct','neutral_correct','prediction_changed','distance_to_neutral_improvement']:s[key]=stat([r[key] for r in rr])
                group.append(s)
        holm(group);summaries.extend(group)
    write(dest/'summary.json',dict(patients=48,conditions=960,additional_baseline_recaptures=48,cohort='confirmation',status='development_motivated_followup',summaries=summaries,api_cost_usd=0))
    fig,axs=plt.subplots(1,2,figsize=(11,4.5),layout='constrained');sites=['new','old','anchor'];labels=['新事实位置','旧事实位置','诊断位置']
    for ax,layer in zip(axs,[14,21]):
        rr=[next(r for r in summaries if r['dataset']=='all' and r['layer']==layer and r['site']==site) for site in sites];mean=np.array([r['mean'] for r in rr]);low=np.array([r['low'] for r in rr]);high=np.array([r['high'] for r in rr]);ax.bar(range(3),mean,color=['#c78c3c','#9299a0','#397b9f']);ax.errorbar(range(3),mean,yerr=np.array([mean-low,high-mean]),fmt='none',capsize=4,c='black');ax.axhline(0,c='gray');ax.set(xticks=range(3),xticklabels=labels,ylabel='目标替换−同位置随机替换的诊断分差',title=f'第{layer}层 · 独立确认48例')
    fig.suptitle('未采纳的病名：替换哪些内部状态能够解除影响？');savefig(fig,dest/'figures/mention_causal_confirmation')
    with (dest/'RESULTS.md').open('w') as f:
        f.write('# 未采纳的病名，也值得单独检验\n\n开发集出现提及效应后追加本阶段。使用事先选定的48例内部确认病例，供体为中性历史，受体为“诊断尚未确定、仅提到一个未采纳候选病名”。三类位置、两个层、目标/随机/自身对照共960个干预，另有48次受体状态重捕捉。\n\n')
        f.write('| 层 | 位置 | 目标−随机分差，95%CI | 六项Holm校正p | 来源答案命中变化 | 首选改变比例 |\n|---|---|---|---:|---|---|\n')
        for r in summaries:
            if r['dataset']=='all':f.write(f'| {r["layer"]} | {dict(zip(sites,labels))[r["site"]]} | {fmt(r)} | {r["p_holm"]:.5f} | {fmt(r["accuracy_change"],True)} | {fmt(r["prediction_changed"],True)} |\n')
        f.write('\n![未采纳病名的位置干预](figures/mention_causal_confirmation.png)\n\n该对照把“曾做出错误诊断”与“上下文里出现了病名”分开。状态替换可以检验影响传播的位置，但不自动说明模型相信了这个病名，更不能仅据分差变化说它曲解了医学证据。提及条件的代码作答对照见[逐层与跨配置报告](../34_multisource_depth/RESULTS.md)，患者级记录见[干预表](patient_interventions.csv)。\n')

if __name__=='__main__':main()
