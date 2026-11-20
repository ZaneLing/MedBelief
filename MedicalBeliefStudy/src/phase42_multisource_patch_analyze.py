"""Patient-level paired intervention effects and held-out confirmation."""
from pathlib import Path
import json
import numpy as np
import matplotlib.pyplot as plt
from phase41_multisource_analyze import ROOT,DATA,RUN,read,write,csvwrite,stat,fmt,holm,SOURCES
from analyze_stages import setup,savefig

def main():
    src=RUN/'patches';assert read(src/'completion.json')['complete'];dest=ROOT/'results/33_multisource_causality';(dest/'figures').mkdir(parents=True,exist_ok=True);setup()
    cases={c['case_id']:c for c in map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines())};rows=[]
    for cid,c in cases.items():
        if not c['mechanism_capture']:continue
        zz=read(src/(cid+'.json'));g,w=c['gold_index'],c['wrong_index']
        def m(lp):return lp[g]-lp[w]
        nm=m(zz['neutral_log_probability']);wm=m(zz['wrong_log_probability']);n_top=int(np.argmax(zz['neutral_log_probability']));w_top=int(np.argmax(zz['wrong_log_probability']))
        for layer in [14,21]:
            for site in ['new','old','anchor']:
                a={x['condition']:x for x in zz['conditions'] if x['layer']==layer and x['site']==site}
                target=a['neutral_to_wrong'];reverse=a['wrong_to_neutral'];rr=[a['random_0'],a['random_1']];rm=np.mean([m(v['log_probability']) for v in rr]);tm=m(target['log_probability']);vm=m(reverse['log_probability'])
                row=dict(case_id=cid,dataset=c['dataset'],cohort=c['cohort'],gold=c['gold_disease'],wrong_prior=c['wrong_disease'],layer=layer,site=site,token_count=target['token_count'],position_offset=target['position_offset'],neutral_margin=nm,wrong_margin=wm,history_gap=nm-wm,delta_norm=target['delta_norm'],target_margin=tm,random_mean_margin=rm,target_change=tm-wm,random_change=rm-wm,target_minus_random=tm-rm,reverse_change=vm-nm,reverse_moves_toward_wrong=int((vm-nm)*(wm-nm)>0),moves_toward_neutral=int((tm-wm)*(nm-wm)>0),distance_to_neutral_improvement=abs(wm-nm)-abs(tm-nm),target_prediction=c['candidates'][int(np.argmax(target['log_probability']))],target_correct=int(np.argmax(target['log_probability'])==g),baseline_wrong_correct=int(w_top==g),baseline_neutral_correct=int(n_top==g),target_choice_changed=int(np.argmax(target['log_probability'])!=w_top),random_choice_changed_mean=float(np.mean([int(np.argmax(v['log_probability'])!=w_top) for v in rr])),target_recovers_neutral_choice=int(np.argmax(target['log_probability'])==n_top),original_histories_disagree=int(n_top!=w_top),random_correct_mean=float(np.mean([int(np.argmax(v['log_probability'])==g) for v in rr])))
                row['target_minus_random_accuracy']=row['target_correct']-row['random_correct_mean'];row['target_minus_baseline_accuracy']=row['target_correct']-row['baseline_wrong_correct']
                if 'generated_disease' in target:row['generated_correct']=int(target['generated_disease']==c['gold_disease']);row['generated_disease']=target['generated_disease']
                rows.append(row)
    csvwrite(dest/'patient_interventions.csv',rows);summaries=[]
    for ds in SOURCES+['all']:
        for cohort in ['all','development','confirmation']:
            group=[]
            for layer in [14,21]:
                for site in ['new','old','anchor']:
                    rr=[r for r in rows if r['layer']==layer and r['site']==site and (ds=='all' or r['dataset']==ds) and (cohort=='all' or r['cohort']==cohort)]
                    if not rr:continue
                    s=stat([r['target_minus_random'] for r in rr],pvalue=True)
                    item=dict(dataset=ds,cohort=cohort,layer=layer,site=site,**s)
                    for field in ['target_change','random_change','reverse_change','distance_to_neutral_improvement','target_choice_changed','target_minus_baseline_accuracy','target_minus_random_accuracy','target_recovers_neutral_choice','moves_toward_neutral','reverse_moves_toward_wrong']:item[field]=stat([r[field] for r in rr])
                    group.append(item)
            holm(group);summaries.extend(group)
    # Direct paired contrast: target-specific effect of new evidence vs old facts.
    contrasts=[]
    for cohort in ['all','development','confirmation']:
        for layer in [14,21]:
            ids=sorted({r['case_id'] for r in rows if r['layer']==layer and (cohort=='all' or r['cohort']==cohort)});vv=[]
            for cid in ids:
                q={r['site']:r for r in rows if r['case_id']==cid and r['layer']==layer};vv.append(q['new']['target_minus_random']-q['old']['target_minus_random'])
            contrasts.append(dict(cohort=cohort,layer=layer,**stat(vv,pvalue=True)))
    for cohort in ['all','development','confirmation']:holm([r for r in contrasts if r['cohort']==cohort])
    summary=dict(patients=len({r['case_id'] for r in rows}),conditions=read(src/'completion.json')['conditions'],summaries=summaries,new_minus_old=contrasts,api_cost_usd=0)
    write(dest/'summary.json',summary)
    fig,axs=plt.subplots(1,2,figsize=(11,4.5),layout='constrained');sites=['new','old','anchor'];names=['新事实位置','旧事实位置','诊断输出位置'];colors=['#c78c3c','#9299a0','#397b9f']
    for ax,layer in zip(axs,[14,21]):
        ss=[next(r for r in summaries if r['dataset']=='all' and r['cohort']=='confirmation' and r['layer']==layer and r['site']==site) for site in sites];mean=np.array([r['mean'] for r in ss]);lo=np.array([r['low'] for r in ss]);hi=np.array([r['high'] for r in ss]);ax.bar(range(3),mean,color=colors);ax.errorbar(range(3),mean,yerr=np.array([mean-lo,hi-mean]),fmt='none',capsize=4,c='black');ax.axhline(0,c='gray',lw=1);ax.set(xticks=range(3),xticklabels=names,title=f'第{layer}层 · 确认集 n={ss[0]["n"]}',ylabel='来源病−错误病分差：目标替换减随机替换')
    fig.suptitle('中性历史状态能解除多少错误历史影响？｜随机干预同位置、同范数')
    savefig(fig,dest/'figures/confirmation_patch_effect')
    with (dest/'RESULTS.md').open('w') as f:
        f.write(f'# 医学信念内部作用：新事实、旧事实与诊断位置\n\n{summary["patients"]}个预先选定病例、{summary["conditions"]}个干预条件完成。供体来自同患者中性历史条件，没有正确答案标签。第14、21层均重新计算干预后的后续层及缓存。\n\n')
        f.write('## 独立确认集\n\n| 层 | 位置 | 病例 | 目标−随机分差，95%CI | Holm校正p | 诊断首选改变比例 | 准确率相对错误历史变化 |\n|---|---|---:|---|---:|---|---|\n')
        for r in summaries:
            if r['dataset']=='all' and r['cohort']=='confirmation':f.write(f'| {r["layer"]} | {dict(zip(sites,names))[r["site"]]} | {r["n"]} | {fmt(r)} | {r["p_holm"]:.5f} | {fmt(r["target_choice_changed"],True)} | {fmt(r["target_minus_baseline_accuracy"],True)} |\n')
        f.write('\n![位置干预](figures/confirmation_patch_effect.png)\n\n分差增加意味着在预定的两个诊断之间向来源答案移动，不等于每例改对。首选变化、准确率和自由生成分别记录。旧事实位置是有效性对照，不预先假定旧事实无关。\n\n## 新事实是否比旧事实更特殊\n\n| 层 | 确认集新−旧位置作用，95%CI | 两层校正p |\n|---|---|---:|\n')
        for r in contrasts:
            if r['cohort']=='confirmation':f.write(f'| {r["layer"]} | {fmt(r)} | {r["p_holm"]:.5f} |\n')
        f.write('\n这项直接对照决定能否把作用特别归于新增事实。各位置单独显著，并不意味着位置之间显著不同。不同位置的自然改变量和词元数量可能不同；同范数随机对照控制各位置内部的任意扰动效应，不使跨位置比较成为完全等量干预。\n\n## 解释范围\n\n状态替换检验历史影响经过哪些位置传播；它不能单独证明模型曲解了某条事实的临床意义。中性与错误历史长度可能不同，已保存对齐位置差；全部新/旧事实词元须按同一原文对齐。开发、确认、数据来源分开的结果及反向替换保留在[汇总](summary.json)和[患者级干预表](patient_interventions.csv)。\n')
    print(json.dumps(dict(output=str(dest),patients=summary['patients'])),flush=True)

if __name__=='__main__':main()
