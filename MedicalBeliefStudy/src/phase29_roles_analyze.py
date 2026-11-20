"""Does source-role metadata change diagnostic choice or decodable content?"""
import numpy as np
import matplotlib.pyplot as plt
from belief_v3_analysis import *
def main():
 run=ROOT/'runs/belief_v3/role_binding';assert (run/'completion.json').exists();dest=ROOT/'results/30_role_binding';(dest/'figures').mkdir(parents=True,exist_ok=True);setup();cases=[c for c in rows(ROOT/'data/belief_v3/cases.private.jsonl') if c['deep_capture']];ds=rows(ROOT/'data/belief_v3/jobs.jsonl')[0]['candidate_diseases'];h=np.load(ROOT/'results/14_fixed_panel/training_heads.npz');cl=h['classes'].tolist();sub=[ds.index(d) for d in cl];data=[];layerdata=[]
 for c in cases:
  cid=c['case_id'];g=ds.index(c['gold_disease']);yi=cl.index(c['gold_disease']);ref=read(run/f'{cid}_neutral.json');qr=np.array(ref['q_sequence']);sr=readout(run,ref,h);comp=max((i for i in range(49) if i!=g),key=lambda i:ref['log_probability'][i]);refmargin=support_margin(ref,g,comp)
  for cond in ['neutral','correct','swapped']:
   r=read(run/f'{cid}_{cond}.json');q=np.array(r['q_sequence']);s=readout(run,r,h);ranks=1+(s>s[:,yi,None]).sum(-1);rankref=1+(sr>sr[:,yi,None]).sum(-1);data.append(dict(case_id=cid,gold=c['gold_disease'],condition=cond,native49=ds[q.argmax()],native24=cl[q[sub].argmax()],probe28=cl[s[-1].argmax()],native49_hit=bool(q.argmax()==g),native24_hit=bool(q[sub].argmax()==yi),probe28_hit=bool(s[-1].argmax()==yi),native49_switched_vs_neutral=bool(q.argmax()!=qr.argmax()),native24_switched_vs_neutral=bool(q[sub].argmax()!=qr[sub].argmax()),probe28_switched_vs_neutral=bool(s[-1].argmax()!=sr[-1].argmax()),gold_support=q[g],gold_rank_probe28=int(ranks[-1]),native_margin_gain_vs_neutral=support_margin(r,g,comp)-refmargin,input_tokens=r['input_tokens']))
   for l in range(28):layerdata.append(dict(case_id=cid,condition=cond,layer=l+1,probe_hit=bool(s[l].argmax()==yi),gold_rank=int(ranks[l]),gold_rank_change_vs_neutral=int(ranks[l]-rankref[l])))
 s=dict(cases=72,observations=len(data),conditions={},exploratory=True,api_cost_usd=0);ref={r['case_id']:r for r in data if r['condition']=='neutral'}
 for cond in ['neutral','correct','swapped']:
  rr=[r for r in data if r['condition']==cond];s['conditions'][cond]={key:summary([r[key] for r in rr]) for key in ['native49_hit','native24_hit','probe28_hit','native49_switched_vs_neutral','native24_switched_vs_neutral','probe28_switched_vs_neutral','native_margin_gain_vs_neutral']};s['conditions'][cond]['paired_change_vs_neutral']={key:summary([float(r[key])-float(ref[r['case_id']][key]) for r in rr]) for key in ['native49_hit','native24_hit','probe28_hit']}
 dump(dest/'summary.json',s);csvwrite(dest/'cases.csv',data);csvwrite(dest/'layers.csv',layerdata);fig,axs=plt.subplots(1,2,figsize=(12,4),layout='constrained');conds=['neutral','correct','swapped'];xx=np.arange(3)
 for i,(key,label) in enumerate([('native24_hit','原模型，同24病'),('probe28_hit','第28层独立读出')]):axs[0].bar(xx+(i-.5)*.32,[s['conditions'][c][key]['mean'] for c in conds],width=.32,label=label)
 axs[0].set(xticks=xx,xticklabels=['不标角色','正确角色','交换角色'],ylabel='完整病例命中来源病比例',ylim=(0,1));axs[0].legend(fontsize=8)
 for cond,label in [('neutral','不标角色'),('correct','正确角色'),('swapped','交换角色')]:axs[1].plot(range(1,29),[np.mean([r['probe_hit'] for r in layerdata if r['condition']==cond and r['layer']==l]) for l in range(1,29)],label=label)
 axs[1].set(xlabel='模型层',ylabel='内部24病读出命中率',ylim=(0,1));axs[1].legend();savefig(fig,dest/'figures/roles')
 gain=s['conditions']['correct']['paired_change_vs_neutral']['native49_hit'];pg=s['conditions']['correct']['paired_change_vs_neutral']['probe28_hit'];claim='正确标注事实角色提高了原模型来源病命中率。' if gain['low']>0 else ('正确标注事实角色降低了原模型来源病命中率。' if gain['high']<0 else '正确标注事实角色没有带来明确的总体命中率改善。');tab='\n'.join(f'| {label} | {fmt(s["conditions"][cond]["native49_hit"])} | {fmt(s["conditions"][cond]["native24_hit"])} | {fmt(s["conditions"][cond]["probe28_hit"])} |' for cond,label in [('neutral','不标角色'),('correct','正确角色'),('swapped','交换角色')]);example=[r for r in data if r['case_id']=='ddx_test_0053572'];et='\n'.join(f'| {r["condition"]} | {r["native49"]} | {r["probe28"]} |' for r in example)
 (dest/'RESULTS.md').write_text(f'''# 模型是否混淆了既往病史和当前表现？

**{claim}** 正确角色相对不标角色，原模型49病命中率变化为{fmt(gain)}，第28层读出变化为{fmt(pg)}。

这一解释由新队列中的心肌梗死/HIV例子触发，属于结果驱动的探索。我们随后对全部72个预选完整轨迹病例测试，不只测试该例。问题、答案、顺序和类别说明相同，仅将每组来源角色标为正确、未指定或反向。

| 条件 | 原模型49病 | 原模型同24病 | 第28层24病读出 |
|---|---|---|---|
{tab}

![角色绑定对照](figures/roles.png)

触发例ddx_test_0053572的来源诊断为Possible NSTEMI / STEMI：

| 条件 | 原模型首选 | 第28层读出 |
|---|---|---|
{et}

HISTORY/CURRENT由来源is_antecedent标记生成，没有使用来源诊断生成提示。交换角色是反事实元数据；不能把它与原病例视作相同临床语义。主比较为正确角色与未指定角色，它们都有同一类别解释和标记格式。实验回答显式角色信息是否帮助当前测量，单项提示成败不等于定位唯一内部回路。

[逐病例](cases.csv) · [所有层](layers.csv) · [精确汇总](summary.json)
''');print(json.dumps(clean(s),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
