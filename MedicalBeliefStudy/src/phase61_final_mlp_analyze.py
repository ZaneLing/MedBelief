"""First-code causal test of the final MLP using frozen activation pairs."""
import json
import numpy as np
import matplotlib.pyplot as plt
from phase41_multisource_analyze import ROOT,DATA,read,write,csvwrite,stat,fmt,holm,SOURCES
from analyze_stages import setup,savefig
DEST=ROOT/'results/40_final_mlp'
def main():
 src=ROOT/'runs/belief_v4_final_mlp';assert read(src/'completion.json')['complete'];setup();(DEST/'figures').mkdir(parents=True,exist_ok=True);cs={c['case_id']:c for c in map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines()) if c['mechanism_capture']};keep={r['case_id'] for r in read(DATA/'text_audit.json')['rows'] if r['strict_keep']};rows=[]
 for cid,c in cs.items():
  z=read(src/(cid+'.json'));g,w=c['gold_index'],c['wrong_index'];lookup={}
  for cond in ['neutral_baseline','wrong_baseline','neutral_mlp_to_wrong','wrong_mlp_to_neutral','random_0','random_1','self']:
   rr=[r for r in z['conditions'] if r['condition']==cond];assert len(rr)==2
   lookup[cond]=dict(accuracy=float(np.mean([np.argmax(r['q'])==g for r in rr])),support=float(np.mean([r['q'][g] for r in rr])),margin=float(np.mean([np.log(max(r['q'][g],1e-30))-np.log(max(r['q'][w],1e-30)) for r in rr])),code_mass=float(np.mean([r['candidate_mass'] for r in rr])))
  row=dict(case_id=cid,dataset=c['dataset'],cohort=c['cohort'],strict_keep=cid in keep)
  for cond,v in lookup.items():
   for k,x in v.items():row[cond+'_'+k]=x
  for k in ['accuracy','support','margin']:
   row['target_minus_random_'+k]=lookup['neutral_mlp_to_wrong'][k]-(lookup['random_0'][k]+lookup['random_1'][k])/2
   row['target_minus_baseline_'+k]=lookup['neutral_mlp_to_wrong'][k]-lookup['wrong_baseline'][k]
   row['reverse_minus_neutral_'+k]=lookup['wrong_mlp_to_neutral'][k]-lookup['neutral_baseline'][k]
  rows.append(row)
 csvwrite(DEST/'patient_interventions.csv',rows);ss=[]
 for cohort in ['all','development','confirmation']:
  for strict in [False,True]:
   rr=[r for r in rows if (cohort=='all' or r['cohort']==cohort) and (not strict or r['strict_keep'])];m={k:stat([r[k] for r in rr]) for k in rows[0] if k not in ['case_id','dataset','cohort','strict_keep']};ss.append(dict(cohort=cohort,strict=strict,n=len(rr),metrics=m))
 write(DEST/'summary.json',dict(patients=94,conditions=940,new_model_prefills=0,outcome='first answer code',followup='Chosen after observing module readout; exploratory in the full cohort, not a newly held-out confirmation',summaries=ss,api_cost_usd=0))
 fig,axs=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
 r=next(r for r in ss if r['cohort']=='confirmation' and r['strict']);m=r['metrics'];conds=['wrong_baseline','neutral_mlp_to_wrong','random_0','random_1','neutral_baseline'];labels=['错误历史','替换末层MLP','随机1','随机2','中性历史']
 for ax,field in zip(axs,['accuracy','margin']):
  v=[m[k+'_'+field] for k in conds];means=np.array([q['mean'] for q in v]);lo=np.array([q['low'] for q in v]);hi=np.array([q['high'] for q in v]);ax.bar(range(5),means,color=['#b7564f','#3287a0','#a4a9ae','#a4a9ae','#6c9b79']);ax.errorbar(range(5),means,yerr=np.array([means-lo,hi-means]),fmt='none',c='black',capsize=3);ax.set(xticks=range(5),xticklabels=labels,ylabel='来源答案命中率' if field=='accuracy' else '来源病−错误病代码分差');ax.tick_params(axis='x',rotation=18)
 fig.suptitle('最后一层MLP是否参与历史偏向？\n严格文本确认队列47例；该干预在读表观察后追加，按探索性结果报告');savefig(fig,DEST/'figures/final_mlp_transfer')
 with (DEST/'RESULTS.md').open('w') as f:
  f.write('# 最后一层MLP的直接检验\n\n逐模块读表提示末层MLP会加强错误历史的分差，因此追加该检验。把同患者中性历史下的末层MLP输出移入错误历史的诊断位置，其他状态保持。供体不含正确答案。由于是最后一层，后续只剩原模型最终归一化和输出头；直接计算与重新前向该位置等价。只评价第一个答案代码，不扩展为后续病名生成改善。\n\n94例、两种映射、目标/反向/自身/两个同范数随机方向，共940个激活干预；复用已有状态，没有新增整段前向。此设计在看过逐层结果后提出，即使列出既定确认队列，也不称它为新的独立确认。\n\n![末层MLP干预](figures/final_mlp_transfer.png)\n\n| 队列 | 严格文本 | 患者数 | 错误历史命中 | 替换后命中 | 中性历史命中 | 目标−随机准确率，95%CI | 目标−随机分差 |\n|---|---|---:|---|---|---|---|---|\n')
  for r in ss:
   m=r['metrics'];f.write(f'| {r["cohort"]} | {r["strict"]} | {r["n"]} | {fmt(m["wrong_baseline_accuracy"],True)} | {fmt(m["neutral_mlp_to_wrong_accuracy"],True)} | {fmt(m["neutral_baseline_accuracy"],True)} | {fmt(m["target_minus_random_accuracy"],True)} | {fmt(m["target_minus_random_margin"])} |\n')
  f.write('\n这是因果参与检验：目标状态与等范数随机扰动比较，反向替换和自身对照分别保留。它不意味着最后一层独立存放了某种医学信念，也不构成无需供体即可部署的诊断修复方法。\n\n[患者级干预](patient_interventions.csv) · [完整统计](summary.json)\n')
 print(json.dumps(dict(output=str(DEST),patients=94)))
if __name__=='__main__':main()
