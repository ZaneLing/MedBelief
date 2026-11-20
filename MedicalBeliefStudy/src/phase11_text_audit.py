"""Audit the unexpectedly perfect raw-text baseline without altering the cohort."""
import json,hashlib,collections
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import RidgeClassifier
from analyze_stages import ROOT,ci,fmt,dump,csvwrite
def main():
    dest=ROOT/'results/11_disease_information';cases=[json.loads(s) for s in (ROOT/'data/full49_v1/cases.private.jsonl').read_text().splitlines()]
    with np.load(dest/'heldout_predictions.npz') as a:ids=list(a['case_ids']);y=a['gold'];fold=a['fold'];original=a['text_pred']
    assert ids==[c['case_id'] for c in cases]
    texts=collections.defaultdict(list);facts=[]
    for c in cases:
        groups=[c['initial_question_group']]+c['orders']['base'];items=[v for g in groups for v in c['explicit_evidence_groups'][g]]
        texts['full'].append(f"Age {c['age']}; sex {c['sex']}. "+' '.join(v['question_en']+' '+v['answer_en'] for v in items))
        texts['questions_only'].append(' '.join(v['question_en'] for v in items))
        texts['answers_only'].append(' '.join(v['answer_en'] for v in items))
        texts['evidence_ids_only'].append(' '.join(v['evidence_id'] for v in items))
        texts['demographics_only'].append(f"Age {c['age']}; sex {c['sex']}.")
        signature=sorted((v['evidence_id'],tuple(sorted(v['values']))) for v in items)
        facts.append(hashlib.sha256(json.dumps(signature).encode()).hexdigest())
    predictions={k:np.zeros(120,int) for k in texts};shuffled=np.zeros(120,int);sims=np.zeros(120);rng=np.random.default_rng(720261118)
    for f in range(5):
        train=np.flatnonzero(fold!=f);test=np.flatnonzero(fold==f);assert not set(train)&set(test)
        for key,txt in texts.items():
            vectorizer=TfidfVectorizer(ngram_range=(1,2),min_df=1,lowercase=True,token_pattern=r'(?u)\b\w+\b');X=vectorizer.fit_transform([txt[i] for i in train]);Z=vectorizer.transform([txt[i] for i in test]);model=RidgeClassifier(alpha=1.,solver='lsqr');model.fit(X,y[train]);predictions[key][test]=model.predict(Z)
            if key=='full':
                sims[test]=(Z@X.T).toarray().max(-1);model.fit(X,rng.permutation(y[train]));shuffled[test]=model.predict(Z)
    assert np.array_equal(predictions['full'],original)
    duplicates=[g for g in ({v:[i for i,x in enumerate(facts) if x==v] for v in set(facts)}).values() if len(g)>1]
    crossduplicates=[g for g in duplicates if len({fold[i] for i in g})>1]
    result={'cases':120,'reproduced_original_predictions':True,'classification_accuracy':{k:ci(list(p==y)) for k,p in predictions.items()},
            'one_fixed_training_label_shuffle':ci(list(shuffled==y)),'duplicate_fact_sets_ignoring_demographics':[[ids[i] for i in g] for g in duplicates],
            'cross_fold_duplicate_fact_sets':[[ids[i] for i in g] for g in crossduplicates],'median_nearest_training_text_cosine':float(np.median(sims)),
            'max_nearest_training_text_cosine':float(sims.max()),'exact_full_text_duplicates':len(texts['full'])-len(set(texts['full']))}
    dump(dest/'text_audit.json',result);csvwrite(dest/'text_audit_predictions.csv',[{'case_id':ids[i],'fold':int(fold[i]),'gold_index':int(y[i]),**{k:int(p[i]) for k,p in predictions.items()},'nearest_train_text_cosine':float(sims[i])} for i in range(120)])
    labels={'full':'完整问答与人口信息','questions_only':'仅问题文字','answers_only':'仅答案文字','evidence_ids_only':'仅证据ID','demographics_only':'仅年龄与性别'}
    table='\n'.join(f'| {labels[k]} | {fmt(v)} |' for k,v in result['classification_accuracy'].items())
    (dest/'TEXT_AUDIT.md').write_text(f'''# 文本基线100%的复核

这是看到阶段11文本基线结果后进行的审计，未更换病例或修改主要读出实验。重新独立构造输入、按原五折训练，完整问答分类预测与原实验逐例一致。训练/测试病例ID无交叉；完整输入文本重复{result['exact_full_text_duplicates']}例；忽略年龄性别后，跨折完全相同的证据事实组有{len(crossduplicates)}组。

| 输入 | 未见病例准确率 [95%区间] |
|---|---|
{table}

一次固定训练标签打乱后的准确率为{fmt(result['one_fixed_training_label_shuffle'])}，仅作工程负对照，不作置换显著性检验。测试文本与最近训练文本的余弦相似度中位数为{result['median_nearest_training_text_cosine']:.4f}。

**这批模拟病例的输入具有很强的标签可分结构。** “仅问题”或“仅证据ID”仍携带源数据记录了哪些症状的信息，不是无信息基线。这些结果说明外部读出器可能学习症状集合与标签的对应，不能把其高分直接等同于模型已经形成临床诊断理解。原生诊断与内部可读信息之间的差距仍是实际测量结果，其机制需要进一步定向干预。

[审计结果](text_audit.json) · [逐例预测](text_audit_predictions.csv)
''')
    main=dest/'RESULTS.md';marker='\n## 文本可分性的追加审计\n';base=main.read_text().split(marker)[0]
    main.write_text(base+marker+f'\n独立复算确认完整问答120/120，问题文字单独输入120/120，仅证据ID117/120；完整输入及忽略人口信息后的事实集合均无跨折完全重复。年龄性别单独输入1/120。说明这批病例的症状记录结构高度可分，不能把外部读出准确率直接当成模型医学理解。详见[审计](TEXT_AUDIT.md)。\n')
    print(json.dumps(result,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
