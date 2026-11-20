"""Independent MedQA source: native trajectories and within-patient controls."""
import collections
import numpy as np
import matplotlib.pyplot as plt
from belief_v3_analysis import *

def main():
 run=ROOT/'runs/belief_v3_medqa';assert (run/'completion.json').exists();dest=ROOT/'results/26_external_medqa';setup()
 for d in ['figures','cases']:(dest/d).mkdir(parents=True,exist_ok=True)
 cases=rows(ROOT/'data/external_medqa/cases.private.jsonl');jobs=rows(ROOT/'data/external_medqa/jobs.jsonl');metrics=[];prefix=[];events=[];controls=[];internal=[];headmaps=[];checkrec=[];cats=collections.Counter()
 for k,c in enumerate(cases):
  cid=c['case_id'];ds=c['candidate_diseases'];g=ds.index(c['gold_disease']);T=len(c['evidence_sentences']);rec=[read(run/'observations'/f'{cid}_base_t{t:02d}.json') for t in range(1,T+1)];q=np.array([r['q_sequence'] for r in rec]);lp=np.array([r['log_probability'] for r in rec]);n=q.argmax(-1);m=dict(case_id=cid,gold=c['gold_disease'],**path_metrics(q,g));metrics.append(m);cats[m['pattern']]+=1;checkrec.append(rec[-1]);raw=[];AA=[]
  for t,r in enumerate(rec):
   with np.load(run/r['state_file']) as a:raw.append(a['residual_stages'][:,4].astype(float));AA.append(a['attention_by_group'].astype(float))
   prefix.append(dict(case_id=cid,round=t+1,native_top=ds[n[t]],gold=c['gold_disease'],gold_support=q[t,g],gold_rank=int(1+(q[t]>q[t,g]).sum()),entropy=float(-np.sum(q[t]*np.log(np.maximum(q[t],1e-30)))/np.log(4))))
   if t:events.append(dict(case_id=cid,round=t+1,previous_top=ds[n[t-1]],current_top=ds[n[t]],switch=bool(n[t]!=n[t-1]),big=bool(np.max(abs(q[t]-q[t-1]))>=.5),max_support_change=float(np.max(abs(q[t]-q[t-1]))),total_variation=float(.5*abs(q[t]-q[t-1]).sum()),delta_gold=float(q[t,g]-q[t-1,g]),new_evidence=c['evidence_sentences'][t]))
  raw=np.array(raw);change=np.linalg.norm(np.diff(raw,axis=0),axis=-1)/np.maximum(np.linalg.norm(raw[:-1],axis=-1),1e-12);tv=.5*abs(np.diff(q,axis=0)).sum(-1);AA=np.array(AA);headmaps.append(AA[:,:, :,1].mean(0))
  for l in range(28):internal.append(dict(case_id=cid,layer=l+1,relative_state_change=change[:,l].mean(),state_output_change_rho=rho(change[:,l],tv),evidence_attention=AA[:,l,:,1].mean(),candidate_attention=AA[:,l,:,2].mean()))
  for cond in ['reverse','shuffle','wrong_history']:
   r=read(run/'observations'/f'{cid}_{cond}.json');qq=np.array(r['q_sequence']);row=dict(case_id=cid,condition=cond,gold=c['gold_disease'],base_top=ds[n[-1]],changed_top=ds[qq.argmax()],switched=bool(qq.argmax()!=n[-1]),correct_before=bool(n[-1]==g),correct_after=bool(qq.argmax()==g),delta_gold=float(qq[g]-q[-1,g]),js=float(js(qq,q[-1])))
   if cond=='wrong_history':w=ds.index(r['prior_disease']);row.update(prior_disease=ds[w],prior_endorsed_before=bool(n[-1]==w),prior_endorsed_after=bool(qq.argmax()==w),prior_vs_gold_margin_gain=(r['log_probability'][w]-r['log_probability'][g])-(lp[-1,w]-lp[-1,g]),prior_support_gain=qq[w]-q[-1,w])
   controls.append(row)
  fig,axs=plt.subplots(2,1,figsize=(11,7),layout='constrained',height_ratios=[1,1]);
  for d in range(4):axs[0].plot(range(1,T+1),q[:,d],marker='o',ms=3,color='black' if d==g else None,lw=2 if d==g else 1.2,label=ds[d]+(' [source answer]' if d==g else ''))
  axs[0].set(ylabel='原模型病名相对支持',ylim=(-.02,1.02),xticks=range(1,T+1));axs[0].legend(fontsize=8);im=axs[1].imshow(change.T,origin='lower',aspect='auto',extent=[1.5,T+.5,.5,28.5],cmap='magma');axs[1].set(ylabel='模型层数',xlabel='新增原文句子的轮次',xticks=range(2,T+1),title='内部状态变化幅度（不代表疾病方向）');fig.colorbar(im,ax=axs[1],label='状态差范数/前轮状态范数');fig.suptitle(cid+' | '+c['gold_disease']);savefig(fig,dest/'cases'/cid)
  tab='\n'.join(f'| {t+1} | {ds[n[t]]} | {q[t,g]:.4f} | {c["evidence_sentences"][t]} |' for t in range(T));ct='\n'.join(f'| {r["condition"]} | {r["changed_top"]} | {r["delta_gold"]:+.4f} |' for r in controls if r['case_id']==cid)
  (dest/'cases'/f'{cid}.md').write_text(f'# {cid}：{c["gold_disease"]}\n\n来源：MedQA四选项test，第{c["source_index"]}行（零起始）。来源答案只用于完整题目评价。路径：{PATTERNS[m["pattern"]]}。下图没有用DDxPlus探针解码MedQA病名。\n\n![逐句轨迹]({cid}.png)\n\n{c["diagnostic_question"]}\n\n| 轮 | 原模型首选 | 来源答案支持 | 本轮新增原文 |\n|---|---|---:|---|\n{tab}\n\n| 完整题目控制 | 原模型首选 | 来源答案支持改变 |\n|---|---|---:|\n{ct}\n\n原题选项：'+json.dumps(c['source_options'],ensure_ascii=False)+'\n')
  if (k+1)%20==0:print('MedQA trajectories',k+1,len(cases),flush=True)
 s=dict(patients=len(cases),unique_answers=len({c['gold_disease'] for c in cases}),prefixes=len(prefix),updates=len(events),native4_accuracy=summary([m['final_hit'] for m in metrics]),switch_events=sum(e['switch'] for e in events),big_events=sum(e['big'] for e in events),patterns=dict(cats),**{v:summary([m[v] for m in metrics]) for v in ['any_switch','any_big','regression','max_step_share','gold_decrease_rate']},controls={cond:dict(switched=summary([r['switched'] for r in controls if r['condition']==cond]),correct_after=summary([r['correct_after'] for r in controls if r['condition']==cond]),paired_accuracy_change=summary([float(r['correct_after'])-float(r['correct_before']) for r in controls if r['condition']==cond])) for cond in ['reverse','shuffle','wrong_history']},api_cost_usd=0)
 wh=[r for r in controls if r['condition']=='wrong_history'];s['wrong_history']=dict(prior_endorsed_before=summary([r['prior_endorsed_before'] for r in wh]),prior_endorsed_after=summary([r['prior_endorsed_after'] for r in wh]),prior_vs_gold_margin_gain=summary([r['prior_vs_gold_margin_gain'] for r in wh]));s['checks']=dict(greedy_exact_label=summary([r['generated_disease']==c['gold_disease'] for r,c in zip(checkrec,cases)]),greedy_listed=sum(r['generated_disease'] in c['candidate_diseases'] for r,c in zip(checkrec,cases)),canonical_mass_median=float(np.median([r['sequence_probability_mass'] for r in checkrec])),sequence_tokenmean_agreement=summary([np.argmax(r['q_sequence'])==np.argmax(r['q_token_mean']) for r in checkrec]));
 for name,data in [('case_metrics',metrics),('prefix_trajectories',prefix),('evidence_updates',events),('controls',controls),('internal_state_change',internal)]:csvwrite(dest/(name+'.csv'),data)
 dump(dest/'summary.json',s);fig,axs=plt.subplots(1,2,figsize=(12,4),layout='constrained');axs[0].barh([PATTERNS[x] for x in PATTERNS],[cats[x] for x in PATTERNS],color='#598d6b');axs[0].set(xlabel=f'病例数（共{len(cases)}题）');xx=['原顺序','反序','乱序','错误历史'];vv=[s['native4_accuracy']['mean']]+[s['controls'][x]['correct_after']['mean'] for x in ['reverse','shuffle','wrong_history']];axs[1].bar(xx,vv,color=['#598d6b','#6284aa','#a28c51','#bd6d6a']);axs[1].set(ylabel='完整题目命中率',ylim=(0,1));savefig(fig,dest/'figures/external_results')
 (dest/'CASE_ATLAS.md').write_text(f'# {len(cases)}道外部来源诊断题：全量图谱\n\n'+'\n'.join(f'- [{c["case_id"]} · {c["gold_disease"]} · {PATTERNS[m["pattern"]]}](cases/{c["case_id"]}.md)' for c,m in zip(cases,metrics))+'\n')
 tab='\n'.join(f'| {cond} | {fmt(v["switched"])} | {fmt(v["correct_after"])} | {fmt(v["paired_accuracy_change"])} |' for cond,v in s['controls'].items())
 (dest/'RESULTS.md').write_text(f'''# 换一种病例来源后，医学判断还会怎样变化？

使用MedQA USMLE四选项公开测试集，按预定规则选取{len(cases)}道直接询问诊断的题，{s['unique_answers']}种不同的来源答案。完整题目命中率为**{fmt(s['native4_accuracy'])}**。

原文逐句输入，共{s['prefixes']}个前缀、{s['updates']}次更新。首选改变{s['switch_events']}次，单次某病名相对支持变化至少50个百分点{s['big_events']}次。至少一次命中来源答案又离开的病例比例为{fmt(s['regression'])}。题目并非病人的真实就诊时序；这里模拟证据逐步揭示。

![外部来源结果](figures/external_results.png)

| 完整题目的条件 | 相对原顺序改变首选 | 完整题目命中率 | 配对命中率变化 |
|---|---|---|---|
{tab}

错误历史中的病名预先从本题非答案选项确定，未按观察结果筛选。其被选中的比例，从原条件{fmt(s['wrong_history']['prior_endorsed_before'])}变为加入历史后{fmt(s['wrong_history']['prior_endorsed_after'])}。模型仍被明确要求依据当前事实重新判断。

## 数据与内部测量的边界

保留原句、原题选项和原答案，没有让模型重写病例。公开原项目为[MedQA](https://github.com/jind11/MedQA)，论文为[What Disease Does This Patient Have?](https://arxiv.org/abs/2009.13081)。本地文件通过公开镜像取得，完整哈希与逐题筛选理由见[data/external_medqa](../../data/external_medqa/provenance.json)。运行前已修复关系从句被误当提问的分割错误，弃用版本没有运行模型。

每轮保存全部28层内部状态及锚点分头注意力。本阶段只量化状态改变，不把DDxPlus的24类读出器套到不同的MedQA病名上；疾病方向的逐层结论来自独立DDxPlus分析。MedQA为考试病例，四选项准确率与DDxPlus49病准确率分别报告。逆序保留所有事实句，但可能改变语言连贯性，因此不能把顺序效应全部归为医学偏见。

[全部病例](CASE_ATLAS.md) · [逐句结果](prefix_trajectories.csv) · [条件对照](controls.csv) · [每层状态](internal_state_change.csv) · [精确汇总](summary.json)
''');print(json.dumps(clean(s),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
