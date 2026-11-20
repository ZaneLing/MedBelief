"""Independent test-patient decoding, matched representations and trajectory atlas."""
import argparse,collections,hashlib,json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import RidgeClassifier
from scipy.stats import spearmanr
from analyze_stages import ROOT,setup,savefig,ci,fmt,csvwrite,dump,js

RUN=ROOT/'runs/belief_v2';DEST=ROOT/'results/14_fixed_panel'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def norm(x):return x/np.maximum(np.linalg.norm(x,axis=-1,keepdims=True),1e-12)
def cases():return [[json.loads(s) for s in (ROOT/f'data/{v}/cases.private.jsonl').read_text().splitlines()] for v in ['full49_v1','belief_v2']]
def record(c,view,t=None,order='base',train=False):
    t=len(c['orders']['base']) if t is None else t;cid=c['case_id']
    if train and view=='append':base=ROOT/'runs/structured_names_v1';p=base/'observations'/f'{cid}_base_t{t:02d}_m0.json'
    else:base=RUN;p=base/'observations'/f'{cid}_{view}_{order}_t{t:02d}.json'
    return base,json.loads(p.read_text())
def getstates(c,view,t=None,train=False):
    base,r=record(c,view,t,train=train)
    with np.load(base/r['state_file']) as a:x=a['residual_stages'][:,4].astype(float)
    return norm(x),r
def train_heads():
    DEST.mkdir(parents=True,exist_ok=True);train,_=cases();classes=sorted({c['gold_disease'] for c in train});y=np.array([classes.index(c['gold_disease']) for c in train]);Y=np.eye(24)[y];bias=Y.mean(0);weights={};centers={};snap={}
    for view in ['append','panel']:
        X=np.array([getstates(c,view,train=True)[0] for c in train]);center=X.mean(0);Z=X-center
        for alpha in [.01,.1,1.]:
            W=np.array([Z[:,l].T@np.linalg.solve(Z[:,l]@Z[:,l].T+alpha*np.eye(120),Y-bias) for l in range(28)])
            weights[f'{view}_{alpha}']=W
        centers[view]=center;snap[view]=X
    np.savez_compressed(DEST/'training_heads.npz',classes=np.array(classes),bias=bias,training_ids=np.array([c['case_id'] for c in train]),
        **{f'weights_{k}':v for k,v in weights.items()},**{f'center_{k}':v for k,v in centers.items()})
    dump(DEST/'training_manifest.json',{'training_cases':120,'training_source':'previous full49_v1 validation cohort; test patients never used for fitting',
        'input_case_sha256':sha(ROOT/'data/full49_v1/cases.private.jsonl'),'source_sha256':sha(__file__),'heads_sha256':sha(DEST/'training_heads.npz'),'layers':list(range(1,29)),'alphas':[.01,.1,1.]})
    print('Fitted and saved old-patient-only readout heads.',flush=True)
def text(c,questions=False):
    return ' '.join(v['question_en']+('' if questions else ' '+v['answer_en']) for g in [c['initial_question_group']]+c['orders']['base'] for v in c['explicit_evidence_groups'][g])
