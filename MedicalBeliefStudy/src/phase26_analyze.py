"""Evidence order, removal, repeated facts and matched historical diagnoses."""
import collections
import numpy as np
import matplotlib.pyplot as plt
from belief_v3_analysis import *

def main():
 run=ROOT/'runs/belief_v3';context=run/'evidence_context';matched=run/'history_matched';assert (context/'completion.json').exists() and (matched/'completion.json').exists();dest=ROOT/'results/25_history_and_evidence';(dest/'figures').mkdir(parents=True,exist_ok=True);setup();cases=rows(ROOT/'data/belief_v3/cases.private.jsonl');ds=rows(ROOT/'data/belief_v3/jobs.jsonl')[0]['candidate_diseases'];heads=np.load(ROOT/'results/14_fixed_panel/training_heads.npz');cl=heads['classes'].tolist();order=[];abl=[];history=[];hlayers=[];ctx=[];ctxcases=[]
 for c in cases:
  if not c['deep_capture']:continue
  cid=c['case_id'];g=ds.index(c['gold_disease']);base=load_record(run,c);bq=np.array(base['q_sequence'])
  for o in ['reverse','shuffle']:
   r=load_record(run,c,order=o);q=np.array(r['q_sequence']);order.append(dict(case_id=cid,order=o,gold=c['gold_disease'],base_top=ds[bq.argmax()],changed_top=ds[q.argmax()],switched=bool(q.argmax()!=bq.argmax()),correct_before=bool(bq.argmax()==g),correct_after=bool(q.argmax()==g),delta_gold=q[g]-bq[g],js=float(js(q,bq))))
  if not c['mechanism_capture']:continue
  for cond in ['repeat_middle','remove_middle','omit_named_history']:
   r=read(run/'observations'/f'{cid}_{cond}.json');q=np.array(r['q_sequence']);abl.append(dict(case_id=cid,condition=cond,gold=c['gold_disease'],base_top=ds[bq.argmax()],changed_top=ds[q.argmax()],switched=bool(q.argmax()!=bq.argmax()),correct_before=bool(bq.argmax()==g),matches_source_after=bool(q.argmax()==g),delta_gold=q[g]-bq[g],js=float(js(q,bq)),removed_groups=';'.join(r['removed_groups']),removed_count=len(r['removed_groups']),same_prompt=base['prompt_sha256']==r['prompt_sha256']))
   if cond=='omit_named_history' and not r['removed_groups']:assert base['prompt_sha256']==r['prompt_sha256'] and np.max(abs(q-bq))<1e-5
  mid=c['fixed_middle_round'];bm=load_record(run,c,mid);records={cond:read(run/'observations'/f'{cid}_{cond}.json') for cond in ['history_actual','history_gold','history_wrong','history_wrong_final']};records['history_gold_final']=read(matched/f'{cid}.json');w=ds.index(records['history_wrong']['prior_disease']);yi=cl.index(c['gold_disease']);ci=cl.index(ds[w]) if ds[w] in cl else None
  bystage={}
  for stage,gr,wr,ref,grrun in [('middle',records['history_gold'],records['history_wrong'],bm,run),('final',records['history_gold_final'],records['history_wrong_final'],base,matched)]:
   qs=np.array(gr['q_sequence']);qw=np.array(wr['q_sequence']);qb=np.array(ref['q_sequence']);mg=support_margin(gr,w,g);mw=support_margin(wr,w,g);gain=mw-mg;sg=readout(grrun,gr,heads);sw=readout(run,wr,heads);rg=1+(sg>sg[:,yi,None]).sum(-1);rw=1+(sw>sw[:,yi,None]).sum(-1);bystage[stage]=gain
   history.append(dict(case_id=cid,stage=stage,gold=c['gold_disease'],wrong_prior=ds[w],wrong_prior_in24=ci is not None,matched_wrong_vs_gold_margin_gain=gain,wrong_history_top=ds[qw.argmax()],gold_history_top=ds[qs.argmax()],no_history_top=ds[qb.argmax()],wrong_history_endorses_prior=bool(qw.argmax()==w),gold_history_endorses_wrong_prior=bool(qs.argmax()==w),wrong_history_matches_gold=bool(qw.argmax()==g),gold_history_matches_gold=bool(qs.argmax()==g),native_matched_top_change=bool(qw.argmax()!=qs.argmax()),wrong_history_probe_last=cl[sw[-1].argmax()],gold_history_probe_last=cl[sg[-1].argmax()],probe_matched_top_change=bool(sw[-1].argmax()!=sg[-1].argmax()),gold_rank_change_last=int(rw[-1]-rg[-1]),nohistory_vs_wrong_margin_gain=support_margin(wr,w,g)-support_margin(ref,w,g)))
   with np.load(run/wr['state_file']) as a:A=a['attention_by_group'].astype(float);hw=a['residual_stages'][:,4].astype(float)
   with np.load(grrun/gr['state_file']) as a:hg=a['residual_stages'][:,4].astype(float)
   for l in range(28):hlayers.append(dict(case_id=cid,stage=stage,layer=l+1,gold_rank_change=int(rw[l]-rg[l]),wrong_minus_gold_probe_margin=(sw[l,ci]-sw[l,yi])-(sg[l,ci]-sg[l,yi]) if ci is not None else None,prior_attention=float(A[l,:,-1].mean()),state_relative_change=float(np.linalg.norm(hw[l]-hg[l])/max(np.linalg.norm(hg[l]),1e-12))))
  for r in history:
   if r['case_id']==cid:r['final_minus_middle_matched_history_gain']=bystage['final']-bystage['middle']
  ra=records['history_actual'];qa=np.array(ra['q_sequence']);history.append(dict(case_id=cid,stage='actual_middle',gold=c['gold_disease'],actual_prior=ra['prior_disease'],actual_prior_is_gold=ra['prior_disease']==c['gold_disease'],actual_prior_endorsed=ds[qa.argmax()]==ra['prior_disease'],no_history_top=ds[np.argmax(bm['q_sequence'])],actual_history_top=ds[qa.argmax()],actual_history_matches_gold=ds[qa.argmax()]==c['gold_disease']))
  comp=max((i for i in range(49) if i!=g),key=lambda i:base['log_probability'][i]);M=support_margin(base,g,comp);path=[load_record(run,c,t) for t in range(len(c['orders']['base'])+1)];effects=[]
  for t,gid in enumerate([c['initial_question_group']]+c['orders']['base']):
   r=read(context/f'{cid}_omit{t:02d}.json');effect=M-support_margin(r,g,comp);seq=support_margin(path[t],g,comp)-support_margin(path[t-1],g,comp) if t else None;valid=t>0 and abs(seq)>=1e-4 and abs(effect)>=1e-4;row=dict(case_id=cid,source_round=t,gold=c['gold_disease'],competitor=ds[comp],evidence_group=gid,evidence_type=evidence_type(c['explicit_evidence_groups'][gid]),sequential_effect=seq,full_context_effect=effect,sign_eligible=valid,opposite_sign=bool(seq*effect<0) if valid else None,full_top=ds[bq.argmax()],without_group_top=ds[np.argmax(r['q_sequence'])]);ctx.append(row);effects.append(row)
  rr=[r for r in effects if r['source_round']];valid=[r for r in rr if r['sign_eligible']];cc=dict(case_id=cid,updates=len(rr),eligible=len(valid),opposite=sum(r['opposite_sign'] for r in valid),opposite_rate=float(np.mean([r['opposite_sign'] for r in valid])) if valid else None,effect_correlation=rho([r['sequential_effect'] for r in rr],[r['full_context_effect'] for r in rr]));
  for thr in [1e-3,1e-2]:
   v=[r for r in rr if abs(r['sequential_effect'])>=thr and abs(r['full_context_effect'])>=thr];cc[f'opposite_rate_{thr}']=float(np.mean([r['sequential_effect']*r['full_context_effect']<0 for r in v])) if v else None
  ctxcases.append(cc)
 s=dict(order={o:dict(cases=72,switched=summary([r['switched'] for r in order if r['order']==o]),paired_accuracy_change=summary([float(r['correct_after'])-float(r['correct_before']) for r in order if r['order']==o])) for o in ['reverse','shuffle']},evidence_controls={cond:dict(cases=24,switched=summary([r['switched'] for r in abl if r['condition']==cond]),delta_gold=summary([r['delta_gold'] for r in abl if r['condition']==cond]),affected_by_ablation=sum(r['removed_count']>0 for r in abl if r['condition']==cond) if cond=='omit_named_history' else 24) for cond in ['repeat_middle','remove_middle','omit_named_history']},history={},context=dict(cases=24,removed_groups=len(ctx),updates=sum(c['updates'] for c in ctxcases),eligible=sum(c['eligible'] for c in ctxcases),opposite_events=sum(c['opposite'] for c in ctxcases),opposite_rate=summary([c['opposite_rate'] for c in ctxcases]),correlation=summary([c['effect_correlation'] for c in ctxcases]),sensitivity={str(thr):summary([c[f'opposite_rate_{thr}'] for c in ctxcases]) for thr in [1e-3,1e-2]}),api_cost_usd=0)
 for stage in ['middle','final']:
  rr=[r for r in history if r['stage']==stage];s['history'][stage]={key:summary([r[key] for r in rr]) for key in ['matched_wrong_vs_gold_margin_gain','wrong_history_endorses_prior','gold_history_endorses_wrong_prior','wrong_history_matches_gold','gold_history_matches_gold','native_matched_top_change','probe_matched_top_change','gold_rank_change_last']}
 s['history']['final_minus_middle_gain']=summary([r['final_minus_middle_matched_history_gain'] for r in history if r['stage']=='final']);p=sign_permutation([r['final_minus_middle_matched_history_gain'] for r in history if r['stage']=='final']);s['history']['final_minus_middle_gain_p_exploratory']=p
 for name,data in [('order_cases',order),('evidence_controls',abl),('history_cases',history),('history_layers',hlayers),('context_group_effects',ctx),('context_case_metrics',ctxcases)]:csvwrite(dest/(name+'.csv'),data)
 dump(dest/'summary.json',s)
 fig,axs=plt.subplots(1,3,figsize=(15,4),layout='constrained');conds=['reverse','shuffle','repeat_middle','remove_middle','omit_named_history'];vals=[s['order'][o]['switched']['mean'] for o in conds[:2]]+[s['evidence_controls'][o]['switched']['mean'] for o in conds[2:]];axs[0].barh(['反序','乱序','重复中间证据','移除中间证据','隐藏具名既往史'],vals);axs[0].set(xlabel='首选改变比例',xlim=(0,1));vv=[r for r in ctx if r['source_round']];axs[1].scatter([r['sequential_effect'] for r in vv],[r['full_context_effect'] for r in vv],s=12,alpha=.5);axs[1].axhline(0,color='gray',lw=.7);axs[1].axvline(0,color='gray',lw=.7);axs[1].set(xlabel='顺序到来时的病对分差变化',ylabel='完整背景中保留该组的影响',title='同一条证据，方向是否改变？')
 for stage,label in [('middle','中间轮'),('final','完整证据')]:
  rr=[r for r in hlayers if r['stage']==stage];axs[2].plot(range(1,29),[np.mean([r['gold_rank_change'] for r in rr if r['layer']==l]) for l in range(1,29)],label=label)
 axs[2].axhline(0,color='gray',ls='--');axs[2].set(xlabel='模型层',ylabel='错误历史使来源诊断排名后退多少',title='先前判断是否改变内部可读信息？');axs[2].legend();savefig(fig,dest/'figures/evidence_and_history')
 tab='\n'.join(f'| {label} | {fmt(s["history"][stage]["native_matched_top_change"])} | {fmt(s["history"][stage]["probe_matched_top_change"])} | {fmt(s["history"][stage]["wrong_history_endorses_prior"])} | {fmt(s["history"][stage]["matched_wrong_vs_gold_margin_gain"],False)} |' for stage,label in [('middle','中间轮'),('final','完整事实')]);ct=s['context']
 (dest/'RESULTS.md').write_text(f'''# 证据的作用，是否取决于顺序、背景和先前判断？

## 同样的全部事实，换顺序

72例中，反序后首选改变{fmt(s['order']['reverse']['switched'])}；确定性乱序改变{fmt(s['order']['shuffle']['switched'])}。24例中，重复一次中间证据改变{fmt(s['evidence_controls']['repeat_middle']['switched'])}。重复不引入新事实，但也可能改变强调和位置。

## 同样的当前事实，换先前诊断

24例分别放入正确或预定错误的先前诊断，其他消息结构与重审指令一致。当前事实相同；“正确”指完整病例来源病名，是离线控制。原模型比较49病，内部读出比较冻结24病，因此两种首选切换率分别报告。

| 证据阶段 | 原模型首选因历史不同而改变 | 最后一层读出首选改变 | 错误历史中选中该错误病 | 错误病相对来源病的分差增益 |
|---|---|---|---|---|
{tab}

错误/正确历史之间的病名分差差距，从中间到终点变化为{fmt(s['history']['final_minus_middle_gain'],False)}；负值表示更多事实后历史病名的影响减弱。这是配对描述，未预先规定一定应减弱。

![证据与历史](figures/evidence_and_history.png)

## 同一条证据，放在不同背景里

对24例完整病例逐一删掉每组证据，共{ct['removed_groups']}个删组条件。固定比较“来源病”与完整病例下最强的另一病：计算这条证据刚到来时的作用，再计算它在完整背景中的作用。

{ct['eligible']}次非微小的可比较更新中，有{ct['opposite_events']}次方向相反；先患者内求比例再平均为**{fmt(ct['opposite_rate'])}**。病例内两种作用的相关为{fmt(ct['correlation'],False)}。阈值从1e-4改为1e-3、1e-2的结果见summary.json。这说明模型对某条证据的支持方向依赖其他已知事实；它本身不等于医学推理错误。

原始源码中的一个证据组可能包含多个问题子项，删除单位为整个组。隐藏具名既往史和删组都改变信息内容，不以删减后的来源标签命中率评价临床正确性。无历史条件的消息结构与有历史不同，因此主要历史对比使用正确/错误历史配对。

[顺序](order_cases.csv) · [重复与删组](evidence_controls.csv) · [历史对照](history_cases.csv) · [历史的逐层影响](history_layers.csv) · [每条证据两种背景下的作用](context_group_effects.csv) · [精确汇总](summary.json)
''');print(json.dumps(clean(s),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
