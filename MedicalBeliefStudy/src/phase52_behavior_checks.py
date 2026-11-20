"""Alternative answer interfaces, full trajectories and order controls."""
import json,collections
import numpy as np
import matplotlib.pyplot as plt
from phase41_multisource_analyze import ROOT,DATA,RUN,read,write,csvwrite,stat,fmt,SOURCES,obs,top,margin
from analyze_stages import setup,savefig

DEST=ROOT/'results/37_behavior_checks'
def main():
    setup();(DEST/'figures').mkdir(parents=True,exist_ok=True)
    cases=list(map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines()));rows=[];steps=[];trace=[]
    for c in cases:
        g=c['gold_index'];T=len(c['sentences']);r=dict(case_id=c['case_id'],dataset=c['dataset'],cohort=c['cohort'])
        for cond in ['none','neutral','wrong','mention']:
            z=obs(c,cond);r[cond+'_complete_correct']=int(top(z)==g)
            q=np.array(z['q_sequence']);r[cond+'_max_support']=float(q.max());r[cond+'_entropy']=float(-np.sum(q*np.log(np.maximum(q,1e-30))));r[cond+'_brier']=float(np.square(q-np.eye(4)[g]).sum());r[cond+'_high_support_error']=int(q.max()>=.9 and top(z)!=g)
            # Use the stored average token log likelihood if present; do not guess
            # lengths from disease names alone (JSON closure/EOS are also scored).
            average=z['q_token_mean']
            if average is not None:r[cond+'_token_mean_correct']=int(np.argmax(average)==g)
            if 'generated_disease' in z:
                r[cond+'_generated_correct']=int(z['generated_disease']==c['gold_disease']);r[cond+'_generated_listed']=int(z['generated_disease'] in c['candidates'])
                r[cond+'_generated_agrees_score']=int(z['generated_disease']==c['candidates'][top(z)])
        rev=obs(c,'none',order='reverse');r['reverse_correct']=int(top(rev)==g);r['reverse_choice_changed']=int(top(rev)!=top(obs(c,'none')));r['reverse_accuracy_change']=r['reverse_correct']-r['none_complete_correct']
        for cond in ['wrong','mention']:
            for interface in ['complete','token_mean','generated']:
                if cond+'_'+interface+'_correct' in r:r[cond+'_minus_neutral_'+interface]=r[cond+'_'+interface+'_correct']-r['neutral_'+interface+'_correct']
        r['wrong_minus_neutral_high_support_error']=r['wrong_high_support_error']-r['neutral_high_support_error'];r['wrong_minus_neutral_brier']=r['wrong_brier']-r['neutral_brier']
        rows.append(r)
        if not c['trajectory_capture']:continue
        for cond in ['neutral','wrong','gold']:
            zz=[obs(c,cond,t) for t in range(1,T+1)];pred=[top(z) for z in zz];qq=np.array([z['q_sequence'] for z in zz]);dq=qq[1:,g]-qq[:-1,g];sw=np.asarray(pred[1:])!=np.asarray(pred[:-1]);changes=[]
            for t in range(1,T):
                tv=float(np.abs(qq[t]-qq[t-1]).sum()/2);changes.append(tv)
                steps.append(dict(case_id=c['case_id'],dataset=c['dataset'],cohort=c['cohort'],condition=cond,round=t+1,source_support_change=float(dq[t-1]),total_variation=tv,top_changed=int(sw[t-1]),source_enter=int(pred[t]==g and pred[t-1]!=g),source_leave=int(pred[t]!=g and pred[t-1]==g),from_disease=c['candidates'][pred[t-1]],to_disease=c['candidates'][pred[t]],evidence=c['sentences'][t]))
            changes=np.array(changes);corr=[j for j,p in enumerate(pred) if p==g];stable=[j for j in range(T) if all(p==g for p in pred[j:])]
            trace.append(dict(case_id=c['case_id'],dataset=c['dataset'],cohort=c['cohort'],condition=cond,groups=T,switches=int(sw.sum()),never_switches=int(not sw.any()),final_correct=int(pred[-1]==g),ever_source=int(bool(corr)),source_then_leave=int(any(pred[t-1]==g and pred[t]!=g for t in range(1,T))),first_source_round=corr[0]+1 if corr else None,stable_source_round=stable[0]+1 if stable else None,nonmonotonic_source_support=int(np.any(dq>.01) and np.any(dq<-.01)),largest_step_share_of_total=float(changes.max()/changes.sum()) if changes.sum()>1e-12 else None,largest_support_step=float(np.max(np.abs(dq))),source_support_path=qq[:,g].tolist(),prediction_path=[c['candidates'][j] for j in pred]))
    csvwrite(DEST/'patient_answer_interfaces.csv',rows);csvwrite(DEST/'all_evidence_transitions.csv',steps)
    write(DEST/'patient_trajectories.json',trace);summaries=[];ts=[];paired=[]
    for ds in SOURCES+['all']:
        for cohort in ['all','development','confirmation']:
            def take(rr):return [r for r in rr if (ds=='all' or r['dataset']==ds) and (cohort=='all' or r['cohort']==cohort)]
            rr=take(rows)
            if rr:summaries.append(dict(dataset=ds,cohort=cohort,n=len(rr),metrics={k:stat([r[k] for r in rr if k in r]) for k in rows[0] if k not in ['case_id','dataset','cohort']}))
            for cond in ['neutral','wrong','gold']:
                rr=[r for r in take(trace) if r['condition']==cond]
                if rr:ts.append(dict(dataset=ds,cohort=cohort,condition=cond,n=len(rr),metrics={k:stat([r[k] for r in rr if r[k] is not None]) for k in ['switches','never_switches','final_correct','ever_source','source_then_leave','nonmonotonic_source_support','largest_step_share_of_total','largest_support_step']}))
            nn={r['case_id']:r for r in take(trace) if r['condition']=='neutral'};ww={r['case_id']:r for r in take(trace) if r['condition']=='wrong'}
            if nn:paired.append(dict(dataset=ds,cohort=cohort,n=len(nn),switch_difference=stat([ww[k]['switches']-nn[k]['switches'] for k in nn]),no_switch_difference=stat([ww[k]['never_switches']-nn[k]['never_switches'] for k in nn])))
    write(DEST/'summary.json',dict(patients=540,trajectory_patients=94,evidence_transitions=sum(len(c['sentences'])-1 for c in cases if c['trajectory_capture']),answer_interfaces=summaries,trajectory_statistics=ts,paired_trajectory_changes=paired,api_cost_usd=0))
    fig,axs=plt.subplots(1,2,figsize=(11,4.8),layout='constrained')
    for j,cond in enumerate(['neutral','wrong','gold']):
        rr=[r for r in trace if r['condition']==cond];cnt=collections.Counter(r['switches'] for r in rr);xx=np.arange(7);axs[0].bar(xx+(j-1)*.25,[cnt[k] for k in xx],width=.25,label={'neutral':'中性历史','wrong':'错误历史','gold':'正确历史强对照'}[cond]);axs[1].scatter([r['largest_step_share_of_total'] for r in rr],[r['largest_support_step'] for r in rr],s=18,alpha=.5,label=cond)
    axs[0].set(xlabel='逐组加入证据期间，首选改变次数',ylabel='病例数',xticks=range(7),title='全部94例的诊断切换');axs[0].legend();axs[1].set(xlabel='最大一次分布变化 / 全程变化之和',ylabel='最大一次来源答案支持变化',title='变化是否集中在单次证据');axs[1].legend();savefig(fig,DEST/'figures/trajectory_population')
    with (DEST/'RESULTS.md').open('w') as f:
        f.write('# 回到实际答案：生成、评分与逐步变化\n\n## 自由生成复核\n\n所有540例的中性/错误历史均实际贪心生成答案。先完成统一JSON前缀，再由模型生成病名。未解析或不在原选项中的输出计为未命中，另列覆盖率。\n\n| 来源 | 例数 | 中性：完整病名评分 | 错误：完整病名评分 | 中性：实际生成 | 错误：实际生成 | 生成准确率变化，95%CI |\n|---|---:|---:|---:|---:|---:|---|\n')
        for r in summaries:
            if r['cohort']=='all':
                m=r['metrics'];n=r['n'];f.write(f'| {r["dataset"]} | {n} | '+ ' | '.join(str(round(m[k]['mean']*n)) for k in ['neutral_complete_correct','wrong_complete_correct','neutral_generated_correct','wrong_generated_correct'])+' | '+fmt(m['wrong_minus_neutral_generated'],True)+' |\n')
        f.write('\n## 错误答案得到多大支持\n\n高支持错误定义为：模型首选错误，且该首选占四候选相对支持的至少90%。它描述模型输出分布，不是模型自报信心或临床患病概率。\n\n| 来源 | 中性高支持错误 | 错误历史高支持错误 | 配对比例变化，95%CI |\n|---|---:|---:|---|\n')
        for r in summaries:
            if r['cohort']=='all':
                m=r['metrics'];n=r['n'];f.write(f'| {r["dataset"]} | {round(n*m["neutral_high_support_error"]["mean"])} / {n} | {round(n*m["wrong_high_support_error"]["mean"])} / {n} | {fmt(m["wrong_minus_neutral_high_support_error"],True)} |\n')
        f.write('\n## 逐步加证据，模型是在平滑更新还是突然换病\n\n![全体轨迹](figures/trajectory_population.png)\n\n| 历史 | 病例数 | 全程不换首选 | 曾选来源答案后又离开 | 来源答案支持有升也有降 | 最终命中 |\n|---|---:|---:|---:|---:|---:|\n')
        for r in ts:
            if r['dataset']=='all' and r['cohort']=='all':
                n=r['n'];m=r['metrics'];f.write(f'| {r["condition"]} | {n} | '+' | '.join(str(round(m[k]['mean']*n)) for k in ['never_switches','source_then_leave','nonmonotonic_source_support','final_correct'])+' |\n')
        f.write('\n首选可以突然换病，而候选支持仍是连续数值。这里同时报告二者：切换次数和最大单步变化，不能仅看折线外观就声称内部发生离散相变。每轮是重新输入累计原文证据、固定历史条件；没有把上一轮生成诊断回填。部分证据没有独立诊断标签，因此“离开最终来源答案”不直接等于当轮医学判断错误。\n\n## 顺序对照\n\n完整病例的原文证据组全部倒序，题目与候选不变。该对照检验文本顺序敏感性，不模拟真实病程倒流。\n\n| 来源 | 首选改变比例 | 最终准确率变化，95%CI |\n|---|---|---|\n')
        for r in summaries:
            if r['cohort']=='all':f.write(f'| {r["dataset"]} | {fmt(r["metrics"]["reverse_choice_changed"],True)} | {fmt(r["metrics"]["reverse_accuracy_change"],True)} |\n')
        f.write('\n[患者回答接口](patient_answer_interfaces.csv) · [每次证据转移](all_evidence_transitions.csv) · [患者完整轨迹](patient_trajectories.json) · [全部区间](summary.json)\n')

if __name__=='__main__':main()
