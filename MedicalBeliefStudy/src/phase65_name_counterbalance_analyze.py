"""Same-format, all-candidate control for unendorsed-name attraction."""
import json
import numpy as np
import matplotlib.pyplot as plt
from phase41_multisource_analyze import ROOT,DATA,read,write,csvwrite,stat,fmt,SOURCES
from analyze_stages import setup,savefig
DEST=ROOT/'results/41_name_counterbalance'
def main():
 setup();(DEST/'figures').mkdir(parents=True,exist_ok=True);cs={c['case_id']:c for c in map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines()) if c['mechanism_capture'] and c['cohort']=='confirmation'};keep={r['case_id'] for r in read(DATA/'text_audit.json')['rows'] if r['strict_keep']};rows=[]
 for model in ['1.7b','4b']:
  src=ROOT/'runs'/('belief_v4_names_'+model);assert read(src/'completion.json')['complete']
  for cid,c in cs.items():
   z=read(src/(cid+'.json'));g=c['gold_index'];rr=z['conditions'];assert len(rr)==10
   groups={j:[r for r in rr if r['named_index']==j] for j in [-1,0,1,2,3]};assert all(len(x)==2 for x in groups.values())
   acc=lambda q:float(np.mean([np.argmax(r['q'])==g for r in q]));selfsupport=float(np.mean([r['q'][j] for j in range(4) for r in groups[j]]));selffollow=float(np.mean([np.argmax(r['q'])==j for j in range(4) for r in groups[j]]))
   targetcorrect=acc(groups[g]);falsecorrect=float(np.mean([acc(groups[j]) for j in range(4) if j!=g]));emptycorrect=acc(groups[-1]);varied=float(np.mean([len({int(np.argmax(next(r for r in groups[j] if r['rotation']==rot)['q'])) for j in range(4)})>1 for rot in [0,2]]))
   rows.append(dict(case_id=cid,dataset=c['dataset'],cohort=c['cohort'],strict_keep=cid in keep,model=model,self_mention_support=selfsupport,self_mention_excess_over_quarter=selfsupport-.25,follow_named_rate=selffollow,follow_named_excess_over_quarter=selffollow-.25,empty_correct=emptycorrect,gold_mentioned_correct=targetcorrect,wrong_mentioned_correct=falsecorrect,wrong_mentioned_minus_empty=falsecorrect-emptycorrect,gold_minus_wrong_mentioned=targetcorrect-falsecorrect,choice_varies_across_named_candidates=varied,code_mass=float(np.mean([r['candidate_mass'] for r in rr])),first_token_code_rate=float(np.mean([r['unrestricted_first_is_code'] for r in rr]))))
 csvwrite(DEST/'patient_counterbalance.csv',rows);ss=[]
 for model in ['1.7b','4b']:
  for ds in SOURCES+['all']:
   for strict in [False,True]:
    rr=[r for r in rows if r['model']==model and (ds=='all' or r['dataset']==ds) and (not strict or r['strict_keep'])];ss.append(dict(model=model,dataset=ds,strict=strict,n=len(rr),metrics={k:stat([r[k] for r in rr]) for k in rows[0] if k not in ['case_id','dataset','cohort','strict_keep','model']}))
 write(DEST/'summary.json',dict(patients=48,strict_patients=47,models=2,conditions=960,status='post_observation_same_format_control',summaries=ss,api_cost_usd=0))
 fig,axs=plt.subplots(1,2,figsize=(11,4.8),layout='constrained')
 for i,model in enumerate(['1.7b','4b']):
  m=next(r['metrics'] for r in ss if r['model']==model and r['dataset']=='all' and r['strict']);s=m['self_mention_support'];axs[0].bar(i,s['mean'],color=['#3988a6','#cb9950'][i]);axs[0].errorbar(i,s['mean'],yerr=np.array([[s['mean']-s['low']],[s['high']-s['mean']]]),fmt='none',c='black',capsize=4)
  vv=[m[k] for k in ['empty_correct','gold_mentioned_correct','wrong_mentioned_correct']];axs[1].plot(range(3),[s['mean'] for s in vv],'-o',label=model)
 axs[0].axhline(.25,c='black',ls='--',label='不受具体病名影响：25%');axs[0].set(xticks=[0,1],xticklabels=['1.7B FP16','4B 8-bit'],ylim=(0,1),ylabel='每个病名被提及时分到的平均支持',title='轮流提及四个候选：支持是否跟着病名走？');axs[0].legend(fontsize=9)
 axs[1].set(xticks=range(3),xticklabels=['同格式未给出病名','提及来源答案','提及错误选项（3项平均）'],ylim=(0,1),ylabel='来源答案命中率',title='都是“未采纳”，具体说了什么病仍有区别');axs[1].tick_params(axis='x',rotation=15);axs[1].legend();fig.suptitle('同一病例、同一字段格式，换四个病名｜严格文本47例，两种代码映射');savefig(fig,DEST/'figures/name_counterbalance')
 with (DEST/'RESULTS.md').open('w') as f:
  f.write('# 不只比较“多了几句话”：轮流放入四个未采纳病名\n\n同48例，两模型，每例固定病例原文和JSON历史格式，将unendorsed_candidate依次设为四个候选；另设同格式Undetermined。所有条件中的diagnosis均为Undetermined。两种代码映射，总960次输入评估。作为看过主结果后追加的格式与病名控制，按探索性复核报告。\n\n![同格式四病名控制](figures/name_counterbalance.png)\n\n## 判定方法\n\n分别问：提到第1种病时，它拿到多少支持；提到第2种时，第2种拿到多少；依此类推，再平均四次。如果具体提到哪个病完全不影响输出，即使模型原本偏爱某个病，这个平均也恰好是25%。因此高于25%测量的是支持随病名移动，不是简单的固定候选偏爱。两种映射先在患者内平均。\n\n| 模型 | 严格文本 | n | 被提及候选的平均支持，95%CI | 超出25%的量 | 首选跟随被提及候选比例 | 首选随病名变化比例（两映射平均） |\n|---|---|---:|---|---|---|---|\n')
  for r in ss:
   if r['dataset']=='all':
    m=r['metrics'];f.write(f'| {r["model"]} | {r["strict"]} | {r["n"]} | {fmt(m["self_mention_support"],True)} | {fmt(m["self_mention_excess_over_quarter"],True)} | {fmt(m["follow_named_rate"],True)} | {fmt(m["choice_varies_across_named_candidates"],True)} |\n')
  f.write('\n## 与同格式空病名比较\n\n| 模型 | 严格文本n | 空病名命中 | 提及来源答案 | 提及错误选项 | 错误提及−空病名，95%CI |\n|---|---:|---|---|---|---|\n')
  for r in ss:
   if r['dataset']=='all' and r['strict']:
    m=r['metrics'];f.write(f'| {r["model"]} | {r["n"]} | '+ ' | '.join(fmt(m[k],True) for k in ['empty_correct','gold_mentioned_correct','wrong_mentioned_correct','wrong_mentioned_minus_empty'])+' |\n')
  f.write('\n这支持对结构化“未采纳候选”情境下病名选择性影响的判断，不把字段里的Undetermined等同于人类心理上的确信/不确信。不同病名仍有词元长度差；全部候选轮换、同格式空病名和两套代码共同减少单一模板/候选偏爱的解释。\n\n[全部患者数据](patient_counterbalance.csv) · [来源分别统计](summary.json)\n')
 print(json.dumps(dict(output=str(DEST),conditions=960)))
if __name__=='__main__':main()
