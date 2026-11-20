from pathlib import Path
import argparse,collections,csv,json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze_stages import ROOT,ZH,COLORS,ci,fmt,js,winner,changed,divinfo,csvwrite,dump,savefig,setup

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run-id',default='expanded_v1');args=ap.parse_args();setup();run=ROOT/'runs'/args.run_id
 assert (run/'interventions/completion.json').exists() and (run/'name_scores/completion.json').exists() and (run/'readouts/completion.json').exists() and (run/'readouts/affine_completion.json').exists()
 rows=[json.loads(p.read_text()) for p in sorted((run/'observations').glob('*.json'))]
 private={r['case_id']:r for r in map(json.loads,(ROOT/'data/cases.private.jsonl').read_text().splitlines())}
 disease=json.loads((run/'manifest.json').read_text())['diseases'];lookup={r['job_id']:r for r in rows};eval_ids=[cid for cid,c in private.items() if c['cohort']=='replication']
 two=ROOT/'results/02_replication';three=ROOT/'results/03_evidence_order';four=ROOT/'results/04_internal_mechanism';five=ROOT/'results/05_synthesis'
 s2=json.loads((two/'summary.json').read_text());s3=json.loads((three/'summary.json').read_text());quality=json.loads((run/'readouts/heldout_quality.json').read_text())
 affine_quality=json.loads((run/'readouts/affine_quality.json').read_text())
 for q,a in zip(quality,affine_quality):q.update(a)
 csvwrite(four/'readout_quality.csv',quality)
 z=np.load(run/'readouts/heldout_predictions.npz');decoded={str(k):i for i,k in enumerate(z['job_ids'])};pred=z['calibrated'];shuffled=z['shuffled'];readout_cases=[]
 az=np.load(run/'readouts/affine_predictions.npz');amap={str(k):i for i,k in enumerate(az['job_ids'])};apred=az['support']
 for cid in eval_ids:
  rr=[r for r in rows if r['case_id']==cid and r['order']=='base' and r['rotation'] in [0,3]];y=disease.index(private[cid]['gold_disease']);raw=[];learned=[];random=[];affine=[]
  for r in rr:
   raw.append(divinfo(r['layer_q'],y)['divergence']);learned.append(divinfo(pred[decoded[r['job_id']]],y)['divergence']);random.append(divinfo(shuffled[decoded[r['job_id']]],y)['divergence']);affine.append(divinfo(apred[amap[r['job_id']]],y)['divergence'])
  readout_cases.append({'case_id':cid,'raw_divergence_rate':float(np.mean(raw)),'learned_divergence_rate':float(np.mean(learned)),
   'shuffled_divergence_rate':float(np.mean(random)),'affine_divergence_rate':float(np.mean(affine)),'raw_any':any(raw),'learned_any':any(learned),'affine_any':any(affine)})
 csvwrite(four/'readout_case_divergence.csv',readout_cases)
 interventions=[json.loads(p.read_text()) for p in sorted((run/'interventions').glob('ddx*.json'))];components=interventions[0]['components'];events=[];patchcases=[]
 for r in interventions:
  y=disease.index(private[r['case_id']]['gold_disease']);old=np.array(r['previous_q']);cur=np.array(r['current_q']);target=int(winner(old));current=int(winner(cur));basejs=float(js(cur,old))
  for j,name in enumerate(components):
   q=np.array(r['q'][j]);events.append({'job_id':r['job_id'],'case_id':r['case_id'],'cohort':r['cohort'],'round':r['round'],'rotation':r['rotation'],
    'component':name,'original_switch':bool(target>=0 and current>=0 and target!=current),'old_top':target,'current_top':current,'patched_top':int(winner(q)),
    'restored_previous':bool(target>=0 and winner(q)==target),'changed_current':bool(changed(cur,q)),
    'toward_previous_js':basejs-float(js(q,old)),'delta_gold':float(q[y]-cur[y]),'candidate_mass':r['candidate_mass'][j]})
 csvwrite(four/'intervention_events.csv',events)
 for cid in eval_ids:
  for comp in components:
   rr=[r for r in events if r['case_id']==cid and r['component']==comp];sw=[r for r in rr if r['original_switch']]
   patchcases.append({'case_id':cid,'component':comp,'evidence_updates':len(rr),'switch_events':len(sw),
    'restore_rate_among_switches':float(np.mean([r['restored_previous'] for r in sw])) if sw else None,
    'change_rate_all':float(np.mean([r['changed_current'] for r in rr])),
    'toward_previous_js_all':float(np.mean([r['toward_previous_js'] for r in rr])),
    'toward_previous_js_switches':float(np.mean([r['toward_previous_js'] for r in sw])) if sw else None,
    'delta_gold_all':float(np.mean([r['delta_gold'] for r in rr])),
    'mean_candidate_mass':float(np.mean([r['candidate_mass'] for r in rr])),
    'fraction_mass_below_0_1':float(np.mean([r['candidate_mass']<.1 for r in rr]))})
 csvwrite(four/'intervention_case_metrics.csv',patchcases)
 patchsummary={}
 for comp in components:
  rr=[r for r in patchcases if r['component']==comp]
  patchsummary[comp]={k:ci([r[k] for r in rr if r[k] is not None]) for k in ['restore_rate_among_switches','change_rate_all','toward_previous_js_all','toward_previous_js_switches','delta_gold_all','mean_candidate_mass','fraction_mass_below_0_1']}
 paired={}
 for actual,control in [('previous_attention','shifted_attention_difference'),('previous_mlp','shifted_mlp_difference')]:
  differences={k:[] for k in ['restore_rate_among_switches','toward_previous_js_all','toward_previous_js_switches']}
  for cid in eval_ids:
   a=next(r for r in patchcases if r['case_id']==cid and r['component']==actual);b=next(r for r in patchcases if r['case_id']==cid and r['component']==control)
   for k in differences:
    if a[k] is not None:differences[k].append(a[k]-b[k])
  paired[actual]={k:ci(v) for k,v in differences.items()}
 readoutsummary={k:ci([r[k] for r in readout_cases]) for k in ['raw_divergence_rate','learned_divergence_rate','shuffled_divergence_rate','affine_divergence_rate','raw_any','learned_any','affine_any']}
 s4={'patches':patchsummary,'paired_direction_controls':paired,'readout_divergence':readoutsummary,
  'readout_l27':quality[26],'sham_max_candidate_logit_error':max(r['sham_max_abs_candidate_logit_error'] for r in interventions),
  'intervention_pairs_all_cohorts':len(interventions),'intervention_pairs_replication':sum(r['cohort']=='replication' for r in interventions),
  'switch_events_replication':int(sum(r['cohort']=='replication' and bool(changed(r['previous_q'],r['current_q'])) for r in interventions))}
 dump(four/'summary.json',s4)
 fig,axs=plt.subplots(1,2,figsize=(13,4.5),constrained_layout=True)
 labels={'previous_attention':'上一轮attention','previous_mlp':'上一轮MLP','shifted_attention_difference':'attention方向对照','shifted_mlp_difference':'MLP方向对照'}
 comps=list(labels)
 for ax,metric,title,percent in [(axs[0],'restore_rate_among_switches','原判断已切换时：恢复上一轮首选的比例',True),(axs[1],'toward_previous_js_all','所有证据更新：分布向上一轮靠近',False)]:
  means=[patchsummary[k][metric]['mean'] for k in comps];low=[patchsummary[k][metric]['low'] for k in comps];high=[patchsummary[k][metric]['high'] for k in comps]
  ax.bar(range(4),means,color=['#477bb5','#de952d','#a7bed5','#e7cda7']);ax.errorbar(range(4),means,yerr=[np.array(means)-low,np.array(high)-means],fmt='none',ecolor='black',capsize=4)
  ax.set_xticks(range(4),[labels[c] for c in comps],rotation=25,ha='right');ax.set(title=title,ylabel='病例平均比例' if percent else 'JS距离减少量（正值=靠近）');ax.axhline(0,color='black',lw=.6)
 savefig(fig,four/'figures/previous_state_interventions')
 fig,axs=plt.subplots(1,2,figsize=(12,4.2),constrained_layout=True)
 for k,label,color in [('raw_kl','原始输出头','#8c5baa'),('calibrated_kl','隐藏向量岭回归','#477bb5'),('affine_kl','六类分数仿射修正','#35947b'),('shuffled_kl','打乱目标对照','#999999'),('constant_kl','常数分布基线','#de952d')]:
  axs[0].plot(range(1,29),[r[k] for r in quality],label=label,color=color)
 for k,label,color in [('raw_agreement','原始输出头','#8c5baa'),('calibrated_agreement','隐藏向量岭回归','#477bb5'),('affine_agreement','六类分数仿射修正','#35947b'),('shuffled_agreement','打乱目标对照','#999999')]:
  axs[1].plot(range(1,29),[r[k] for r in quality],label=label,color=color)
 axs[0].set(title='预测同轮最终分布的误差',xlabel='层',ylabel='KL（越低越好）');axs[1].set(title='预测同轮最终首选的一致率',xlabel='层',ylabel='病例平均一致率',ylim=(0,1.05))
 for ax in axs:ax.legend(fontsize=8)
 savefig(fig,four/'figures/readout_quality')
 # Naming alternative and alias-length sensitivity.
 name_rows=[json.loads(p.read_text()) for p in sorted((run/'name_scores').glob('ddx*.json'))];name_effects=[]
 for r in name_rows:
  cid=r['case_id'];y=disease.index(private[cid]['gold_disease']);code=[x for x in rows if x['case_id']==cid and x['order']==r['order'] and x['round']==r['round']]
  assert len(code)==6;q=np.array([x['q'] for x in code]).mean(0);n=np.array(r['sequence_support']);ln=np.array(r['length_normalized_score_support'])
  name_effects.append({'case_id':cid,'cohort':r['cohort'],'order':r['order'],'code_top':int(winner(q)),'name_top':int(winner(n)),
   'mean_length_top':int(winner(ln)),'name_code_agree':bool(winner(n)==winner(q)),'name_correct':bool(winner(n)==y),'code_correct':bool(winner(q)==y),
   'length_normalized_correct':bool(winner(ln)==y),'length_metric_changes_top':bool(winner(n)!=winner(ln)),
   'name_code_js':float(js(n,q)),'name_candidate_mass':r['candidate_sequence_mass']})
 csvwrite(two/'name_endpoint_controls.csv',name_effects)
 name_cases=[]
 for cid in eval_ids:
  rr=[r for r in name_effects if r['case_id']==cid]
  name_cases.append({'case_id':cid,**{k:float(np.mean([r[k] for r in rr])) for k in ['name_code_agree','name_correct','code_correct','length_normalized_correct','length_metric_changes_top','name_code_js','name_candidate_mass']},
   'name_order_any_change':len({r['name_top'] for r in rr})>1,'code_order_any_change':len({r['code_top'] for r in rr})>1})
 ns={k:ci([r[k] for r in name_cases]) for k in name_cases[0] if k!='case_id'};dump(two/'name_control_summary.json',ns);csvwrite(two/'name_case_metrics.csv',name_cases)
 # Reproduction of original 12 cases under the new scorer.
 oldroot=ROOT.parent/'MedicalBelief1_7B/runs/phase1_direct_v2';oldobs=[json.loads(p.read_text()) for p in (oldroot/'observations').glob('*_m0.json')]
 concord=[]
 for old in oldobs:
  job=f'{old["case_id"]}_base_t{old["round"]:02d}_m0';cur=lookup[job]
  assert old['prompt_sha256']==cur['prompt_sha256']
  concord.append({'case_id':old['case_id'],'round':old['round'],'top_same':old['conditional_top_disease']==cur['top_disease'],'max_support_difference':float(np.abs(np.array(old['candidate_support'])-cur['q']).max())})
 dump(five/'pilot_reproduction.json',{'observations':len(concord),'top_agreements':sum(r['top_same'] for r in concord),'max_support_difference':max(r['max_support_difference'] for r in concord),'rows':concord})
 # Stage 02 paper text.
 text=['# 阶段02：独立病例中的层间分歧与诊断转移','', '## 方法','',
  '新增60个DDxPlus病例，六类疾病各10例；另保留12例探索病例。年龄18—90岁，至少4组新增明确证据，按固定哈希选择，逐组揭示全部记录。所有前缀运行两种循环映射；初始、中间和终点补齐六映射。主要分析以新增病例为单位；区间为2000次病例bootstrap的95%区间，病例事件比例为0或1时使用精确二项边界区间。', '',
  '评分取诊断位置未采样logits的六类归一化分布，不要求生成完整回答。“正确/错误”指与数据最终标签的关系，不将早期资料不全时的标签偏离单独判为临床推理错误。两个时间点均有唯一首选且疾病不同才计为疾病切换；并列单独记录。', '',
  '层间分歧定义为：第24—27层原始输出头读出一致首选同一疾病，而第28层首选其他疾病。跨映射重复要求同一前缀在两种映射下都出现分歧，且转向的疾病对相同。', '',
  '## 结果','', '| 指标 | 新增60例中的结果 |','|---|---|']
 for key,label in [('any_divergence','至少一次层间分歧的病例'),('divergence_rate','病例平均前缀分歧率'),('any_robust_divergence','两映射重复同一分歧的病例'),('robust_divergence_rate','两映射重复的前缀比例'),('harmful_rate','前面层标签正确、末层标签错误的前缀比例'),('corrective_rate','前面层标签错误、末层标签正确的前缀比例'),('regression_any','曾先对后错的病例'),('stable_late_final_flip_any','前面四层维持原首选、末层随新证据翻转的病例'),('mapping_endpoint_changes','终点首选随映射改变的病例'),('final_mapping_mean_correct','六映射平均支持的终点标签一致率')]:text.append(f'| {label} | {fmt(s2["case_weighted"][key])} |')
 text += ['',f'共有{s2["new_case_counts"]["any_divergence"]}/60例出现层间分歧，其中{s2["new_case_counts"]["any_robust_divergence"]}/60例在两种映射下重复同一疾病转向。探索12例单独报告于统计文件，未进入上表。', '',
  '![层间分歧的疾病组分布](figures/divergence_prevalence.png)','', '![逐条证据的疾病转移](figures/disease_transition_matrix.png)','', '![逐层方向与最终输出](figures/layer_profile.png)', '',
  '## 支持强度与错误方向','',f'首选错误且候选支持至少90%的病例平均前缀比例为{fmt(s2["case_weighted"]["wrong_high_support_rate"])}。至少一次出现“保持同一错误首选、支持增加超过5个百分点”的病例比例为{fmt(s2["case_weighted"]["wrong_support_increase_any"])}。六类Brier分数的病例平均值为{fmt(s2["case_weighted"]["brier_score"],False)}。这些是概率偏好的描述性指标，不表示临床患病概率已经校准。', '',
  '## 输出形式对照','',f'终点改为直接输出疾病名称后，与代码六映射平均首选的一致率为{fmt(ns["name_code_agree"])}；名称完整序列评分的标签一致率为{fmt(ns["name_correct"])}。按名称每词元平均分评分时，首选改变比例为{fmt(ns["length_metric_changes_top"])}。名称序列总概率均值为{ns["name_candidate_mass"]["mean"]:.6g}。', '',
  '名称总log概率为主分析，每词元平均log概率为长度敏感性分析。名称与代码任务并不等价；差异说明测量依赖，不能只选更准确的评分形式作为结论。', '',
  '## 结论','',
  f'层间分歧在新增病例中出现，但跨映射重复病例数由{s2["new_case_counts"]["any_divergence"]}降至{s2["new_case_counts"]["any_robust_divergence"]}。'+('本轮没有支持“前面四层保持医学信念、末层稳定推翻它”的跨编码机制解释。' if s2['new_case_counts']['any_robust_divergence']==0 else '跨编码重复部分与单一映射现象必须分开解释。')+'原始层读出表示该固定读出下可见的疾病支持，是否参与最终决策由阶段04的局部替换进一步检验。', '',
  '[逐病例指标](case_metrics.csv) · [完整证据转移](evidence_transitions.csv) · [层间分歧表](layer_divergence.csv) · [72例图谱索引](CASE_ATLAS.md) · [名称对照](name_endpoint_controls.csv)','']
 (two/'RESULTS.md').write_text('\n'.join(text))
 text=['# 阶段03：相同证据集合的顺序效应','','## 方法','',
  '每个病例使用基础哈希、逆序和另一哈希三种揭示顺序。初始组与最终证据集合保持相同。每轮独立输入累计记录，模型不接收前轮答案。终点逐病例、逐映射配对；六映射平均分布作为辅助汇总。中间轮信息集合不同，因此仅展示路径，不把中间差异当作纯顺序效应。', '',
  '## 结果','','| 指标 | 逆序 vs 基础 | 另一哈希 vs 基础 |','|---|---|---|']
 for key,label in [('single_mapping_flip_fraction','病例平均同映射首选改变比例'),('any_mapping_flip','至少一种映射首选改变的病例'),('mean_mapping_top_flip','六映射平均首选改变的病例'),('mean_total_variation','终点分布总变差'),('mean_js','终点JS散度'),('alternative_mean_correct','替代顺序六映射平均标签一致率')]:
  text.append(f'| {label} | {fmt(s3["reverse"][key],key not in ["mean_total_variation","mean_js"])} | {fmt(s3["shuffle"][key],key not in ["mean_total_variation","mean_js"])} |')
 text += ['','![配对终点效应](figures/order_endpoint_effects.png)','','![证据揭示过程](figures/evidence_progress.png)','','## 结论','',
  '最终资料内容相同，但其排列可以改变模型终端分布和首选疾病。当前实验支持提示内的排列敏感性；由于每轮重新计算且不保留前轮回答，不把该结果解释为持久记忆或自我承诺。按问题ID规范排序后，三种顺序的终点输入完全一致。', '',
  f'疾病名称评分下，三种顺序至少一次改变首选的病例比例为{fmt(ns["name_order_any_change"])}；代码六映射平均首选对应比例为{fmt(ns["code_order_any_change"])}。', '',
  '[终点配对数据](matched_endpoint_effects.csv) · [完整轨迹指标](trajectory_metrics.csv) · [证据进度分数](evidence_progress.csv)','']
 (three/'RESULTS.md').write_text('\n'.join(text))
 text=['# 阶段04：独立读出与最后层计算的局部干预','','## 方法','',
  '使用独立fit病例120例训练、60例选择正则，每例初始、中间和终点三个前缀。每层用L2归一化隐藏状态拟合六类岭回归，目标为同轮模型的最终疾病分布。真值标签不参与训练。测试在新增60例上进行；加入病例块打乱目标及常数分布对照。该读出是六类任务读出，不是全词表Tuned Lens。', '',
  '对基础顺序、两种映射下的全部相邻轮，在最后层诊断锚点分别替换attention或MLP增量为上一轮状态。attention替换后重新计算最后层MLP。方向对照将相同增量差沿隐藏维度循环移位；sham用当前状态。恢复率只在原本发生首选切换的点上定义，再按病例平均。', '',
  '## 读出结果','',
  f'第27层原始读出预测最终分布的KL为{quality[26]["raw_kl"]:.4f}；独立任务读出为{quality[26]["calibrated_kl"]:.4f}；打乱目标对照为{quality[26]["shuffled_kl"]:.4f}。对应首选一致率分别为{quality[26]["raw_agreement"]:.2%}、{quality[26]["calibrated_agreement"]:.2%}、{quality[26]["shuffled_agreement"]:.2%}。', '',
  f'原始读出的病例平均层间分歧率为{fmt(readoutsummary["raw_divergence_rate"])}，独立任务读出为{fmt(readoutsummary["learned_divergence_rate"])}。读出训练目标本身是最终分布，分歧减少不能单独作为内部已经一致的证据。', '',
  f'开发集上隐藏向量岭回归未改善后几层，因此增加六类logits的仿射修正，仍只用原有训练与开发病例选参数。独立测试第27层KL为{quality[26]["affine_kl"]:.4f}，首选一致率为{quality[26]["affine_agreement"]:.2%}；修正后的病例平均层间分歧率为{fmt(readoutsummary["affine_divergence_rate"])}。这是开发集驱动的方法迭代，未改动测试病例。', '',
  '![独立读出的预测质量](figures/readout_quality.png)','','## 干预结果','','| 替换方式 | 切换点恢复上一轮首选 | 全部更新向上一轮靠近的JS量 | 干预后候选质量 |','|---|---|---|---|']
 for comp in comps:
  s=patchsummary[comp];text.append(f'| {labels[comp]} | {fmt(s["restore_rate_among_switches"])} | {fmt(s["toward_previous_js_all"],False)} | {fmt(s["mean_candidate_mass"])} |')
 text += ['',f'新增病例共有{s4["intervention_pairs_replication"]}对相邻轮，其中{s4["switch_events_replication"]}对发生首选切换。', '',
  f'相对等范数方向对照，attention替换的恢复率差为{fmt(paired["previous_attention"]["restore_rate_among_switches"])}；MLP替换的恢复率差为{fmt(paired["previous_mlp"]["restore_rate_among_switches"])}。区间按病例配对重采样。', '',
  '![上一轮内部状态替换](figures/previous_state_interventions.png)','','## 结论','',
  f'最后层MLP的上一轮增量可以定向恢复部分旧诊断：病例平均恢复率为{fmt(patchsummary["previous_mlp"]["restore_rate_among_switches"])}，方向对照为{fmt(patchsummary["shifted_mlp_difference"]["restore_rate_among_switches"])}。注意力替换未显示同等恢复作用。因此，最后层MLP的计算内容参与了本任务的诊断更新，而不是任意同等扰动都能得到同样结果。', '',
  f'内部“分歧”的频率也取决于读法：原始输出头为{fmt(readoutsummary["raw_divergence_rate"])}，隐藏向量岭回归为{fmt(readoutsummary["learned_divergence_rate"])}，预测最终分布更准确的六维仿射修正为{fmt(readoutsummary["affine_divergence_rate"])}。应把读出差异与实际干预效果分别解释。', '',
  '[逐层读出质量](readout_quality.csv) · [所有干预事件](intervention_events.csv) · [病例级干预统计](intervention_case_metrics.csv) · [读出分歧](readout_case_divergence.csv)','']
 (four/'RESULTS.md').write_text('\n'.join(text))
 # Explicit supported conclusions depend on paired intervals rather than selected cases.
 claims=[]
 for comp in ['previous_attention','previous_mlp']:
  c=paired[comp]['restore_rate_among_switches'];label='attention' if comp=='previous_attention' else 'MLP'
  if c['low'] is not None and c['low']>0:claims.append(f'最后层{label}的上一轮状态替换，比同范数方向对照更能恢复旧诊断（差值{fmt(c)}）。这支持该增量的信息方向参与当前诊断更新。')
  else:claims.append(f'最后层{label}的恢复率相对方向对照差值为{fmt(c)}；当前病例区间未支持稳定的正向差异。')
 if quality[26]['calibrated_kl']<quality[26]['raw_kl']:claims.append('第27层的独立任务读出降低了预测最终分布的误差，为原始输出头之外的表征测量提供补充。')
 else:claims.append('第27层的独立任务读出未优于原始输出头；这套线性读出不足以充当更可靠的内部信念估计。')
 claims[-1]+=f' 六类分数仿射修正后的KL为{quality[26]["affine_kl"]:.4f}（原始{quality[26]["raw_kl"]:.4f}），其层间分歧率为{fmt(readoutsummary["affine_divergence_rate"])}。'
 original_hypothesis=('原始个案提出的跨编码稳定层间分歧未获支持：独立60例中没有重复同一转向的病例。不能据原始图宣称存在被末层压制的稳定医学信念。' if s2['new_case_counts']['any_robust_divergence']==0 else f'跨两个编码重复的层间分歧见于{s2["new_case_counts"]["any_robust_divergence"]}/60例，结论限于这一稳定子集。')
 synthesis=['# 医学证据更新的层间分歧：独立病例、顺序对照与局部干预','','## 摘要','',
  f'在Qwen3-1.7B上，对60例独立DDxPlus病例与12例探索病例进行三种证据顺序和多种答案映射的逐层测量，并使用180例独立病例训练、开发任务读出。共完成6600个直接诊断观察点、{len(interventions)}对最后层干预及{len(name_rows)}个疾病名称评分终点。新增病例中{s2["new_case_counts"]["any_divergence"]}/60例出现第24—27层一致而第28层不同的原始读出分歧；{s2["new_case_counts"]["any_robust_divergence"]}/60例在两种映射下重复同一疾病转向。', '',
  original_hypothesis,'','## 主要结论','']+[f'{i+1}. {s}' for i,s in enumerate(claims)]+['',
  f'4. 相同证据集合的逆序，使同一映射下终点首选改变的病例平均比例达到{fmt(s3["reverse"]["single_mapping_flip_fraction"])}。顺序效应与最终事实集合相同可以同时存在。', '',
  f'5. 输出编码是实质影响因素：{s2["new_case_counts"]["mapping_endpoint_changes"]}/60例的终点首选随六种映射改变；疾病名称与代码的终点首选一致率为{fmt(ns["name_code_agree"])}。因此层间现象必须报告跨编码稳定部分。', '',
  '## 论文逻辑','',
  '研究问题：新医学证据怎样改变模型内部的疾病支持，最终诊断是否忠实保留后几层的方向？', '',
  '实验链：逐层轨迹发现分歧 → 独立病例估计频率 → 编码与名称对照定位测量依赖 → 固定事实集合的顺序配对 → 独立读出评价 → 最后层状态替换与方向对照。', '',
  '结论范围：单个1.7B模型、六类限定候选、模拟病例、无历史回答的直接诊断。稳定机制的进一步外推需要更多模型和疾病，以及病例历史条件；未据此提出临床决策建议。', '',
  '## 阶段结果','',
  '- [01 探索](../01_pilot/RESULTS.md)', '- [02 独立复现与疾病转移](../02_replication/RESULTS.md)', '- [03 证据顺序](../03_evidence_order/RESULTS.md)', '- [04 内部读出与局部干预](../04_internal_mechanism/RESULTS.md)', '',
  '## 方法依据','',
  '逐层任务读出参考[Tuned Lens](https://arxiv.org/abs/2303.08112)的读出验证思路；局部替换的指标和对照参考[activation patching方法研究](https://arxiv.org/abs/2309.16042)及[解释指南](https://arxiv.org/abs/2404.15255)。本研究不将六类岭回归命名为完整Tuned Lens。','']
 (five/'RESULTS.md').write_text('\n'.join(synthesis))
 dump(run/'synthesis_completion.json',{'complete':True,'observations':6600,'intervention_pairs':len(interventions),'name_endpoints':len(name_rows),'new_cases':60,'exploratory_cases':12,'independent_readout_cases':180,
  'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'claims':claims,'api_cost_usd':0})
 print(json.dumps({'stage4':s4,'names':ns,'claims':claims},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
