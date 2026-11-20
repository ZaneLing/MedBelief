"""Connect individual evidence updates to held-out readouts and block computations."""
import json,collections
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from phase14_analyze import cases,record,ROOT,RUN,DEST as PREV,norm
from analyze_stages import setup,savefig,ci,fmt,csvwrite,dump,js

def main():
    setup();assert (PREV/'summary.json').exists();dest=ROOT/'results/16_update_mechanism';(dest/'figures').mkdir(parents=True,exist_ok=True)
    _,test=cases();heads=np.load(PREV/'training_heads.npz');classes=heads['classes'].tolist();diseases=json.loads((RUN/'manifest.json').read_text())['candidate_diseases'];sub=[diseases.index(d) for d in classes]
    evidence=[];decomposed=[];case_rows=[];switchrows=[];modulefig={}
    for c in [c for c in test if c['deep_capture']]:
        cid=c['case_id'];T=len(c['orders']['base']);gi=diseases.index(c['gold_disease']);yi=classes.index(c['gold_disease'])
        for view in ['append','panel']:
            rr=[];states=[]
            for t in range(T+1):
                base,r=record(c,view,t);rr.append(r)
                with np.load(base/r['state_file']) as a:states.append(a['residual_stages'].astype(float))
            states=np.array(states);normalized=norm(states);W=heads[f'weights_{view}_0.1'];center=heads[f'center_{view}'];S=np.einsum('tlkd,ldc->tlkc',normalized-center[None,:,None,:],W)+heads['bias'];P=S[:,:,4].argmax(-1)
            q=np.array([r['q_sequence'] for r in rr]);logs=np.array([r['log_probability'] for r in rr]);first=np.array([[v[0] for v in r['token_log_probability']] for r in rr]);nt=q.argmax(-1);n24=q[:,sub].argmax(-1)
            switch=nt[1:]!=nt[:-1];loc=[]
            for t in range(1,T+1):
                old=int(nt[t-1]);new=int(nt[t]);old24=int(n24[t-1]);new24=int(n24[t]);tokens=np.array([s[0] for s in rr[t]['suffix_ids']]);total=(logs[t,new]-logs[t,old])-(logs[t-1,new]-logs[t-1,old]);fst=(first[t,new]-first[t,old])-(first[t-1,new]-first[t-1,old])
                er=dict(case_id=cid,view=view,round=t,native_switch=bool(switch[t-1]),native24_switch=bool(old24!=new24),previous_disease=diseases[old],current_disease=diseases[new],previous_disease24=classes[old24],current_disease24=classes[new24],same_first_token=bool(tokens[old]==tokens[new]),total_switch_logodds=float(total),first_switch_logodds=float(fst),tail_switch_logodds=float(total-fst),gold_support=float(q[t,gi]),delta_gold=float(q[t,gi]-q[t-1,gi]))
                for l in [20,27]:
                    er[f'probe{l+1}_stable']=bool(P[t,l]==P[t-1,l]);er[f'probe{l+1}_stable_gold']=bool(P[t,l]==P[t-1,l]==yi)
                    er[f'probe{l+1}_gold_correct']=bool(P[t,l]==yi)
                    dd=(S[t,l,4,new24]-S[t,l,4,old24])-(S[t-1,l,4,new24]-S[t-1,l,4,old24]);er[f'probe{l+1}_switch_direction']=float(dd)
                evidence.append(er);loc.append(er)
                # Fixed disease pair per event; comparison remains the same across stages.
                competitor=max((j for j in range(24) if j!=yi),key=lambda j:q[t-1,sub[j]])
                for l in range(28):
                    v=S[:,l,:,yi]-S[:,l,:,competitor]
                    inp=v[t,0]-v[t-1,0];att=(v[t,2]-v[t,0])-(v[t-1,2]-v[t-1,0]);mlp=(v[t,4]-v[t,2])-(v[t-1,4]-v[t-1,2]);out=v[t,4]-v[t-1,4]
                    assert abs(out-(inp+att+mlp))<1e-9
                    decomposed.append(dict(case_id=cid,view=view,round=t,layer=l+1,gold=c['gold_disease'],competitor=classes[competitor],incoming_change=float(inp),attention_change=float(att),mlp_change=float(mlp),outgoing_change=float(out)))
            sw=[r for r in loc if r['native_switch']];sw24=[r for r in loc if r['native24_switch']]
            cr=dict(case_id=cid,view=view,updates=T,switches=len(sw),switches24=len(sw24),same_first_switches=sum(r['same_first_token'] for r in sw),native49_accuracy=float(np.mean(nt==gi)),native24_switch_rate=float(np.mean(n24[1:]!=n24[:-1])))
            for l in [21,28]:
                cr[f'probe{l}_switch_rate']=float(np.mean(P[1:,l-1]!=P[:-1,l-1]))
                cr[f'probe{l}_stable_when_native24_switches']=float(np.mean([r[f'probe{l}_stable'] for r in sw24])) if sw24 else None
                cr[f'probe{l}_stable_gold_when_native24_switches']=float(np.mean([r[f'probe{l}_stable_gold'] for r in sw24])) if sw24 else None
                cr[f'probe{l}_stable_when_native_switches']=float(np.mean([r[f'probe{l}_stable'] for r in sw])) if sw else None
                cr[f'probe{l}_stable_gold_when_native_switches']=float(np.mean([r[f'probe{l}_stable_gold'] for r in sw])) if sw else None
                cr[f'probe{l}_opposes_native24_switch']=float(np.mean([r[f'probe{l}_switch_direction']<0 for r in sw24])) if sw24 else None
            case_rows.append(cr);switchrows+=sw
    summary={'cases':24,'views':{},'description':'Eventwise score changes are descriptive. Block score decomposition is an identity of an external normalized readout, not causal attribution.'}
    for view in ['append','panel']:
        cr=[r for r in case_rows if r['view']==view];sw=[r for r in switchrows if r['view']==view]
        summary['views'][view]={'updates':sum(r['updates'] for r in cr),'switches':len(sw),'switches24':sum(r['switches24'] for r in cr),'same_first_switches':sum(r['same_first_token'] for r in sw),'native24_switch_rate':ci([r['native24_switch_rate'] for r in cr]),
            'first_80pct_switches':sum(r['first_switch_logodds']>=.8*r['total_switch_logodds'] for r in sw),
            'tail_80pct_switches':sum(r['tail_switch_logodds']>=.8*r['total_switch_logodds'] for r in sw),
            **{key:ci([r[key] for r in cr if r[key] is not None]) for key in cr[0] if key.startswith('probe')}}
        mat=[]
        for l in range(1,29):
            values=[]
            for c in [c for c in test if c['deep_capture']]:
                rs=[r for r in decomposed if r['case_id']==c['case_id'] and r['view']==view and r['layer']==l]
                # Mean magnitude is explicitly not signed medical support or causal effect.
                values.append([np.mean([abs(r[k]) for r in rs]) for k in ['incoming_change','attention_change','mlp_change','outgoing_change']])
            mat.append(np.mean(values,axis=0))
        modulefig[view]=np.array(mat)
    csvwrite(dest/'evidence_internal_changes.csv',evidence);csvwrite(dest/'block_readout_decomposition.csv',decomposed);csvwrite(dest/'case_metrics.csv',case_rows);csvwrite(dest/'natural_switches.csv',switchrows);dump(dest/'summary.json',summary)
    fig,axs=plt.subplots(1,2,figsize=(11,4.5),sharey=True)
    for ax,view in zip(axs,['append','panel']):
        for k,label in enumerate(['进入该层的差异','注意力步骤的差异','MLP步骤的差异','离开该层的差异']):ax.plot(range(1,29),modulefig[view][:,k],label=label)
        ax.set(title={'append':'逐条追加','panel':'固定问卷'}[view],xlabel='层');ax.legend(fontsize=8)
    axs[0].set_ylabel('标签—竞争病读出分差的平均绝对更新量');fig.tight_layout();savefig(fig,dest/'figures/block_updates')
    fig,ax=plt.subplots(figsize=(9,4.8));positions=np.arange(2)
    for li,l in enumerate([21,28]):
        vals=[summary['views'][v][f'probe{l}_stable_when_native24_switches'] for v in ['append','panel']];ax.bar(positions+(li-.5)*.3,[r['mean'] for r in vals],width=.3,label=f'第{l}层读出')
    ax.set(xticks=positions,xticklabels=['逐条追加','固定问卷'],ylabel='同24病输出换病时，内部读出首选保持的比例',ylim=(0,1));ax.legend();fig.tight_layout();savefig(fig,dest/'figures/stable_readout_switching_output')
    table='\n'.join(f"| {v} | {s['switches24']} | {fmt(s['probe21_stable_when_native24_switches'])} | {fmt(s['probe28_stable_when_native24_switches'])} |" for v,s in summary['views'].items())
    (dest/'RESULTS.md').write_text(f'''# 阶段16：把输出转向与内部疾病变化接起来

## 问题

新增证据后模型换病时，各层可读出的疾病也同步更换吗？变化经过attention和MLP时怎样被增减？

## 方法

沿用新24例两种呈现的全部轮次，读出头只在旧120例终点训练。统计每次输出首选更换时，第21/28层读出首选是否保持。先病例内求比例，再对有相应事件的病例汇总，分母在summary中保留。

| 呈现 | 同24病输出换病次数 | 第21层首选保持比例 | 第28层首选保持比例 |
|---|---:|---|---|
{table}

![内部保持与输出转向](figures/stable_readout_switching_output.png)

主要比较统一限制到同24病；49病原始转向和病名分解另行保留。首选保持不代表内部向量没有变化，也不自动代表内部判断正确；同一表中进一步保存“保持的是最终标签病”的比例。读出分差方向与模型输出方向相反的比例独立记录，使用同一疾病对，避免随轮次换竞争病造成假变化。

## 每层计算怎样改变疾病相关分差

对每次更新固定“最终标签病—上一轮最强非标签病”作为比较，分别读取进入层、attention后、MLP后的归一化状态。新旧轮次的离层分差变化严格分解为：进入层的变化＋attention步骤变化＋MLP步骤变化。这是读出分数的数学分解，不把线性读出分量当作模块的医学因果贡献；阶段15的干预才检验输出作用。

![计算步骤分解](figures/block_updates.png)

## 自然更新与输出路径

自然新增证据改变整段输入，既能改变病名开头，也能改变后续词元。与最后层锚点干预不同，同首词元疾病之间的自然转向是真正由病名后续条件概率决定的。因此不能把全部诊断跳变都归为首词元效应，也不能用一个最后层锚点替换覆盖整个诊断更新机制。

[逐证据内部变化](evidence_internal_changes.csv) · [28层计算分解](block_readout_decomposition.csv) · [自然转向分解](natural_switches.csv) · [精确结果](summary.json)
''')
    print(json.dumps(summary,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