def structured(c,presence=False):
    return {v['evidence_id']+'='+('recorded' if presence else str(value)):1 for a in c['explicit_evidence_groups'].values() for v in a for value in (['recorded'] if presence else v['values'])}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--train-only',action='store_true');args=ap.parse_args();train_heads()
    if args.train_only:return
    assert (RUN/'completion.json').exists();setup();(DEST/'figures').mkdir(exist_ok=True);(DEST/'cases').mkdir(exist_ok=True)
    train,test=cases();diseases=json.loads((RUN/'manifest.json').read_text())['candidate_diseases'];classes=sorted({c['gold_disease'] for c in train});sub=[diseases.index(d) for d in classes];y=np.array([classes.index(c['gold_disease']) for c in test]);ytrain=np.array([classes.index(c['gold_disease']) for c in train]);gold49=np.array([diseases.index(c['gold_disease']) for c in test]);heads=np.load(DEST/'training_heads.npz')
    native={};endstates={};pred={};records={};endrows=[];textpred={}
    for name in ['full','questions','structured_values','presence']:
        if name in ['full','questions']:
            v=TfidfVectorizer(ngram_range=(1,2),token_pattern=r'(?u)\b\w+\b');X=v.fit_transform([text(c,name=='questions') for c in train]);Z=v.transform([text(c,name=='questions') for c in test])
        else:
            v=DictVectorizer();X=v.fit_transform([structured(c,name=='presence') for c in train]);Z=v.transform([structured(c,name=='presence') for c in test])
        m=RidgeClassifier(alpha=1,solver='lsqr');m.fit(X,ytrain);textpred[name]=m.predict(Z)
    for view in ['append','panel']:
        pairs=[getstates(c,view) for c in test];X=np.array([v[0] for v in pairs]);rr=[v[1] for v in pairs];records[view]=rr;endstates[view]=X;native[view]=np.array([r['q_sequence'] for r in rr])
        for alpha in [.01,.1,1.]:
            S=np.einsum('nld,ldk->nlk',X-heads[f'center_{view}'],heads[f'weights_{view}_{alpha}'])+heads['bias'];pred[f'{view}_{alpha}']=S.argmax(-1)
        for i,c in enumerate(test):
            q=native[view][i];ref=np.array([c['reference_differential'].get(d,0) for d in diseases]);endrows.append(dict(case_id=c['case_id'],view=view,family=c['family'],gold=c['gold_disease'],native49=diseases[q.argmax()],native24=classes[q[sub].argmax()],correct49=bool(q.argmax()==gold49[i]),correct24=bool(q[sub].argmax()==y[i]),gold_support=q[gold49[i]],reference_js=float(js(q,ref)),generated_disease=rr[i]['generated_disease'],sequence_mass=rr[i]['sequence_probability_mass'],input_tokens=rr[i]['input_tokens'],probe21=classes[pred[f'{view}_0.1'][i,20]],probe28=classes[pred[f'{view}_0.1'][i,27]]))
    summary={'training_cases':120,'test_cases':120,'classes':classes,'source':'DDxPlus official test split; same synthetic generator as training source','endpoints':{},'text_baselines':{k:ci(list(v==y)) for k,v in textpred.items()},'deep':{},'api_cost_usd':0}
    for view in ['append','panel']:
        q=native[view];pred49=q.argmax(-1);pred24=q[:,sub].argmax(-1);rs=[r for r in endrows if r['view']==view]
        summary['endpoints'][view]={'native49':ci(list(pred49==gold49)),'native24':ci(list(pred24==y)),
            'layer_accuracy':(pred[f'{view}_0.1']==y[:,None]).mean(0).tolist(),
            'layers':{str(l):ci(list(pred[f'{view}_0.1'][:,l-1]==y)) for l in [7,14,21,28]},
            'alpha_sensitivity_layer28':{str(a):float(np.mean(pred[f'{view}_{a}'][:,27]==y)) for a in [.01,.1,1.]},
            'probe28_minus_native24':ci((pred[f'{view}_0.1'][:,27]==y).astype(float)-(pred24==y)),
            'reference_js':ci([r['reference_js'] for r in rs]),'greedy_correct':ci([r['generated_disease']==c['gold_disease'] for r,c in zip(rs,test)]),
            'mean_input_tokens':float(np.mean([r['input_tokens'] for r in rs])),
            'canonical_mass_median':float(np.median([r['sequence_mass'] for r in rs])),
            'canonical_mass_below_point1':sum(r['sequence_mass']<.1 for r in rs),
            'generated_in_candidates':sum(r['generated_disease'] in diseases for r in rs),
            'sequence_vs_tokenmean_agreement':float(np.mean([np.argmax(r['q_sequence'])==np.argmax(r['q_token_mean']) for r in records[view]])),
            'reference_top_accuracy':ci([diseases[pred49[i]]==max(c['reference_differential'],key=c['reference_differential'].get) for i,c in enumerate(test)])}
    stratified=[]
    for view in ['append','panel']:
        for grouping in ['family','label_matches_reference_top']:
            labels=[c['family'] if grouping=='family' else str(c['gold_disease']==max(c['reference_differential'],key=c['reference_differential'].get)) for c in test]
            for label in sorted(set(labels)):
                idx=np.array([i for i,x in enumerate(labels) if x==label]);stratified.append(dict(view=view,grouping=grouping,group=label,cases=len(idx),native49_accuracy=float(np.mean(native[view][idx].argmax(-1)==gold49[idx])),native24_accuracy=float(np.mean(native[view][idx][:,sub].argmax(-1)==y[idx])),probe21_accuracy=float(np.mean(pred[f'{view}_0.1'][idx,20]==y[idx])),probe28_accuracy=float(np.mean(pred[f'{view}_0.1'][idx,27]==y[idx]))))
    summary['stratified']=stratified;csvwrite(DEST/'stratified_metrics.csv',stratified)
    summary['panel_minus_append_accuracy49']=ci((native['panel'].argmax(-1)==gold49).astype(float)-(native['append'].argmax(-1)==gold49))
    summary['presentation_switch']=ci(list(native['append'].argmax(-1)!=native['panel'].argmax(-1)))
    events=[];trajectories=[];case_metrics=[];scorepack={};statepack={};attentionrows=[]
    for c in [c for c in test if c['deep_capture']]:
        cid=c['case_id'];T=len(c['orders']['base']);yi=classes.index(c['gold_disease']);gi=diseases.index(c['gold_disease']);plotdata={}
        for view in ['append','panel']:
            pairs=[getstates(c,view,t) for t in range(T+1)];X=np.array([v[0] for v in pairs]);rr=[v[1] for v in pairs];q=np.array([r['q_sequence'] for r in rr]);S=np.einsum('tld,ldk->tlk',X-heads[f'center_{view}'],heads[f'weights_{view}_0.1'])+heads['bias'];P=S.argmax(-1);ranks=1+(S>S[:,:,yi,None]).sum(-1)
            scorepack[f'{cid}_{view}']=S.astype(np.float32);statepack[f'{cid}_{view}']=X.astype(np.float32);plotdata[view]=(q,ranks)
            dp=q[1:]-q[:-1];j=js(q[1:],q[:-1]);big=np.max(abs(dp),axis=-1)>=.5;switch=q[1:].argmax(-1)!=q[:-1].argmax(-1);correct=q.argmax(-1)==gi;readable=P[:,20]==yi
            internal=1-(X[1:]*X[:-1]).sum(-1);corr=[]
            for l in range(28):
                corr.append(float(spearmanr(internal[:,l],j).statistic) if np.ptp(internal[:,l])>1e-12 and np.ptp(j)>1e-12 else float('nan'))
            reg=any(correct[t-1] and not correct[t] for t in range(1,T+1))
            cm=dict(case_id=cid,view=view,updates=T,switches=int(switch.sum()),big_updates=int(big.sum()),switch_rate=float(switch.mean()),big_rate=float(big.mean()),any_switch=bool(switch.any()),any_big=bool(big.any()),label_regression=bool(reg),native24_prefix_accuracy=float(np.mean(q[:,sub].argmax(-1)==yi)),probe21_prefix_accuracy=float(readable.mean()),probe28_prefix_accuracy=float(np.mean(P[:,27]==yi)),native49_prefix_accuracy=float(correct.mean()),late_state_output_rho=float(np.nanmean(corr[20:])))
            case_metrics.append(cm)
            for t in range(T+1):
                trajectories.append(dict(case_id=cid,view=view,round=t,gold=c['gold_disease'],top=diseases[q[t].argmax()],gold_support=q[t,gi],probe21=classes[P[t,20]],probe28=classes[P[t,27]],gold_rank21=int(ranks[t,20]),gold_rank28=int(ranks[t,27])))
                if not t:continue
                old24=int(q[t-1,sub].argmax());new24=int(q[t,sub].argmax());ds=S[t,:,new24]-S[t,:,old24]-(S[t-1,:,new24]-S[t-1,:,old24])
                g=c['orders']['base'][t-1];typ='history' if all(v['is_antecedent'] for v in c['explicit_evidence_groups'][g]) else 'presentation_or_mixed'
                events.append(dict(case_id=cid,view=view,round=t,new_group=g,evidence_type=typ,previous_top=diseases[q[t-1].argmax()],current_top=diseases[q[t].argmax()],switch=bool(switch[t-1]),big=bool(big[t-1]),max_change=float(abs(dp[t-1]).max()),js=float(j[t-1]),delta_gold=float(dp[t-1,gi]),gold_support=float(q[t,gi]),internal21=float(internal[t-1,20]),internal28=float(internal[t-1,27]),native24_switch=bool(old24!=new24),probe21_supports_native24_change=bool(ds[20]>0) if old24!=new24 else None,probe28_supports_native24_change=bool(ds[27]>0) if old24!=new24 else None))
            # Attention is an observational summary, never a causal importance score.
            for t in [0,T//2,T]:
                base,rec=record(c,view,t)
                with np.load(base/rec['state_file']) as a:att=a['attention_by_group'].astype(float)
                for l in [7,14,21,28]:
                    for k,label in enumerate(rec['group_labels']):attentionrows.append(dict(case_id=cid,view=view,round=t,layer=l,group=label,mean_head_attention=float(att[l-1,:,k].mean())))
        fig,axs=plt.subplots(2,2,figsize=(12,8),layout='constrained')
        for vi,view in enumerate(['append','panel']):
            q,ranks=plotdata[view];chosen=sorted(set(q.argmax(-1).tolist()+[gi]));chosen=sorted(chosen,key=lambda d:-q[:,d].max())[:6]
            if gi not in chosen:chosen[-1]=gi
            for d in chosen:axs[0,vi].plot(range(T+1),q[:,d],marker='o',ms=3,lw=2 if d==gi else 1,label=diseases[d]+(' [label]' if d==gi else ''))
            axs[0,vi].set(title={'append':'逐条追加','panel':'固定问卷'}[view],xlabel='新增证据轮次',ylabel='49病名相对支持',ylim=(-.02,1.02));axs[0,vi].legend(fontsize=6)
            im=axs[1,vi].imshow(ranks.T,origin='lower',aspect='auto',extent=[-.5,T+.5,.5,28.5],vmin=1,vmax=24,cmap='viridis_r');axs[1,vi].set(xlabel='新增证据轮次',ylabel='模型层数',title='独立训练读出器中的最终标签排名')
        fig.colorbar(im,ax=axs[1,:].tolist(),label='排名（1最好；非概率）',shrink=.8);fig.suptitle(cid+' | '+c['gold_disease']);savefig(fig,DEST/'cases'/cid)
        tr=[r for r in trajectories if r['case_id']==cid];table='\n'.join(f"| {r['view']} | {r['round']} | {r['top']} | {r['gold_support']:.4f} | {r['probe21']} | {r['gold_rank21']} |" for r in tr)
        evidence='\n'.join(f"- 第{t}轮："+'；'.join(v['question_en']+' **'+v['answer_en']+'**' for v in c['explicit_evidence_groups'][g]) for t,g in enumerate([c['initial_question_group']]+c['orders']['base']))
        (DEST/'cases'/f'{cid}.md').write_text(f'# {cid}\n\n源标签：{c["gold_disease"]}。来源：DDxPlus test 第{c["source_row_zero_based"]}行（零起始）。\n\n![轨迹]({cid}.png)\n\n{evidence}\n\n| 条件 | 轮 | 模型首选 | 标签支持 | 第21层读出首选 | 标签读出排名 |\n|---|---|---|---:|---|---:|\n{table}\n')
    for view in ['append','panel']:
        cm=[r for r in case_metrics if r['view']==view];ee=[r for r in events if r['view']==view]
        summary['deep'][view]={'cases':len(cm),'updates':sum(r['updates'] for r in cm),'switch_events':sum(r['switch'] for r in ee),'big_events':sum(r['big'] for r in ee),
            **{k:ci([r[k] for r in cm]) for k in ['switch_rate','big_rate','any_switch','any_big','label_regression','native24_prefix_accuracy','probe21_prefix_accuracy','probe28_prefix_accuracy','late_state_output_rho']}}
    order=[];presence=[]
    for c in [c for c in test if c['deep_capture']]:
        _,b=record(c,'append');baseq=np.array(b['q_sequence'])
        for o in ['reverse','shuffle']:
            _,r=record(c,'append',order=o);q=np.array(r['q_sequence']);order.append(dict(case_id=c['case_id'],order=o,switched=bool(q.argmax()!=baseq.argmax()),js=float(js(q,baseq))))
        _,p=record(c,'panel');_,r=record(c,'presence');q=np.array(r['q_sequence']);presence.append(dict(case_id=c['case_id'],correct=bool(diseases[q.argmax()]==c['gold_disease']),switched=bool(q.argmax()!=np.argmax(p['q_sequence'])),js=float(js(q,p['q_sequence']))))
    summary['order']={o:ci([r['switched'] for r in order if r['order']==o]) for o in ['reverse','shuffle']};summary['presence_control']={k:ci([r[k] for r in presence]) for k in ['correct','switched','js']}
    csvwrite(DEST/'endpoint_cases.csv',endrows);csvwrite(DEST/'evidence_updates.csv',events);csvwrite(DEST/'prefix_trajectories.csv',trajectories);csvwrite(DEST/'case_metrics.csv',case_metrics);csvwrite(DEST/'attention_summary.csv',attentionrows);csvwrite(DEST/'order_cases.csv',order);csvwrite(DEST/'presence_cases.csv',presence)
    csvwrite(DEST/'text_baseline_cases.csv',[{'case_id':c['case_id'],'gold':c['gold_disease'],**{k:classes[v[i]] for k,v in textpred.items()}} for i,c in enumerate(test)])
    np.savez_compressed(DEST/'test_predictions.npz',classes=np.array(classes),case_ids=np.array([c['case_id'] for c in test]),gold=y,**pred,**{f'q_{k}':v for k,v in native.items()})
    np.savez_compressed(DEST/'prefix_readout_scores.npz',classes=np.array(classes),**scorepack);dump(DEST/'summary.json',summary)
    fig,ax=plt.subplots(figsize=(9,5))
    for view,label in [('append','逐条追加'),('panel','固定问卷')]:
        ax.plot(range(1,29),summary['endpoints'][view]['layer_accuracy'],label=label+'：内部读出');ax.axhline(summary['endpoints'][view]['native24']['mean'],ls='--',label=label+'：模型名称评分')
    ax.set(xlabel='层',ylabel='新120例准确率（统一24病）',ylim=(0,1));ax.legend();fig.tight_layout();savefig(fig,DEST/'figures/heldout_layers')
    tab='\n'.join(f"| {label} | {fmt(summary['endpoints'][v]['native49'])} | {fmt(summary['endpoints'][v]['native24'])} | {fmt(summary['endpoints'][v]['layers']['21'])} | {fmt(summary['endpoints'][v]['layers']['28'])} |" for v,label in [('append','逐条追加'),('panel','固定问卷')])
    deep='\n'.join(f"| {v} | {s['updates']} | {s['switch_events']} | {s['big_events']} | {fmt(s['label_regression'])} |" for v,s in summary['deep'].items())
    (DEST/'RESULTS.md').write_text(f'''# 阶段14：在新病例与固定问卷中追踪医学判断

## 方法

旧120例训练，新120例独立测试；24病种各5例，6疾病组。测试来自DDxPlus另一数据划分，与旧病例无完全相同事实集合，但仍属同一模拟生成来源。预定24例追踪全部轮次。固定问卷包含公开字典全部223个字段，已知值按源记录填写，缺失保持未知。与相同病例的原追加式提示配对；固定问卷同时改变长度、位置和未知信息展示，效果不能单独归因于某一因素。

## 终点表现

| 呈现 | 模型49病 | 模型限制24病 | 第21层24病读出 | 第28层24病读出 |
|---|---|---|---|---|
{tab}

读出器仅在旧120例上训练，模型参数冻结；alpha=.1，所有28层均报告。区间为固定训练头后的测试病例bootstrap，不含训练集重采样不确定性。

![独立病例逐层读出](figures/heldout_layers.png)

## 每条证据如何改变判断

| 呈现 | 新增证据次数 | 首选改变次数 | 任一病分数变化≥50个百分点 | 曾命中标签后偏离的病例比例 |
|---|---:|---:|---:|---|
{deep}

这里的分数是49条完整病名序列之间的相对支持，不是患者患病概率。最终标签不是每轮标准答案；新增证据也不必使标签支持单调增加。内部热图是独立读出器排名，不能解释为各层的校准疾病概率。

## 内容与呈现对照

固定问卷与追加式终点首选不同：{fmt(summary['presentation_switch'])}。追加式相同事实逆序后首选改变：{fmt(summary['order']['reverse'])}；乱序：{fmt(summary['order']['shuffle'])}。

24例终点只保留哪些答案已记录、删去具体值后，模型49病命中：{fmt(summary['presence_control']['correct'])}；相对完整问卷首选改变：{fmt(summary['presence_control']['switched'])}。固定问题并未去掉“哪些答案已知”的信息，这个对照用于识别记录结构的残留影响。单独的文本基线继续保留在附表，不把高分类准确率当成复杂医学推理。

## 交付

[24例完整轨迹与证据](CASE_ATLAS.md) · [终点逐病例](endpoint_cases.csv) · [每次证据更新](evidence_updates.csv) · [逐轮读出](prefix_trajectories.csv) · [注意力观察](attention_summary.csv) · [精确汇总](summary.json)
''')
    (DEST/'CASE_ATLAS.md').write_text('# 新病例逐轮图谱\n\n上排为最终输出，下面为28层读出中的源标签排名。每例均展示两种呈现方式和完整证据。\n\n'+'\n'.join(f'- [{c["case_id"]}：{c["gold_disease"]}](cases/{c["case_id"]}.md)' for c in test if c['deep_capture'])+'\n')
    print(json.dumps({k:summary[k] for k in ['endpoints','deep','text_baselines']},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
