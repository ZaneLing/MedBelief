"""Case-level inference, transition atlas, paper-style stage results."""
from pathlib import Path
import argparse,collections,csv,hashlib,json,re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import ListedColormap,BoundaryNorm
from evidence_labels import describe
ROOT=Path(__file__).resolve().parents[1]
ZH=['肺炎','支气管炎','哮喘急性发作','肺栓塞','自发性气胸','急性肺水肿']
COLORS=['#c43b37','#de952d','#477bb5','#8c5baa','#35947b','#69717d']
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def csvwrite(p,rows):
 if not rows:return
 keys=list(dict.fromkeys(k for r in rows for k in r))
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def winner(q):
 q=np.asarray(q);ix=q.argmax(-1);return np.where((q==q.max(-1,keepdims=True)).sum(-1)==1,ix,-1)
def changed(a,b):
 aa,bb=winner(a),winner(b)
 return (aa>=0)&(bb>=0)&(aa!=bb)
def js(p,q):
 p=np.asarray(p);q=np.asarray(q);m=(p+q)/2
 return .5*np.sum(p*np.log((p+1e-12)/(m+1e-12))+q*np.log((q+1e-12)/(m+1e-12)),axis=-1)
def entropy(p):return -np.sum(p*np.log(np.maximum(p,1e-12)),axis=-1)/np.log(6)
def ci(values):
 binary=bool(len(values)) and all(isinstance(v,(bool,np.bool_)) for v in values)
 x=np.asarray(values,dtype=float);x=x[np.isfinite(x)]
 if len(x)==0:return {'mean':None,'low':None,'high':None,'cases':0}
 if binary and (np.all(x==0) or np.all(x==1)):
  low,high=(0.,1-.025**(1/len(x))) if np.all(x==0) else (.025**(1/len(x)),1.)
  return {'mean':float(x.mean()),'low':low,'high':high,'cases':len(x),'method':'exact_binomial_boundary'}
 rng=np.random.default_rng(20261119);means=x[rng.integers(0,len(x),(2000,len(x)))].mean(-1)
 return {'mean':float(x.mean()),'low':float(np.quantile(means,.025)),'high':float(np.quantile(means,.975)),'cases':len(x)}
def fmt(c,percent=True):
 if c['mean'] is None:return '无适用病例'
 factor=100 if percent else 1;suffix='%' if percent else ''
 if c['mean']==0 and c['low']==0 and c['high']==0:return f'0.00{suffix}（样本内全零）'
 precision=2 if percent else 4
 return f'{c["mean"]*factor:.{precision}f}{suffix} [{c["low"]*factor:.{precision}f}, {c["high"]*factor:.{precision}f}]'
def savefig(fig,path):
 fig.savefig(path.with_suffix('.png'),dpi=160);fig.savefig(path.with_suffix('.pdf'));plt.close(fig)
def setup():
 for font in ['/System/Library/Fonts/Supplemental/Arial Unicode.ttf','/System/Library/Fonts/Hiragino Sans GB.ttc']:
  if Path(font).exists():font_manager.fontManager.addfont(font);plt.rcParams['font.family']=font_manager.FontProperties(fname=font).get_name();break
 plt.rcParams['axes.unicode_minus']=False
