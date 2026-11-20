"""All 47 held-out evidence trajectories for four frozen structural variants."""
import csv,gzip,textwrap
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from structural_v1_analysis import *
from analyze_stages import setup,savefig
OUT=ROOT/'results/45_structural_synthesis'
def main():
    src=RUN/'trajectories';done=read(src/'completion.json');assert done['complete'];setup()
    for d in ['figures','cases']:(OUT/d).mkdir(parents=True,exist_ok=True)
    spec=read(src/'manifest.json');cs={c['case_id']:c for c in map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines())};names=[r['name'] for r in spec['candidates']];sel=read(RUN/'selected.json');gate=next(v for v in sel['candidates'] if v['name']==sel['repair_candidate'])['anchor_drop_heads'];selected_heads=[(int(l),h) for l,hh in gate.items() for h in hh];rows=[];headrows=[];case_index=[];candidate_rows=[]
    colors=['#317f9e','#c99738','#61a17e','#a3649c'];diseasecolors=['#d55e00','#0072b2','#009e73','#cc79a7'];configlabels={names[0]:'完整模型',names[1]:'删除所选MLP',names[2]:'小型线性替换',names[3]:'诊断位置头干预'}
    for ci,cid in enumerate(spec['cases']):
        c=cs[cid];T=len(c['sentences']);g=c['gold_index'];cache={}
        for name in names:
            z=read(src/(cid+'_'+name+'.json'));conddata={}
            for cond in ['neutral','wrong']:
                rrs=[[next(r for r in z['conditions'] if r['condition']==cond and r['rotation']==rot and r['round']==t) for t in range(1,T+1)] for rot in [0,2]]
                q=np.array([[r['layer_q'] for r in rr] for rr in rrs]);mass=np.array([[r['layer_mass'] for r in rr] for rr in rrs]);conddata[cond]=dict(q=q,mass=mass)
                if name=='baseline':
                    att=np.array([[r['attention_by_group'] for r in rr] for rr in rrs])
                    for l,h in selected_heads:
                        for t in range(T):headrows.append(dict(case_id=cid,condition=cond,round=t+1,total_rounds=T,layer=l,head=h,prior_attention=float(att[:,t,l-1,h-1,3].mean()),facts_attention=float(att[:,t,l-1,h-1,1:3].sum(-1).mean())))
                for rotidx,rot in enumerate([0,2]):
                    for t in range(T):
                        for k,disease in enumerate(c['candidates']):candidate_rows.append(dict(case_id=cid,dataset=c['dataset'],candidate=name,condition=cond,rotation=rot,round=t+1,disease=disease,relative_support=float(q[rotidx,t,-1,k])))
            cache[name]=conddata
        for name in names:
            for cond in ['neutral','wrong']:
                q=cache[name][cond]['q'][:,:,-1];base=cache['baseline'][cond]['q'][:,:,-1];pred=q.argmax(-1);bp=base.argmax(-1)
                rows.append(dict(case_id=cid,dataset=c['dataset'],candidate=name,condition=cond,rounds=T,all_round_fidelity=float(np.mean(pred==bp)),final_fidelity=float(np.mean(pred[:,-1]==bp[:,-1])),final_accuracy=float(np.mean(pred[:,-1]==g)),final_accuracy_change=float(np.mean(pred[:,-1]==g)-np.mean(bp[:,-1]==g)),switches=float(np.mean(np.sum(pred[:,1:]!=pred[:,:-1],axis=1))),source_then_leave=float(np.mean(np.any((pred[:,:-1]==g)&(pred[:,1:]!=g),axis=1))),source_support_change=float(np.mean(q[:,:,g]-base[:,:,g]))))
        # Source support and full candidate trajectory, all selected structures.
        fig,axs=plt.subplots(2,2,figsize=(13,8),layout='constrained');xx=np.arange(1,T+1)
        for i,cond in enumerate(['neutral','wrong']):
            for j,name in enumerate(names):axs[i,0].plot(xx,cache[name][cond]['q'][:,:,-1,g].mean(0),'-o',ms=3,c=colors[j],label=configlabels[name])
            axs[i,0].set(title=('中性历史' if cond=='neutral' else '错误历史')+'：来源答案支持',ylim=(-.02,1.02),xlabel='累计原文组',ylabel='候选内支持');axs[i,0].legend(fontsize=8)
            predictions=np.array([cache[name][cond]['q'][:,:,-1].argmax(-1) for name in names]);mat=predictions[:,0].copy();mat[predictions[:,0]!=predictions[:,1]]=4
            axs[i,1].imshow(mat,aspect='auto',cmap=ListedColormap(diseasecolors+['#8a8c8e']),vmin=-.5,vmax=4.5,extent=(.5,T+.5,3.5,-.5));axs[i,1].set(title='四种结构的首选；灰色表示两映射不一致',yticks=range(4),yticklabels=[configlabels[n] for n in names],xticks=xx,xlabel='累计原文组；数字为候选编号，斜线保留两种判断')
            for j in range(4):
                for t in range(T):
                    label='/'.join(str(k+1) for k in sorted(set(predictions[j,:,t].tolist())))
                    axs[i,1].text(t+1,j,label,ha='center',va='center',color='white',fontsize=9 if T<=10 else 7)
        fig.suptitle(cid+'\n'+textwrap.fill('来源答案：'+c['gold_disease']+'｜旧诊断：'+c['wrong_disease'],95),fontsize=11);savefig(fig,OUT/'cases'/cid)
        fig,axs=plt.subplots(2,4,figsize=(16,8),layout='constrained')
        for i,cond in enumerate(['neutral','wrong']):
            for j,name in enumerate(names):
                q=cache[name][cond]['q'];w=q.mean(0).argmax(-1).T;ag=q[0].argmax(-1)==q[1].argmax(-1);w[~ag.T]=4;w[cache[name][cond]['mass'].mean(0).T<.5]=5
                axs[i,j].imshow(w,aspect='auto',origin='lower',cmap=ListedColormap(diseasecolors+['#8a8c8e','#e5e7e9']),vmin=-.5,vmax=5.5,extent=(.5,T+.5,.5,28.5));axs[i,j].set(title=configlabels[name]+(' · 中性' if cond=='neutral' else ' · 错误历史'),xlabel='累计原文组',ylabel='层',yticks=[1,7,14,21,28])
        legend=[Patch(color=col,label=str(k+1)+'='+textwrap.shorten(d,width=45,placeholder='…')) for k,(col,d) in enumerate(zip(diseasecolors,c['candidates']))]+[Patch(color='#8a8c8e',label='两映射首选不同'),Patch(color='#e5e7e9',label='平均代码总概率<0.5')]
        fig.legend(handles=legend,loc='outside lower center',ncol=3,fontsize=8);fig.suptitle(cid+'\n最终输出头对每层的投影；四种结构均保留28层',fontsize=11);savefig(fig,OUT/'cases'/(cid+'_layers'))
        lines=[f'# {cid}\n\n来源答案：**{c["gold_disease"]}**；固定错误历史：**{c["wrong_disease"]}**。\n\n候选：'+'；'.join(f'{k+1}={d}' for k,d in enumerate(c['candidates']))+'。\n\n',f'![逐证据轨迹]({cid}.png)\n\n![每层与每轮]({cid}_layers.png)\n\n曲线颜色代表四种结构，方格颜色及数字代表四个候选。曲线先平均两套代码支持；右侧方格与下表在两套代码不一致时同时列出两个候选编号，方格标灰。统计仍先各映射判定后在病例内平均。逐层图是最终输出头投影；浅灰表示代码总概率不足0.5，深灰表示两映射首选不同，未将这些格子解释为确定的疾病判断。\n\n']
        for cond in ['neutral','wrong']:
            lines.append('## '+('中性历史' if cond=='neutral' else '错误历史')+'\n\n| 轮 | '+' | '.join(configlabels[n] for n in names)+' |\n|---:|---|---|---|---|\n')
            for t in range(T):
                values=[]
                for n in names:values.append(' / '.join(str(k+1) for k in sorted(set(cache[n][cond]['q'][:,t,-1].argmax(-1).tolist()))))
                lines.append(f'| {t+1} | '+' | '.join(values)+' |\n')
        lines.append('\n## 新增原文\n\n')
        for t,s in enumerate(c['sentences'],1):lines.append(f'{t}. '+s.replace('\n','; ')+'\n')
        (OUT/'cases'/(cid+'.md')).write_text(''.join(lines));case_index.append(dict(case_id=cid,dataset=c['dataset'],gold=c['gold_disease'],rounds=T))
        if ci==0 or (ci+1)%10==0:print(json.dumps(dict(atlas=ci+1,total=47)),flush=True)
    csvwrite(OUT/'patient_trajectories.csv',rows);csvwrite(OUT/'selected_head_attention_by_round.csv',headrows)
    with gzip.open(OUT/'all_candidate_trajectories.csv.gz','wt',newline='') as f:w=csv.DictWriter(f,fieldnames=list(candidate_rows[0]));w.writeheader();w.writerows(candidate_rows)
    summary=[]
    for name in names:
        for cond in ['neutral','wrong']:
            rr=[r for r in rows if r['candidate']==name and r['condition']==cond];summary.append(dict(candidate=name,condition=cond,**{f:stat([r[f] for r in rr]) for f in ['all_round_fidelity','final_fidelity','final_accuracy','final_accuracy_change','switches','source_then_leave','source_support_change']}))
    write(OUT/'trajectory_summary.json',dict(cases=47,prefixes=done['prefixes'],configurations=names,selected_heads=selected_heads,summaries=summary))
    lines=['# 全部47例：结构改变后，医学判断怎样随证据变化\n\n每例展示四个冻结结构、两种历史、两套答案映射、每轮和28层投影。图谱覆盖全部预定确认病例，未按干预是否成功选择。\n\n| 来源 | 病例 | 来源答案 | 原文组数 |\n|---|---|---|---:|\n']
    for r in case_index:lines.append(f'| {r["dataset"]} | [{r["case_id"]}](cases/{r["case_id"]}.md) | {r["gold"]} | {r["rounds"]} |\n')
    (OUT/'CASE_ATLAS.md').write_text(''.join(lines))
    print(json.dumps(dict(cases=47,prefixes=done['prefixes'],output=str(OUT))))
if __name__=='__main__':main()
