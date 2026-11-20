"""Source-only sensitivity audit after a runtime boundary error exposed missing media.

No generated answers are loaded. Frozen data, training and selections stay intact.
"""
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from phase90_structure2_prepare import *

FLAGS={
 'missing_referenced_material':[
 'medqa_train_06823','medqa_train_05721','medmcqa_train_2034031b-c816-400f-bc77-9e7cfbb73c19','medmcqa_train_6dd7cc2c-1704-4e8f-aa1b-fb30c061f8c9','medmcqa_train_1bba25d9-7512-458e-b47c-65a5a78c975f','medmcqa_train_87f606b2-8e1c-423e-9a9c-8c887c4c4323','medmcqa_train_202cb4ea-c9ef-4e19-868c-eaae7fca2262','medqa_train_04038','medmcqa_train_673357fb-4a08-4e56-b846-b67c0cb8ec3b','medmcqa_train_b980ef1f-f337-435c-8922-82b0b58535a4',
 'medmcqa_validation_ccca9015-2ce5-40cf-bed4-187f9428d984','medmcqa_train_b8f2180c-8e26-45df-8306-66865eae4bc1','medmcqa_train_7cf6e2d1-35af-4b06-a98e-789e5ed50f80','medmcqa_train_fcdea38d-dcee-4c77-866c-136e55daf419',
 'medmcqa_train_1701b45f-25de-4c77-9166-a843d1af0844','medmcqa_train_d974f874-5222-4597-b7ff-5377c3cec88b','medmcqa_train_56aa938d-40f2-4917-9866-8bc915c61f90','medmcqa_train_cd4d2102-2c63-4399-8b39-de47f52bf8bf','medmcqa_train_e4498791-b38f-49c4-b7bf-3287bdd4ab47','medmcqa_train_7cffb021-2110-41d1-963f-50936f881550','medmcqa_train_e0ca5a07-a1ad-499c-a92d-719a7ff1af01','medmcqa_train_6c36cef4-fde7-41c9-8412-c9ad468514a7'],
 'procedure_without_report':['medqa_train_01503','medqa_train_06038','medqa_dev_00188'],
 'task_only_evidence_round':['medqa_train_07093','medqa_train_05615','medmcqa_train_e20b8e6c-221c-4b87-9876-378740bb8cea']}

def main():
    cs=cases();old=list(map(json.loads,(ROOT/'data/belief_v4/cases.private.jsonl').read_text().splitlines()));allc=cs+old;idx={c['case_id']:i for i,c in enumerate(cs)};flags={cid:reason for reason,ids in FLAGS.items() for cid in ids};assert set(flags)<=set(idx)
    # A stricter sensitivity threshold, not a retrospective replacement for the
    # inherited global0.90 deduplication used to build this cohort.
    X=TfidfVectorizer(lowercase=True,ngram_range=(1,2),min_df=1,sublinear_tf=True).fit_transform(['\n'.join(c['sentences']) for c in allc]);prior=[i for i,c in enumerate(cs) if c['cohort'] in ['train','development']]+list(range(len(cs),len(allc)));pairs=[];rows=[];near_by={}
    for i in sorted([i for i,c in enumerate(cs) if c['cohort']=='confirmation'],key=lambda i:rank(cs[i]['case_id']+':sensitivity_dedup')):
        sim=(X[i]@X[prior].T).toarray().ravel();near=[]
        for j in np.flatnonzero(sim>=.80):near.append(dict(case_id=allc[prior[j]]['case_id'],cohort=allc[prior[j]]['cohort'] if prior[j]<len(cs) else 'previous540',cosine=float(sim[j])))
        near_by[i]=near
        if not near:prior.append(i)
    for i,c in enumerate(cs):
        near=[]
        if c['cohort']=='confirmation':
            near=near_by[i]
            pairs.extend(dict(case_id=c['case_id'],**{'matched_'+k:v for k,v in r.items()}) for r in near)
        rows.append(dict(case_id=c['case_id'],dataset=c['dataset'],cohort=c['cohort'],source_quality_flag=flags.get(c['case_id']),near_previous=near,strict_source_keep=c['case_id'] not in flags,strict_source_and_similarity_keep=c['case_id'] not in flags and not near))
    result=dict(status='Source-only sensitivity audit after129 baseline confirmation cases; no model outcomes consulted, no re-selection/re-training.',cases_sha256=sha(DATA/'cases.private.jsonl'),source_sha256=sha(Path(__file__)),similarity_threshold=.80,similarity_corpus='880 new + previous540; word/bigram TF-IDF on source evidence sentences only; confirmation compared with currenttrain/development plus previous540, then hash-ordered greedy confirmation dedup at the same0.80 threshold.',flags=FLAGS,counts={co:dict(total=sum(c['cohort']==co for c in cs),source_kept=sum(r['cohort']==co and r['strict_source_keep'] for r in rows),source_and_similarity_kept=sum(r['cohort']==co and r['strict_source_and_similarity_keep'] for r in rows)) for co in ['train','development','confirmation']},rows=rows,near_pairs=pairs,training_remains_original400=True,selection_remains_original80=True)
    write(DATA/'source_sensitivity_audit.json',result);lines=['# 来源文本复核与运行修正\n\n初始正则审计漏掉了“图在下方”等引用。确认运行至第130例时，候选首字符的引号触发分词断言，查看该病例也暴露了未提供的X光图。随后只根据源文本复核材料引用、无报告的检查，以及被当成新事实的题干尾语；不读取模型答案来决定排除。原880例、训练、开发选择和400例确认全部保留，另外报告严格子集。\n\n| 本实验分组 | 原样本 | 来源复核保留 | 再排除相似度≥0.80病例（含确认集内部重复） |\n|---|---:|---:|---:|\n']
    for co,r in result['counts'].items():lines.append(f'| {co} | {r["total"]} | {r["source_kept"]} | {r["source_and_similarity_kept"]} |\n')
    lines.append('\n相似度复核是新的敏感性分析，不更改原来的全库0.90去重，也不宣称所有语义近重复已经排除。确认集内部也按病例散列顺序、同一0.80阈值贪心去重。训练/开发中的来源问题仍属于本次训练与选型记录；本轮没有重新训练一个声称完全清洁的模型。带有“如下”的实验室表格若数据在后文实际提供，保持纳入。\n\n## 标记的源文本\n\n')
    for r in rows:
        if r['source_quality_flag']:
            c=cs[idx[r['case_id']]];lines.append(f'### {r["case_id"]}（{r["cohort"]}，{r["source_quality_flag"]}）\n\n'+ '\n\n'.join(c['sentences'])+'\n\n')
    lines.append('## 分词修正\n\n[修正清单](TOKENIZATION_AMENDMENT.json)保留原提示文本和词元；只在候选文本跨越已固定JSON前缀发生BPE合并时，把后续字符串作为续写单独编码。全880例×3种历史核查，只有一例的一个候选受影响；先前129例共258个回答的提示与续写编码均不变。原核心、解码器、模型权重和已冻结的方案选择不变。\n');(DOC/'SOURCE_AUDIT.md').write_text(''.join(lines));print(json.dumps(dict(counts=result['counts'],near_pairs=pairs),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
