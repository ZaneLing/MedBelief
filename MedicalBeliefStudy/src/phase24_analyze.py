"""Patient-level test of predeclared natural-update removals."""
import argparse,collections
import numpy as np
import matplotlib.pyplot as plt
from belief_v3_analysis import *

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--replication',action='store_true');args=ap.parse_args();run=ROOT/'runs/belief_v3'/('natural_interventions_replication' if args.replication else 'natural_interventions');assert (run/'completion.json').exists();dest=ROOT/'results/24_natural_update_causality';dest=dest/'replication' if args.replication else dest;(dest/'figures').mkdir(parents=True,exist_ok=True);setup();rr=[];checks=[];out={};heads=np.load(ROOT/'results/14_fixed_panel/training_heads.npz');classes=heads['classes'].tolist();N=48 if args.replication else 24;ds=rows(ROOT/'data/belief_v3/jobs.jsonl')[0]['candidate_diseases'];sub=[ds.index(x) for x in classes]
 for p in sorted(run.glob('ddx*.json')):
  c=read(p);g=c['gold_index'];k=c['competitor_index'];old=c['old_log_probability'][g]-c['old_log_probability'][k];new=c['new_log_probability'][g]-c['new_log_probability'][k];dy=new-old;records={(r['layer'],r['condition']):r for r in c['conditions']};states=np.load(run/c['state_file'])
  for l in [14,21,28]:
   sham=records[l,'self'];checks.append(sham['sham_max_logp_error']);baseline=sham['log_probability'][g]-sham['log_probability'][k];w=heads['weights_append_0.1'][l-1,:,classes.index(c['gold'])]-heads['weights_append_0.1'][l-1,:,classes.index(c['competitor'])];pn=norm(states[f'L{l}_self_after'].astype(float))@w;po=norm(states[f'L{l}_old'].astype(float))@w;pd=pn-po
   for cond in ['self','remove_target','random_matched','replace_old']:
    r=records[l,cond];post=r['log_probability'][g]-r['log_probability'][k];effect=post-baseline;atten=-np.sign(dy)*effect if abs(dy)>=1e-8 else None
    pe=norm(states[f'L{l}_{cond}_after'].astype(float))@w-pn
    rr.append(dict(case_id=c['case_id'],gold=c['gold'],competitor=c['competitor'],round=c['round'],layer=l,condition=cond,same_first_token=c['same_first_token'],old_margin=old,new_margin=new,natural_update=dy,intervened_margin=post,sham_margin=baseline,effect_vs_sham=effect,attenuation=atten,natural_probe_update=pd,probe_effect_vs_sham=pe,probe_attenuation=-np.sign(pd)*pe if abs(pd)>1e-10 else None,top_changed=bool(np.argmax(r['q_sequence'])!=np.argmax(sham['q_sequence'])),correct_before=bool(np.argmax(sham['q_sequence'])==g),correct_after=bool(np.argmax(r['q_sequence'])==g),requested_delta_norm=r['requested_delta_norm'],actual_delta_norm=r['actual_delta_norm'],natural_delta_norm=r['natural_delta_norm'],projection_fraction=r['projection_fraction']))
    rr[-1].update(top24_changed=bool(np.argmax(np.array(r['q_sequence'])[sub])!=np.argmax(np.array(sham['q_sequence'])[sub])),correct24_before=bool(sub[np.argmax(np.array(sham['q_sequence'])[sub])]==g),correct24_after=bool(sub[np.argmax(np.array(r['q_sequence'])[sub])]==g))
 paired=[];ps=[]
 for l in [14,21,28]:
  ll=[r for r in rr if r['layer']==l];effects=[]
  for cid in sorted({r['case_id'] for r in ll}):
   d={r['condition']:r for r in ll if r['case_id']==cid};a=d['remove_target'];b=d['random_matched'];delta=a['attenuation']-b['attenuation'] if a['attenuation'] is not None else None;paired.append(dict(case_id=cid,layer=l,target_minus_random_attenuation=delta,same_first_token=a['same_first_token'],natural_update=a['natural_update'],projection_fraction=a['projection_fraction']));
   if delta is not None:effects.append(delta)
  p=sign_permutation(effects);ps.append(p);out[str(l)]=dict(patients=len(effects),target_minus_random=summary(effects),p_unadjusted=p,projection_fraction=summary([r['projection_fraction'] for r in ll if r['condition']=='self']),conditions={cond:dict(attenuation=summary([r['attenuation'] for r in ll if r['condition']==cond]),raw_effect=summary([r['effect_vs_sham'] for r in ll if r['condition']==cond]),top_changes=sum(r['top_changed'] for r in ll if r['condition']==cond),correct_after=sum(r['correct_after'] for r in ll if r['condition']==cond)) for cond in ['self','remove_target','random_matched','replace_old']})
 for l,p in zip([14,21,28],holm(ps)):
  out[str(l)]['p_holm']=p;target=[r for r in rr if r['layer']==l and r['condition']=='remove_target'];out[str(l)]['probe_attenuation']=summary([r['probe_attenuation'] for r in target]);out[str(l)]['probe_update_reversed_count']=sum(r['probe_attenuation']>0 for r in target if r['probe_attenuation'] is not None)
  for cond in ['self','remove_target','random_matched','replace_old']:out[str(l)]['conditions'][cond].update(top24_changes=sum(r['top24_changed'] for r in rr if r['layer']==l and r['condition']==cond),correct24_after=sum(r['correct24_after'] for r in rr if r['layer']==l and r['condition']==cond))
 same=[r for r in rr if r['layer']==28 and r['same_first_token'] and r['condition']!='self'];result=dict(patients=N,replication=args.replication,conditions=len(rr),layers=out,sham_max_logp_error=max(checks),last_layer_same_first_token_patients=len({r['case_id'] for r in same}),last_layer_same_first_token_max_margin_effect=max([abs(r['effect_vs_sham']) for r in same],default=None),api_cost_usd=0)
 csvwrite(dest/'all_conditions.csv',rr);csvwrite(dest/'paired_patients.csv',paired);dump(dest/'summary.json',result)
 fig,axs=plt.subplots(1,2,figsize=(12,4),layout='constrained');labels=['14','21','28'];means=[out[x]['target_minus_random']['mean'] for x in labels];low=[out[x]['target_minus_random']['low'] for x in labels];high=[out[x]['target_minus_random']['high'] for x in labels];axs[0].errorbar(range(3),means,yerr=[np.array(means)-low,np.array(high)-means],fmt='o',capsize=4);axs[0].axhline(0,color='gray',ls='--');axs[0].set(xticks=range(3),xticklabels=labels,xlabel='干预层',ylabel='目标移除−随机移除：输出回退量',title='移除自然疾病分量，是否更能抵消更新？')
 for i,cond in enumerate(['remove_target','random_matched','replace_old']):axs[1].bar(np.arange(3)+(i-1)*.23,[out[l]['conditions'][cond]['top_changes'] for l in labels],width=.23,label={'remove_target':'移除疾病方向分量','random_matched':'等范数随机改动','replace_old':'换回旧诊断锚点'}[cond])
 axs[1].set(xticks=range(3),xticklabels=labels,xlabel='干预层',ylabel=f'首选改变病例数（每组{N}）');axs[1].legend(fontsize=8);savefig(fig,dest/'figures/natural_necessity')
 tab='\n'.join(f'| {l} | {fmt(out[l]["target_minus_random"],False)} | {out[l]["p_holm"]:.4f} | {out[l]["conditions"]["remove_target"]["top_changes"]}/{N} |' for l in labels);sig=[l for l in labels if out[l]['p_holm']<.05 and out[l]['target_minus_random']['mean']>0];claim=('在第'+ '、'.join(sig)+'层，移除自然变化中的疾病分量，比同范数随机移除更强地抵消了原输出更新。') if sig else '本次没有测得：移除自然变化中的疾病分量，比同范数随机移除更强地抵消原输出更新。此前“人工推动方向能影响分数”的结果，不能替代自然必要性的证据。'
 (dest/'RESULTS.md').write_text(f'''# 自然内部变化，是否真的参与了诊断更新？

**{claim}**

{N}个新患者、每病{N//24}例，在预定中间轮加入一条证据。先测量新旧状态差，再在新证据输入不变的条件下，删掉其中沿疾病读出方向的分量。对照是同等长度的随机正交改动，另有零改动及完整换回旧锚点。第14、21、28层预先指定，共{N*12}个条件。{'本页为独立48例复核组；与首批24例分开统计。' if args.replication else '本页为首批24例；追加48例复核单独保存。'}

| 层 | 目标移除比随机移除多造成的回退 | 三层Holm校正p | 目标移除改变首选 |
|---|---|---:|---:|
{tab}

![自然更新必要性](figures/natural_necessity.png)

回退量以原模型固定疾病对的完整字符串对数分差计算，正值表示抵消原来的更新方向；统计单位是患者。主对比由两种干预相减，零干预用来核验复现。零干预最大log概率误差为{max(checks):.6f}。

本实验只改诊断位置的状态，并保留其他位置及更早层缓存。它检验这一位置、这一方向的作用，不是把新证据从整个网络删除。最后一层两候选同首词元的结构性对照共{result['last_layer_same_first_token_patients']}例，其病对分差最大变化{result['last_layer_same_first_token_max_margin_effect']}。

[每个条件](all_conditions.csv) · [每个患者的配对差](paired_patients.csv) · [精确汇总](summary.json)
''');print(json.dumps(clean(result),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
