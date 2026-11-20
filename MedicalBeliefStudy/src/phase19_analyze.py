"""Presentation follow-up with no outcome-based case selection."""
import collections,json
import numpy as np
import matplotlib.pyplot as plt
from phase14_analyze import ROOT,RUN,cases,norm
from analyze_stages import setup,savefig,ci,fmt,csvwrite,dump
from phase15_analyze import permutation_p
def main():
    setup();run=RUN/'presentation';assert (run/'completion.json').exists();dest=ROOT/'results/19_presentation_mechanism';(dest/'figures').mkdir(parents=True,exist_ok=True);_,test=cases();test=[c for c in test if c['deep_capture']];diseases=json.loads((RUN/'manifest.json').read_text())['candidate_diseases'];h=np.load(ROOT/'results/14_fixed_panel/training_heads.npz');classes=h['classes'].tolist();rows=[]
    for c in test:
        cid=c['case_id'];T=len(c['orders']['base']);gi=diseases.index(c['gold_disease']);yi=classes.index(c['gold_disease'])
        for condition in ['public_order','known_first','known_last','compact']:
            p=RUN/'observations'/f'{cid}_panel_base_t{T:02d}.json' if condition=='public_order' else run/f'{cid}_{condition}.json';r=json.loads(p.read_text());q=np.array(r['q_sequence'])
            with np.load(RUN/r['state_file']) as a:
                X=norm(a['residual_stages'][:,4].astype(float));att=a['attention_by_group'].astype(float);counts=np.bincount(a['token_groups']);known=float(att[20:,:,3:5].sum(-1).mean());tokens=int(counts[3:5].sum());unk=float(att[20:,:,5].mean()) if att.shape[-1]>5 else 0.
            s=np.einsum('ld,ldc->lc',X-h['center_panel'],h['weights_panel_0.1'])+h['bias']
            sub=[diseases.index(d) for d in classes]
            rows.append(dict(case_id=cid,condition=condition,gold=c['gold_disease'],prediction=diseases[q.argmax()],correct=bool(q.argmax()==gi),native24_correct=bool(q[sub].argmax()==yi),gold_support=float(q[gi]),gold_logp=float(r['log_probability'][gi]),probe21_correct=bool(s[20].argmax()==yi),probe28_correct=bool(s[27].argmax()==yi),input_tokens=r['input_tokens'],known_attention=known,known_attention_per_token=known/max(tokens,1),unknown_attention=unk))
    summary={'cases':24,'conditions':{},'exploratory_followup':True,'api_cost_usd':0}
    for condition in ['public_order','known_first','known_last','compact']:
        rs=[r for r in rows if r['condition']==condition];summary['conditions'][condition]={k:ci([r[k] for r in rs]) for k in ['correct','native24_correct','gold_support','probe21_correct','probe28_correct','known_attention','known_attention_per_token','unknown_attention']};summary['conditions'][condition]['prediction_counts']=dict(collections.Counter(r['prediction'] for r in rs));summary['conditions'][condition]['mean_tokens']=float(np.mean([r['input_tokens'] for r in rs]))
    lookup={(r['case_id'],r['condition']):r for r in rows};paired=[]
    for c in test:
        cid=c['case_id'];a=lookup[cid,'known_last'];b=lookup[cid,'known_first'];base=lookup[cid,'public_order'];compact=lookup[cid,'compact']
        paired.append(dict(case_id=cid,last_minus_first_accuracy=float(a['correct'])-float(b['correct']),last_minus_first_gold_support=a['gold_support']-b['gold_support'],last_minus_first_known_attention=a['known_attention']-b['known_attention'],last_first_same_tokens=a['input_tokens']==b['input_tokens'],compact_minus_public_accuracy=float(compact['correct'])-float(base['correct'])))
    summary['paired']={k:ci([r[k] for r in paired]) for k in paired[0] if k!='case_id'};summary['last_minus_first_accuracy_p']=permutation_p([r['last_minus_first_accuracy'] for r in paired]);summary['last_minus_first_support_p']=permutation_p([r['last_minus_first_gold_support'] for r in paired])
    candidate_rows=[]
    for c in test:
        cid=c['case_id'];T=len(c['orders']['base'])
        for condition,baseview in [('public_24','panel'),('append_24','append')]:
            r=json.loads((run/f'{cid}_{condition}.json').read_text());local=r['candidate_diseases'];pred=local[np.argmax(r['q_sequence'])];base=json.loads((RUN/'observations'/f'{cid}_{baseview}_base_t{T:02d}.json').read_text());sub=[diseases.index(d) for d in classes];rank=classes[np.array(base['q_sequence'])[sub].argmax()]
            candidate_rows.append(dict(case_id=cid,condition=condition,gold=c['gold_disease'],prompt24_prediction=pred,rerank49_to24_prediction=rank,prompt24_correct=pred==c['gold_disease'],rerank49_to24_correct=rank==c['gold_disease']))
    summary['candidate_prompt_control']={condition:{'prompt24_accuracy':ci([r['prompt24_correct'] for r in candidate_rows if r['condition']==condition]),'rerank49_to24_accuracy':ci([r['rerank49_to24_correct'] for r in candidate_rows if r['condition']==condition]),'paired_accuracy_gain':ci([float(r['prompt24_correct'])-float(r['rerank49_to24_correct']) for r in candidate_rows if r['condition']==condition])} for condition in ['public_24','append_24']}
    csvwrite(dest/'candidate_prompt_controls.csv',candidate_rows)
    dump(dest/'summary.json',summary);csvwrite(dest/'case_results.csv',rows);csvwrite(dest/'paired_cases.csv',paired)
    fig,axs=plt.subplots(1,2,figsize=(11,4.8));labels=['原公开字段顺序','已知资料放前面','已知资料放后面','只保留已知资料'];keys=list(summary['conditions'])
    for key,label in [('native24_correct','模型限制24病首选'),('probe28_correct','第28层24病读出')]:
        vals=[summary['conditions'][k][key]['mean'] for k in keys];axs[0].plot(range(4),vals,marker='o',label=label)
    axs[0].set(xticks=range(4),xticklabels=labels,ylim=(0,1),ylabel='同24病例准确率');axs[0].tick_params(axis='x',labelrotation=20);axs[0].legend(fontsize=8)
    vals=[summary['conditions'][k]['known_attention']['mean'] for k in keys];axs[1].bar(range(4),vals);axs[1].set(xticks=range(4),xticklabels=labels,ylabel='第21—28层诊断位置对已知问答的注意力');axs[1].tick_params(axis='x',labelrotation=20);fig.tight_layout();savefig(fig,dest/'figures/positions_and_diagnosis')
    table='\n'.join(f"| {label} | {fmt(summary['conditions'][k]['correct'])} | {fmt(summary['conditions'][k]['probe28_correct'])} | {fmt(summary['conditions'][k]['known_attention'])} |" for k,label in zip(keys,labels))
    (dest/'RESULTS.md').write_text(f'''# 阶段19：有信息，却在什么位置影响诊断？

## 方法

由新24例固定问卷的输出集中现象触发的探索性追加。对全部预定24例，不筛选失败病例。known_first与known_last含相同223问题、相同所有答案与候选，仅改变已知问答所在位置；compact删去Unknown行，保留全部已知事实与原字段顺序。首选准确率与内部读出分别报告，24病读出与49病首选的数值不作直接差值。

## 结果

| 呈现方式 | 模型49病终点命中 | 原问卷训练头的第28层24病读出 | 已知问答注意力总量 |
|---|---|---|---|
{table}

![证据位置与诊断](figures/positions_and_diagnosis.png)

相同全部问题与答案，已知资料放后面减放前面的准确率差：{fmt(summary['paired']['last_minus_first_accuracy'])}；标签支持差：{fmt(summary['paired']['last_minus_first_gold_support'],False)}。同token长度病例比例：{fmt(summary['paired']['last_first_same_tokens'])}。两个配对p值为探索性未多重校正结果，见summary。

已知资料位置的改变是输入层面的配对干预；注意力变化是同时观察到的量，不能单独指定某个头的医学因果作用。compact同时减少未知问题内容和长度，不能只归因于其中一个因素。内部读出头不在新条件重新拟合，体现跨呈现迁移而非每个条件单独训练后的最好结果。

## 提示候选数的补充控制

真正把提示列表改为24病，而非对原49病分数事后重排：固定问卷命中{fmt(summary['candidate_prompt_control']['public_24']['prompt24_accuracy'])}，原49提示限制24类重排为{fmt(summary['candidate_prompt_control']['public_24']['rerank49_to24_accuracy'])}；追加式命中{fmt(summary['candidate_prompt_control']['append_24']['prompt24_accuracy'])}，原49提示重排为{fmt(summary['candidate_prompt_control']['append_24']['rerank49_to24_accuracy'])}。该对照控制了候选提示范围，仍没有给予原模型与分类器相同的监督训练。[逐例候选控制](candidate_prompt_controls.csv)

[全部病例](case_results.csv) · [配对差值](paired_cases.csv) · [精确汇总](summary.json)
''');print(json.dumps(summary,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
