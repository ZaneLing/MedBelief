"""Frozen-design non-LLM baselines and all-patient transition summaries."""
import csv,collections,copy
import numpy as np
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import RidgeClassifier
from phase14_analyze import text,structured
from belief_v3_analysis import *

def main():
 dest=ROOT/'results/27_building_synthesis';(dest/'figures').mkdir(parents=True,exist_ok=True);setup()
 train=rows(ROOT/'data/full49_v1/cases.private.jsonl');test=rows(ROOT/'data/belief_v3/cases.private.jsonl');cl=sorted({c['gold_disease'] for c in train});yt=[cl.index(c['gold_disease']) for c in train];models={};result={};records=[];prefix=[]
 assert len(train)==120 and len(test)==240 and not {c['case_id'] for c in train}&{c['case_id'] for c in test}
 for name in ['full','questions','structured_values','presence']:
  fn=(lambda c:text(c,name=='questions')) if name in ['full','questions'] else (lambda c:structured(c,name=='presence'))
  v=TfidfVectorizer(ngram_range=(1,2),token_pattern=r'(?u)\b\w+\b') if name in ['full','questions'] else DictVectorizer();X=v.fit_transform([fn(c) for c in train]);m=RidgeClassifier(alpha=1,solver='lsqr').fit(X,yt);pred=m.predict(v.transform([fn(c) for c in test]));hits=[]
  for c,p in zip(test,pred):
   hit=cl[p]==c['gold_disease'];hits.append(hit);records.append(dict(case_id=c['case_id'],family=c['family'],baseline=name,gold=c['gold_disease'],prediction=cl[p],hit=hit))
  result[name]=dict(correct=sum(hits),patients=240,accuracy=summary(hits))
  for c in [c for c in test if c['deep_capture']]:
   partials=[]
   for t in range(len(c['orders']['base'])+1):
    cc=copy.deepcopy(c);cc['orders']['base']=cc['orders']['base'][:t];visible=[cc['initial_question_group']]+cc['orders']['base'];cc['explicit_evidence_groups']={k:cc['explicit_evidence_groups'][k] for k in visible};partials.append(fn(cc))
   pp=m.predict(v.transform(partials))
   for t,p in enumerate(pp):prefix.append(dict(case_id=c['case_id'],round=t,baseline=name,gold=c['gold_disease'],prediction=cl[p],hit=cl[p]==c['gold_disease']))
  result[name]['patient_mean_prefix_hit']=summary([np.mean([r['hit'] for r in prefix if r['baseline']==name and r['case_id']==c['case_id']]) for c in test if c['deep_capture']])
 csvwrite(dest/'text_baseline_endpoints.csv',records);csvwrite(dest/'text_baseline_prefixes.csv',prefix)
 paths=list(csv.DictReader((ROOT/'results/23_new_patients/prefix_trajectories.csv').open()));trans=[];mats={}
 for key in ['native24','probe28']:
  mat=np.zeros((24,24),dtype=int)
  for cid in sorted({r['case_id'] for r in paths}):
   rr=sorted([r for r in paths if r['case_id']==cid],key=lambda r:int(r['round']))
   for a,b in zip(rr,rr[1:]):
    mat[cl.index(a[key]),cl.index(b[key])]+=1;trans.append(dict(case_id=cid,round=int(b['round']),interface=key,previous=a[key],current=b[key],switched=a[key]!=b[key]))
  mats[key]=mat
 assert all(int(m.sum())==567 for m in mats.values())
 np.savez_compressed(dest/'transition_matrices.npz',classes=np.array(cl),**mats);csvwrite(dest/'all_disease_transitions.csv',trans)
 fig,axs=plt.subplots(1,2,figsize=(16,8),layout='constrained')
 for ax,(key,title) in zip(axs, [('native24','原模型：同24种病'),('probe28','第28层：独立读出')]):
  mat=mats[key].copy();np.fill_diagonal(mat,0);im=ax.imshow(mat,cmap='Blues',vmin=0,vmax=max(mats['native24'][~np.eye(24,dtype=bool)].max(),mats['probe28'][~np.eye(24,dtype=bool)].max()));ax.set(xticks=range(24),yticks=range(24),xticklabels=[ZH.get(d,d) for d in cl],yticklabels=[ZH.get(d,d) for d in cl],title=title,xlabel='新首选',ylabel='上一轮首选');ax.tick_params(axis='x',labelrotation=90,labelsize=7);ax.tick_params(axis='y',labelsize=7)
 fig.colorbar(im,ax=axs,label='首选转移事件数；对角线隐藏');savefig(fig,dest/'figures/disease_transitions')
 out=dict(training_patients=120,test_patients=240,classes=24,hyperparameters='same as phase14: TF-IDF 1-2 grams / field indicators; Ridge alpha=1',results=result,api_cost_usd=0);dump(dest/'text_baselines.json',out)
 labels={'full':'完整问题和答案','questions':'只有记录到的问题，不看答案','structured_values':'证据字段与取值','presence':'只看哪些证据字段被记录'};tab='\n'.join(f'| {labels[k]} | {r["correct"]}/240 | {fmt(r["patient_mean_prefix_hit"])} |' for k,r in result.items())
 (dest/'TEXT_BASELINES.md').write_text(f'''# 新240例上的简单分类器控制

沿用旧实验的120个训练患者、特征和超参数，在本轮240个全新患者评价；没有根据新患者标签调参。逐轮指标先在每个患者内求比例，再平均72条轨迹。

| 输入给分类器的内容 | 完整病例命中 | 逐轮命中比例 |
|---|---|---|
{tab}

这个对照决定如何解释内部读出：如果不看患者回答、只看哪些问题被记录就能识别疾病，说明模拟数据的记录结构本身包含强预测线索。它不支持用分类器替代真实临床诊断，也不证明语言模型已经在内部完成了医学推理。新的240例结果与此前120例分开保存。

[全部患者](text_baseline_endpoints.csv) · [所有前缀](text_baseline_prefixes.csv) · [全疾病转移](all_disease_transitions.csv)
''');print(json.dumps(clean(out),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
