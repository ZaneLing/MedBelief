"""Exploratory joint reanalysis of existing observations; no model inference."""
import csv,collections
import numpy as np
from belief_v3_analysis import ROOT,rows,read,load_record,summary,dump,csvwrite

def main():
 dest=ROOT/'results/31_argument_audit';dest.mkdir(parents=True,exist_ok=True)
 cases=[c for c in rows(ROOT/'data/belief_v3/cases.private.jsonl') if c['mechanism_capture']]
 ds=rows(ROOT/'data/belief_v3/jobs.jsonl')[0]['candidate_diseases'];cl=np.load(ROOT/'results/14_fixed_panel/training_heads.npz')['classes'].tolist();sub=[ds.index(d) for d in cl]
 run=ROOT/'runs/belief_v3';hr=list(csv.DictReader((ROOT/'results/25_history_and_evidence/history_cases.csv').open()));out=[];joints={};layer_reports=[]
 for c in cases:
  cid=c['case_id'];g=ds.index(c['gold_disease']);wm=read(run/'observations'/f'{cid}_history_wrong.json');wf=read(run/'observations'/f'{cid}_history_wrong_final.json');gm=read(run/'observations'/f'{cid}_history_gold.json');gf=read(run/'history_matched'/f'{cid}.json');w=ds.index(wm['prior_disease']);nm=load_record(run,c,c['fixed_middle_round']);nf=load_record(run,c)
  def m(z):return z['log_probability'][g]-z['log_probability'][w]
  def first(z):return z['token_log_probability'][g][0]-z['token_log_probability'][w][0]
  dr=m(wf)-m(wm);dg=m(gf)-m(gm);dn=m(nf)-m(nm)
  H=m(wf)-m(gf);H1=first(wf)-first(gf);Hr=H-H1
  item=dict(case_id=cid,gold=c['gold_disease'],wrong_prior=ds[w],wrong_in24=ds[w] in cl,added_groups=len(c['orders']['base'])-c['fixed_middle_round'],block_effect_wrong=dr,block_effect_correct=dg,block_effect_no_history=dn,history_by_evidence_interaction=dr-dg,wrong_vs_correct_sign_flip=bool(dr*dg<0) if min(abs(dr),abs(dg))>.01 else None,wrong_vs_nohistory_sign_flip=bool(dr*dn<0) if min(abs(dr),abs(dn))>.01 else None,final_history_margin_effect=H,first_token_history_effect=H1,remaining_tokens_history_effect=Hr,absolute_first_token_share=abs(H1)/(abs(H1)+abs(Hr)) if abs(H1)+abs(Hr)>1e-10 else None)
  for stage,gr,wr in [('middle',gm,wm),('final',gf,wf)]:
   h=next(r for r in hr if r['case_id']==cid and r['stage']==stage);ntopg=cl[np.argmax(np.array(gr['q_sequence'])[sub])];ntopw=cl[np.argmax(np.array(wr['q_sequence'])[sub])];nc=ntopg!=ntopw;pc=h['gold_history_probe_last']!=h['wrong_history_probe_last'];item[stage+'_native24_changed']=nc;item[stage+'_probe24_changed']=pc;item[stage+'_joint']=('both_changed' if nc and pc else 'native_only_changed' if nc else 'probe_only_changed' if pc else 'neither_changed')
  out.append(item)
 for stage in ['middle','final']:joints[stage]=dict(collections.Counter(r[stage+'_joint'] for r in out))
 for threshold in [.001,.01,.1,1.]:
  eligible=[z for z in out if min(abs(z['block_effect_wrong']),abs(z['block_effect_correct']))>threshold];layer_reports.append(dict(threshold=threshold,patients=len(eligible),opposite=sum(z['block_effect_wrong']*z['block_effect_correct']<0 for z in eligible)))
 s=dict(new_model_calls=0,api_cost_usd=0,exploratory=True,patients=len(out),candidate_matched_24_joint=joints,history_by_block_interaction=summary([r['history_by_evidence_interaction'] for r in out]),wrong_correct_block_sign_flip=sum(z['wrong_vs_correct_sign_flip'] is True for z in out),wrong_correct_block_sign_eligible=sum(z['wrong_vs_correct_sign_flip'] is not None for z in out),block_sign_sensitivity=layer_reports,first_token_share=summary([r['absolute_first_token_share'] for r in out]),interpretation='Two history conditions at middle and final endpoints; measures effects of the remaining evidence block, not individual evidence meaning or persistent state after history removal.')
 csvwrite(dest/'paired_history_reanalysis.csv',out);dump(dest/'summary.json',s)
 (dest/'RESULTS.md').write_text(f'''# 论证复核：当前结果真正区分了什么？

只重算既有记录，没有新增模型推理，API费用0美元。以下为结果驱动的探索性分析。

## 同24病比较，历史究竟改变了哪一侧的首选？

这里把原模型与内部读出都限制到同24种病。比较同一病例的正确/错误历史条件；“内部不变”仅指读出首选不变，不指整个状态不变。

| 反应组合 | 中间轮，24例 | 完整事实，24例 |
|---|---:|---:|
| 原模型和读出首选都变 | {joints['middle'].get('both_changed',0)} | {joints['final'].get('both_changed',0)} |
| 只有原模型首选变 | {joints['middle'].get('native_only_changed',0)} | {joints['final'].get('native_only_changed',0)} |
| 只有读出首选变 | {joints['middle'].get('probe_only_changed',0)} | {joints['final'].get('probe_only_changed',0)} |
| 两种首选都不变 | {joints['middle'].get('neither_changed',0)} | {joints['final'].get('neither_changed',0)} |

这支持把反应分开描述，尚不能把四格命名为四种已经证实的神经机制。读出可能保留患者字段或历史病名的编码，首选相同也可能有很大的分数变化。

## 后半段事实的作用，是否受先前诊断影响？

固定来源病和注入的错误病为比较对象，计算中间轮到终点的分差变化。正/误历史下，两种变化方向相反的有{s['wrong_correct_block_sign_flip']}/{s['wrong_correct_block_sign_eligible']}例（两侧绝对变化均超过0.01）；多个阈值结果保存在summary.json。

两种历史下的证据块效应差的平均值为{s['history_by_block_interaction']['mean']:.3f}，95%CI [{s['history_by_block_interaction']['low']:.3f}, {s['history_by_block_interaction']['high']:.3f}]。这是后半段整组事实的作用，不是单条证据的临床含义。本轮不能据此认定“预期把反证解释成支持”，也不能认定“更多证据平均放大旧判断”。

## 为什么最后一层干预不能包办机制解释？

既有第28层干预只改变诊断锚点，缓存保持不变；它直接改变病名首词元的分数。它说明这个局部方向能影响原生评分，不能单独定位证据如何被理解、哪条证据被重新解释。自然疾病方向移除在两批患者中通过复核是有效局部结果，但与“医学信念形成机制已经完整解释”是不同层次的结论。

[逐病例重算](paired_history_reanalysis.csv) · [精确汇总](summary.json)
''');print(s)
if __name__=='__main__':main()
