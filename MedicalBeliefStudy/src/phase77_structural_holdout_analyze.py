"""Held-out diagnoses, real name generation, and synchronized efficiency."""
import matplotlib.pyplot as plt
from structural_v1_analysis import *
from analyze_stages import setup,savefig
OUT=ROOT/'results/44_structural_holdout'
LABELS={'baseline':'完整模型','early_exit':'运行前27层','drop_mlp_2':'删MLP 25、26','linear_mlp_2_r16':'MLP 25、26 → 秩16','drop_block_1':'删第27整层','anchor_heads_8':'诊断位置干预8个头','depth_matched_random_mlp_2':'对照：删MLP 24、28','block_influence_2':'对照：删第14、26整层','linear_mlp_2_r64':'MLP 25、26 → 秩64'}
def main():
    for d in ['test','generation','timing']:assert read(RUN/d/'completion.json')['complete']
    setup();(OUT/'figures').mkdir(parents=True,exist_ok=True);rows,sizes,spec=load('test');summaries=summarize(rows);sel=read(RUN/'selected.json');baseline=sizes['baseline'];names=[c['name'] for c in spec['candidates']]
    csvwrite(OUT/'patient_code_results.csv',rows);genrows=[];timing=[];history=[]
    for cid in read(RUN/'generation/manifest.json')['cases']:
        b=read(RUN/'generation'/(cid+'_baseline.json'));bb={r['condition']:r for r in b['conditions']}
        for name in names:
            z=read(RUN/'generation'/(cid+'_'+name+'.json'))
            for r in z['conditions']:
                base=bb[r['condition']];genrows.append(dict(case_id=cid,dataset=z['dataset'],candidate=name,condition=r['condition'],correct=int(r['correct']),listed=int(r['listed']),accuracy_change=int(r['correct'])-int(base['correct']),same_diagnosis=int(r['generated_disease']==base['generated_disease']),generated_disease=r['generated_disease'],baseline_disease=base['generated_disease'],repaired=int(r['correct'] and not base['correct']),damaged=int(base['correct'] and not r['correct'])))
    generation=[]
    for name in names:
        for cond in ['neutral','wrong']:
            rr=[r for r in genrows if r['candidate']==name and r['condition']==cond];generation.append(dict(candidate=name,condition=cond,n=len(rr),correct=sum(r['correct'] for r in rr),**{('accuracy' if f=='correct' else f):stat([r[f] for r in rr]) for f in ['correct','listed','accuracy_change','same_diagnosis','repaired','damaged']}))
        rr=[r for r in rows if r['candidate']==name];paired=[]
        for cid in spec['cases']:
            a=next(r for r in rr if r['case_id']==cid and r['condition']=='neutral');b=next(r for r in rr if r['case_id']==cid and r['condition']=='wrong');paired.append(dict(case_id=cid,candidate=name,accuracy_effect=b['accuracy']-a['accuracy'],margin_effect=b['margin']-a['margin']))
        history.append(dict(candidate=name,accuracy_effect=stat([r['accuracy_effect'] for r in paired]),margin_effect=stat([r['margin_effect'] for r in paired])))
        if name!='baseline':
            z=read(RUN/'timing'/(name+'.json'));t=z['trials'];rr=[]
            for cid in sorted({r['case_id'] for r in t}):rr.append(float(np.mean([np.log(r['ratio']) for r in t if r['case_id']==cid])))
            st=stat(rr);timing.append(dict(candidate=name,patients=len(rr),paired_trials=len(t),median_ratio=float(np.median([r['ratio'] for r in t])),geometric_ratio=float(np.exp(st['mean'])),ratio_low=float(np.exp(st['low'])),ratio_high=float(np.exp(st['high'])),median_baseline_ms=1000*float(np.median([r['baseline_seconds'] for r in t])),median_variant_ms=1000*float(np.median([r['variant_seconds'] for r in t]))))
    csvwrite(OUT/'patient_generation_results.csv',genrows);csvwrite(OUT/'timing_results.csv',timing)
    contrasts=[]
    for left,right in [('linear_mlp_2_r16','linear_mlp_2_r64'),('linear_mlp_2_r16','drop_mlp_2'),('drop_mlp_2','depth_matched_random_mlp_2')]:
        for cond in ['neutral','wrong']:
            a={r['case_id']:r for r in rows if r['candidate']==left and r['condition']==cond};b={r['case_id']:r for r in rows if r['candidate']==right and r['condition']==cond}
            contrasts.append(dict(left=left,right=right,condition=cond,**{f:stat([a[cid][f]-b[cid][f] for cid in a]) for f in ['accuracy','strict_accuracy','fidelity','js','gold_support','wrong_support']}))
    interaction=[]
    for name in names:
        a={r['case_id']:r for r in rows if r['candidate']==name and r['condition']=='neutral'};b={r['case_id']:r for r in rows if r['candidate']==name and r['condition']=='wrong'}
        interaction.append(dict(candidate=name,wrong_minus_neutral_accuracy_change=stat([b[cid]['accuracy_change']-a[cid]['accuracy_change'] for cid in a])))
    write(OUT/'paired_contrasts.json',dict(contrasts=contrasts,history_interactions=interaction,interpretation='Exploratory paired contrasts; no selection or multiplicity-adjusted discovery claim. Differences are left minus right.'))
    macro=[];rng=np.random.default_rng(77051)
    for name in names:
        for cond in ['neutral','wrong']:
            result=dict(candidate=name,condition=cond)
            for field in ['accuracy','accuracy_change','fidelity','strict_accuracy_change']:
                samples=[];means=[]
                for ds in ['MedQA','MedMCQA','MMLU']:
                    x=np.array([r[field] for r in rows if r['candidate']==name and r['condition']==cond and r['dataset']==ds]);means.append(float(x.mean()));samples.append(x[rng.integers(0,len(x),(4000,len(x)))].mean(1))
                boot=np.mean(samples,axis=0);result[field]=dict(mean=float(np.mean(means)),low=float(np.quantile(boot,.025)),high=float(np.quantile(boot,.975)))
            macro.append(result)
    write(OUT/'source_balanced_summary.json',dict(method='Equal source weights; bootstrap patients within each source, then average the three source means.',summaries=macro))
    verdicts=[]
    for name in names:
        nn=[r for r in summaries if r['candidate']==name and r['dataset']=='all'];v=dict(candidate=name,parameters=sizes[name]['parameters'],parameter_reduction=1-sizes[name]['parameters']/baseline['parameters'],weight_bytes=sizes[name]['weight_bytes'],candidate_fidelity_at_least_95pct=all(r['fidelity']['mean']>=.95 for r in nn),accuracy_noninferiority_2pp=all(r['accuracy_change']['low']>=-.02 for r in nn),strict_accuracy_noninferiority_2pp=all(r['strict_accuracy_change']['low']>=-.02 for r in nn))
        gg=[r for r in generation if r['candidate']==name];v['generation_accuracy_noninferiority_2pp']=all(r['accuracy_change']['low']>=-.02 for r in gg);verdicts.append(v)
    write(OUT/'summary.json',dict(cases=345,source_cases={'MedQA':194,'MedMCQA':125,'MMLU':26},configurations=len(names),code_summaries=summaries,generation=generation,timing=timing,history_effects=history,parameter_stats=sizes,verdicts=verdicts,selection=sel,api_cost_usd=0))
    fig,axs=plt.subplots(1,2,figsize=(13,6),layout='constrained');yy=np.arange(len(names))
    for cond,col,off in [('neutral','#317f9e',-.12),('wrong','#bc534c',.12)]:
        rr=[next(r for r in summaries if r['candidate']==n and r['dataset']=='all' and r['condition']==cond) for n in names]
        for ax,f in zip(axs,['fidelity','accuracy_change']):
            m=np.array([r[f]['mean'] for r in rr]);lo=np.array([r[f]['low'] for r in rr]);hi=np.array([r[f]['high'] for r in rr]);ax.errorbar(m,yy+off,xerr=[m-lo,hi-m],fmt='o',capsize=2,label=cond,c=col)
    for ax in axs:ax.set(yticks=yy,yticklabels=[LABELS[n] for n in names]);ax.invert_yaxis();ax.legend()
    axs[0].set(title='是否保留完整模型的诊断',xlabel='候选一致率，病例级95%CI');axs[1].set(title='是否改善来源答案命中',xlabel='准确率配对变化');axs[1].axvline(0,c='gray',lw=.8);savefig(fig,OUT/'figures/heldout_diagnoses')
    fig,axs=plt.subplots(1,3,figsize=(14,5.5),layout='constrained',sharey=True)
    for name in names:
        if name=='baseline':continue
        v=next(r for r in verdicts if r['candidate']==name);tt=next(r for r in timing if r['candidate']==name);rr=[r for r in summaries if r['candidate']==name and r['dataset']=='all'];acc=np.mean([r['accuracy_change']['mean'] for r in rr]);i=names.index(name)-1;axs[0].barh(i,v['parameter_reduction']*100,color='#317f9e');axs[1].plot(acc*100,i,'o',c='#bc534c');axs[2].errorbar(tt['geometric_ratio'],i,xerr=[[tt['geometric_ratio']-tt['ratio_low']],[tt['ratio_high']-tt['geometric_ratio']]],fmt='o',c='#317f9e')
    axs[0].set(title='实际保存的参数',xlabel='参数减少 (%)',yticks=range(len(names)-1),yticklabels=[LABELS[n] for n in names[1:]]);axs[0].invert_yaxis();axs[1].axvline(0,c='gray',lw=.8);axs[1].set(title='来源答案命中',xlabel='两历史平均准确率变化 (百分点)');axs[2].axvline(1,c='gray',ls='--');axs[2].set(title='同步实测预填充耗时',xlabel='相对完整模型耗时（小于1更快）');savefig(fig,OUT/'figures/efficiency_tradeoff')
    lines=['# 固定结构在345例上的留出检验\n\nMedQA194、MedMCQA125、MMLU26。结构只由18例定位与27例组合开发确定；本轮345例不用于选择位置或拟合模块。每患者两种代码映射先平均，表中正确率不转成伪整数患者数。\n\n![诊断检验](figures/heldout_diagnoses.png)\n\n| 结构 | 历史 | 来源答案命中，95%CI | 与完整模型一致，95%CI | 准确率变化，95%CI | 首词元属于代码 |\n|---|---|---|---|---|---|\n']
    for r in summaries:
        if r['dataset']=='all':lines.append(f'| {r["candidate"]} | {r["condition"]} | {fmt(r["accuracy"],True)} | {fmt(r["fidelity"],True)} | {fmt(r["accuracy_change"],True)} | {fmt(r["code_rate"],True)} |\n')
    lines.append('\n差值百分数按百分点解释。严格首词元命中、修复/损坏与分来源区间见summary。\n\n## 实际生成完整病名\n\n同一留出队列按哈希每来源取20例，共60例。模型直接生成完整病名，未解析或不在原候选中的输出不计正确。\n\n| 结构 | 历史 | 答对/60 | 相对完整模型变化，95%CI |\n|---|---|---:|---|\n')
    for r in generation:lines.append(f'| {r["candidate"]} | {r["condition"]} | {r["correct"]} | {fmt(r["accuracy_change"],True)} |\n')
    lines.append('\n## 实际结构与速度\n\n![效率](figures/efficiency_tradeoff.png)\n\n| 结构 | 参数数 | 参数减少 | 相对耗时，病例级95%CI |\n|---|---:|---:|---|\n')
    for v in verdicts:
        tt=next((r for r in timing if r['candidate']==v['candidate']),None);latency=f'{tt["geometric_ratio"]:.3f} [{tt["ratio_low"]:.3f}, {tt["ratio_high"]:.3f}]' if tt else '1.000';lines.append(f'| {v["candidate"]} | {v["parameters"]:,} | {v["parameter_reduction"]*100:.2f}% | {latency} |\n')
    lines.append('\n计时使用6例、两历史、3次交错配对重复，预热后同步GPU；测量预分词输入的预填充及最终词表输出头，不含模型加载、分词或持续生成。头干预保留原模型参数且增加门控计算，不把它称为模型压缩。\n\n[全部患者代码结果](patient_code_results.csv) · [实际病名生成](patient_generation_results.csv) · [完整汇总](summary.json) · [计时](timing_results.csv)\n')
    (OUT/'RESULTS.md').write_text(''.join(lines));print(json.dumps(dict(cases=345,generation_cases=60,configurations=names,verdicts=verdicts),ensure_ascii=False))
if __name__=='__main__':main()
