"""Matched 1.7B/4B patient trajectories, with all prefixes and separate readouts."""
import json
import numpy as np
import matplotlib.pyplot as plt
from phase14_analyze import ROOT,RUN,cases
from analyze_stages import setup,savefig,csvwrite
from render_readable_v2 import ZH
def main():
    setup();dest=ROOT/'results/18_model_replication';(dest/'cases').mkdir(exist_ok=True)
    small=np.load(ROOT/'results/14_fixed_panel/prefix_readout_scores.npz');big=np.load(dest/'prefix_readout_scores.npz');classes=small['classes'].tolist();assert classes==big['classes'].tolist()
    ds=json.loads((RUN/'manifest.json').read_text())['candidate_diseases'];_,test=cases();index=[];allrows=[]
    for c in [c for c in test if c['deep_capture']]:
        cid=c['case_id'];T=len(c['orders']['base']);gi=ds.index(c['gold_disease']);yi=classes.index(c['gold_disease']);views=[];picksets=[]
        for run,scores,label,L in [(RUN,small[f'{cid}_append'],'1.7B FP16',28),(ROOT/'runs/belief_v2_4b',big[cid],'4B 8-bit',36)]:
            q=np.array([json.loads((run/'observations'/f'{cid}_append_base_t{t:02d}.json').read_text())['q_sequence'] for t in range(T+1)])
            rank=1+(scores>scores[:,:,yi,None]).sum(-1);picks=sorted(set(q.argmax(-1).tolist()+[gi]),key=lambda d:-q[:,d].max())[:6]
            if gi not in picks:picks[-1]=gi
            views.append((label,L,q,scores,rank));picksets.append(picks)
            for t in range(T+1):allrows.append(dict(case_id=cid,model=label,round=t,gold=c['gold_disease'],native49_top=ds[q[t].argmax()],gold_support=float(q[t,gi]),last_layer_probe_top=classes[scores[t,-1].argmax()],gold_last_layer_rank=int(rank[t,-1])))
        union=sorted(set(sum(picksets,[])));colors={d:plt.get_cmap('tab20')(i/20) for i,d in enumerate(union)};colors[gi]='black'
        fig,axs=plt.subplots(2,2,figsize=(12,8),layout='constrained')
        for i,(label,L,q,s,rank) in enumerate(views):
            for d in picksets[i]:axs[0,i].plot(range(T+1),q[:,d],marker='s' if d==gi else 'o',ms=3,lw=2.2 if d==gi else 1.4,color=colors[d],label=ZH.get(ds[d],ds[d])+('【来源标签】' if d==gi else ''),zorder=10 if d==gi else 2)
            axs[0,i].set(title=label+'：模型自己选择什么',xlabel='新增证据轮次',ylabel='49病名相对支持',ylim=(-.02,1.02),xticks=range(T+1));axs[0,i].legend(fontsize=8,loc='best')
            im=axs[1,i].imshow(rank.T,origin='lower',aspect='auto',extent=[-.5,T+.5,.5,L+.5],vmin=1,vmax=24,cmap='viridis_r');axs[1,i].set(title='内部读出：来源标签排第几？',xlabel='新增证据轮次',ylabel='模型层数',xticks=range(T+1),yticks=[1,L//4,L//2,L*3//4,L])
        fig.colorbar(im,ax=axs[1,:].tolist(),label='24类外部读出排名；黄色更靠前',ticks=[1,6,12,18,24],shrink=.85);fig.suptitle(cid+'｜'+ZH.get(c['gold_disease'],c['gold_disease']),fontsize=14);savefig(fig,dest/'cases'/cid)
        rr=[r for r in allrows if r['case_id']==cid];table='\n'.join(f"| {r['model']} | {r['round']} | {ZH.get(r['native49_top'],r['native49_top'])} | {r['gold_support']:.5f} | {ZH.get(r['last_layer_probe_top'],r['last_layer_probe_top'])} | {r['gold_last_layer_rank']} |" for r in rr)
        (dest/'cases'/f'{cid}.md').write_text(f'''# {cid}：两模型配置的同一条证据轨迹

来源标签：{ZH.get(c['gold_disease'],c['gold_disease'])}（{c['gold_disease']}）。全部轮次使用相同追加式事实。

![逐轮输出与逐层读出]({cid}.png)

上排黑线是来源标签病的模型支持；下排黄色表示从内部更容易识别来源标签。两模型读出器分别只用相同旧120例训练；隐藏维、层数及精度不同。

| 模型配置 | 轮次 | 模型首选 | 标签病支持 | 最后层读出首选 | 标签读出排名 |
|---|---:|---|---:|---|---:|
{table}

[每轮实际新增证据](../../14_fixed_panel/cases/{cid}.md)。这些轮次表示获得资料的顺序，不是患者病情的时间进展。
''')
        index.append(f"| [{cid}](cases/{cid}.md) | {ZH.get(c['gold_disease'],c['gold_disease'])} | {T} | {ZH.get(ds[views[0][2][-1].argmax()])} | {ZH.get(ds[views[1][2][-1].argmax()])} |")
    csvwrite(dest/'matched_model_prefixes.csv',allrows)
    (dest/'CASE_ATLAS.md').write_text('# 24例：从1.7B到4B的逐轮、逐层轨迹\n\n所有预定病例均展示，不按效果筛选。每图上排为49病名支持，下排为独立监督读出中的标签排名；两者不是同一种概率。参数规模和量化精度同时变化。\n\n| 病例 | 来源标签 | 更新次数 | 1.7B终点首选 | 4B终点首选 |\n|---|---|---:|---|---|\n'+'\n'.join(index)+'\n\n[全部逐轮数值](matched_model_prefixes.csv) · [总体结果](RESULTS.md)\n')
    print(json.dumps({'paired_case_figures':24,'prefix_rows':len(allrows)}),flush=True)
if __name__=='__main__':main()
