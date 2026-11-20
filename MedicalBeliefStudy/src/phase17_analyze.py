"""Sensitivity to polarity, without assuming a counterfactual diagnosis oracle."""
import json
import numpy as np
import matplotlib.pyplot as plt
from phase14_analyze import ROOT,RUN,norm
from analyze_stages import setup,savefig,ci,fmt,csvwrite,dump,js
def cosine(a,b):return np.sum(a*b,axis=-1)/np.maximum(np.linalg.norm(a,axis=-1)*np.linalg.norm(b,axis=-1),1e-12)
def main():
    setup();run=RUN/'polarity';assert (run/'completion.json').exists();dest=ROOT/'results/17_answer_polarity';(dest/'figures').mkdir(parents=True,exist_ok=True)
    heads=np.load(ROOT/'results/14_fixed_panel/training_heads.npz');W=heads['weights_panel_0.1'];center=heads['center_panel'];classes=heads['classes'].tolist();diseases=json.loads((RUN/'manifest.json').read_text())['candidate_diseases'];rows=[];layerrows=[]
    for p in sorted(run.glob('ddx*.json')):
        no=json.loads(p.read_text());yes=json.loads((RUN/'observations'/f"{no['yes_job_id']}.json").read_text());unknown=json.loads((RUN/'observations'/f"{no['unknown_job_id']}.json").read_text());xx=[]
        for r in [unknown,yes,no]:
            with np.load(RUN/r['state_file']) as a:xx.append(a['residual_stages'][:,4].astype(float))
        X=norm(np.array(xx));S=np.einsum('nld,ldc->nlc',X-center,W)+heads['bias'];du=X[1]-X[0];dn=X[2]-X[0];cs=cosine(du,dn);ds=S[1]-S[0];ns=S[2]-S[0];sc=cosine(ds,ns)
        uq=np.array(unknown['q_sequence']);yq=np.array(yes['q_sequence']);nq=np.array(no['q_sequence'])
        rr=dict(case_id=no['case_id'],round=no['round'],question=no['question'],yes_no_same_length=no['yes_no_same_length'],unknown_top=diseases[uq.argmax()],yes_top=diseases[yq.argmax()],no_top=diseases[nq.argmax()],yes_no_switch=bool(yq.argmax()!=nq.argmax()),yes_unknown_switch=bool(yq.argmax()!=uq.argmax()),no_unknown_switch=bool(nq.argmax()!=uq.argmax()),yes_no_js=float(js(yq,nq)),yes_unknown_js=float(js(yq,uq)),no_unknown_js=float(js(nq,uq)),output_update_cosine=float(cosine(yq-uq,nq-uq)))
        for l in [20,27]:rr.update({f'probe{l+1}_yes_no_switch':bool(S[1,l].argmax()!=S[2,l].argmax()),f'probe{l+1}_yes':classes[S[1,l].argmax()],f'probe{l+1}_no':classes[S[2,l].argmax()],f'state_cosine{l+1}':float(cs[l]),f'readout_cosine{l+1}':float(sc[l])})
        rows.append(rr)
        for l in range(28):layerrows.append(dict(case_id=no['case_id'],layer=l+1,state_update_cosine=float(cs[l]),readout_update_cosine=float(sc[l]),yes_no_state_distance=float(np.linalg.norm(X[1,l]-X[2,l])),yes_unknown_state_distance=float(np.linalg.norm(du[l])),no_unknown_state_distance=float(np.linalg.norm(dn[l]))))
    keys=['yes_no_switch','yes_unknown_switch','no_unknown_switch','yes_no_js','yes_unknown_js','no_unknown_js','output_update_cosine','probe21_yes_no_switch','probe28_yes_no_switch','state_cosine21','state_cosine28','readout_cosine21','readout_cosine28']
    summary={'cases':len(rows),'same_length_cases':sum(r['yes_no_same_length'] for r in rows),'counterfactual_ground_truth':None,'metrics':{k:ci([r[k] for r in rows]) for k in keys},'layer_state_cosine':[ci([r['state_update_cosine'] for r in layerrows if r['layer']==l]) for l in range(1,29)],'layer_readout_cosine':[ci([r['readout_update_cosine'] for r in layerrows if r['layer']==l]) for l in range(1,29)]}
    csvwrite(dest/'case_results.csv',rows);csvwrite(dest/'layer_updates.csv',layerrows);dump(dest/'summary.json',summary)
    fig,ax=plt.subplots(figsize=(9,5))
    for key,label in [('layer_state_cosine','完整内部状态'),('layer_readout_cosine','24病读出分数')]:
        v=summary[key];ax.plot(range(1,29),[r['mean'] for r in v],label=label);ax.fill_between(range(1,29),[r['low'] for r in v],[r['high'] for r in v],alpha=.15)
    ax.axhline(0,color='gray',lw=1);ax.set(xlabel='层',ylabel='Unknown→Yes 与 Unknown→No 的更新方向余弦',ylim=(-1,1));ax.legend();fig.tight_layout();savefig(fig,dest/'figures/polarity_updates')
    table='\n'.join(f"| {r['case_id']} | {r['question']} | {r['unknown_top']} | {r['yes_top']} | {r['no_top']} |" for r in rows)
    (dest/'RESULTS.md').write_text(f'''# 阶段17：模型是否区分“有”和“没有”？

## 方法

在新24例中，各选一个距中间轮最近的单字段二元证据组。固定223问题和其他答案，将来源Yes改为No，与同字段Unknown比较。Yes和Unknown复用自然观测，No为新增反事实；全部选择只依据字段类型与轮次。Yes/No同token长度：{summary['same_length_cases']}/24。反事实未设置最终疾病标签，不评价其诊断正确率。

## 结果

- Yes与No使49病首选不同：{fmt(summary['metrics']['yes_no_switch'])}。
- Yes/No分布JS：{fmt(summary['metrics']['yes_no_js'],False)}。
- 第21层外部读出首选随Yes/No改变：{fmt(summary['metrics']['probe21_yes_no_switch'])}；第28层：{fmt(summary['metrics']['probe28_yes_no_switch'])}。
- 第21层完整状态中，Unknown→Yes与Unknown→No的更新方向余弦：{fmt(summary['metrics']['state_cosine21'],False)}；第28层：{fmt(summary['metrics']['state_cosine28'],False)}。

![取值方向与内部更新](figures/polarity_updates.png)

更新方向同向并不自动证明模型忽略否定，因为两者都包含“未知变为已知”的共同变化。输出与读出首选是否区分Yes/No、两个条件分别转向什么疾病，需要同时查看。相同首选也不代表完整分布相同。

## 全部病例

| 病例 | 被修改的问题 | Unknown首选 | Yes首选 | No首选 |
|---|---|---|---|---|
{table}

[逐病例指标](case_results.csv) · [逐层更新](layer_updates.csv) · [精确汇总](summary.json)
''')
    print(json.dumps(summary['metrics'],ensure_ascii=False),flush=True)
if __name__=='__main__':main()
