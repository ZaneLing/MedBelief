"""External evidence-state replacement against an equal-norm random control."""
import numpy as np
import matplotlib.pyplot as plt
from belief_v3_analysis import *
def main():
 run=ROOT/'runs/belief_v3_medqa/natural_interventions';assert (run/'completion.json').exists();dest=ROOT/'results/29_external_internal_causality';(dest/'figures').mkdir(parents=True,exist_ok=True);setup();data=[];paired=[];out={};errors=[]
 for p in sorted(run.glob('medqa*.json')):
  c=read(p);g=c['gold_index'];k=c['competitor_index'];dy=(c['new_log_probability'][g]-c['new_log_probability'][k])-(c['old_log_probability'][g]-c['old_log_probability'][k]);records={(r['layer'],r['condition']):r for r in c['conditions']}
  for l in [14,21,28]:
   z=records[l,'self'];baseline=z['log_probability'][g]-z['log_probability'][k];errors.append(z['sham_max_logp_error']);a={}
   for cond in ['self','replace_old','random_matched']:
    r=records[l,cond];effect=(r['log_probability'][g]-r['log_probability'][k])-baseline;atten=-np.sign(dy)*effect if abs(dy)>=1e-8 else None;a[cond]=atten;data.append(dict(case_id=c['case_id'],gold=c['gold'],competitor=c['competitor'],round=c['round'],layer=l,condition=cond,natural_update=dy,effect_vs_sham=effect,attenuation=atten,same_first_token=c['same_first_token'],top_changed=bool(np.argmax(r['q_sequence'])!=np.argmax(z['q_sequence'])),source_hit_before=bool(np.argmax(z['q_sequence'])==g),source_hit_after=bool(np.argmax(r['q_sequence'])==g),requested_delta_norm=r['requested_delta_norm'],actual_delta_norm=r['actual_delta_norm']))
   paired.append(dict(case_id=c['case_id'],layer=l,old_minus_random_attenuation=a['replace_old']-a['random_matched'] if a['replace_old'] is not None else None))
 ps=[]
 for l in [14,21,28]:
  x=[r['old_minus_random_attenuation'] for r in paired if r['layer']==l and r['old_minus_random_attenuation'] is not None];p=sign_permutation(x);ps.append(p);out[str(l)]=dict(old_minus_random=summary(x),p_unadjusted=p,conditions={cond:dict(attenuation=summary([r['attenuation'] for r in data if r['layer']==l and r['condition']==cond]),top_changes=sum(r['top_changed'] for r in data if r['layer']==l and r['condition']==cond)) for cond in ['self','replace_old','random_matched']})
 for l,p in zip([14,21,28],holm(ps)):out[str(l)]['p_holm']=p
 same=[r for r in data if r['layer']==28 and r['same_first_token']];s=dict(patients=87,conditions=len(data),layers=out,sham_max_logp_error=max(errors),same_first_token_cases=len({r['case_id'] for r in same}),same_first_token_last_layer_max_effect=max([abs(r['effect_vs_sham']) for r in same],default=None),api_cost_usd=0);dump(dest/'summary.json',s);csvwrite(dest/'all_conditions.csv',data);csvwrite(dest/'paired_cases.csv',paired)
 fig,ax=plt.subplots(figsize=(8,4),layout='constrained');m=[out[str(l)]['old_minus_random'] for l in [14,21,28]];y=np.array([v['mean'] for v in m]);ax.errorbar([14,21,28],y,yerr=[y-[v['low'] for v in m],np.array([v['high'] for v in m])-y],fmt='o',capsize=4);ax.axhline(0,color='gray',ls='--');ax.set(xticks=[14,21,28],xlabel='干预层',ylabel='旧状态替换−随机操作：输出回退量',title='外部病例：自然状态更新是否有方向特异的作用？');savefig(fig,dest/'figures/external_natural_necessity')
 sig=[str(l) for l in [14,21,28] if out[str(l)]['p_holm']<.05 and out[str(l)]['old_minus_random']['mean']>0];claim='第'+ '、'.join(sig)+'层的旧状态替换，比等范数随机操作更强地抵消自然诊断更新。' if sig else '本次未测得旧状态替换比等范数随机操作更强的方向性回退。';tab='\n'.join(f'| {l} | {fmt(out[str(l)]["old_minus_random"],False)} | {out[str(l)]["p_holm"]:.4f} | {out[str(l)]["conditions"]["replace_old"]["top_changes"]}/87 | {out[str(l)]["conditions"]["random_matched"]["top_changes"]}/87 |' for l in [14,21,28])
 (dest/'RESULTS.md').write_text(f'''# 外部病例：新证据引起的内部状态变化，是否参与诊断？

**{claim}**

87道MedQA题全部纳入，在预定中间轮的第14、21、28层，将诊断锚点换回前一轮状态，保持新证据输入和其他位置状态不变。对照为等范数且与自然状态差正交的随机改动，以及零改动。共783条件。

| 层 | 旧状态替换比随机操作多造成的回退 | 三层Holm校正p | 旧状态改变首选 | 随机改动改变首选 |
|---|---|---:|---:|---:|
{tab}

![外部自然状态检验](figures/external_natural_necessity.png)

回退方向相对于模型原来的病对分差更新定义。正值表示抵消更新，未要求原更新一定指向来源答案。零干预最大log概率误差为{max(errors):.6f}。

这里替换整个局部状态差，没有使用DDxPlus的疾病读出方向。因此它检验外部来源中的自然状态作用，与DDxPlus的疾病方向特异性检验互补，不能把二者合并成同一种因果效应。

[全部条件](all_conditions.csv) · [逐题配对](paired_cases.csv) · [精确结果](summary.json)
''');print(json.dumps(clean(s),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
