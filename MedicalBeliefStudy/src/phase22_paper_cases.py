"""Post-hoc exhaustive case synthesis; no new patients or model calls."""
import json,csv,collections,sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from phase14_analyze import ROOT,RUN,cases
from analyze_stages import csvwrite,dump,savefig,ci
from render_readable_v2 import ZH
DEST=ROOT/'results/22_paper_case_synthesis';PAPER=ROOT/'acl_paper/submission';FIG=PAPER/'figures'
LABELS={'stable':'始终命中标签','acquired':'进入标签后保持','recovered':'偏离标签后恢复','lost':'曾命中、最终偏离','fixed_wrong':'始终同一非标签病','changing_wrong':'多次变化、从未命中'}
SELECT=['0041136','0027885','0032489','0044249','0048692','0006854','0101113','0079685','0037913','0123136']
def cat(pred,g):
 hit=pred==g
 if hit.all():return 'stable'
 if not hit.any():return 'fixed_wrong' if len(set(pred))==1 else 'changing_wrong'
 if not hit[-1]:return 'lost'
 return 'recovered' if any(hit[:-1]&~hit[1:]) else 'acquired'
def esc(s):
 return str(s).replace('\\',r'\textbackslash{}').replace('&',r'\&').replace('%',r'\%').replace('_',r'\_').replace('#',r'\#').replace('é',r"\'{e}")
