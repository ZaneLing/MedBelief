"""Readable examples spanning every observed trajectory type, with explicit selection."""
import csv
from belief_v3_analysis import *
from belief_v3_labels import describe
def main():
 d=ROOT/'research_v3';cases={c['case_id']:c for c in rows(ROOT/'data/belief_v3/cases.private.jsonl')};metrics=list(csv.DictReader((ROOT/'results/23_new_patients/case_metrics.csv').open()));paths=list(csv.DictReader((ROOT/'results/23_new_patients/prefix_trajectories.csv').open()));out=['# 七个入口：同一实验里有哪些不同情况？','','本页帮助阅读，不替代群体统计。前六例在每种观察到的路径中，按case_id取最小者；没有按异常大小挑选。路径分类依据原模型49病首选相对最终来源病的变化。简表保留初始轮、任一首选变化轮和终点；每组证据只列第一项，完整组内容见病例页。内部读出是同一冻结24病分类器，不能与49病输出的疾病范围混淆。','']
 for pat,label in PATTERNS.items():
  c=cases[min(m['case_id'] for m in metrics if m['pattern']==pat)];cid=c['case_id'];rr=sorted([r for r in paths if r['case_id']==cid],key=lambda r:int(r['round']));selected=[r for i,r in enumerate(rr) if i==0 or i==len(rr)-1 or r['native49']!=rr[i-1]['native49'] or r['probe28']!=rr[i-1]['probe28']];out +=[f'## {label}：{ZH.get(c["gold_disease"],c["gold_disease"])}', '',f'模拟病例{cid}；来源疾病为{ZH.get(c["gold_disease"],c["gold_disease"])}。原模型终点首选{ZH.get(rr[-1]["native49"],rr[-1]["native49"])}，内部末层终点首选{ZH.get(rr[-1]["probe28"],rr[-1]["probe28"])}。','', '| 轮次 | 本轮证据组首项 | 原模型首选 | 第28层读出首选 |','|---:|---|---|---|']
  for r in selected:
   item=describe(c['explicit_evidence_groups'][r['evidence_group']]).replace('|','/');out.append(f'| {r["round"]} | {item} | {ZH.get(r["native49"],r["native49"])} | {ZH.get(r["probe28"],r["probe28"])} |')
  out +=['',f'[完整证据、每轮支持和逐层图](../results/23_new_patients/cases/{cid}.md)','']
 ep=list(csv.DictReader((ROOT/'results/23_new_patients/endpoint_cases.csv').open()));z=min((r for r in ep if r['view']=='append' and r['native24']==r['gold'] and r['probe_last']!=r['gold']),key=lambda r:r['case_id']);out+=['## 原模型对、内部读出错的反例','',f'在同24病比较中，{z["case_id"]}的来源病为{ZH.get(z["gold"],z["gold"])}，原模型排对了，末层读出却选择{ZH.get(z["probe_last"],z["probe_last"])}。全部240例有12例属于这一格；有101例是反过来只有读出对。这说明两种测量有差距，但内部读出不是不会错的隐藏医生。','', '[全体终点逐病例表](../results/23_new_patients/endpoint_cases.csv) · [全部72条轨迹](../results/23_new_patients/CASE_ATLAS.md) · [全部87条外部原题](../results/26_external_medqa/CASE_ATLAS.md)','']
 (d/'CASE_GALLERY.md').write_text('\n'.join(out));print('Wrote six trajectory examples plus a native-correct/readout-wrong counterexample.')
if __name__=='__main__':main()
