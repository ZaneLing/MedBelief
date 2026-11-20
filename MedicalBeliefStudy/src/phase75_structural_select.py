"""Choose and freeze candidates on 27 development cases, before test scoring."""
import hashlib
import matplotlib.pyplot as plt
from structural_v1_analysis import *
from analyze_stages import setup,savefig
OUT=ROOT/'results/43_structural_development'
def main():
    assert read(RUN/'tune/completion.json')['complete'];setup();(OUT/'figures').mkdir(parents=True,exist_ok=True)
    rows,sizes,spec=load('tune');stats=summarize(rows);cs={r['name']:r for r in spec['candidates']};point={}
    for name in cs:
        r={}
        for cond in ['neutral','wrong']:
            sub=[x for x in rows if x['candidate']==name and x['condition']==cond]
            for field in ['accuracy','accuracy_change','fidelity','code_rate_change','strict_accuracy_change']:r[cond+'_'+field]=float(np.mean([x[field] for x in sub]))
        r['passes']=all(r[c+'_fidelity']>=.90 and r[c+'_accuracy_change']>=-.02 and r[c+'_code_rate_change']>=-.02 for c in ['neutral','wrong']);point[name]=r
    def choose(names):
        qualified=[n for n in names if point[n]['passes']]
        if qualified:return min(qualified,key=lambda n:sizes[n]['parameters'])
        return max(names,key=lambda n:(min(point[n][c+'_fidelity'] for c in ['neutral','wrong']),np.mean([point[n][c+'_accuracy_change'] for c in ['neutral','wrong']]),-sizes[n]['parameters']))
    mlp=choose(['drop_mlp_2','drop_mlp_4']);n=len(cs[mlp]['drop_mlps']);block=choose(['drop_block_1','drop_block_2']);linear=choose([f'linear_mlp_{n}_r16',f'linear_mlp_{n}_r64'])
    heads=max([f'anchor_heads_{n}' for n in [2,4,8]],key=lambda n:(point[n]['neutral_accuracy_change']>=-.02,point[n]['wrong_accuracy_change']+point[n]['neutral_accuracy_change'],point[n]['wrong_accuracy_change'],-int(n.split('_')[-1])))
    alternate=f'linear_mlp_{n}_r'+('64' if cs[linear]['rank']==16 else '16')
    names=['baseline','early_exit',mlp,linear,block,heads,f'depth_matched_random_mlp_{n}','block_influence_2',alternate]
    selected=dict(status='frozen_before_holdout',candidates=[cs[n] for n in names],development_patients=27,screen_patients=18,holdout_patients=345,qualification=point,parameter_stats=sizes,mlp_pair=[mlp,linear],compression_candidates=[mlp,block,'early_exit',linear],repair_candidate=heads,source_sha256=hashlib.sha256(open(__file__,'rb').read()).hexdigest(),development_manifest_sha256=hashlib.sha256((RUN/'tune/manifest.json').read_bytes()).hexdigest(),selection_criterion='per-history >=90% original decision fidelity, accuracy and code-rate loss <=2 percentage points; smallest qualified, otherwise most faithful failure candidate',api_cost_usd=0)
    if (RUN/'selected.json').exists():assert read(RUN/'selected.json')==selected
    else:write(RUN/'selected.json',selected)
    csvwrite(OUT/'patient_results.csv',rows);write(OUT/'summary.json',dict(cases=27,summaries=stats,selection=selected));labels=list(cs)
    fig,axs=plt.subplots(1,2,figsize=(14,6),layout='constrained')
    for cond,style in [('neutral','-o'),('wrong','-s')]:
        axs[0].plot([point[n][cond+'_fidelity'] for n in labels],range(len(labels)),style,label=cond)
        axs[1].plot([100*point[n][cond+'_accuracy_change'] for n in labels],range(len(labels)),style,label=cond)
    for ax in axs:ax.set(yticks=range(len(labels)),yticklabels=labels);ax.invert_yaxis();ax.legend()
    axs[0].set(title='组合删除是否仍保持原诊断',xlabel='与完整模型一致率');axs[1].set(title='有没有改善来源答案命中',xlabel='相对完整模型，百分点');axs[1].axvline(0,c='gray',lw=.8);savefig(fig,OUT/'figures/development_tradeoffs')
    lines=['# 结构候选的开发选择\n\n18例用于定位与小模块拟合，另27例用于组合选择。本表不是留出集结论。结构及对照均在345例检验前冻结。\n\n![候选对比](figures/development_tradeoffs.png)\n\n| 候选 | 参数数 | 中性一致率 | 错误历史一致率 | 中性准确率变化 | 错误历史准确率变化 | 达到开发保留标准 |\n|---|---:|---:|---:|---:|---:|---|\n']
    for name,p in point.items():lines.append(f'| {name} | {sizes[name]["parameters"]:,} | {p["neutral_fidelity"]:.3f} | {p["wrong_fidelity"]:.3f} | {p["neutral_accuracy_change"]*100:+.2f} | {p["wrong_accuracy_change"]*100:+.2f} | {p["passes"]} |\n')
    lines.append('\n冻结候选：'+', '.join(names)+'。未达开发标准的候选仍作为失败检验保存，不因排名靠前称为有效压缩模型。\n\n[逐病例结果](patient_results.csv) · [汇总及冻结配置](summary.json)\n')
    (OUT/'RESULTS.md').write_text(''.join(lines));print(json.dumps(dict(selected=names,configurations=[cs[n] for n in names],qualification={n:point[n] for n in names}),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