def main():
 DEST.mkdir(exist_ok=True);(DEST/'cases').mkdir(exist_ok=True);FIG.mkdir(exist_ok=True)
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'pdf.fonttype':42})
 train,test=cases();ds=json.loads((RUN/'manifest.json').read_text())['candidate_diseases'];scores=np.load(ROOT/'results/14_fixed_panel/prefix_readout_scores.npz');cl=scores['classes'].tolist();big=np.load(ROOT/'results/18_model_replication/prefix_readout_scores.npz');deep=sorted([c for c in test if c['deep_capture']],key=lambda c:c['case_id']);rows=[];events=[];packs={};tex=[];md=['# 全部24例的医学信念轨迹：从病例到总体规律\n','本次为已有冻结观测的事后汇总，没有新增患者或模型调用。全体病例均进入统计；正文的10个展示病例按不同轨迹与失败类型选择，不用于估计这些类型的发生率。\n']
 for c in deep:
  cid=c['case_id'];T=len(c['orders']['base']);g=ds.index(c['gold_disease']);y=cl.index(c['gold_disease']);packs[cid]={}
  for view in ['append','panel','4b']:
   run=ROOT/'runs/belief_v2_4b' if view=='4b' else RUN;v='append' if view=='4b' else view
   rr=[json.loads((run/'observations'/f'{cid}_{v}_base_t{t:02d}.json').read_text()) for t in range(T+1)]
   q=np.array([r['q_sequence'] for r in rr]);s=big[cid] if view=='4b' else scores[f'{cid}_{view}'];pred=q.argmax(1);pr=s[:,-1].argmax(1);rank=1+(s>s[:,:,y,None]).sum(-1)
   category=cat(pred,g);switch=np.r_[False,pred[1:]!=pred[:-1]];jump=np.r_[False,abs(np.diff(q,axis=0)).max(1)>=.5];hit=pred==g
   row=dict(case_id=cid,gold=c['gold_disease'],family=c['family'],view=view,updates=T,category=category,category_zh=LABELS[category],switches=int(switch.sum()),large_updates=int(jump.sum()),final_top=ds[pred[-1]],final_correct=bool(hit[-1]),final_probe=cl[pr[-1]],final_probe_correct=bool(pr[-1]==y),first_label_hit=next((t for t in range(T+1) if hit[t]),None),stable_label_from=next((t for t in range(T+1) if hit[t:].all()),None),first_probe_hit=next((t for t in range(T+1) if pr[t]==y),None))
   rows.append(row);packs[cid][view]=(q,s,rank,row)
   for t in range(T+1):
    group=c['initial_question_group'] if t==0 else c['orders']['base'][t-1];facts=c['explicit_evidence_groups'][group];fact='; '.join(f"{f['question_en']} {f['answer_en']}" for f in facts)
    events.append(dict(case_id=cid,view=view,round=t,gold=c['gold_disease'],new_evidence=fact,top=ds[pred[t]],gold_support=float(q[t,g]),probe=cl[pr[t]],gold_probe_rank=int(rank[t,-1]),switch=bool(switch[t]),large_update=bool(jump[t])))
  q,s,rank,row=packs[cid]['append'];facts=[]
  for t in range(T+1):
   e=next(e for e in events if e['case_id']==cid and e['view']=='append' and e['round']==t)
   facts.append(f"**第{t}轮新增事实：** {e['new_evidence']}\n\n| 输入/模型 | 首选疾病 | 标签病支持 | 末层读出首选 | 标签病读出排名 |\n|---|---|---:|---|---:|")
   for v,label in [('append','1.7B追加'),('panel','1.7B问卷'),('4b','4B追加')]:
    z=next(z for z in events if z['case_id']==cid and z['view']==v and z['round']==t);facts.append(f"| {label} | {ZH.get(z['top'],z['top'])} | {z['gold_support']:.5f} | {ZH.get(z['probe'],z['probe'])} | {z['gold_probe_rank']} |")
  card=f"# {cid}：{ZH.get(c['gold_disease'],c['gold_disease'])}\n\n来源标签：{c['gold_disease']}；疾病组：{c['family']}；来源DDxPlus test。\n\n1.7B追加轨迹类型：**{LABELS[row['category']]}**。首选变化{row['switches']}次，大幅更新{row['large_updates']}次。标签表示完整病例来源诊断，不是每轮唯一合理诊断。\n\n"+'\n\n'.join(facts)+f"\n\n[两输入逐层图](../../14_fixed_panel/cases/{cid}.png) · [两模型逐层图](../../18_model_replication/cases/{cid}.png)\n"
  (DEST/'cases'/f'{cid}.md').write_text(card)
  # English appendix: every source group and every trajectory, compact symbols.
  tex.append((r'\clearpage' if tex else '')+r'\subsection{'+esc(cid+' -- '+c['gold_disease'])+'}\n'+r'\label{case:'+cid+'}\n')
  tex.append('Source label: '+esc(c['gold_disease'])+'. Family: '+c['family']+'. Evidence updates: '+str(T)+'. All facts below are source-recorded; their order is acquisition order.\n')
  tex.append(r'\begin{center}\includegraphics[width=.96\linewidth]{figures/'+cid+'.pdf}'+r'\end{center}'+'\n')
  tex.append(r'{\small\begin{longtable}{>{\raggedright\arraybackslash}p{.07\textwidth}>{\raggedright\arraybackslash}p{.415\textwidth}>{\raggedright\arraybackslash}p{.415\textwidth}}\toprule Round & Newly revealed source evidence & Native top / label support / final-layer probe top \\ \midrule\endhead'+'\n')
  for t in range(T+1):
   e=next(e for e in events if e['case_id']==cid and e['view']=='append' and e['round']==t);out=[]
   for v,label in [('append','1.7B append'),('panel','1.7B panel'),('4b','4B append')]:
    z=next(z for z in events if z['case_id']==cid and z['view']==v and z['round']==t);out.append(esc(f"{label}: {z['top']} / {z['gold_support']:.4f} / {z['probe']}"))
   tex.append(str(t)+' & '+esc(e['new_evidence'])+' & '+r'\newline '.join(out)+r' \\ '+'\n')
  tex.append(r'\bottomrule\end{longtable}}'+'\n')
  fig,ax=plt.subplots(2,3,figsize=(7,4.2),layout='constrained')
  for col,(a,(v,label)) in enumerate(zip(ax[0],[('append','1.7B append'),('panel','1.7B fixed panel'),('4b','4B append')])):
   qq,ss,rk,_=packs[cid][v];pp=qq.argmax(1);a.plot(range(T+1),qq[:,g],'-o',ms=2,color='#1675a9',label='Source-label support');a.plot(range(T+1),qq.max(1),'--',color='#a55d26',label='Top-name support');a.set(title=label,ylim=(-.02,1.04),xlabel='Evidence round');a.set_xticks(range(0,T+1,max(1,T//6)));im=ax[1,col].imshow(rk.T,origin='lower',aspect='auto',extent=[-.5,T+.5,.5,rk.shape[1]+.5],vmin=1,vmax=24,cmap='viridis_r');ax[1,col].set(xlabel='Evidence round',ylabel='Layer' if col==0 else '',yticks=[1,rk.shape[1]//2,rk.shape[1]],xticks=range(0,T+1,max(1,T//6)))
  ax[0,0].set_ylabel('49-name support');ax[0,0].legend(fontsize=5.5);fig.colorbar(im,ax=list(ax[1]),label='Label rank (readout)',ticks=[1,12,24],shrink=.85);fig.suptitle(cid+' | '+c['gold_disease'],fontsize=10);savefig(fig,FIG/cid)
 csvwrite(DEST/'trajectory_categories.csv',rows);csvwrite(DEST/'all_rounds.csv',events)
 counts={v:dict(collections.Counter(r['category'] for r in rows if r['view']==v)) for v in ['append','panel','4b']}
 ep=list(csv.DictReader((ROOT/'results/14_fixed_panel/endpoint_cases.csv').open()));joint={}
 for v in ['append','panel']:
  rr=[r for r in ep if r['view']==v];cnt=collections.Counter(('both' if r['native24']==r['gold'] and r['probe28']==r['gold'] else 'probe_only' if r['probe28']==r['gold'] else 'native_only' if r['native24']==r['gold'] else 'neither') for r in rr);joint[v]=dict(cnt)
 summary={'status':'posthoc_existing_records','new_patients':0,'new_model_calls':0,'trajectory_cases':24,'diseases':len(set(c['gold_disease'] for c in deep)),'trajectory_categories':counts,'endpoint_joint24':joint,'display_cases':['ddx_test_'+i for i in SELECT]};dump(DEST/'summary.json',summary)
 md+=['## 轨迹类型：所有24例，不只展示有趣病例\n','| 类型 | 1.7B追加 | 1.7B问卷 | 4B追加 |\n|---|---:|---:|---:|']
 for k,l in LABELS.items():md.append(f"| {l} | {counts['append'].get(k,0)} | {counts['panel'].get(k,0)} | {counts['4b'].get(k,0)} |")
 md+=['\n这是来源标签命中轨迹分类，不把每次偏离解释为医学上不合理。类别互斥且覆盖全部病例。\n','## 120例内部读出与自身判断的四种组合\n','| 输入 | 两者都对 | 仅内部读出对 | 仅模型判断对 | 两者都错 |\n|---|---:|---:|---:|---:|']
 for v,l in [('append','追加'),('panel','问卷')]:md.append('| '+l+' | '+' | '.join(str(joint[v].get(k,0)) for k in ['both','probe_only','native_only','neither'])+' |')
 md+=['\n两个通道都在同24病比较；读出有额外标签监督。四格表说明它们的关系，不把读出器等同于模型自身信念。\n','## 全部病例入口\n','| 病例与完整证据 | 疾病 | 1.7B追加类型 | 1.7B问卷类型 | 4B追加类型 |\n|---|---|---|---|---|']
 for c in deep:
  cid=c['case_id'];md.append(f"| [{cid}](cases/{cid}.md) | {ZH.get(c['gold_disease'],c['gold_disease'])} | "+' | '.join(LABELS[packs[cid][v][3]['category']] for v in ['append','panel','4b'])+' |')
 md+=['\n[全部逐轮数值](all_rounds.csv) · [类别统计](trajectory_categories.csv) · [精确汇总](summary.json)\n']
 (DEST/'RESULTS.md').write_text('\n'.join(md));(PAPER/'sections/all_cases.tex').write_text('\n'.join(tex))
 # Main figure, 10 deliberately contrasting examples; all 24 in appendix.
 fig,axs=plt.subplots(5,2,figsize=(7,10),layout='constrained')
 for ax,suffix in zip(axs.flat,SELECT):
  cid='ddx_test_'+suffix;c=next(c for c in deep if c['case_id']==cid);g=ds.index(c['gold_disease'])
  for v,label,col in [('append','1.7B append','#1675a9'),('panel','1.7B panel','#d2782b'),('4b','4B append','#4b966c')]:
   q,_,_,r=packs[cid][v];ax.plot(range(len(q)),q[:,g],'-o',ms=2,color=col,label=label)
  ax.set(title=c['gold_disease'].replace(' syndrome','\nsyndrome').replace(' reactions','\nreactions'),ylim=(-.03,1.03),xlabel='Evidence round');ax.text(.02,.04,suffix,transform=ax.transAxes,fontsize=7)
 axs[0,0].legend(fontsize=6);axs[0,0].set_ylabel('Source-label support');axs[1,0].set_ylabel('Source-label support');savefig(fig,FIG/'case_gallery')
 # English main result/depth and alignment.
 a=json.loads((ROOT/'results/14_fixed_panel/summary.json').read_text());b=json.loads((ROOT/'results/18_model_replication/summary.json').read_text());al=json.loads((ROOT/'results/16_update_mechanism/natural_alignment_summary.json').read_text());bl=json.loads((ROOT/'results/18_model_replication/natural_alignment_summary.json').read_text())
 fig,axs=plt.subplots(1,2,figsize=(7,2.7),layout='constrained')
 for v,label,col in [('append','Append','#1675a9'),('panel','Fixed panel','#d2782b')]:
  z=a['endpoints'][v];axs[0].plot(np.arange(1,29),z['layer_accuracy'],label=label+' readout',color=col);axs[0].axhline(z['native24']['mean'],color=col,ls='--',label=label+' native')
  rr=[al[v][str(l)]['spearman'] for l in range(1,29)];axs[1].plot(range(1,29),[r['mean'] for r in rr],label=label,color=col);axs[1].fill_between(range(1,29),[r['low'] for r in rr],[r['high'] for r in rr],color=col,alpha=.15)
 axs[0].set(xlabel='Layer (1.7B)',ylabel='24-class accuracy',ylim=(0,1));axs[0].legend(fontsize=6);axs[1].set(xlabel='Layer (1.7B)',ylabel='Mean within-case Spearman',ylim=(-.6,1));axs[1].legend(fontsize=7);savefig(fig,FIG/'depth_alignment')
 causal=json.loads((ROOT/'results/15_disease_directions/summary.json').read_text());fig,ax=plt.subplots(figsize=(7,2.8),layout='constrained');rr=causal['contrasts'];labs=[f"{r['view']} L{r['layer']}\n{r['site']}" for r in rr];z=[r['target_minus_random_logodds'] for r in rr];xx=np.arange(len(rr));ax.bar(xx,[r['mean'] for r in z],yerr=[[r['mean']-r['low'] for r in z],[r['high']-r['mean'] for r in z]],color=['#1675a9']*4+['#d2782b']*4,capsize=3);ax.set(xticks=xx,xticklabels=labs,ylabel='Target minus random\nlog-score-ratio change');ax.tick_params(axis='x',labelsize=7);savefig(fig,FIG/'causal')
 print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
