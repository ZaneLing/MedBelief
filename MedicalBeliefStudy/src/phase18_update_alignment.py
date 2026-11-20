"""Post-hoc cross-configuration comparison of natural update alignment across depth."""
import json
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from phase14_analyze import ROOT,cases
from analyze_stages import setup,savefig,csvwrite,dump,ci,fmt
def main():
    setup();run=ROOT/'runs/belief_v2_4b';dest=ROOT/'results/18_model_replication';sfile=np.load(dest/'prefix_readout_scores.npz');classes=sfile['classes'].tolist();ds=json.loads((run/'manifest.json').read_text())['candidate_diseases'];sub=[ds.index(d) for d in classes];_,test=cases();rows=[];case_rows=[]
    for c in [c for c in test if c['deep_capture']]:
        cid=c['case_id'];T=len(c['orders']['base']);yi=classes.index(c['gold_disease']);gi=ds.index(c['gold_disease']);s=sfile[cid];logs=np.array([json.loads((run/'observations'/f'{cid}_append_base_t{t:02d}.json').read_text())['log_probability'] for t in range(T+1)]);xx=[];yy=[]
        for t in range(1,T+1):
            co=max((j for j in range(24) if j!=yi),key=lambda j:logs[t-1,sub[j]]);dx=(s[t,:,yi]-s[t,:,co])-(s[t-1,:,yi]-s[t-1,:,co]);dy=(logs[t,gi]-logs[t,sub[co]])-(logs[t-1,gi]-logs[t-1,sub[co]]);xx.append(dx);yy.append(dy)
            for l in range(36):rows.append(dict(case_id=cid,round=t,layer=l+1,gold=c['gold_disease'],competitor=classes[co],readout_margin_change=float(dx[l]),native_margin_change=float(dy)))
        X=np.array(xx);Y=np.array(yy)
        for l in range(36):
            valid=(abs(X[:,l])>1e-8)&(abs(Y)>1e-8);rho=float(spearmanr(X[:,l],Y).statistic) if np.ptp(X[:,l])>1e-8 and np.ptp(Y)>1e-8 else None
            case_rows.append(dict(case_id=cid,layer=l+1,updates=T,spearman=rho,same_direction=float(np.mean((X[:,l]*Y>0)[valid])) if valid.any() else None,nonzero_updates=int(valid.sum())))
    summary={str(l):{key:ci([r[key] for r in case_rows if r['layer']==l and r[key] is not None]) for key in ['spearman','same_direction']} for l in range(1,37)};dump(dest/'natural_alignment_summary.json',summary);csvwrite(dest/'natural_alignment_updates.csv',rows);csvwrite(dest/'natural_alignment_cases.csv',case_rows)
    small=json.loads((ROOT/'results/16_update_mechanism/natural_alignment_summary.json').read_text())['append'];sa=json.loads((ROOT/'results/14_fixed_panel/summary.json').read_text())['endpoints']['append']['layer_accuracy'];ba=json.loads((dest/'summary.json').read_text())['layer_accuracy']
    fig,axs=plt.subplots(1,2,figsize=(11,4.7))
    for L,s,acc,label,color in [(28,small,sa,'1.7B FP16','#2878b5'),(36,summary,ba,'4B 8-bit','#e07b21')]:
        x=np.arange(1,L+1)/L;axs[0].plot(x,acc,label=label,color=color);rr=[s[str(l)]['spearman'] for l in range(1,L+1)];axs[1].plot(x,[r['mean'] for r in rr],label=label,color=color);axs[1].fill_between(x,[r['low'] for r in rr],[r['high'] for r in rr],color=color,alpha=.15)
    axs[0].set(title='终点：疾病信息何时可读？',ylabel='新120例24病读出准确率',ylim=(0,1));axs[1].set(title='逐轮：内部更新何时与输出相关？',ylabel='24病例平均Spearman相关',ylim=(-1,1));axs[1].axhline(0,color='gray',ls='--',lw=1)
    for ax in axs:ax.set(xlabel='相对模型深度');ax.legend()
    fig.tight_layout();savefig(fig,dest/'figures/information_and_update_depth')
    table='\n'.join(f"| {l} | {fmt(summary[str(l)]['spearman'],False)} | {fmt(summary[str(l)]['same_direction'])} |" for l in [9,18,27,36])
    (dest/'NATURAL_ALIGNMENT.md').write_text(f'''# 4B：信息可读与输出更新的逐层关系

沿用1.7B的连续量分析：每次新证据固定标签病与前轮24类最强非标签病，比较读出分差和原输出对数分差的变化。使用相同24例184次更新、36层读出，先病例内计算再汇总。此为在观察1.7B曲线后追加的描述性复核，未预定特定转折层。

| 层 | 病例平均相关 | 同方向比例 |
|---:|---|---|
{table}

![可读性与输出关联的深度](figures/information_and_update_depth.png)

左图是120例终点分类，右图是24例自然证据更新，两图统计对象与纵轴不同。比较曲线形状用于区分可读性与更新关联，不能从某个层的拐点直接定位因果回路。4B为8-bit、1.7B为FP16，不把差异只归于参数规模。

[病例统计](natural_alignment_cases.csv) · [每次更新](natural_alignment_updates.csv) · [精确汇总](natural_alignment_summary.json)
''');print(json.dumps({l:summary[l] for l in ['9','18','27','36']},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
