"""New-patient endpoints, all trajectories, layers and evidence attention."""
import argparse,collections,csv,json
import numpy as np
import matplotlib.pyplot as plt
from belief_v3_analysis import *
from belief_v3_labels import describe

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--model',default='1.7b',choices=['1.7b','4b']);ap.add_argument('--skip-atlas',action='store_true');args=ap.parse_args();big=args.model=='4b'
 run=ROOT/'runs'/('belief_v3_4b' if big else 'belief_v3');dest=ROOT/'results'/('28_new_4b_replication' if big else '23_new_patients');assert (run/'completion.json').exists();setup()
 for subdir in ['figures','cases']:(dest/subdir).mkdir(parents=True,exist_ok=True)
 cases=rows(ROOT/'data/belief_v3/cases.private.jsonl');jobs=rows(ROOT/'data/belief_v3/jobs.jsonl');ds=jobs[0]['candidate_diseases'];headfile=ROOT/'results'/('18_model_replication/training_heads.npz' if big else '14_fixed_panel/training_heads.npz');head=np.load(headfile);cl=head['classes'].tolist();sub=[ds.index(d) for d in cl];layers=36 if big else 28;focus=[layers//2,3*layers//4,layers];yy=np.array([cl.index(c['gold_disease']) for c in cases]);gg=np.array([ds.index(c['gold_disease']) for c in cases]);views=['append'] if big else ['append','panel'];endrows=[];endpoints={};endpack={}
 for view in views:
  rec=[load_record(run,c,view=view) for c in cases];scores=np.array([readout(run,r,head,view,args.model) for r in rec]);q=np.array([r['q_sequence'] for r in rec]);pred=scores.argmax(-1);n=q.argmax(-1);n24=q[:,sub].argmax(-1);joint=collections.Counter((bool(n24[i]==yy[i]),bool(pred[i,-1]==yy[i])) for i in range(len(cases)))
  endpoints[view]=dict(patients=len(cases),native49=summary(n==gg),native24=summary(n24==yy),layer_accuracy=(pred==yy[:,None]).mean(0),layers={str(l):summary(pred[:,l-1]==yy) for l in focus},probe_minus_native24=summary((pred[:,-1]==yy).astype(float)-(n24==yy)),joint24={str(k):v for k,v in joint.items()},checks=measurement_checks(rec,cases,ds));endpack['q_'+view]=q;endpack['probe_'+view]=pred
  for i,c in enumerate(cases):endrows.append(dict(case_id=c['case_id'],family=c['family'],gold=c['gold_disease'],view=view,native49=ds[n[i]],native24=cl[n24[i]],probe_last=cl[pred[i,-1]],**{f'probe{l}':cl[pred[i,l-1]] for l in focus},gold_support=q[i,gg[i]],greedy_disease=rec[i]['generated_disease'],canonical_mass=rec[i]['sequence_probability_mass']))
 deep=[c for c in cases if c['mechanism_capture' if big else 'deep_capture']];prefix=[];events=[];metrics=[];layerrows=[];attrows=[];scorespack={};caseatt=[];casestate=[];casecorr=[];stageflows=[];families=[]
 for k,c in enumerate(deep):
  cid=c['case_id'];T=len(c['orders']['base']);gi=ds.index(c['gold_disease']);yi=cl.index(c['gold_disease']);rec=[load_record(run,c,t) for t in range(T+1)];q=np.array([r['q_sequence'] for r in rec]);lp=np.array([r['log_probability'] for r in rec]);s=np.array([readout(run,r,head,model=args.model,all_stages=True) for r in rec]);S=s[:,:,4];P=S.argmax(-1);n=q.argmax(-1);n24=q[:,sub].argmax(-1);rank=1+(S>S[:,:,yi,None]).sum(-1);scorespack[cid]=S.astype(np.float32);cm=dict(case_id=cid,family=c['family'],gold=c['gold_disease'],**path_metrics(q,gi));cm.update(native24_prefix_hit=float(np.mean(n24==yi)),probe_last_prefix_hit=float(np.mean(P[:,-1]==yi)),probe_last_stable_hit=stable(P[:,-1]==yi));metrics.append(cm)
  ns=stable(n24==yi);ps=stable(P[:,-1]==yi);cm.update(native24_stable_hit=ns,native24_switches=int(np.sum(n24[1:]!=n24[:-1])),probe_last_switches=int(np.sum(P[1:,-1]!=P[:-1,-1])),native24_switch_rate=float(np.mean(n24[1:]!=n24[:-1])),probe_last_switch_rate=float(np.mean(P[1:,-1]!=P[:-1,-1])),internal_gold_native_other_fraction=float(np.mean((P[:,-1]==yi)&(n24!=yi))),stable_internal_lead_fraction=(ns-ps)/T if ns is not None and ps is not None else None)
  raw=[];att=[];newatt=[];numatt=[];candatt=[]
  for t,r in enumerate(rec):
   with np.load(run/r['state_file']) as a:
    raw.append(a['residual_stages'][:,4].astype(float));A=a['attention_by_group'].astype(float);tg=a['token_groups'];G=r['group_labels'];candatt.append(A[:,:,1]);att.append(A[:,:,3:].sum(-1));newatt.append(A[:,:,-1]);counts=np.bincount(tg,minlength=len(G));numatt.append(A[:,:,-1]/max(counts[-1]/len(tg),1e-12))
   pr=dict(case_id=cid,round=t,evidence_group=([c['initial_question_group']]+c['orders']['base'])[t],native49=ds[n[t]],native24=cl[n24[t]],gold_support=q[t,gi],gold_log_probability=lp[t,gi],gold_rank_native=int(1+(q[t]>q[t,gi]).sum()),entropy=float(-np.sum(q[t]*np.log(np.maximum(q[t],1e-30)))/np.log(len(ds))),**{f'probe{l}':cl[P[t,l-1]] for l in focus},**{f'gold_rank{l}':int(rank[t,l-1]) for l in focus});prefix.append(pr)
  raw=np.array(raw);change=np.linalg.norm(np.diff(raw,axis=0),axis=-1)/np.maximum(np.linalg.norm(raw[:-1],axis=-1),1e-12);casestate.append(change.mean(0));caseatt.append(np.array(newatt)[1:].mean(0));corr=[];dmargin=[];dout=[];attflow=[];mlpflow=[]
  for t in range(1,T+1):
   comp=max((x for x in range(24) if x!=yi),key=lambda x:lp[t-1,sub[x]]);out=(lp[t,gi]-lp[t,sub[comp]])-(lp[t-1,gi]-lp[t-1,sub[comp]]);dm=(S[t,:,yi]-S[t,:,comp])-(S[t-1,:,yi]-S[t-1,:,comp]);dmargin.append(dm);dout.append(out);gid=c['orders']['base'][t-1]
   af=(s[t,:,2,yi]-s[t,:,2,comp])-(s[t,:,0,yi]-s[t,:,0,comp]);mf=(s[t,:,4,yi]-s[t,:,4,comp])-(s[t,:,2,yi]-s[t,:,2,comp]);pa=(s[t-1,:,2,yi]-s[t-1,:,2,comp])-(s[t-1,:,0,yi]-s[t-1,:,0,comp]);pm=(s[t-1,:,4,yi]-s[t-1,:,4,comp])-(s[t-1,:,2,yi]-s[t-1,:,2,comp]);inherited=(s[t,:,0,yi]-s[t,:,0,comp])-(s[t-1,:,0,yi]-s[t-1,:,0,comp]);assert np.max(abs(dm-inherited-(af-pa)-(mf-pm)))<1e-10;attflow.append(abs(af-pa));mlpflow.append(abs(mf-pm))
   events.append(dict(case_id=cid,round=t,family=c['family'],gold=c['gold_disease'],evidence_group=gid,evidence_type=evidence_type(c['explicit_evidence_groups'][gid]),previous_top=ds[n[t-1]],current_top=ds[n[t]],switch=bool(n[t]!=n[t-1]),big=bool(np.max(abs(q[t]-q[t-1]))>=.5),max_support_change=float(np.max(abs(q[t]-q[t-1]))),total_variation=float(.5*abs(q[t]-q[t-1]).sum()),js=float(js(q[t],q[t-1])),delta_gold=float(q[t,gi]-q[t-1,gi]),competitor=cl[comp],native_pair_update=out,probe_last_pair_update=dm[-1],probe_last_stable=bool(P[t,-1]==P[t-1,-1])))
   for l in range(layers):layerrows.append(dict(case_id=cid,round=t,layer=l+1,relative_state_change=change[t-1,l],disease_margin_update=dm[l],native_pair_update=out,inherited_readout_update=inherited[l],attention_readout_update=af[l]-pa[l],mlp_readout_update=mf[l]-pm[l],attention_readout_step=af[l],mlp_readout_step=mf[l],new_evidence_attention=np.mean(newatt[t][l]),new_evidence_attention_per_token_relative=np.mean(numatt[t][l]),candidate_attention=np.mean(candatt[t][l]),all_evidence_attention=np.mean(att[t][l])))
  dm=np.array(dmargin)
  for l in range(layers):corr.append(rho(dm[:,l],dout))
  casecorr.append(corr);stageflows.append([np.mean(attflow,axis=0),np.mean(mlpflow,axis=0)]);cm['update_alignment_last']=corr[-1];fc=max((k for k in range(24) if k!=yi),key=lambda k:lp[-1,sub[k]]);cm['fixed_pair_competitor']=cl[fc];cm['fixed_pair_update_alignment_last']=rho(np.diff(S[:,-1,yi]-S[:,-1,fc]),np.diff(lp[:,gi]-lp[:,sub[fc]]));sw=n24[1:]!=n24[:-1];cm['probe_last_stable_when_native24_switches']=float(np.mean((P[1:,-1]==P[:-1,-1])[sw])) if sw.any() else None
  for l in range(layers):attrows.append(dict(case_id=cid,layer=l+1,new_evidence_attention=np.mean(np.array(newatt)[1:,l]),all_evidence_attention=np.mean(np.array(att)[1:,l]),candidates_attention=np.mean(np.array(candatt)[1:,l]),update_alignment=corr[l],relative_state_change=change[:,l].mean()))
  if not args.skip_atlas:
   selected=sorted(set(n.tolist()+[gi]),key=lambda d:-q[:,d].max())[:6]
   if gi not in selected:selected[-1]=gi
   fig,axs=plt.subplots(3,1,figsize=(10,10),layout='constrained',height_ratios=[1.2,1.3,1])
   for d in selected:axs[0].plot(range(T+1),q[:,d],marker='o',ms=3,lw=2 if d==gi else 1.2,color='black' if d==gi else None,label=ZH.get(ds[d],ds[d])+('【来源诊断】' if d==gi else ''))
   axs[0].set(ylabel='原模型病名相对支持',ylim=(-.02,1.02),xticks=range(T+1));axs[0].legend(fontsize=8,ncol=2)
   im=axs[1].imshow(rank.T,origin='lower',aspect='auto',extent=[-.5,T+.5,.5,layers+.5],vmin=1,vmax=24,cmap='viridis_r');axs[1].set(ylabel='模型层数',title='内部状态读出：来源诊断排第几（黄色靠前）',xticks=range(T+1));fig.colorbar(im,ax=axs[1],label='排名，不是疾病概率',ticks=[1,6,12,18,24])
   im2=axs[2].imshow(change.T,origin='lower',aspect='auto',extent=[.5,T+.5,.5,layers+.5],cmap='magma');axs[2].set(ylabel='模型层数',xlabel='证据轮次（0已有初始证据）',title='加入这条证据后：锚点状态改变多少',xticks=range(1,T+1));fig.colorbar(im2,ax=axs[2],label='状态差范数 / 前轮状态范数');fig.suptitle(cid+' | '+ZH.get(c['gold_disease'],c['gold_disease']));savefig(fig,dest/'cases'/cid)
   tab='\n'.join('| '+str(t)+' | '+ZH.get(ds[n[t]],ds[n[t]])+' | '+f'{q[t,gi]:.4f}'+' | '+' | '.join(ZH.get(cl[P[t,l-1]],cl[P[t,l-1]]) for l in focus)+' |' for t in range(T+1))
   ev='\n\n'.join('**第'+str(t)+'轮** '+gid+'\n\n'+describe(c['explicit_evidence_groups'][gid],True)+'\n\n'+'\n'.join('- '+v['question_en']+' **'+v['answer_en']+'**' for v in c['explicit_evidence_groups'][gid]) for t,gid in enumerate([c['initial_question_group']]+c['orders']['base']))
   (dest/'cases'/f'{cid}.md').write_text(f'# {cid}：{ZH.get(c["gold_disease"],c["gold_disease"])}\n\nDDxPlus test 原始第{c["source_row_zero_based"]}行（零起始）。轨迹类型：{PATTERNS[cm["pattern"]]}。来源诊断适用于完整病例；中间轮没有逐轮医学标准答案。\n\n![证据—输出—内部轨迹]({cid}.png)\n\n| 轮 | 原模型首选（49病） | 来源诊断相对支持 | '+' | '.join(f'第{l}层读出（24病）' for l in focus)+' |\n|---|---|---:|'+'---|'*len(focus)+'\n'+tab+'\n\n## 原始证据\n\n'+ev+'\n')
  if (k+1)%12==0:print('Analyzed trajectories',k+1,len(deep),flush=True)
 counts=collections.Counter(c['pattern'] for c in metrics);summaryobj=dict(model=args.model,patients=len(cases),classes=24,heldout_readout_training_patients=120,head_sha256=sha(headfile),endpoints=endpoints,deep=dict(patients=len(deep),updates=sum(c['updates'] for c in metrics),switch_events=sum(c['switches'] for c in metrics),native24_switch_events=sum(c['native24_switches'] for c in metrics),probe_last_switch_events=sum(c['probe_last_switches'] for c in metrics),big_events=sum(c['big_updates'] for c in metrics),patterns=dict(counts),**{k:summary([r[k] for r in metrics]) for k in ['any_switch','any_big','switch_rate','big_rate','regression','max_step_share','gold_decrease_rate','native_prefix_hit','native24_prefix_hit','probe_last_prefix_hit','update_alignment_last','probe_last_stable_when_native24_switches','internal_gold_native_other_fraction','stable_internal_lead_fraction','native24_switch_rate','probe_last_switch_rate']}),layer_update_alignment=[summary([v[l] for v in casecorr]) for l in range(layers)],relative_state_change=np.mean(casestate,axis=0),api_cost_usd=0)
 summaryobj['deep']['fixed_pair_update_alignment_last']=summary([r['fixed_pair_update_alignment_last'] for r in metrics]);summaryobj['mean_abs_component_update']=dict(attention=np.mean(stageflows,axis=0)[0],mlp=np.mean(stageflows,axis=0)[1])
 if not big:summaryobj['presentation_switch']=summary(endpack['q_append'].argmax(-1)!=endpack['q_panel'].argmax(-1))
 else:
  old=np.load(ROOT/'results/23_new_patients/endpoint_predictions.npz');summaryobj['paired_4b_minus_1p7b_native49']=summary((endpack['q_append'].argmax(-1)==gg).astype(float)-(old['q_append'].argmax(-1)==gg));summaryobj['paired_4b_minus_1p7b_probe_final']=summary((endpack['probe_append'][:,-1]==yy).astype(float)-(old['probe_append'][:,-1]==yy));oldcm={r['case_id']:r for r in csv.DictReader((ROOT/'results/23_new_patients/case_metrics.csv').open())};summaryobj['paired_trajectory_4b_minus_1p7b']={key:summary([r[key]-float(oldcm[r['case_id']][key]) for r in metrics]) for key in ['switch_rate','native24_switch_rate','probe_last_switch_rate','big_rate','native24_prefix_hit','probe_last_prefix_hit','internal_gold_native_other_fraction']}
 for f in sorted({c['family'] for c in cases}):
  for view in views:
   ee=[r for r in endrows if r['family']==f and r['view']==view];families.append(dict(family=f,view=view,patients=len(ee),native49_correct=sum(r['native49']==r['gold'] for r in ee),native24_correct=sum(r['native24']==r['gold'] for r in ee),probe_last_correct=sum(r['probe_last']==r['gold'] for r in ee)))
 for name,data in [('endpoint_cases',endrows),('prefix_trajectories',prefix),('evidence_updates',events),('case_metrics',metrics),('layer_updates',layerrows),('attention_by_case_layer',attrows),('family_endpoints',families)]:csvwrite(dest/(name+'.csv'),data)
 np.savez_compressed(dest/'prefix_readout_scores.npz',classes=np.array(cl),**scorespack);np.savez_compressed(dest/'endpoint_predictions.npz',case_ids=np.array([c['case_id'] for c in cases]),gold24=yy,gold49=gg,**endpack);dump(dest/'summary.json',summaryobj)
 fig,axs=plt.subplots(1,2,figsize=(12,4),layout='constrained')
 for view in views:axs[0].plot(range(1,layers+1),endpoints[view]['layer_accuracy'],label=view+' 内部读出');axs[0].axhline(endpoints[view]['native24']['mean'],ls='--',label=view+' 原模型24病')
 axs[0].set(xlabel='模型层数',ylabel='240例终点命中率',ylim=(0,1));axs[0].legend(fontsize=8);names=list(PATTERNS);axs[1].barh([PATTERNS[x] for x in names],[counts[x] for x in names],color='#437aa3');axs[1].set(xlabel=f'完整轨迹病例数（共{len(deep)}例）');savefig(fig,dest/'figures/formation_and_readout')
 fig,axs=plt.subplots(1,3,figsize=(15,4),layout='constrained');axs[0].plot(range(1,layers+1),summaryobj['relative_state_change']);axs[0].set(xlabel='层',ylabel='相对状态变化',title='证据在哪些层改变状态？');rhos=summaryobj['layer_update_alignment'];axs[1].plot(range(1,layers+1),[r['mean'] for r in rhos]);axs[1].fill_between(range(1,layers+1),[r['low'] for r in rhos],[r['high'] for r in rhos],alpha=.2);axs[1].set(xlabel='层',ylabel='病例内更新相关',ylim=(-1,1),title='内部疾病分差与最终输出同向吗？');im=axs[2].imshow(np.mean(caseatt,axis=0),origin='lower',aspect='auto',cmap='magma');axs[2].set(xlabel='注意力头（0起）',ylabel='层（0起）',title='诊断锚点对最新证据的注意力');fig.colorbar(im,ax=axs[2]);savefig(fig,dest/'figures/internal_update')
 fig,ax=plt.subplots(figsize=(9,4),layout='constrained')
 for key,label in [('attention','注意力步骤'),('mlp','前馈网络步骤')]:ax.plot(range(1,layers+1),summaryobj['mean_abs_component_update'][key],label=label)
 ax.set(xlabel='模型层',ylabel='疾病对读出分差：新增证据引起的步骤变化绝对值',title='新证据带来的变化，在哪些计算步骤更大？');ax.legend();savefig(fig,dest/'figures/component_updates')
 tab='\n'.join(f'| {v} | {fmt(e["native49"])} | {fmt(e["native24"])} | {fmt(e["layers"][str(layers)])} |' for v,e in endpoints.items());deepinfo=summaryobj['deep'];tax='；'.join(PATTERNS[k]+f' {counts[k]}例' for k in PATTERNS)
 (dest/'RESULTS.md').write_text(f'''# 新队列：{args.model}模型的医学判断怎样形成和改变

新增240个DDxPlus test患者，24病×10例，与既有病例没有相同事实集合。旧120例训练的读出器完全冻结。{len(deep)}例预先选定，逐条记录{deepinfo['updates']}次证据加入；覆盖全部24种病。此处所有统计使用新患者，不合并旧探索病例。

| 完整病例呈现 | 原模型49病 | 原模型限制24病 | 最后一层内部24病读出 |
|---|---|---|---|
{tab}

这里“内部读出”是从冻结模型的状态中训练一个外部小分类器；原模型是逐个比较完整候选病名的生成分数。统一24病的两列用于公平比较候选范围。读出命中意味着状态含有可识别的标签信息，不能直接等同于模型自己在内部作出诊断。

![形成及读出](figures/formation_and_readout.png)

## 信念的变化不是只有一种

{tax}。

共{deepinfo['updates']}次证据更新，首选改变{deepinfo['switch_events']}次，任意病名支持单次改变至少50个百分点{deepinfo['big_events']}次。至少一次首选改变的病例比例为{fmt(deepinfo['any_switch'])}；曾命中来源诊断又离开的病例比例为{fmt(deepinfo['regression'])}。这些是相对完整病例来源诊断的路径描述，并没有把不完整证据下的判断一概判错。

## 往模型里面看

最后一层疾病分差更新与原输出更新的病例内相关为{fmt(deepinfo['update_alignment_last'],False)}。图中左侧测量状态移动幅度，中间比较疾病方向与输出的同步性，右侧显示锚点向最新证据分配的注意力。全部先在患者内汇总，再跨患者平均。注意力高低本身不证明因果，因果结果单独报告。

![内部更新](figures/internal_update.png)

![注意力与前馈步骤](figures/component_updates.png)

进一步将同一层的疾病分差更新分成：从前一层继承的变化、注意力步骤新增的变化、前馈网络步骤新增的变化。三者在固定读出坐标中严格相加，完整逐轮数值见layer_updates.csv。图展示各步骤变化的平均绝对值，用于定位计算位置；因果作用由独立干预判断。

模型权重在推理中没有改变；改变的是每轮输入引起的内部激活、注意力分配和病名输出分数。逐层读出排名不作为各层自行报告的疾病概率。分数归一化在固定候选字符串内进行，不是患者患病概率。

[全部逐例图谱](CASE_ATLAS.md) · [逐轮变化](prefix_trajectories.csv) · [每条证据](evidence_updates.csv) · [每层更新](layer_updates.csv) · [按疾病组汇总](family_endpoints.csv) · [精确结果](summary.json)
''')
 (dest/'CASE_ATLAS.md').write_text(f'# 全部{len(deep)}例逐条证据图谱\n\n病例在观察模型结果之前选定；全部呈现，不按是否惊人筛选。\n\n'+'\n'.join(f'- [{c["case_id"]} · {ZH.get(c["gold_disease"],c["gold_disease"])} · {PATTERNS[m["pattern"]]}](cases/{c["case_id"]}.md)' for c,m in zip(deep,metrics))+'\n');print(json.dumps(clean(summaryobj),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
