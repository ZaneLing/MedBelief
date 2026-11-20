"""Cross-configuration replication without treating quantization as a size effect."""
import json
import numpy as np
import matplotlib.pyplot as plt
from phase14_analyze import ROOT,cases,norm
from analyze_stages import setup,savefig,ci,fmt,csvwrite,dump,js
RUN=ROOT/'runs/belief_v2_4b'
def load(c,t=None):
    t=len(c['orders']['base']) if t is None else t;r=json.loads((RUN/'observations'/f"{c['case_id']}_append_base_t{t:02d}.json").read_text())
    with np.load(RUN/r['state_file']) as a:x=a['residual_stages'][:,4].astype(float)
    return norm(x),r
def main():
    assert (RUN/'completion.json').exists();setup();dest=ROOT/'results/18_model_replication';(dest/'figures').mkdir(parents=True,exist_ok=True)
    train,test=cases();classes=sorted({c['gold_disease'] for c in train});diseases=json.loads((RUN/'manifest.json').read_text())['candidate_diseases'];sub=[diseases.index(d) for d in classes];y=np.array([classes.index(c['gold_disease']) for c in test]);yt=np.array([classes.index(c['gold_disease']) for c in train]);g49=np.array([diseases.index(c['gold_disease']) for c in test])
    X=np.array([load(c)[0] for c in train]);mean=X.mean(0);X-=mean;pair=[load(c) for c in test];endpoint_records=[p[1] for p in pair];Z=np.array([p[0] for p in pair]);q=np.array([p[1]['q_sequence'] for p in pair]);Y=np.eye(24)[yt];bias=Y.mean(0);preds={};weights=None
    for alpha in [.01,.1,1.]:
        W=np.array([X[:,l].T@np.linalg.solve(X[:,l]@X[:,l].T+alpha*np.eye(120),Y-bias) for l in range(36)]);S=np.einsum('nld,ldc->nlc',Z-mean,W)+bias;preds[str(alpha)]=S.argmax(-1)
        if alpha==.1:weights=W
    np.savez_compressed(dest/'training_heads.npz',weights=weights,train_center=mean,bias=bias,classes=np.array(classes),training_ids=np.array([c['case_id'] for c in train]));np.savez_compressed(dest/'test_predictions.npz',case_ids=np.array([c['case_id'] for c in test]),gold=y,q=q,**preds)
    endrows=[dict(case_id=c['case_id'],gold=c['gold_disease'],native49=diseases[q[i].argmax()],native24=classes[q[i,sub].argmax()],probe27=classes[preds['0.1'][i,26]],probe36=classes[preds['0.1'][i,35]]) for i,c in enumerate(test)]
    events=[];case_rows=[];prefix=[];readouts={}
    for c in [c for c in test if c['deep_capture']]:
        T=len(c['orders']['base']);pair=[load(c,t) for t in range(T+1)];states=np.array([p[0] for p in pair]);qq=np.array([p[1]['q_sequence'] for p in pair]);scores=np.einsum('tld,ldc->tlc',states-mean,weights)+bias;P=scores.argmax(-1);n=qq.argmax(-1);n24=qq[:,sub].argmax(-1);gi=diseases.index(c['gold_disease']);yi=classes.index(c['gold_disease']);switch=n[1:]!=n[:-1];sw24=n24[1:]!=n24[:-1];big=np.max(abs(qq[1:]-qq[:-1]),axis=-1)>=.5;corr=n==gi
        cr=dict(case_id=c['case_id'],updates=T,switches=int(switch.sum()),switches24=int(sw24.sum()),big_updates=int(big.sum()),any_switch=bool(switch.any()),any_big=bool(big.any()),label_regression=bool(any(corr[t-1] and not corr[t] for t in range(1,T+1))),native24_prefix_accuracy=float(np.mean(n24==yi)))
        for l in [27,36]:
            cr[f'probe{l}_prefix_accuracy']=float(np.mean(P[:,l-1]==yi));cr[f'probe{l}_stable_when_native24_switches']=float(np.mean((P[1:,l-1]==P[:-1,l-1])[sw24])) if sw24.any() else None
        case_rows.append(cr);readouts[c['case_id']]=scores.astype(np.float32)
        for t in range(T+1):
            prefix.append(dict(case_id=c['case_id'],round=t,top=diseases[n[t]],gold_support=float(qq[t,gi]),probe27=classes[P[t,26]],probe36=classes[P[t,35]]))
            if t:events.append(dict(case_id=c['case_id'],round=t,previous_top=diseases[n[t-1]],current_top=diseases[n[t]],switch=bool(switch[t-1]),big=bool(big[t-1]),js=float(js(qq[t],qq[t-1])),delta_gold=float(qq[t,gi]-qq[t-1,gi])))
    summary={'model':'Qwen3-4B-8bit','layers':36,'train_cases':120,'test_cases':120,'native49':ci(list(q.argmax(-1)==g49)),'native24':ci(list(q[:,sub].argmax(-1)==y)),
        'layers_accuracy':{str(l):ci(list(preds['0.1'][:,l-1]==y)) for l in [9,18,27,36]},'layer_accuracy':(preds['0.1']==y[:,None]).mean(0).tolist(),
        'probe36_minus_native24':ci((preds['0.1'][:,35]==y).astype(float)-(q[:,sub].argmax(-1)==y)),
        'alpha_sensitivity_final':{a:float(np.mean(p[:,-1]==y)) for a,p in preds.items()},
        'deep':{'cases':24,'updates':sum(c['updates'] for c in case_rows),'switch_events':sum(c['switches'] for c in case_rows),'big_events':sum(c['big_updates'] for c in case_rows),**{k:ci([c[k] for c in case_rows if c[k] is not None]) for k in ['any_switch','any_big','label_regression','native24_prefix_accuracy','probe27_prefix_accuracy','probe36_prefix_accuracy','probe27_stable_when_native24_switches','probe36_stable_when_native24_switches']}},
        'comparison_scope':'different parameter counts and precision; not isolated causal model-size effect','api_cost_usd':0,
        'measurement_checks':{'greedy_accuracy':ci([r['generated_disease']==c['gold_disease'] for r,c in zip(endpoint_records,test)]),'greedy_canonical_count':sum(r['generated_disease'] in diseases for r in endpoint_records),'canonical_mass_median':float(np.median([r['sequence_probability_mass'] for r in endpoint_records])),'canonical_mass_below_point1':sum(r['sequence_probability_mass']<.1 for r in endpoint_records),'sequence_tokenmean_top_agreement':float(np.mean([np.argmax(r['q_sequence'])==np.argmax(r['q_token_mean']) for r in endpoint_records]))}}
    small=json.loads((ROOT/'results/14_fixed_panel/summary.json').read_text());smallpred=np.load(ROOT/'results/14_fixed_panel/test_predictions.npz');sq=smallpred['q_append'];summary['paired_4b_minus_1p7b_native49']=ci((q.argmax(-1)==g49).astype(float)-(sq.argmax(-1)==g49))
    summary['paired_4b_minus_1p7b_probe_final']=ci((preds['0.1'][:,-1]==y).astype(float)-(smallpred['append_0.1'][:,-1]==y))
    panelrows=[]
    for c in [c for c in test if c['deep_capture']]:
        t=len(c['orders']['base']);r=json.loads((RUN/'observations'/f"{c['case_id']}_panel_base_t{t:02d}.json").read_text());_,a=load(c);p=diseases[np.argmax(r['q_sequence'])];panelrows.append(dict(case_id=c['case_id'],gold=c['gold_disease'],panel_top=p,panel_correct=p==c['gold_disease'],append_correct=diseases[np.argmax(a['q_sequence'])]==c['gold_disease']))
    summary['fixed_panel_followup']={'cases':24,'panel_accuracy49':ci([r['panel_correct'] for r in panelrows]),'append_accuracy49_same_cases':ci([r['append_correct'] for r in panelrows]),'panel_minus_append':ci([float(r['panel_correct'])-float(r['append_correct']) for r in panelrows]),'panel_predictions':{d:sum(r['panel_top']==d for r in panelrows) for d in sorted({r['panel_top'] for r in panelrows})}}
    csvwrite(dest/'fixed_panel_cases.csv',panelrows)
    csvwrite(dest/'endpoint_cases.csv',endrows);csvwrite(dest/'case_metrics.csv',case_rows);csvwrite(dest/'evidence_updates.csv',events);csvwrite(dest/'prefix_trajectories.csv',prefix);np.savez_compressed(dest/'prefix_readout_scores.npz',classes=np.array(classes),**readouts);dump(dest/'summary.json',summary)
    fig,ax=plt.subplots(figsize=(9,5));ax.plot(np.arange(1,29)/28,small['endpoints']['append']['layer_accuracy'],label='1.7B FP16：内部读出');ax.plot(np.arange(1,37)/36,summary['layer_accuracy'],label='4B 8-bit：内部读出');ax.axhline(small['endpoints']['append']['native24']['mean'],ls='--',label='1.7B FP16：名称评分');ax.axhline(summary['native24']['mean'],ls=':',label='4B 8-bit：名称评分');ax.set(xlabel='相对层深度',ylabel='同24病独立测试准确率',ylim=(0,1));ax.legend();fig.tight_layout();savefig(fig,dest/'figures/model_replication')
    (dest/'RESULTS.md').write_text(f'''# 阶段18：在4B配置上复核

同一旧120例训练、新120例测试，24例全部逐轮前缀，共424次追加式观测；另加同24例固定问卷终点复核，共448次。模型为项目已下载的Qwen3-4B 8-bit，36层、隐藏维2560、32个查询注意力头；聊天模板关闭显式thinking。此处不运行疾病方向干预，也不训练4B固定问卷专用读出头。

| 指标 | 1.7B FP16 | 4B 8-bit |
|---|---|---|
| 原模型49病终点命中 | {fmt(small['endpoints']['append']['native49'])} | {fmt(summary['native49'])} |
| 原模型限制24病命中 | {fmt(small['endpoints']['append']['native24'])} | {fmt(summary['native24'])} |
| 四分之三深度内部读出 | {fmt(small['endpoints']['append']['layers']['21'])} | {fmt(summary['layers_accuracy']['27'])} |
| 最终层内部读出 | {fmt(small['endpoints']['append']['layers']['28'])} | {fmt(summary['layers_accuracy']['36'])} |

![两模型配置](figures/model_replication.png)

新24例共{summary['deep']['updates']}次证据更新：4B配置首选切换{summary['deep']['switch_events']}次，任一病支持单次变化≥50个百分点{summary['deep']['big_events']}次；至少一次命中后偏离标签的病例比例为{fmt(summary['deep']['label_regression'])}。

同24类输出切换时，第27层读出首选保持比例为{fmt(summary['deep']['probe27_stable_when_native24_switches'])}，第36层为{fmt(summary['deep']['probe36_stable_when_native24_switches'])}。按有切换的病例先求比例再汇总。

这项复核改变了参数规模和量化设置，不能把差异单独归因于模型更大；两者均来自Qwen3系列、同一模拟来源，不能称跨架构或外部临床验证。当前因果干预结果仍限定1.7B。

评分接口补充：4B贪心实际续写标签命中{fmt(summary['measurement_checks']['greedy_accuracy'])}，{summary['measurement_checks']['greedy_canonical_count']}/120例生成可解析的规范候选病名；规范字符串总质量中位数{summary['measurement_checks']['canonical_mass_median']:.4f}，低于0.1的有{summary['measurement_checks']['canonical_mass_below_point1']}例。序列总分与每token平均分的首选一致率为{summary['measurement_checks']['sequence_tokenmean_top_agreement']:.2%}。

额外24例固定问卷的49病终点准确率为{fmt(summary['fixed_panel_followup']['panel_accuracy49'])}，同24例追加式为{fmt(summary['fixed_panel_followup']['append_accuracy49_same_cases'])}。该项在1.7B呈现现象出现后预定，属于另一模型配置的探索性复核；完整预测分布见[固定问卷病例表](fixed_panel_cases.csv)。

[逐病例终点](endpoint_cases.csv) · [逐轮变化](evidence_updates.csv) · [逐轮读出](prefix_trajectories.csv) · [精确汇总](summary.json)
''');print(json.dumps(summary,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
