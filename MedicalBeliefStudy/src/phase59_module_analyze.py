"""Patient-paired module readout differences, not attention-as-explanation."""
import json
import numpy as np
import matplotlib.pyplot as plt
from phase41_multisource_analyze import ROOT,DATA,read,write,csvwrite,stat,fmt,SOURCES
from analyze_stages import setup,savefig
DEST=ROOT/'results/39_module_readout'
def main():
 src=ROOT/'runs/belief_v4_module_readout';assert read(src/'completion.json')['complete'];setup();(DEST/'figures').mkdir(parents=True,exist_ok=True)
 cases={c['case_id']:c for c in map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines()) if c['mechanism_capture']};keep={r['case_id'] for r in read(DATA/'text_audit.json')['rows'] if r['strict_keep']};rows=[];max_closure=0
 for cid,c in cases.items():
  z=read(src/(cid+'.json'));arr={cond:np.mean([np.array(r['stage_code_logits']) for r in z['conditions'] if r['condition']==cond],axis=0) for cond in ['neutral','wrong']};m={k:a[:,:,c['gold_index']]-a[:,:,c['wrong_index']] for k,a in arr.items()};h=m['wrong']-m['neutral'];con=h[:,2]-h[:,0];max_closure=max(max_closure,abs(float(con.sum()-(h[-1,2]-h[0,0]))));assert max_closure<.1
  for l in range(28):rows.append(dict(case_id=cid,dataset=c['dataset'],cohort=c['cohort'],strict_keep=cid in keep,layer=l+1,neutral_before=m['neutral'][l,0],neutral_after_attention=m['neutral'][l,1],neutral_after_mlp=m['neutral'][l,2],wrong_before=m['wrong'][l,0],wrong_after_attention=m['wrong'][l,1],wrong_after_mlp=m['wrong'][l,2],history_gap_before=h[l,0],history_gap_after_attention=h[l,1],history_gap_after_mlp=h[l,2],attention_history_increment=h[l,1]-h[l,0],mlp_history_increment=h[l,2]-h[l,1]))
 csvwrite(DEST/'patient_module_increments.csv',rows);ss=[]
 for cohort in ['all','development','confirmation']:
  for strict in [False,True]:
   for l in range(1,29):
    rr=[r for r in rows if r['layer']==l and (cohort=='all' or r['cohort']==cohort) and (not strict or r['strict_keep'])];ss.append(dict(cohort=cohort,strict=strict,layer=l,n=len(rr),**{f:stat([r[f] for r in rr]) for f in ['history_gap_after_mlp','attention_history_increment','mlp_history_increment']}))
 fig,axs=plt.subplots(2,1,figsize=(11,7.5),layout='constrained');sub=[r for r in ss if r['cohort']=='confirmation' and r['strict']];x=np.arange(1,29)
 for field,col,label,offset in [('attention_history_increment','#447e9e','attention步骤',-.18),('mlp_history_increment','#bd9146','MLP步骤',.18)]:
  vals=[r[field] for r in sub];m=np.array([r['mean'] for r in vals]);lo=np.array([r['low'] for r in vals]);hi=np.array([r['high'] for r in vals]);axs[0].bar(x+offset,m,width=.36,label=label,color=col);axs[0].errorbar(x+offset,m,yerr=np.array([m-lo,hi-m]),fmt='none',ecolor='black',lw=.6,capsize=1)
 vals=[r['history_gap_after_mlp'] for r in sub];axs[1].plot(x,[r['mean'] for r in vals],'-o',ms=3,c='#b7544c');axs[1].fill_between(x,[r['low'] for r in vals],[r['high'] for r in vals],color='#b7544c',alpha=.15)
 for ax in axs:ax.axhline(0,c='gray',lw=.7);ax.set(xticks=[1,7,14,21,22,28],xlabel='层')
 axs[0].set(ylabel='该模块带来的历史分差增量',title='哪一步使错误历史相对中性历史更偏向错误病名？');axs[0].legend();axs[1].set(ylabel='累计历史分差',title='原输出头读出的历史影响何时变得明显？');fig.suptitle('严格文本确认47例｜相同代码读表的阶段变化，非模块消融')
 savefig(fig,DEST/'figures/module_history_readout')
 write(DEST/'summary.json',dict(patients=94,strict_confirmation_patients=47,rows=len(rows),max_telescoping_error=max_closure,summaries=ss,api_cost_usd=0))
 with (DEST/'RESULTS.md').open('w') as f:
  f.write('# 从整层再拆到attention与MLP\n\n对既有94例×两种历史×两种代码映射的最终输入状态重新读表，没有新增模型前向，也没有训练探针。每层比较三个位置：整层输入、attention之后、MLP之后。用同一个输出头读取来源病相对固定错误病的代码logit分差。\n\n![模块读表](figures/module_history_readout.png)\n\n上图每个柱表示该步骤使“错误历史减去中性历史”的分差改变多少。负值意味着向错误病名偏移；下图是每层结束时的累计差距。区间按患者计算，展示47例严格文本确认病例。\n\n这是计算过程中可直接复核的读表轨迹，不能把柱高当作模块独立的因果贡献。层归一化与输出头是非线性读表的一部分；真正的因果证据来自[状态替换](../33_multisource_causality/RESULTS.md)和[通路阻断](../36_history_routes/RESULTS.md)。\n\n| 层 | attention历史增量，95%CI | MLP历史增量，95%CI | 整层末历史分差 |\n|---|---|---|---|\n')
  for r in sub:
   if r['layer'] in [7,14,20,21,22,23,24,25,26,27,28]:f.write(f'| {r["layer"]} | {fmt(r["attention_history_increment"])} | {fmt(r["mlp_history_increment"])} | {fmt(r["history_gap_after_mlp"])} |\n')
  f.write('\n两种代码映射先在患者内平均。全部层、开发/确认、严格/完整队列均保留于[summary.json](summary.json)，[患者级阶段分差](patient_module_increments.csv)可复算。\n')
 print(json.dumps(dict(output=str(DEST),patients=94,rows=len(rows))))
if __name__=='__main__':main()