def divinfo(q,y):
 q=np.asarray(q);pred=winner(q);late=pred[23:27];unanimous=bool(np.all(late==late[0]) and late[0]>=0)
 divergence=bool(unanimous and pred[-1]>=0 and late[0]!=pred[-1])
 return {'unanimous':unanimous,'late_disease':int(late[0]) if unanimous else -1,'final_disease':int(pred[-1]),
  'divergence':divergence,'harmful':bool(divergence and late[0]==y),'corrective':bool(divergence and pred[-1]==y),
  'l27_disagree':bool(pred[-2]>=0 and pred[-1]>=0 and pred[-2]!=pred[-1]),'late_final_js':float(js(q[23:27].mean(0),q[-1]))}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run-id',default='expanded_v1');ap.add_argument('--skip-atlas',action='store_true');args=ap.parse_args();setup()
 run=ROOT/'runs'/args.run_id;assert (run/'completion.json').exists()
 private={r['case_id']:r for r in map(json.loads,(ROOT/'data/cases.private.jsonl').read_text().splitlines())}
 jobs={r['job_id']:r for r in map(json.loads,(ROOT/'data/jobs.public.jsonl').read_text().splitlines())}
 rows=[json.loads(p.read_text()) for p in sorted((run/'observations').glob('*.json'))];assert len(rows)==6600
 disease=json.loads((run/'manifest.json').read_text())['diseases'];names=dict(zip(disease,ZH))
 lookup={(r['case_id'],r['order'],r['round'],r['rotation']):r for r in rows}
 core=[r for r in rows if r['cohort'] in ['replication','pilot'] and r['rotation'] in [0,3]]
 eval_ids=[cid for cid,c in private.items() if c['cohort']=='replication'];pilot_ids=[cid for cid,c in private.items() if c['cohort']=='pilot'];assert len(eval_ids)==60
 output={n:ROOT/'results'/n for n in ['02_replication','03_evidence_order','04_internal_mechanism','05_synthesis']}
 for p in output.values():
  (p/'figures').mkdir(exist_ok=True)
 two=output['02_replication'];three=output['03_evidence_order'];four=output['04_internal_mechanism'];five=output['05_synthesis']
 case_metrics=[];all_events=[];divs=[];trajectory_metrics=[];transition=np.zeros((6,6));layer_count=np.zeros((28,6,6));mass_by_layer=[]
 for cid in eval_ids+pilot_ids:
  c=private[cid];y=disease.index(c['gold_disease']);T=len(c['new_group_order']);case_rows=[];events=[]
  for order in ['base','reverse','shuffle']:
   for rotation in [0,3]:
    traj=[lookup[cid,order,t,rotation] for t in range(T+1)];qq=np.array([r['q'] for r in traj]);pred=winner(qq);correct=pred==y
    first=next((t for t,v in enumerate(correct) if v),None);stable=next((t for t in range(T+1) if np.all(correct[t:])),None)
    trajectory_metrics.append({'case_id':cid,'cohort':c['cohort'],'disease':c['gold_disease'],'order':order,'rotation':rotation,'first_correct':first,'stable_correct':stable,
     'first_correct_fraction':first/T if first is not None else None,'stable_correct_fraction':stable/T if stable is not None else None,
     'final_correct':bool(correct[-1]),'regressions':int(np.sum(correct[:-1]&~correct[1:]&(pred[1:]>=0))),'recoveries':int(np.sum(~correct[:-1]&correct[1:]&(pred[:-1]>=0))),
     'switches':int(np.sum(changed(qq[:-1],qq[1:]))),'tied_rounds':int(np.sum(pred<0)),'final_entropy':float(entropy(qq[-1]))})
    for t,r in enumerate(traj):
     info=divinfo(r['layer_q'],y);record={'case_id':cid,'cohort':c['cohort'],'round':t,'order':order,'rotation':rotation,
      'wrong_high_support':bool(winner(r['q'])!=y and max(r['q'])>=.9),
      'brier_score':float(np.sum((np.array(r['q'])-np.eye(6)[y])**2)),**info}
     divs.append(record)
     if order=='base':case_rows.append(record)
     if c['cohort']=='replication' and order=='base':
      mass_by_layer.append(r['layer_mass']);w=winner(r['layer_q'])
      for l in range(28):
       if w[l]>=0 and w[-1]>=0:layer_count[l,w[l],w[-1]]+=1
     if t:
      prev=traj[t-1];a=np.array(prev['q']);b=np.array(r['q']);previous_info=divinfo(prev['layer_q'],y)
      same_late=previous_info['unanimous'] and info['unanimous'] and previous_info['late_disease']==info['late_disease']
      event={'job_id':r['job_id'],'case_id':cid,'cohort':c['cohort'],'order':order,'rotation':rotation,'round':t,'question_group':r['new_question_group'],
       'previous_top':int(winner(a)),'current_top':int(winner(b)),'switch':bool(changed(a,b)),
       'delta_gold':float(b[y]-a[y]),'js':float(js(a,b)),'delta_entropy':float(entropy(b)-entropy(a)),
       'regression':bool(winner(a)==y and winner(b)>=0 and winner(b)!=y),'recovery':bool(winner(a)>=0 and winner(a)!=y and winner(b)==y),
       'stable_late_final_flip':bool(same_late and previous_info['final_disease']==info['late_disease'] and info['divergence']),
       'wrong_support_increase_5pp':bool(winner(a)>=0 and winner(a)==winner(b) and winner(b)!=y and b[int(winner(b))]-a[int(winner(a))]>.05),
       'layer_top_changes':int(np.sum(winner(prev['layer_q'])!=winner(r['layer_q']))),
       **{f'delta_{d}':float(b[j]-a[j]) for j,d in enumerate(disease)}}
      all_events.append(event)
      if order=='base':events.append(event)
      if order=='base' and c['cohort']=='replication' and event['previous_top']>=0 and event['current_top']>=0:transition[event['previous_top'],event['current_top']]+=1
  robust=[]
  for t in range(T+1):
   rr=[d for d in case_rows if d['round']==t]
   robust.append(all(d['divergence'] for d in rr) and len({(d['late_disease'],d['final_disease']) for d in rr})==1)
  finals=[lookup[cid,'base',T,m] for m in range(6)];fq=np.array([r['q'] for r in finals]);end_disagree=len(set(winner(fq))-{ -1 })>1
  casescore={'case_id':cid,'cohort':c['cohort'],'gold':c['gold_disease'],'evidence_updates':T,
   'divergence_rate':float(np.mean([r['divergence'] for r in case_rows])),'any_divergence':any(r['divergence'] for r in case_rows),
   'robust_divergence_rate':float(np.mean(robust)),'any_robust_divergence':any(robust),
   'harmful_rate':float(np.mean([r['harmful'] for r in case_rows])),'corrective_rate':float(np.mean([r['corrective'] for r in case_rows])),
   'l27_disagree_rate':float(np.mean([r['l27_disagree'] for r in case_rows])),
   'wrong_high_support_rate':float(np.mean([r['wrong_high_support'] for r in case_rows])),
   'brier_score':float(np.mean([r['brier_score'] for r in case_rows])),
   'wrong_support_increase_any':any(e['wrong_support_increase_5pp'] for e in events),
   'switch_rate':float(np.mean([e['switch'] for e in events])),'regression_any':any(e['regression'] for e in events),
   'recovery_any':any(e['recovery'] for e in events),'stable_late_final_flip_any':any(e['stable_late_final_flip'] for e in events),
   'mean_update_js':float(np.mean([e['js'] for e in events])),'mean_delta_gold':float(np.mean([e['delta_gold'] for e in events])),
   'mapping_endpoint_changes':end_disagree,'mapping_endpoint_distinct':len(set(winner(fq))-{ -1 }),'mapping_endpoint_ties':int(np.sum(winner(fq)<0)),
   'final_mapping_mean_correct':bool(winner(fq.mean(0))==y),'final_single_mapping_correct':bool(winner(fq[0])==y),
   'final_mapping_mean_gold_support':float(fq.mean(0)[y])}
  case_metrics.append(casescore)
 csvwrite(two/'case_metrics.csv',case_metrics);csvwrite(two/'evidence_transitions.csv',all_events);csvwrite(two/'layer_divergence.csv',divs);csvwrite(three/'trajectory_metrics.csv',trajectory_metrics)
 new=[r for r in case_metrics if r['cohort']=='replication'];old=[r for r in case_metrics if r['cohort']=='pilot']
 measures=['divergence_rate','any_divergence','robust_divergence_rate','any_robust_divergence','harmful_rate','corrective_rate','l27_disagree_rate','switch_rate','regression_any','recovery_any','stable_late_final_flip_any','mapping_endpoint_changes','final_mapping_mean_correct','final_single_mapping_correct','mean_update_js','wrong_high_support_rate','brier_score','wrong_support_increase_any']
 summary2={'independent_cases':60,'pilot_cases':12,'independent_primary_prefixes':sum(2*(r['evidence_updates']+1) for r in new),'case_weighted':{k:ci([r[k] for r in new]) for k in measures},
  'new_case_counts':{k:sum(bool(r[k]) for r in new) for k in ['any_divergence','any_robust_divergence','regression_any','stable_late_final_flip_any','mapping_endpoint_changes','final_mapping_mean_correct','final_single_mapping_correct']},
  'pilot_case_counts':{k:sum(bool(r[k]) for r in old) for k in ['any_divergence','any_robust_divergence','regression_any','stable_late_final_flip_any']}}
 dump(two/'summary.json',summary2)
 groups=[]
 for d in disease:
  rr=[r for r in new if r['gold']==d];groups.append({'disease':d,'n':len(rr),'any_divergence':sum(r['any_divergence'] for r in rr),'any_robust_divergence':sum(r['any_robust_divergence'] for r in rr),
   'mean_divergence_rate':float(np.mean([r['divergence_rate'] for r in rr])),'regression_cases':sum(r['regression_any'] for r in rr),'final_mapping_mean_correct':sum(r['final_mapping_mean_correct'] for r in rr)})
 csvwrite(two/'disease_groups.csv',groups)
 fig,ax=plt.subplots(figsize=(10,4.5),constrained_layout=True);xx=np.arange(6)
 ax.bar(xx-.18,[g['any_divergence']/10 for g in groups],.36,label='至少一次层间分歧',color='#477bb5');ax.bar(xx+.18,[g['any_robust_divergence']/10 for g in groups],.36,label='两种映射重复同一转向',color='#de952d')
 ax.set_xticks(xx,ZH);ax.set(ylabel='病例比例',ylim=(0,1.05),title='独立60例：24—27层一致、28层不同的发生范围');ax.legend();savefig(fig,two/'figures/divergence_prevalence')
 norm=transition/np.maximum(transition.sum(-1,keepdims=True),1)
 fig,ax=plt.subplots(figsize=(8,6),constrained_layout=True);im=ax.imshow(norm,vmin=0,vmax=1,cmap='Blues')
 ax.set_xticks(range(6),ZH,rotation=35,ha='right');ax.set_yticks(range(6),ZH);ax.set(xlabel='新增证据后的首选',ylabel='新增证据前的首选',title='逐条证据的疾病转移（含保持原判断）')
 for a in range(6):
  for b in range(6):ax.text(b,a,f'{norm[a,b]:.0%}\n(n={int(transition[a,b])})',ha='center',va='center',color='white' if norm[a,b]>.6 else 'black',fontsize=8)
 fig.colorbar(im,ax=ax);savefig(fig,two/'figures/disease_transition_matrix');np.savetxt(two/'transition_counts.csv',transition,delimiter=',',fmt='%d')
 # Layer profiles are case-weighted; each case carries all its rounds and both core mappings.
 profiles=[]
 for l in range(28):
  per_case=[];acc=[]
  for cid in eval_ids:
   rr=[r for r in core if r['case_id']==cid and r['order']=='base'];y=disease.index(private[cid]['gold_disease'])
   per_case.append(np.mean([winner(r['layer_q'])[l]!=winner(r['q']) for r in rr]));acc.append(np.mean([winner(r['layer_q'])[l]==y for r in rr]))
  profiles.append({'layer':l+1,'disagree_final':ci(per_case),'gold_agreement':ci(acc)})
 dump(two/'layer_profiles.json',profiles)
 fig,ax=plt.subplots(figsize=(10,4),constrained_layout=True)
 for k,label,color in [('disagree_final','与最终层首选不同','#8c5baa'),('gold_agreement','与数据标签相同','#35947b')]:
  mean=np.array([p[k]['mean'] for p in profiles]);lo=[p[k]['low'] for p in profiles];hi=[p[k]['high'] for p in profiles]
  ax.plot(range(1,29),mean,label=label,color=color);ax.fill_between(range(1,29),lo,hi,color=color,alpha=.15)
 ax.set(xlabel='模型层',ylabel='病例平均比例',ylim=(0,1),title='逐层读出：疾病方向与最终输出的关系');ax.legend();savefig(fig,two/'figures/layer_profile')
 # Order endpoints: matched content, matched mapping.
 order_rows=[]
 for cid in eval_ids+pilot_ids:
  y=disease.index(private[cid]['gold_disease']);T=len(private[cid]['new_group_order'])
  qs={order:np.array([lookup[cid,order,T,m]['q'] for m in range(6)]) for order in ['base','reverse','shuffle']}
  # Canonical evidence rendering must agree across orders, independently of labels.
  canonical=[]
  for order in qs:
   job=jobs[lookup[cid,order,T,0]['job_id']];gs=sorted(job['revealed_groups'],key=lambda g:int(g['question_group_id'].split('_')[1]));canonical.append(json.dumps(gs,sort_keys=True))
  assert len(set(canonical))==1
  for order in ['reverse','shuffle']:
   a,b=qs['base'],qs[order];row={'case_id':cid,'cohort':private[cid]['cohort'],'alternative':order,
    'single_mapping_flip_fraction':float(np.mean(changed(a,b))),'any_mapping_flip':bool(np.any(changed(a,b))),
    'ambiguous_pair_fraction':float(np.mean((winner(a)<0)|(winner(b)<0))),
    'mean_total_variation':float(.5*np.abs(a-b).sum(-1).mean()),'mean_js':float(js(a,b).mean()),
    'mean_mapping_top_flip':bool(changed(a.mean(0),b.mean(0))),
    'base_mean_correct':bool(winner(a.mean(0))==y),'alternative_mean_correct':bool(winner(b.mean(0))==y),
    'delta_mean_gold':float(b.mean(0)[y]-a.mean(0)[y])}
   order_rows.append(row)
 csvwrite(three/'matched_endpoint_effects.csv',order_rows)
 summary3={}
 for order in ['reverse','shuffle']:
  rr=[r for r in order_rows if r['cohort']=='replication' and r['alternative']==order]
  summary3[order]={k:ci([r[k] for r in rr]) for k in ['single_mapping_flip_fraction','any_mapping_flip','mean_total_variation','mean_js','mean_mapping_top_flip','base_mean_correct','alternative_mean_correct','delta_mean_gold']}
 dump(three/'summary.json',summary3)
 fig,axs=plt.subplots(1,2,figsize=(12,4),constrained_layout=True)
 for ax,measure,title in [(axs[0],'mean_total_variation','相同资料，最终疾病分布变化'),(axs[1],'single_mapping_flip_fraction','六种映射中首选改变的比例')]:
  for j,order in enumerate(['reverse','shuffle']):
   vals=[r[measure] for r in order_rows if r['cohort']=='replication' and r['alternative']==order];rng=np.random.default_rng(j)
   ax.scatter(j+rng.uniform(-.16,.16,len(vals)),vals,s=18,alpha=.6,color=['#477bb5','#de952d'][j]);c=ci(vals);ax.errorbar(j,c['mean'],yerr=[[c['mean']-c['low']],[c['high']-c['mean']]],fmt='ks',capsize=5)
  ax.set_xticks([0,1],['逆序 vs 基础','另一哈希顺序 vs 基础']);ax.set(title=title,ylabel='每个点为一个病例')
 savefig(fig,three/'figures/order_endpoint_effects')
 # Evidence progress: step-function snapshots at common fractions, no claim of matched intermediate content.
 progress=[];fig,ax=plt.subplots(figsize=(9,4.5),constrained_layout=True)
 for order,color,label in [('base','#477bb5','基础顺序'),('reverse','#de952d','逆序'),('shuffle','#35947b','另一哈希顺序')]:
  values=[]
  for cid in eval_ids:
   y=disease.index(private[cid]['gold_disease']);T=len(private[cid]['new_group_order']);curve=[]
   for fraction in np.linspace(0,1,11):
    t=int(np.ceil(T*fraction));curve.append(float(np.mean([lookup[cid,order,t,m]['q'][y] for m in [0,3]])))
   values.append(curve)
  values=np.array(values);cc=[ci(values[:,i]) for i in range(11)];ax.plot(np.linspace(0,1,11),[c['mean'] for c in cc],label=label,color=color);ax.fill_between(np.linspace(0,1,11),[c['low'] for c in cc],[c['high'] for c in cc],alpha=.12,color=color)
  progress.extend({'order':order,'evidence_fraction':i/10,**c} for i,c in enumerate(cc))
 ax.set(xlabel='已揭示新增证据的比例',ylabel='数据标签疾病的支持',ylim=(0,1),title='三种顺序的判断路径（中间点的证据集合不同）');ax.legend();savefig(fig,three/'figures/evidence_progress');csvwrite(three/'evidence_progress.csv',progress)
 # Compact case atlas: all cohorts, all orders, two-mapping spread; no outcome selection.
 atlas=two/'cases';atlas.mkdir(exist_ok=True);index=[]
 if not args.skip_atlas:
  for cid in eval_ids+pilot_ids:
   c=private[cid];T=len(c['new_group_order']);y=disease.index(c['gold_disease'])
   fig,axs=plt.subplots(2,3,figsize=(15,7),constrained_layout=True,gridspec_kw={'height_ratios':[2,1]})
   for j,(order,label) in enumerate([('base','基础顺序'),('reverse','逆序'),('shuffle','另一哈希顺序')]):
    a=np.array([[lookup[cid,order,t,m]['q'] for t in range(T+1)] for m in [0,3]])
    for d in range(6):axs[0,j].plot(range(T+1),a.mean(0)[:,d],color=COLORS[d],lw=2.5 if d==y else 1,label=ZH[d]);axs[0,j].fill_between(range(T+1),a.min(0)[:,d],a.max(0)[:,d],color=COLORS[d],alpha=.08)
    axs[0,j].set(title=label,ylim=(-.02,1.02),xlabel='证据轮次',ylabel='两种映射的平均支持')
    layers=np.array([lookup[cid,order,t,0]['layer_q'] for t in range(T+1)]);w=winner(layers).T[23:]
    axs[1,j].imshow(np.where(w<0,6,w),origin='lower',aspect='auto',cmap=ListedColormap(COLORS+['#dddddd']),norm=BoundaryNorm(np.arange(-.5,7.5),7),extent=[-.5,T+.5,23.5,28.5]);axs[1,j].set(yticks=range(24,29),xlabel='证据轮次',ylabel='模型层（映射0）')
   handles,labels=axs[0,0].get_legend_handles_labels();fig.legend(handles,labels,ncol=6,loc='outside lower center',fontsize=9)
   fig.suptitle(f'{cid}｜数据标签：{ZH[y]}｜阴影为两种映射范围，不是置信区间',fontsize=12)
   savefig(fig,atlas/cid)
   appendix=[f'# {cid}', '',f'队列：{c["cohort"]}；数据标签：{ZH[y]}；新增证据组数：{T}。', '',f'![三种顺序的概率与后五层轨迹]({cid}.png)', '', '| 基础轮次 | 新证据 | 原始明确记录 |', '|---|---|---|']
   for t,gid in enumerate([c['initial_question_group']]+c['new_group_order']):
    text='；'.join(x['question_en']+' '+x['answer_en'] for x in c['explicit_evidence_groups'][gid]).replace('|','/')
    appendix.append(f'| {t} | {describe(gid,c["explicit_evidence_groups"][gid])}（{gid}） | {text} |')
   (atlas/f'{cid}.md').write_text('\n'.join(appendix)+'\n')
   index.append({'case_id':cid,'cohort':c['cohort'],'disease':ZH[y],'file':f'cases/{cid}.md'})
  csvwrite(two/'case_atlas_index.csv',index)
  lines=['# 全部病例的证据与逐层轨迹','', '| 病例 | 队列 | 数据标签 |','|---|---|---|']
  lines.extend(f'| [{r["case_id"]}]({r["file"]}) | {"独立复现" if r["cohort"]=="replication" else "原始探索"} | {r["disease"]} |' for r in index)
  (two/'CASE_ATLAS.md').write_text('\n'.join(lines)+'\n')
 # Save stage metrics before downstream mechanisms; subsequent script produces integrated prose.
 dump(run/'behavior_analysis_completion.json',{'complete':True,'all_observations':len(rows),'new_cases':60,'pilot_cases':12,'stage2_summary':summary2,'stage3_summary':summary3,'analysis_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
 print(json.dumps({'stage2':summary2,'stage3':summary3},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
