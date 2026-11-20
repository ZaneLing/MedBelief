"""Endpoint fidelity versus evidence-path preservation, all held-out cases."""
import csv
import matplotlib.pyplot as plt
from structural_v1_analysis import *
from analyze_stages import setup,savefig
OUT=ROOT/'results/45_structural_synthesis'
LABELS={'baseline':'完整模型','drop_mlp_2':'删除MLP 25、26','linear_mlp_2_r16':'MLP 25、26 → 秩16','anchor_heads_8':'诊断位置干预8个头'}

def main():
    assert read(RUN/'trajectories/completion.json')['complete'];setup();spec=read(RUN/'trajectories/manifest.json');names=[r['name'] for r in spec['candidates']]
    cases={c['case_id']:c for c in map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines())};rows=[];layers=[];histories=[]
    for cid in spec['cases']:
        c=cases[cid];T=len(c['sentences']);data={}
        for name in names:
            rr=read(RUN/'trajectories'/(cid+'_'+name+'.json'))['conditions'];data[name]={}
            for cond in ['neutral','wrong']:
                z=[[next(r for r in rr if r['condition']==cond and r['rotation']==rot and r['round']==t) for t in range(1,T+1)] for rot in [0,2]]
                q=np.array([[r['layer_q'] for r in a] for a in z]);m=np.array([[r['layer_mass'] for r in a] for a in z]);data[name][cond]=(q,m)
        for name in names:
            for cond in ['neutral','wrong']:
                q,m=data[name][cond];b,bm=data['baseline'][cond];pred=q.argmax(-1);bp=b.argmax(-1);p=pred[:,:,-1];pbase=bp[:,:,-1];agree=p==pbase;final=agree[:,-1];anychange=np.any(~agree[:,:-1],axis=1)
                stable=np.all(p[:,1:]==p[:,:-1],axis=1);gold=q[:,:,-1,c['gold_index']];steps=np.abs(np.diff(gold,axis=1));total=steps.sum(-1);concentration=np.divide(steps.max(-1),total,out=np.zeros(2),where=total>1e-9)
                rows.append(dict(case_id=cid,dataset=c['dataset'],candidate=name,condition=cond,rounds=T,endpoint_fidelity=float(final.mean()),all_round_fidelity=float(agree.mean()),same_final_changed_earlier=float(np.mean(final&anychange)),any_round_changed=float(np.any(~agree,axis=1).mean()),no_diagnosis_switch=float(stable.mean()),largest_step_share=float(concentration.mean())))
                for l in range(28):
                    eligible=(m[:,:,l]>=.5)&(bm[:,:,l]>=.5);diff=pred[:,:,l]==bp[:,:,l]
                    layers.append(dict(case_id=cid,dataset=c['dataset'],candidate=name,condition=cond,layer=l+1,agreement=float(diff.mean()),eligible_fraction=float(eligible.mean()),eligible_agreement=float(diff[eligible].mean()) if eligible.any() else None))
            qn=data[name]['neutral'][0][:,:,-1];qw=data[name]['wrong'][0][:,:,-1]
            histories.append(dict(case_id=cid,candidate=name,mean_wrong_history_gold_support_effect=float((qw[:,:,c['gold_index']]-qn[:,:,c['gold_index']]).mean()),mean_wrong_history_named_support_effect=float((qw[:,:,c['wrong_index']]-qn[:,:,c['wrong_index']]).mean()),mean_history_diagnosis_disagreement=float(np.mean(qw.argmax(-1)!=qn.argmax(-1)))))
    csvwrite(OUT/'endpoint_vs_path_patient.csv',rows);csvwrite(OUT/'layer_trajectory_preservation.csv',layers);csvwrite(OUT/'history_effects_all_rounds.csv',histories)
    summary=[]
    for name in names:
        for cond in ['neutral','wrong']:
            rr=[r for r in rows if r['candidate']==name and r['condition']==cond]
            summary.append(dict(candidate=name,condition=cond,**{f:stat([r[f] for r in rr]) for f in ['endpoint_fidelity','all_round_fidelity','same_final_changed_earlier','any_round_changed','no_diagnosis_switch','largest_step_share']}))
    write(OUT/'dynamics_summary.json',dict(cases=47,summary=summary))
    fig,axs=plt.subplots(1,2,figsize=(12,4.8),layout='constrained');colors=['#317f9e','#c99738','#61a17e']
    for i,cond in enumerate(['neutral','wrong']):
        for j,name in enumerate(names[1:]):
            rr=next(r for r in summary if r['candidate']==name and r['condition']==cond);fields=['endpoint_fidelity','all_round_fidelity','same_final_changed_earlier'];means=np.array([rr[f]['mean'] for f in fields]);lo=np.array([rr[f]['low'] for f in fields]);hi=np.array([rr[f]['high'] for f in fields]);xx=np.arange(3)+(j-1)*.22
            axs[i].bar(xx,means,.2,color=colors[j],label=LABELS[name]);axs[i].errorbar(xx,means,yerr=[means-lo,hi-means],fmt='none',color='#333333',capsize=2)
        axs[i].set(xticks=range(3),xticklabels=['最终诊断一致','每轮诊断一致','最终一致\n但中间曾改变'],ylim=(0,1.05),title='中性历史' if cond=='neutral' else '错误历史',ylabel='病例级比例（两映射先平均）');axs[i].legend(fontsize=8)
    savefig(fig,OUT/'figures/endpoint_vs_path')
    fig,axs=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
    for i,cond in enumerate(['neutral','wrong']):
        for j,name in enumerate(names[1:]):
            yy=[np.mean([r['agreement'] for r in layers if r['condition']==cond and r['candidate']==name and r['layer']==l]) for l in range(1,29)]
            axs[i].plot(range(1,29),yy,label=LABELS[name],c=colors[j]);
        axs[i].set(title='中性历史' if cond=='neutral' else '错误历史',xlabel='模型层',ylabel='与原模型同层投影的一致率',ylim=(0,1.04));axs[i].legend(fontsize=8)
    fig.suptitle('全47例、全部轮次；这是同层读表一致性，早层不等于已形成诊断',fontsize=11);savefig(fig,OUT/'figures/layer_path_preservation')
    with (OUT/'selected_head_attention_by_round.csv').open() as f:attention=list(csv.DictReader(f))
    head_curves=[]
    for cond in ['neutral','wrong']:
        for layer,head in sorted({(int(r['layer']),int(r['head'])) for r in attention}):
            rr=[r for r in attention if r['condition']==cond and int(r['layer'])==layer and int(r['head'])==head]
            for progress in [0,.25,.5,.75,1]:
                vv=[]
                for cid in spec['cases']:
                    patient=sorted([r for r in rr if r['case_id']==cid],key=lambda r:int(r['round']));x=(np.array([int(r['round']) for r in patient])-1)/(len(patient)-1);y=np.array([float(r['prior_attention']) for r in patient]);vv.append(float(np.interp(progress,x,y)))
                head_curves.append(dict(condition=cond,layer=layer,head=head,progress=progress,**stat(vv)))
    csvwrite(OUT/'selected_head_attention_progress.csv',head_curves)
    fig,axs=plt.subplots(1,2,figsize=(12,4.7),layout='constrained')
    for i,cond in enumerate(['neutral','wrong']):
        for layer,head in sorted({(r['layer'],r['head']) for r in head_curves}):
            rr=[r for r in head_curves if r['condition']==cond and r['layer']==layer and r['head']==head];axs[i].plot([r['progress'] for r in rr],[r['mean'] for r in rr],'-o',ms=3,label=f'L{layer} H{head}')
        axs[i].set(title='中性历史' if cond=='neutral' else '错误历史',xlabel='证据进度（首组到末组，病例内插值）',ylabel='最后输入位置对历史JSON的注意力');axs[i].legend(ncol=2,fontsize=8)
    fig.suptitle('所选8个头在完整模型中的注意力变化；观察量不等同于因果作用',fontsize=11);savefig(fig,OUT/'figures/selected_heads_over_evidence')
    lines=['# 简化结构是否保留医学判断的更新过程\n\n预定47例，完整累计证据轨迹。每例两历史、两代码映射，四个冻结结构。所有病例均列入图谱。\n\n![终点与过程](figures/endpoint_vs_path.png)\n\n| 结构 | 历史 | 最终与原模型一致 | 所有轮次与原模型一致 | 最终一致、但中间曾改变 |\n|---|---|---|---|---|\n']
    for r in summary:lines.append(f'| {LABELS[r["candidate"]]} | {r["condition"]} | {fmt(r["endpoint_fidelity"],True)} | {fmt(r["all_round_fidelity"],True)} | {fmt(r["same_final_changed_earlier"],True)} |\n')
    lines.append('\n前两列分别统计终点与各轮平均；第三列统计每套映射中最终相同、至少一个更早轮次不同的轨迹，再在病例内平均。95%区间按病例重采样。\n\n![逐层保持](figures/layer_path_preservation.png)\n\n这张图比较同一层在结构改变前后的投影，不把早层投影当作实际诊断。原始表还提供两者代码总概率均≥0.5时的覆盖比例及一致率。\n\n![头随证据的变化](figures/selected_heads_over_evidence.png)\n\n每条线对应一个已冻结的注意力头。先在每例内将首组至末组映射到0–1进度并插值，再对47例平均，因此长病例不会获得更多权重。它显示这些头怎样继续读取旧历史；因果作用由对应删除实验判断。\n\n[全部病例与原文](CASE_ATLAS.md) · [逐病例终点/过程对照](endpoint_vs_path_patient.csv) · [逐层保持](layer_trajectory_preservation.csv) · [逐轮候选支持](all_candidate_trajectories.csv.gz)\n')
    (OUT/'RESULTS.md').write_text(''.join(lines));print(json.dumps(dict(complete=True,cases=47,output=str(OUT))))

if __name__=='__main__':main()
