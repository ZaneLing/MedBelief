"""Text-audit sensitivity for every major result; no records are deleted."""
import json,csv
from phase41_multisource_analyze import ROOT,DATA,read,write,csvwrite,stat,fmt,cohort_tables,SOURCES
DEST=ROOT/'results/38_text_quality'
def csvrows(p):
 rr=list(csv.DictReader(p.open()))
 for r in rr:
  for k,v in r.items():
   try:r[k]=float(v)
   except (ValueError,TypeError):pass
 return rr
def main():
 DEST.mkdir(parents=True,exist_ok=True);audit=read(DATA/'text_audit.json');keep={r['case_id'] for r in audit['rows'] if r['strict_keep']};rows=csvrows(ROOT/'results/32_multisource_belief/patient_results.csv');tables=cohort_tables([r for r in rows if r['case_id'] in keep]);patch=[];mention=[];routes=[];models=[]
 for name,dest in [('33_multisource_causality',patch),('35_unendorsed_name',mention)]:
  rr=[r for r in csvrows(ROOT/'results'/name/'patient_interventions.csv') if r['case_id'] in keep]
  if name.startswith('33'):rr=[r for r in rr if r['cohort']=='confirmation']
  for layer in [14,21]:
   for site in ['new','old','anchor']:
    vv=[r for r in rr if r['layer']==layer and r['site']==site];dest.append(dict(layer=layer,site=site,n=len(vv),specific_effect=stat([r['target_minus_random'] for r in vv]),target_change=stat([r['target_change'] for r in vv])))
 rr=[r for r in csvrows(ROOT/'results/36_history_routes/patient_history_effects.csv') if r['case_id'] in keep]
 for model in ['1.7b','4b']:
  for hist in ['wrong','mention']:
   for route in ['full','block_to_facts','block_to_decision','block_both']:
    v=[r for r in rr if r['model']==model and r['history']==hist and r['route']==route];routes.append(dict(model=model,history=hist,route=route,n=len(v),margin_effect=stat([r['margin_effect'] for r in v]),accuracy_effect=stat([r['accuracy_effect'] for r in v])))
 rr=[r for r in csvrows(ROOT/'results/34_multisource_depth/matched_models.csv') if r['case_id'] in keep]
 for model in ['1.7B','4B8bit']:
  for cohort in ['all','confirmation']:
   v=[r for r in rr if cohort=='all' or r['cohort']==cohort];models.append(dict(model=model,cohort=cohort,n=len(v),neutral_correct=stat([r[model+'_neutral_correct'] for r in v]),wrong_correct=stat([r[model+'_wrong_correct'] for r in v]),mention_correct=stat([r[model+'_mention_correct'] for r in v]),history_accuracy_change=stat([r[model+'_history_accuracy_change'] for r in v])))
 trace=[r for r in read(ROOT/'results/37_behavior_checks/patient_trajectories.json') if r['case_id'] in keep];tr=[]
 for cond in ['neutral','wrong','gold']:
  v=[r for r in trace if r['condition']==cond];tr.append(dict(condition=cond,n=len(v),metrics={k:stat([r[k] for r in v]) for k in ['never_switches','source_then_leave','nonmonotonic_source_support','final_correct']}))
 write(DEST/'summary.json',dict(status='post_run_text_only_sensitivity',evaluated=540,strict_text_cases=len(keep),strict_mechanism_cases=92,strict_confirmation_mechanism_cases=47,behavior=tables,confirmation_patches=patch,confirmation_mention_patches=mention,confirmation_routes=routes,matched_models=models,trajectories=tr))
 with (DEST/'RESULTS.md').open('w') as f:
  f.write('# 全部结果是否依赖文本质量问题\n\n主队列540例在运行前冻结；运行后审计原文发现20例需要标记：7例纯任务尾语、8例缺少引用的图像/报告、4例只提及检查执行而未提供结果、1例事实组混入任务尾语。该敏感性分析按文本选择，不按模型效果删样本。全部原结果保留，严格子集520例。内部94例剩92例，确认48例剩47例。原自动检查文件已明确标记失效的文本覆盖结论。\n\n## 严格文本子集的历史效应\n\n| 来源 | 病例数 | 中性命中 | 错误历史命中 | 仅提及命中 | 错误−中性，95%CI | 提及−中性，95%CI |\n|---|---:|---:|---:|---:|---|---|\n')
  for ds in SOURCES+['all']:
   t=tables[ds+':all'];n=t['accuracy_neutral']['n'];f.write(f'| {ds} | {n} | '+ ' | '.join(str(round(t['accuracy_'+k]['mean']*n)) for k in ['neutral','wrong','mention'])+' | '+fmt(t['wrong_minus_neutral_accuracy'],True)+' | '+fmt(t['mention_minus_neutral_accuracy'],True)+' |\n')
  for title,rr in [('错误旧诊断：确认47例',patch),('未采纳病名：确认47例',mention)]:
   f.write('\n## '+title+'\n\n| 层 | 位置 | 目标−随机分差，95%CI |\n|---|---|---|\n')
   for r in rr:f.write(f'| {r["layer"]} | {r["site"]} | {fmt(r["specific_effect"])} |\n')
  f.write('\n## 通路检验：确认47例\n\n| 模型 | 历史 | 设置 | 历史分差效应，95%CI |\n|---|---|---|---|\n')
  for r in routes:f.write(f'| {r["model"]} | {r["history"]} | {r["route"]} | {fmt(r["margin_effect"])} |\n')
  f.write('\n所有标记病例、具体轮次和原文见[审计清单](../../data/belief_v4/text_audit_review.json)。完整模型/轨迹复核见[summary.json](summary.json)。未提供的影像不由模型合成补全；任务尾语造成的变化不能算医学证据更新。\n')
 print(json.dumps(dict(strict_cases=520,strict_mechanism_cases=92,strict_confirmation_cases=47)))
if __name__=='__main__':main()
