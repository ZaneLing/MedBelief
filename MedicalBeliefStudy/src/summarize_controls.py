from pathlib import Path
import argparse,collections,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze_stages import ROOT,ZH,ci,fmt,js,winner,changed,divinfo,csvwrite,dump,savefig,setup
from evidence_labels import EVIDENCE_ZH

def insert_before(path,heading,lines):
 text=path.read_text();assert heading in text
 text=text.replace(heading,'\n'.join(lines)+'\n\n'+heading,1);path.write_text(text)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run-id',default='expanded_v1');args=ap.parse_args();setup();run=ROOT/'runs'/args.run_id
 for d in ['content_controls','depth_interventions']:assert (run/d/'completion.json').exists()
 two=ROOT/'results/02_replication';four=ROOT/'results/04_internal_mechanism';five=ROOT/'results/05_synthesis'
 private={r['case_id']:r for r in map(json.loads,(ROOT/'data/cases.private.jsonl').read_text().splitlines())};diseases=json.loads((run/'manifest.json').read_text())['diseases']
 observed={p.stem:json.loads(p.read_text()) for p in (run/'observations').glob('*.json')}
 neutral=[json.loads(p.read_text()) for p in sorted((run/'content_controls').glob('ddx*.json'))];events=[]
 for r in neutral:
  y=diseases.index(private[r['case_id']]['gold_disease']);a,b,n=map(np.array,[r['previous_q'],r['real_q'],r['neutral_q']]);actual=observed[r['job_id']]
  events.append({'case_id':r['case_id'],'cohort':r['cohort'],'job_id':r['job_id'],'rotation':r['rotation'],'round':r['round'],'replaced_tokens':r['replaced_tokens'],
   'real_update_js':float(js(a,b)),'neutral_update_js':float(js(a,n)),'real_minus_neutral_update_js':float(js(a,b)-js(a,n)),
   'real_top_change':bool(changed(a,b)),'neutral_top_change':bool(changed(a,n)),
   'real_neutral_top_different':bool(changed(b,n)),'real_delta_gold':float(b[y]-a[y]),'neutral_delta_gold':float(n[y]-a[y]),
   'real_divergence':divinfo(actual['layer_q'],y)['divergence'],'neutral_divergence':divinfo(r['neutral_layer_q'],y)['divergence'],'neutral_mass':r['neutral_mass']})
 csvwrite(four/'content_control_events.csv',events);cases=[]
 for cid,c in private.items():
  if c['cohort']!='replication':continue
  rr=[r for r in events if r['case_id']==cid];assert len(rr)==2
  cases.append({'case_id':cid,**{k:float(np.mean([r[k] for r in rr])) for k in ['real_update_js','neutral_update_js','real_minus_neutral_update_js','real_top_change','neutral_top_change','real_neutral_top_different','real_delta_gold','neutral_delta_gold','real_divergence','neutral_divergence','neutral_mass']}})
 csvwrite(four/'content_control_cases.csv',cases);summary={k:ci([r[k] for r in cases]) for k in cases[0] if k!='case_id'}
 dump(four/'content_control_summary.json',summary)
 fig,axs=plt.subplots(1,2,figsize=(11,4.5),constrained_layout=True)
 for ax,keys,title in [(axs[0],['real_update_js','neutral_update_js'],'新增内容引起的疾病分布变化'),(axs[1],['real_top_change','neutral_top_change'],'首选疾病切换比例')]:
  xx=[summary[k]['mean'] for k in keys];lo=[summary[k]['low'] for k in keys];hi=[summary[k]['high'] for k in keys]
  ax.bar([0,1],xx,color=['#477bb5','#aab3bd']);ax.errorbar([0,1],xx,yerr=[np.array(xx)-lo,np.array(hi)-xx],fmt='none',ecolor='black',capsize=4)
  ax.set_xticks([0,1],['真实新证据','等长行政占位']);ax.set(title=title,ylabel='JS散度' if ax is axs[0] else '病例平均比例')
 savefig(fig,four/'figures/content_control')
 # Depth profiles, excluding only predeclared numerical instability.
 depth=[json.loads(p.read_text()) for p in sorted((run/'depth_interventions').glob('ddx*.json'))];de=[]
 for r in depth:
  if r['cohort']!='replication':continue
  old=np.array(r['previous_q']);cur=np.array(r['current_q']);sw=bool(changed(old,cur))
  for j,component in enumerate(r['components']):
   q=np.array(r['q'][j]);de.append({'case_id':r['case_id'],'job_id':r['job_id'],'layer':r['layer'],'rotation':r['rotation'],'component':component,
    'stable':r['numerically_stable'],'original_switch':bool(sw),'restore_previous':bool(winner(q)==winner(old)),
    'toward_previous_js':float(js(cur,old)-js(q,old)),'candidate_mass':r['candidate_mass'][j]})
 csvwrite(four/'depth_intervention_events.csv',de);dc=[]
 comps=depth[0]['components'];cids=sorted({r['case_id'] for r in de})
 for cid in cids:
  for l in range(24,29):
   for comp in comps:
    rr=[r for r in de if r['case_id']==cid and r['layer']==l and r['component']==comp and r['stable']]
    if not rr:continue
    sw=[r for r in rr if r['original_switch']]
    dc.append({'case_id':cid,'layer':l,'component':comp,'valid_mappings':len(rr),'toward_previous_js':float(np.mean([r['toward_previous_js'] for r in rr])),
     'restore_rate':float(np.mean([r['restore_previous'] for r in sw])) if sw else None,'candidate_mass':float(np.mean([r['candidate_mass'] for r in rr]))})
 csvwrite(four/'depth_case_metrics.csv',dc);ds=[]
 for l in range(24,29):
  for comp in comps:
   rr=[r for r in dc if r['layer']==l and r['component']==comp]
   ds.append({'layer':l,'component':comp,'toward_previous_js':ci([r['toward_previous_js'] for r in rr]),'restore_rate':ci([r['restore_rate'] for r in rr if r['restore_rate'] is not None]),'candidate_mass':ci([r['candidate_mass'] for r in rr])})
 paired=[]
 for l in range(24,29):
  for comp,ctrl in [('previous_attention','shifted_attention_difference'),('previous_mlp','shifted_mlp_difference')]:
   diff=[]
   for cid in cids:
    aa=[r for r in dc if r['case_id']==cid and r['layer']==l and r['component']==comp];bb=[r for r in dc if r['case_id']==cid and r['layer']==l and r['component']==ctrl]
    if aa and bb:diff.append(aa[0]['toward_previous_js']-bb[0]['toward_previous_js'])
   paired.append({'layer':l,'component':comp,'actual_minus_direction_control':ci(diff)})
 excluded=[r for r in depth if r['cohort']=='replication' and not r['numerically_stable']]
 dump(four/'depth_summary.json',{'profiles':ds,'paired_direction_controls':paired,'excluded_numeric_checks':len(excluded),'checked_replication_prefix_depths':600,'exclusions':[r['job_id']+f'_l{r["layer"]}' for r in excluded]})
 fig,ax=plt.subplots(figsize=(10,4.5),constrained_layout=True)
 for comp,label,color,style in [('previous_attention','上一轮attention','#477bb5','-'),('previous_mlp','上一轮MLP','#de952d','-'),('shifted_attention_difference','attention方向对照','#477bb5','--'),('shifted_mlp_difference','MLP方向对照','#de952d','--')]:
  rr=[r for r in ds if r['component']==comp];yy=[r['toward_previous_js']['mean'] for r in rr];ax.plot(range(24,29),yy,style,color=color,label=label,marker='o')
  ax.fill_between(range(24,29),[r['toward_previous_js']['low'] for r in rr],[r['toward_previous_js']['high'] for r in rr],color=color,alpha=.08)
 ax.axhline(0,color='black',lw=.6);ax.set(xticks=range(24,29),xlabel='被干预的层',ylabel='最终分布向上一轮靠近的JS量',title='固定中间轮：干预位置从第24层移动到第28层');ax.legend(fontsize=9);savefig(fig,four/'figures/depth_profile')
 extra=['## 新证据内容与长度对照','',
  f'每例固定中间轮、两种映射，新增病例共120个对照点。真实证据相对上一轮引起的JS变化为{fmt(summary["real_update_js"],False)}；等词元长度占位为{fmt(summary["neutral_update_js"],False)}；病例配对差为{fmt(summary["real_minus_neutral_update_js"],False)}。真实与占位的首选切换率分别为{fmt(summary["real_top_change"])}和{fmt(summary["neutral_top_change"])}。', '',
  '占位保留输入长度、诊断位置及其他所有词元，仅替换新证据正文。占位语言不是自然医学问答，该对照隔离长度与位置，不能完全隔离语言自然度。', '',
  '![内容对照](figures/content_control.png)', '',
  '## 干预深度对照','',f'在相同中间轮对第24—28层分别干预，再重新计算后续层的诊断锚点。600个独立病例“前缀×深度”检查中，{len(excluded)}个未通过预设sham一致性检查，已保留并排除于深度主统计。', '',
  '| 干预层 | attention相对方向对照的JS增益 | MLP相对方向对照的JS增益 |','|---|---|---|']
 for l in range(24,29):
  aa=next(r for r in paired if r['layer']==l and r['component']=='previous_attention');bb=next(r for r in paired if r['layer']==l and r['component']=='previous_mlp')
  extra.append(f'| {l} | {fmt(aa["actual_minus_direction_control"],False)} | {fmt(bb["actual_minus_direction_control"],False)} |')
 mlp26=next(r['toward_previous_js'] for r in ds if r['layer']==26 and r['component']=='previous_mlp')
 mlp27=next(r['toward_previous_js'] for r in ds if r['layer']==27 and r['component']=='previous_mlp')
 mlp28=next(r['toward_previous_js'] for r in ds if r['layer']==28 and r['component']=='previous_mlp')
 reversal=(mlp26['high']<0 and mlp27['high']<0 and mlp28['low']>0)
 depth_claim=(f'旧MLP增量的作用随层位置反转：在第26层和第27层，最终分布平均更远离上一轮（JS靠近量分别为{fmt(mlp26,False)}、{fmt(mlp27,False)}）；在第28层则更接近上一轮（{fmt(mlp28,False)}）。三个区间均不跨0。该符号模式属于探索性归纳，区间未经多重比较校正。' if reversal else '不同层的旧MLP增量替换效果见完整曲线，本轮未形成同样的方向反转模式。')
 extra+=['',depth_claim,'','![干预深度曲线](figures/depth_profile.png)','', '[内容对照数据](content_control_events.csv) · [逐深度干预数据](depth_intervention_events.csv) · [数值检查排除表](depth_summary.json)','']
 insert_before(four/'RESULTS.md','## 结论',extra)
 # Aggregate evidence effects at the case level; exploratory groups with >=5 independent cases.
 import csv
 with (two/'evidence_transitions.csv').open() as f:ev=[r for r in csv.DictReader(f) if r['cohort']=='replication' and r['order']=='base']
 groups=collections.defaultdict(list)
 for r in ev:groups[r['question_group']].append(r)
 erows=[]
 for gid,rr in groups.items():
  cset=sorted({r['case_id'] for r in rr});per=[]
  for cid in cset:
   cr=[r for r in rr if r['case_id']==cid]
   per.append({'js':float(np.mean([float(r['js']) for r in cr])),'switch':float(np.mean([r['switch']=='True' for r in cr])),
    **{d:float(np.mean([float(r['delta_'+d]) for r in cr])) for d in diseases}})
  erows.append({'question_group':gid,'description_zh':EVIDENCE_ZH.get(gid,gid),'cases':len(cset),'mean_js':float(np.mean([r['js'] for r in per])),
   'switch_rate':float(np.mean([r['switch'] for r in per])),**{d:float(np.mean([r[d] for r in per])) for d in diseases},
   'case_ids':';'.join(cset)})
 erows.sort(key=lambda r:-r['mean_js']);csvwrite(two/'evidence_group_effects.csv',erows)
 selected=[r for r in erows if r['cases']>=5][:15]
 fig,ax=plt.subplots(figsize=(10,8),constrained_layout=True);a=np.array([[r[d] for d in diseases] for r in selected]);bound=max(.1,float(np.abs(a).max()))
 short={'E_129':'皮肤问题及其细节','E_53':'疼痛及其细节','E_151':'身体肿胀及部位'}
 im=ax.imshow(a,aspect='auto',vmin=-bound,vmax=bound,cmap='RdBu');ax.set_xticks(range(6),ZH,rotation=30,ha='right');ax.set_yticks(range(len(selected)),[short.get(r['question_group'],r['description_zh'])+f' (n={r["cases"]})' for r in selected],fontsize=9)
 ax.set(title='哪些证据把支持推向哪些疾病？（至少5例，按JS排序）',xlabel='新增证据后的平均疾病支持变化');fig.colorbar(im,ax=ax,label='蓝=推高；红=压低');savefig(fig,two/'figures/evidence_effects')
 insert_before(two/'RESULTS.md','## 输出形式对照',['## 证据类型与疾病方向','',
  '对每个证据问题，先在病例内平均两种映射，再对出现该问题的病例平均。下图显示至少5个病例中出现的证据组，按JS变化选前15组；完整问题表均保留。这是条件于当前上下文的描述性关联，不是对某条证据固有临床权重的估计。', '',
  '![证据组与疾病支持变化](figures/evidence_effects.png)','', '[全部证据组统计](evidence_group_effects.csv)',''])
 conclusion=f'内容对照：真实新证据比等长占位引起的JS变化多{fmt(summary["real_minus_neutral_update_js"],False)}。'
 if summary['real_minus_neutral_update_js']['low']>0:conclusion+='这支持医学内容的影响超过单纯长度与位置变化。'
 else:conclusion+='配对均值差的95%区间包含0，尚未确认真实内容的平均变化大于等长占位。'
 insert_before(five/'RESULTS.md','## 论文逻辑',['## 内容与深度复核','',depth_claim,'',conclusion,'',
  f'第24—28层均做了固定中间轮的局部干预，完整深度曲线见阶段04。数值一致性不通过的{len(excluded)}个前缀×深度记录保留在排除表中；论文对层位置的解释应依据全深度曲线，而非只挑最后一层。',''])
 dump(run/'controls_analysis_completion.json',{'complete':True,'content_prefixes':144,'depth_prefix_layer_checks':720,'new_case_numeric_exclusions':len(excluded),'content_summary':summary,'depth_paired_controls':paired,'posthoc_depth_sign_reversal':reversal})
 print(json.dumps({'content':summary,'depth_exclusions':len(excluded),'depth_paired':paired},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
