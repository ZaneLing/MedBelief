"""Patient-held-out true-disease decoding, cross-interface controls and text baseline."""
from pathlib import Path
import hashlib,json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import RidgeClassifier
import matplotlib.pyplot as plt
from analyze_stages import setup,savefig,ci,fmt,csvwrite,dump,winner
ROOT=Path(__file__).resolve().parents[1]
def normalize(x):return x/np.maximum(np.linalg.norm(x,axis=-1,keepdims=True),1e-12)
def main():
    setup();run=ROOT/'runs/structured_names_v1';assert (run/'completion.json').exists();dest=ROOT/'results/11_disease_information';(dest/'figures').mkdir(parents=True,exist_ok=True)
    cases=[json.loads(s) for s in (ROOT/'data/full49_v1/cases.private.jsonl').read_text().splitlines()];classes=sorted({c['gold_disease'] for c in cases});assert len(classes)==24
    ids=[c['case_id'] for c in cases];y=np.array([classes.index(c['gold_disease']) for c in cases]);fold=np.zeros(120,int)
    for disease in classes:
        idx=[i for i,c in enumerate(cases) if c['gold_disease']==disease];idx.sort(key=lambda i:hashlib.sha256(('disease-probe-v1:'+ids[i]).encode()).hexdigest())
        for j,i in enumerate(idx):fold[i]=j
    views={k:[] for k in ['name','code0','code16']};native=[];texts=[];deepstates={};deepnative={};all_diseases=json.loads((run/'manifest.json').read_text())['candidate_diseases'];sub=[all_diseases.index(d) for d in classes]
    def case_text(c,t):
        order=[c['initial_question_group']]+c['orders']['base'][:t]
        return f"Age {c['age']}; sex {c['sex']}. "+' '.join(v['question_en']+' '+v['answer_en'] for g in order for v in c['explicit_evidence_groups'][g])
    for c in cases:
        cid=c['case_id'];T=len(c['orders']['base'])
        for view,folder,m in [('name',run,0),('code0',ROOT/'runs/full49_v1',0),('code16',ROOT/'runs/full49_v1',16)]:
            r=json.loads((folder/'observations'/f'{cid}_base_t{T:02d}_m{m}.json').read_text())
            with np.load(folder/r['state_file']) as a:views[view].append(a['residual_stages'][:,4].astype(float))
            if view=='name':native.append(np.array(r['q_sequence'])[sub])
        texts.append(case_text(c,T))
        if c['deep_capture']:
            states=[];nq=[]
            for t in range(T+1):
                r=json.loads((run/'observations'/f'{cid}_base_t{t:02d}_m0.json').read_text())
                with np.load(run/r['state_file']) as a:states.append(a['residual_stages'][:,4].astype(float))
                nq.append(np.array(r['q_sequence'])[sub])
            deepstates[cid]=normalize(np.array(states))
            deepnative[cid]=np.array(nq)
    views={k:normalize(np.array(v)) for k,v in views.items()};native=np.array(native);native_pred=winner(native)
    conditions={'name_to_name':('name','name'),'code0_to_code0':('code0','code0'),'code0_to_code16':('code0','code16'),'code0_to_name':('code0','name')}
    alphas=[.01,.1,1.];predictions={str(alpha):{k:np.full((120,28),-1,int) for k in conditions} for alpha in alphas}
    null=np.full((100,120,28),-1,int);textpred=np.full(120,-1,int);trajectory=[];prefix_baselines=[];rng=np.random.default_rng(20261118)
    name_weights=np.zeros((5,28,2048,24));name_centers=np.zeros((5,28,2048));prefix_scores={cid:np.zeros((len(states),28,24)) for cid,states in deepstates.items()}
    for f in range(5):
        train=np.flatnonzero(fold!=f);test=np.flatnonzero(fold==f);targets=np.eye(24)[y[train]];ym=targets.mean(0);yc=targets-ym
        perms=np.stack([np.eye(24)[rng.permutation(y[train])]-ym for _ in range(100)])
        vectorizer=TfidfVectorizer(ngram_range=(1,2),min_df=1,lowercase=True,token_pattern=r'(?u)\b\w+\b');tx=vectorizer.fit_transform([texts[i] for i in train]);te=vectorizer.transform([texts[i] for i in test]);baseline=RidgeClassifier(alpha=1.,solver='lsqr');baseline.fit(tx,y[train]);textpred[test]=baseline.predict(te)
        for i in test:
            cid=ids[i]
            if cid not in deepstates:continue
            c=cases[i];T=len(c['orders']['base']);bp=baseline.predict(vectorizer.transform([case_text(c,t) for t in range(T+1)]));npred=winner(deepnative[cid])
            for t in range(T+1):prefix_baselines.append({'case_id':cid,'round':t,'gold':classes[y[i]],'text_prediction':classes[bp[t]],
                'native24_prediction':classes[npred[t]] if npred[t]>=0 else 'TIED','text_correct':bool(bp[t]==y[i]),'native24_correct':bool(npred[t]==y[i])})
        for l in range(28):
            for source in ['name','code0']:
                X=views[source][train,l];center=X.mean(0);X=X-center;gram=X@X.T
                for alpha in alphas:
                    inverse_targets=np.linalg.solve(gram+alpha*np.eye(len(train)),yc)
                    weights=X.T@inverse_targets
                    for condition,(src,tgt) in conditions.items():
                        if src!=source:continue
                        scores=(views[tgt][test,l]-center)@weights+ym;predictions[str(alpha)][condition][test,l]=winner(scores)
                    if source=='name' and alpha==.1:
                        name_weights[f,l]=weights;name_centers[f,l]=center
                        inverse=np.linalg.solve(gram+alpha*np.eye(len(train)),np.eye(len(train)))
                        transfer=(views['name'][test,l]-center)@X.T@inverse
                        randomscores=np.einsum('ij,rjk->rik',transfer,perms,optimize=True)+ym;null[:,test,l]=winner(randomscores)
                        for i in test:
                            cid=ids[i]
                            if cid not in deepstates:continue
                            scores=(deepstates[cid][:,l]-center)@weights+ym;pp=winner(scores)
                            prefix_scores[cid][:,l]=scores
                            for t in range(len(scores)):
                                s=scores[t];target=y[i];rank=int(1+np.sum(s>s[target]));margin=float(s[target]-np.max(np.delete(s,target)))
                                trajectory.append({'case_id':cid,'fold':f,'round':t,'layer':l+1,'gold':classes[target],'predicted_disease':classes[pp[t]] if pp[t]>=0 else 'TIED','gold_rank':rank,'gold_margin':margin})
        print(f'Completed disease probe fold {f+1}/5',flush=True)
    primary=predictions['0.1'];acc={k:(v==y[:,None]).mean(0) for k,v in primary.items()};nullacc=(null==y[None,:,None]).mean(1)
    case_rows=[]
    for i,c in enumerate(cases):
        for l in range(28):case_rows.append({'case_id':ids[i],'family':c['family'],'fold':int(fold[i]),'gold':classes[y[i]],'layer':l+1,
            **{k:classes[v[i,l]] if v[i,l]>=0 else 'TIED' for k,v in primary.items()},'name_native_restricted24_correct':bool(native_pred[i]==y[i]),'text_baseline_correct':bool(textpred[i]==y[i])})
    csvwrite(dest/'heldout_case_predictions.csv',case_rows);csvwrite(dest/'heldout_trajectory_readouts.csv',trajectory);csvwrite(dest/'prefix_baselines.csv',prefix_baselines)
    timing=[]
    for c in cases:
        if not c['deep_capture']:continue
        cid=c['case_id'];base=sorted([r for r in prefix_baselines if r['case_id']==cid],key=lambda r:r['round']);native_correct=np.array([r['native24_correct'] for r in base]);text_correct=np.array([r['text_correct'] for r in base])
        for l in [21,28]:
            rr=sorted([r for r in trajectory if r['case_id']==cid and r['layer']==l],key=lambda r:r['round']);correct=np.array([r['predicted_disease']==r['gold'] for r in rr])
            first=lambda vals:next((i for i,v in enumerate(vals) if v),len(vals))
            timing.append({'case_id':cid,'layer':l,'first_probe_correct':first(correct),'first_native24_correct':first(native_correct),'first_text_correct':first(text_correct),
               'probe_correct_rate':float(correct.mean()),'native24_correct_rate':float(native_correct.mean()),'text_correct_rate':float(text_correct.mean()),
               'probe_earlier_than_native':bool(first(correct)<first(native_correct)),'probe_later_than_native':bool(first(correct)>first(native_correct))})
    csvwrite(dest/'prefix_case_metrics.csv',timing)
    np.savez_compressed(dest/'heldout_predictions.npz',case_ids=np.array(ids),gold=y,fold=fold,classes=np.array(classes),native_pred=native_pred,text_pred=textpred,null_pred=null,**{f'{a}_{k}':v for a,conditions_ in predictions.items() for k,v in conditions_.items()})
    np.savez_compressed(dest/'heldout_name_readouts.npz',weights=name_weights,train_centers=name_centers,bias=np.full(24,1/24),classes=np.array(classes),case_ids=np.array(ids),fold=fold)
    np.savez_compressed(dest/'heldout_prefix_class_scores.npz',classes=np.array(classes),**prefix_scores)
    summary={'cases':120,'diseases':24,'folds':5,'alpha':.1,'native_restricted24_accuracy':ci(list(native_pred==y)),'text_accuracy':ci(list(textpred==y)),
             'layers':{str(l):{k:ci(list(v[:,l-1]==y)) for k,v in primary.items()} for l in [7,14,21,28]},
             'name_layer28_minus_native':ci((primary['name_to_name'][:,27]==y).astype(float)-(native_pred==y)),
             'name_layer28_minus_text':ci((primary['name_to_name'][:,27]==y).astype(float)-(textpred==y)),
             'layer_accuracy':{k:v.tolist() for k,v in acc.items()},'null_mean_accuracy':nullacc.mean(0).tolist(),
             'name_best_layer_exploratory':int(acc['name_to_name'].argmax()+1),'name_best_accuracy_exploratory':float(acc['name_to_name'].max()),
             'permutation_p_max_over_28_layers':float((1+np.sum(nullacc.max(1)>=acc['name_to_name'].max()))/101),
             'alpha_sensitivity':{a:{k:float((v[:,27]==y).mean()) for k,v in conds.items()} for a,conds in predictions.items()}}
    summary['prefixes']={str(l):{k:ci([r[k] for r in timing if r['layer']==l]) for k in ['probe_correct_rate','native24_correct_rate','text_correct_rate','probe_earlier_than_native','probe_later_than_native']} for l in [21,28]}
    dump(dest/'summary.json',summary)
    manifest={'protocol_sha256':hashlib.sha256((ROOT/'protocol/DISEASE_INFORMATION_PROBE.md').read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'name_manifest_sha256':hashlib.sha256((run/'manifest.json').read_bytes()).hexdigest(),'api_cost_usd':0};dump(dest/'manifest.json',manifest)
    fig,ax=plt.subplots(figsize=(10,5.5))
    for k,label in [('name_to_name','Name → name'),('code0_to_code0','Code 0 → code 0'),('code0_to_code16','Code 0 → code 16'),('code0_to_name','Code 0 → name')]:ax.plot(range(1,29),acc[k],label=label)
    ax.plot(range(1,29),nullacc.mean(0),color='gray',ls=':',label='Shuffled training labels');ax.axhline(np.mean(textpred==y),color='black',ls='--',label='Raw-case text baseline');ax.axhline(np.mean(native_pred==y),color='darkred',ls='-.',label='Native name score, restricted to 24')
    ax.set(xlabel='Layer',ylabel='Held-out patient accuracy (24 diseases)',ylim=(0,1));ax.legend(fontsize=9);fig.tight_layout();savefig(fig,dest/'figures/heldout_disease_information')
    fig,axes=plt.subplots(2,2,figsize=(11,8));chosen=[c for c in cases if c['deep_capture']][:4]
    for ax,c in zip(axes.flat,chosen):
        T=len(c['orders']['base']);mat=np.zeros((28,T+1))
        for r in trajectory:
            if r['case_id']==c['case_id']:mat[r['layer']-1,r['round']]=r['gold_rank']
        im=ax.imshow(mat,origin='lower',aspect='auto',vmin=1,vmax=24,cmap='viridis_r');ax.set(title=c['gold_disease'],xlabel='Evidence round',ylabel='Layer')
    fig.colorbar(im,ax=axes.ravel().tolist(),label='Ground-truth rank under held-out linear readout',shrink=.75);fig.subplots_adjust(right=.82,hspace=.4);savefig(fig,dest/'figures/heldout_readout_examples')
    table='\n'.join(f'| {l} | '+ ' | '.join(fmt(summary['layers'][str(l)][k]) for k in conditions)+' |' for l in [7,14,21,28])
    (dest/'RESULTS.md').write_text(f'''# 阶段11：从未见患者的内部状态识别疾病

## 问题与设计

**模型内部到底有没有能用于识别疾病的信息？** 用其他患者训练简单线性读出器，再测试未见患者。120例、24病种各5例，按病种固定五折：每折96例训练、24例测试。同一患者所有轮次和接口始终隔离。目标为源疾病标签，不是模型自己的最终输出。

每层诊断位置状态先逐向量L2归一化、按训练均值中心化，岭分类器主正则0.1；0.01和1另作敏感性检查。病例文本基线用原始问答TF-IDF与线性分类，词表只在训练患者拟合，不含候选列表。100次训练标签置换作为负对照。所有模型和数据均冻结；本阶段训练的是外部读出器。

## 结果

| 层 | 名称→名称 | 编码0→编码0 | 编码0→编码16 | 编码0→名称 |
|---|---|---|---|---|
{table}

原始病例文本分类准确率：{fmt(summary['text_accuracy'])}。模型名称评分在相同24类中的准确率：{fmt(summary['native_restricted24_accuracy'])}。名称第28层读出减去该模型输出基线的配对差为{fmt(summary['name_layer28_minus_native'])}，减去文本基线的差为{fmt(summary['name_layer28_minus_text'])}。

探索性最高名称读出准确率出现在第{summary['name_best_layer_exploratory']}层，为{summary['name_best_accuracy_exploratory']:.1%}；按28层最大值与100次标签置换比较，p={summary['permutation_p_max_over_28_layers']:.4f}。正文优先使用预定的第7/14/21/28层，最高层不作为事先选定结果。

![未见患者读出](figures/heldout_disease_information.png)

## 从终点读出回到逐轮轨迹

将每折只用其他患者终点训练的读出器，应用于同一折深描病例的每一轮，得到每层的疾病排序。下图展示预先哈希排序中的前4例；完整24例读出数据均保留。排名1表示外部线性读出器可以把源标签排在首位，不等于模型此时作出了该诊断。

在固定24例全部轮次上，先病例内平均，第21层读出标签命中为{fmt(summary['prefixes']['21']['probe_correct_rate'])}，同24类的模型名称评分为{fmt(summary['prefixes']['21']['native24_correct_rate'])}，文本分类基线为{fmt(summary['prefixes']['21']['text_correct_rate'])}。第21层读出比模型评分更早把最终标签排首位的病例比例为{fmt(summary['prefixes']['21']['probe_earlier_than_native'])}，更晚的为{fmt(summary['prefixes']['21']['probe_later_than_native'])}。这衡量标签信息可读出的时间，不给中间轮制造医学标准答案。

![逐轮疾病排名](figures/heldout_readout_examples.png)

## 解释

这个实验区分“内部状态能否提供疾病信息”和“模型最终选了什么”。读出器可能从表示中重新学会诊断规则，尤其当文本基线也能很好分类时；不能仅凭高读出准确率说模型早已知道答案。跨未见患者、跨编码或接口的迁移，决定可读出信息是否稳定。模型实际使用什么，仍由阶段10的内部干预判断。

区间为固定五折预测上的病例bootstrap，不含重新训练的不确定性。24类读出只与同24类的模型评分直接比较；49候选结果在阶段09单列。

[逐患者预测](heldout_case_predictions.csv) · [逐层逐轮疾病排名](heldout_trajectory_readouts.csv) · [精确结果与正则敏感性](summary.json)
''')
    print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
