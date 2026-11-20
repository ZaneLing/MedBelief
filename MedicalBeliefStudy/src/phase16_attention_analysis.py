"""Descriptive per-head attention atlas on all 120 held-out patient endpoints."""
import json
import numpy as np
import matplotlib.pyplot as plt
from phase14_analyze import ROOT,RUN,cases
from analyze_stages import setup,savefig,csvwrite,dump,ci,fmt
def main():
    setup();dest=ROOT/'results/16_update_mechanism';_,test=cases();heads=[];patients=[];matrices={};summary={}
    for view in ['append','panel']:
        values=[]
        for c in test:
            t=len(c['orders']['base']);r=json.loads((RUN/'observations'/f"{c['case_id']}_{view}_base_t{t:02d}.json").read_text())
            with np.load(RUN/r['state_file']) as a:att=a['attention_by_group'].astype(float);groups=a['token_groups'];counts=np.bincount(groups,minlength=att.shape[-1])
            known_idx=list(range(3,att.shape[-1])) if view=='append' else [3,4];known_idx=[i for i in known_idx if i<att.shape[-1]]
            known=att[:,:,known_idx].sum(-1);nknown=int(counts[known_idx].sum());unknown=att[:,:,5] if view=='panel' and att.shape[-1]>5 else np.zeros_like(known);nunknown=int(counts[5]) if view=='panel' and len(counts)>5 else 0
            arr=np.stack([att[:,:,0],att[:,:,1],att[:,:,2],known,unknown],axis=-1);assert np.allclose(arr.sum(-1),1,atol=1e-5);values.append(arr)
            for l in range(28):
                for h in range(16):heads.append(dict(case_id=c['case_id'],view=view,layer=l+1,head=h+1,format_attention=float(arr[l,h,0]),candidate_attention=float(arr[l,h,1]),demographic_attention=float(arr[l,h,2]),known_attention=float(known[l,h]),unknown_attention=float(unknown[l,h]),known_per_token=float(known[l,h]/max(nknown,1)),unknown_per_token=float(unknown[l,h]/max(nunknown,1))))
            patients.append(dict(case_id=c['case_id'],view=view,known_tokens=nknown,unknown_tokens=nunknown,late_known_attention=float(known[20:].mean()),late_candidate_attention=float(att[20:,:,1].mean()),late_unknown_attention=float(unknown[20:].mean()),late_format_attention=float(att[20:,:,0].mean())))
        matrices[view]=np.array(values).mean(0);rr=[r for r in patients if r['view']==view];summary[view]={k:ci([r[k] for r in rr]) for k in ['late_known_attention','late_candidate_attention','late_unknown_attention','late_format_attention']}
    csvwrite(dest/'endpoint_attention_heads.csv',heads);csvwrite(dest/'endpoint_attention_patients.csv',patients);dump(dest/'attention_summary.json',summary)
    fig,axs=plt.subplots(2,2,figsize=(11,10),layout='constrained');vmax=max(m[:,:,k].max() for m in matrices.values() for k in [1,3])
    for col,(view,label) in enumerate([('append','逐条追加'),('panel','固定问卷')]):
        for row,(k,g) in enumerate([(3,'已知患者问答'),(1,'候选病名列表')]):
            im=axs[row,col].imshow(matrices[view][:,:,k],origin='lower',aspect='auto',vmin=0,vmax=vmax,cmap='YlOrRd',extent=[.5,16.5,.5,28.5]);axs[row,col].set(title=label+'：看向'+g,xlabel='查询注意力头',ylabel='模型层数',xticks=[1,4,8,12,16],yticks=[1,7,14,21,28])
    fig.colorbar(im,ax=axs.ravel().tolist(),label='诊断锚点的组注意力质量（120病例平均）',shrink=.7);savefig(fig,dest/'figures/attention_heads')
    table='\n'.join(f"| {label} | {fmt(summary[v]['late_known_attention'])} | {fmt(summary[v]['late_candidate_attention'])} | {fmt(summary[v]['late_unknown_attention'])} | {fmt(summary[v]['late_format_attention'])} |" for v,label in [('append','逐条追加'),('panel','固定问卷')])
    (dest/'ATTENTION_ATLAS.md').write_text(f'''# 120例的逐层、逐头注意力

## 测量

同一新120例终点、1.7B的28层×16个查询头，测量回答前诊断位置看向输入各部分的注意力质量。先在每例内部汇总，再对病例求均值及区间。固定问卷的已知项为当前症状和病史问答；追加式将全部已揭示证据组合并。格式包含系统/任务指令、特殊词元、证据标记及回答前缀；不是“没有信息”的同义词。

| 输入方式 | 第21—28层：已知问答 | 候选列表 | 未知字段 | 格式与指令 |
|---|---|---|---|---|
{table}

![逐头注意力](figures/attention_heads.png)

颜色越深表示该头在诊断位置分配给相应输入组的注意力越多。两个输入条件的token数量不同，原始质量不能单独判断是否忽略信息；逐头CSV同时给出每token质量。头编号只在同一个模型配置中对应，不代表不同模型中的同一种功能。

注意力质量是信息读取位置的描述，不是该信息对疾病选择的因果贡献。阶段19固定长度的已知资料前移/后移对照显示，注意力增多未伴随更好的诊断；阶段15才进一步检验内部方向的输出作用。

[全部107520个病例×层×头记录](endpoint_attention_heads.csv) · [病例汇总](endpoint_attention_patients.csv) · [精确均值与区间](attention_summary.json)
''')
    print(json.dumps(summary,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
