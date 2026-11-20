"""Exploratory residual-update geometry after the prespecified confirmation."""
from pathlib import Path
import json
import numpy as np
import matplotlib.pyplot as plt
from analyze_stages import setup,savefig,ci,fmt,csvwrite,dump
ROOT=Path(__file__).resolve().parents[1]
def main():
    setup();cases=[json.loads(s) for s in (ROOT/'data/full49_v1/cases.private.jsonl').read_text().splitlines()];dest=ROOT/'results/10_name_causal_mechanism';(dest/'figures').mkdir(parents=True,exist_ok=True);rows=[]
    for view,run,maps in [('code',ROOT/'runs/full49_v1',[0,16]),('name',ROOT/'runs/structured_names_v1',[0])]:
        if view=='code':assert (run/'completion.json').exists()
        for c in cases:
            if view=='name' and not c['deep_capture']:continue
            values=[];t=c['fixed_middle_round'];cid=c['case_id']
            for m in maps:
                pair=[]
                for tt in [t-1,t]:
                    record=json.loads((run/'observations'/f'{cid}_base_t{tt:02d}_m{m}.json').read_text())
                    with np.load(run/record['state_file']) as a:pair.append(a['residual_stages'].astype(float))
                delta=pair[1]-pair[0];mid=delta[:,2];mlp=delta[:,3];post=delta[:,4];midnorm=np.linalg.norm(mid,axis=-1);postnorm=np.linalg.norm(post,axis=-1);mlpnorm=np.linalg.norm(mlp,axis=-1)
                cosine=np.sum(mid*mlp,axis=-1)/np.maximum(midnorm*mlpnorm,1e-12);contraction=1-postnorm/np.maximum(midnorm,1e-12)
                values.append(np.stack([cosine,contraction,midnorm,postnorm,mlpnorm],axis=-1))
            v=np.mean(values,axis=0)
            for l in range(28):rows.append({'view':view,'case_id':cid,'layer':l+1,**{k:float(x) for k,x in zip(['cosine_mlp_mid','contraction','mid_distance','post_distance','mlp_change_norm'],v[l])}})
    csvwrite(dest/'component_geometry.csv',rows);summary={view:{str(l):{k:ci([r[k] for r in rows if r['view']==view and r['layer']==l]) for k in ['cosine_mlp_mid','contraction']} for l in range(1,29)} for view in ['code','name']};dump(dest/'component_geometry_summary.json',summary)
    fig,axes=plt.subplots(1,2,figsize=(11,4.4))
    for view,label in [('code','Code interface, 120 cases'),('name','Disease names, 24 cases')]:
        for ax,key in zip(axes,['cosine_mlp_mid','contraction']):ax.plot(range(1,29),[summary[view][str(l)][key]['mean'] for l in range(1,29)],label=label)
    for ax in axes:ax.axhline(0,color='gray',lw=.8);ax.set_xlabel('Layer');ax.legend(fontsize=8)
    axes[0].set_ylabel('Cosine(MLP update, incoming update)');axes[1].set_ylabel('Contraction of between-round state distance');fig.tight_layout();savefig(fig,dest/'figures/update_geometry')
    table='\n'.join(f'| {l} | {fmt(summary["code"][str(l)]["contraction"],False)} | {fmt(summary["name"][str(l)]["contraction"],False)} |' for l in [26,27,28])
    verdict='两个接口的第26—28层平均都扩大了新旧状态的欧氏距离，区间均不跨0。因此，编码实验中的干预方向翻转不能用“26/27层整体收缩、28层整体放大”这个简单解释说明。应进一步测量疾病相关方向，而非只看变化幅度。' if all(summary[v][str(l)]['contraction']['high']<0 for v in ['code','name'] for l in [26,27,28]) else '整体距离变化并未提供足以解释诊断干预方向的统一模式。'
    (dest/'GEOMETRY.md').write_text(f'''# 补充：MLP在放大还是抵消新旧状态之间的差异

观察到阶段08层方向模式后追加的探索性分析。对固定中间轮，测量进入MLP前、经过MLP后的新旧轮状态距离。收缩量为1减去后/前距离比；正值是拉近、负值是拉远。它是整个隐藏向量的几何量，不是某个疾病的概率。

| 层 | 编码接口120例收缩量 [95%区间] | 名称接口24例收缩量 [95%区间] |
|---|---|---|
{table}

**{verdict}**

![状态距离](figures/update_geometry.png)

该量检验“MLP抵消前面部分状态改变”是否与干预结果相容。即使存在收缩，也不能只凭范数认定其压制或增强某种医学信念；疾病方向需要结合未见病例读出及因果诊断变化。

[逐病例数据](component_geometry.csv) · [汇总](component_geometry_summary.json)
''')

if __name__=='__main__':main()
