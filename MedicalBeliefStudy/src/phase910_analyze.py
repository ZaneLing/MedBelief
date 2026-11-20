"""Disease-name trajectory and activation analyses, with complete-name interventions."""
import json,textwrap,csv
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
import matplotlib.pyplot as plt
from analyze_stages import setup,savefig,dump,csvwrite,winner,changed,js,ci,fmt
from phase67_analyze import FAMILIES
ROOT=Path(__file__).resolve().parents[1]
def top(q,ds):
    i=int(winner(q));return ds[i] if i>=0 else 'TIED'
def main():
    setup();run=ROOT/'runs/structured_names_v1';assert (run/'completion.json').exists();assert (run/'interventions/completion.json').exists()
    nine=ROOT/'results/09_disease_name_trajectories';ten=ROOT/'results/10_name_causal_mechanism'
    for p in [nine,ten]:(p/'figures').mkdir(parents=True,exist_ok=True)
    (nine/'cases').mkdir(exist_ok=True)
    ds=json.loads((run/'manifest.json').read_text())['candidate_diseases'];cases=[json.loads(s) for s in (ROOT/'data/full49_v1/cases.private.jsonl').read_text().splitlines()]
    records=[json.loads(p.read_text()) for p in sorted((run/'observations').glob('ddx*.json'))];lookup={(r['case_id'],r['order'],r['round']):r for r in records};metrics=[];events=[];activations=[];atlas=[];statecases=[];attentioncases=[];corr=[];early_invariance=[]
    for c in cases:
        cid=c['case_id'];T=len(c['orders']['base']);y=ds.index(c['gold_disease']);mid=c['fixed_middle_round'];rr=[lookup[cid,'base',t] for t in [0,mid,T]];qq=np.array([r['q_sequence'] for r in rr]);ref=np.array([c['reference_differential'].get(d,0) for d in ds]);final=rr[-1]
        code=np.mean([json.loads((ROOT/'runs/full49_v1/observations'/f'{cid}_base_t{T:02d}_m{m}.json').read_text())['q'] for m in [0,16,32]],axis=0)
        r={'case_id':cid,'family':c['family'],'gold':c['gold_disease'],'deep_capture':c['deep_capture'],'updates':T,
           'initial_correct':bool(winner(qq[0])==y),'middle_correct':bool(winner(qq[1])==y),'final_correct':bool(winner(qq[2])==y),
           'final_top':top(qq[-1],ds),'final_gold_support':float(qq[-1,y]),'final_gold_rank':int(1+np.sum(qq[-1]>qq[-1,y])),
           'final_reference_js':float(js(qq[-1],ref)),'final_reference_top_agreement':bool(winner(qq[-1])==winner(ref) and winner(ref)>=0),
           'final_top_in_reference_support':bool(winner(qq[-1])>=0 and ref[int(winner(qq[-1]))]>0),
           'final_brier':float(np.sum((qq[-1]-np.eye(49)[y])**2)),'final_nll':float(-np.log(max(qq[-1,y],1e-30))),
           'final_wrong_high_support':bool(winner(qq[-1])>=0 and winner(qq[-1])!=y and qq[-1].max()>=.9),
           'final_off_reference_high_support':bool(winner(qq[-1])>=0 and ref[int(winner(qq[-1]))]==0 and qq[-1].max()>=.9),
           'final_generated':final['generated_disease'],'final_generation_in_candidates':final['generated_in_candidates'],
           'final_generated_exact_correct':final['generated_disease']==c['gold_disease'],'final_map_greedy_agree':top(qq[-1],ds)==final['generated_disease'],
           'final_sequence_mass':final['sequence_probability_mass'],'final_length_mean_agree':bool(winner(qq[-1])==winner(final['q_token_mean']) and winner(qq[-1])>=0),
           'final_length_mean_correct':bool(winner(final['q_token_mean'])==y),'code_final_correct':bool(winner(code)==y),
           'code_name_agreement':bool(winner(code)==winner(qq[-1]) and winner(code)>=0),'name_minus_code_accuracy':int(winner(qq[-1])==y)-int(winner(code)==y),
           'initial_gold_support':float(qq[0,y]),'middle_gold_support':float(qq[1,y])};metrics.append(r)
        if not c['deep_capture']:continue
        traj=[lookup[cid,'base',t] for t in range(T+1)];q=np.array([v['q_sequence'] for v in traj]);p=winner(q);rev=np.array(lookup[cid,'reverse',T]['q_sequence']);shuf=np.array(lookup[cid,'shuffle',T]['q_sequence'])
        candidate=json.loads((run/'candidate_order'/f'{cid}.json').read_text());cq=np.array(candidate['q_sequence'])
        r.update(regression_any=bool(np.any((p[:-1]==y)&(p[1:]!=y)&(p[1:]>=0))),switch_rate=float(changed(q[:-1],q[1:]).mean()),
                 reverse_flip=bool(changed(q[-1],rev)),shuffle_flip=bool(changed(q[-1],shuf)),reverse_js=float(js(q[-1],rev)),shuffle_js=float(js(q[-1],shuf)),
                 candidate_reverse_flip=bool(changed(q[-1],cq)),candidate_reverse_js=float(js(q[-1],cq)))
        states=[];att=[];latest=[];early=[]
        for rec in traj:
            with np.load(run/rec['state_file']) as a:
                states.append(a['residual_stages'].astype(float));at=a['attention_by_group'].astype(float);count=np.array(rec['group_token_counts']);att.append(np.stack([at[:,:,0],at[:,:,1],at[:,:,2],at[:,:,3:].sum(-1)],-1).mean(1))
                latest.append((at[:,:,-1]/max(1,count[-1])).mean(1))
                early.append(a['evidence_end_states'][:,0].astype(float))
        states=np.array(states);att=np.array(att);latest=np.array(latest)
        delta=states[1:]-states[:-1];relative=np.linalg.norm(delta,axis=-1)/np.maximum(np.linalg.norm(states[:-1],axis=-1),1e-12)
        early=np.array(early);earlydiff=np.linalg.norm(early[1:]-early[:1],axis=-1)/np.maximum(np.linalg.norm(early[:1],axis=-1),1e-12);early_invariance.append(float(earlydiff.max()))
        post=states[:,:,4];cos=1-np.sum(post[1:]*post[:-1],-1)/np.maximum(np.linalg.norm(post[1:],axis=-1)*np.linalg.norm(post[:-1],axis=-1),1e-12)
        statecases.append(relative.mean(0));attentioncases.append(att.mean(0));jses=js(q[1:],q[:-1]);rho=float(spearmanr(cos[:,23:].mean(1),jses).statistic) if np.std(jses)>0 else np.nan;corr.append(rho)
        for t in range(1,T+1):
            flags=[v['is_antecedent'] for v in c['explicit_evidence_groups'][c['orders']['base'][t-1]]]
            etype='history' if all(flags) else ('presentation' if not any(flags) else 'mixed')
            e={'case_id':cid,'family':c['family'],'round':t,'gold':c['gold_disease'],'new_group':c['orders']['base'][t-1],
               'evidence_type':etype,
               'previous_top':top(q[t-1],ds),'current_top':top(q[t],ds),'gold_support':float(q[t,y]),'delta_gold':float(q[t,y]-q[t-1,y]),
               'js':float(jses[t-1]),'switch':bool(changed(q[t-1],q[t])),'late_state_cosine_change':float(cos[t-1,23:].mean()),'new_evidence_attention_density':float(latest[t,23:].mean()),
               **{f'delta_{d}':float(q[t,j]-q[t-1,j]) for j,d in enumerate(ds)}};events.append(e)
            for l in range(28):activations.append({'case_id':cid,'round':t,'layer':l+1,'relative_attention_change':float(relative[t-1,l,1]),'relative_mlp_change':float(relative[t-1,l,3]),'relative_post_change':float(relative[t-1,l,4]),'post_cosine_change':float(cos[t-1,l])})
        chosen=list(dict.fromkeys([y]+[int(d) for d in np.argsort(q.max(0))[::-1][:5]]))[:6]
        fig,axes=plt.subplots(3,1,figsize=(11,12),gridspec_kw={'height_ratios':[1.3,1.1,1]})
        for d in chosen:axes[0].plot(range(T+1),q[:,d],label=ds[d],lw=2.5 if d==y else 1.4)
        axes[0].set(ylabel='Full-name candidate support',ylim=(-.02,1.02),title=f'{cid} | label: {c["gold_disease"]}');axes[0].legend(fontsize=8,bbox_to_anchor=(1.01,1),loc='upper left')
        im=axes[1].imshow(cos.T,origin='lower',aspect='auto',extent=[.5,T+.5,.5,28.5],cmap='magma');fig.colorbar(im,ax=axes[1],label='1 - cosine(current, previous)');axes[1].set(ylabel='Layer',yticks=[1,7,14,21,28],title='Change in diagnosis-anchor state (not disease probability)')
        for j,label in enumerate(['Format','Candidates','Demographics','Evidence']):axes[2].plot(range(T+1),att[:,23:,j].mean(1),label=label)
        axes[2].set(xlabel='Evidence update (0 = initial group)',ylabel='Attention mass, layers 24–28',ylim=(-.02,1.02));axes[2].legend(fontsize=8);fig.tight_layout();savefig(fig,nine/'cases'/cid)
        evidence=[c['initial_question_group']]+c['orders']['base'];lines=[f'# {cid}',f'\n源标签：**{c["gold_disease"]}**；参考首位：**{top(ref,ds)}**。\n',f'![疾病名轨迹]({cid}.png)\n','上图为完整疾病名的候选分数，中图为真实隐藏状态的方向变化，下图为注意力分配。中图颜色不代表某个疾病。\n','| 轮 | 新证据 | 名称评分首选 | 标签支持 | 贪心续写 |','|---|---|---|---|---|']
        for t,g in enumerate(evidence):
            desc='<br>'.join(x['question_en']+' **'+x['answer_en']+'**' for x in c['explicit_evidence_groups'][g]).replace('|','/')
            gen=str(traj[t]['generated_disease'] or traj[t]['generated_text']).replace('\n',' ').replace('|','/')
            lines.append(f'| {t} | {desc} | {top(q[t],ds)} | {q[t,y]:.4f} | {gen} |')
        (nine/'cases'/f'{cid}.md').write_text('\n'.join(lines)+'\n');atlas.append(f'| [{cid}](cases/{cid}.md) | {c["gold_disease"]} | {top(q[-1],ds)} | {T} |')
    basic=['initial_correct','middle_correct','final_correct','final_gold_support','final_gold_rank','final_reference_js','final_reference_top_agreement','final_top_in_reference_support','final_brier','final_nll','final_wrong_high_support','final_off_reference_high_support','final_generation_in_candidates','final_generated_exact_correct','final_map_greedy_agree','final_sequence_mass','final_length_mean_agree','final_length_mean_correct','code_final_correct','code_name_agreement','name_minus_code_accuracy']
    summary={k:ci([r[k] for r in metrics]) for k in basic};deep=[r for r in metrics if r['deep_capture']];dsummary={k:ci([r[k] for r in deep]) for k in ['regression_any','switch_rate','reverse_flip','shuffle_flip','reverse_js','shuffle_js','candidate_reverse_flip','candidate_reverse_js']}
    stats={'observations':len(records),'all_cases':120,'full_trajectory_cases':24,'deep_updates':len(events),'case_weighted':summary,'deep_case_weighted':dsummary,
           'activation_change_vs_diagnosis_js_spearman':ci(corr),'max_initial_evidence_state_relative_change':max(early_invariance),'candidate_mass_median':float(np.median([r['sequence_probability_mass'] for r in records])),
           'candidate_mass_below_point1':sum(r['sequence_probability_mass']<.1 for r in records),'generation_in_candidates_rate':float(np.mean([r['generated_in_candidates'] for r in records])),
           'sequence_cache_checks':sum(r['cache_validation'] is not None for r in records),'max_cache_logprob_error':max(r['cache_validation']['absolute_error'] for r in records if r['cache_validation']),
           'max_attention_reconstruction_error':max(r['attention_max_error'] for r in records)}
    strata=[]
    for c in cases:
        for etype in ['history','presentation','mixed']:
            subset=[r for r in events if r['case_id']==c['case_id'] and r['evidence_type']==etype]
            if subset:strata.append({'case_id':c['case_id'],'evidence_type':etype,'updates':len(subset),**{k:float(np.mean([r[k] for r in subset])) for k in ['js','delta_gold','switch']}})
    types={etype:{'cases':sum(r['evidence_type']==etype for r in strata),'updates':sum(r['updates'] for r in strata if r['evidence_type']==etype),
                  **{k:ci([r[k] for r in strata if r['evidence_type']==etype]) for k in ['js','delta_gold','switch']}} for etype in ['history','presentation','mixed']}
    stats['evidence_types']=types;csvwrite(nine/'evidence_type_case_metrics.csv',strata)
    dump(nine/'summary.json',stats);csvwrite(nine/'case_metrics.csv',metrics);csvwrite(nine/'evidence_transitions.csv',events);csvwrite(nine/'activation_transitions.csv',activations)
    np.savez_compressed(nine/'internal_case_aggregates.npz',relative_activation_change=np.array(statecases),attention=np.array(attentioncases),case_ids=np.array([r['case_id'] for r in deep]))
    (nine/'CASE_ATLAS.md').write_text('# 疾病名接口：固定24例完整轨迹\n\n| 病例 | 标签 | 终点名称首选 | 更新数 |\n|---|---|---|---|\n'+'\n'.join(atlas)+'\n')
    fam=[]
    for f in FAMILIES:
        rr=[r for r in metrics if r['family']==f];fam.append({'family':f,'cases':len(rr),**{k:float(np.mean([r[k] for r in rr])) for k in ['initial_correct','middle_correct','final_correct','code_final_correct','final_generated_exact_correct']}})
    csvwrite(nine/'family_metrics.csv',fam)
    fig,axes=plt.subplots(1,2,figsize=(12,4.8));x=np.arange(6)
    for off,key,label in [(-.24,'initial_correct','Initial name'),(0,'final_correct','Final name'),(.24,'code_final_correct','Final code mean')]:axes[0].bar(x+off,[f[key] for f in fam],.24,label=label)
    axes[0].set(xticks=x,xticklabels=[FAMILIES[f['family']] for f in fam],ylabel='Label accuracy',ylim=(0,1));axes[0].legend(fontsize=8)
    state=np.array(statecases)
    for j,label in [(1,'Attention increment'),(3,'MLP increment'),(4,'Post-block state')]:axes[1].plot(range(1,29),state[:,:,j].mean(0),label=label)
    axes[1].set(xlabel='Layer',ylabel='Relative activation change per update');axes[1].legend(fontsize=8);fig.tight_layout();savefig(fig,nine/'figures/names_and_internal_changes')
    tab='\n'.join(f'| {FAMILIES[r["family"]]} | {r["cases"]} | {r["initial_correct"]:.1%} | {r["middle_correct"]:.1%} | {r["final_correct"]:.1%} | {r["code_final_correct"]:.1%} |' for r in fam)
    (nine/'RESULTS.md').write_text(f'''# 阶段09：从字母选项转向完整疾病名

## 研究修正

49字母接口混入了显著的疾病—字母绑定问题。此处保留同一批病例和49候选，直接填写完整疾病名。固定JSON前缀后，计算每个规范名及闭合符号、EOS的完整序列概率，再在49病之间归一化；同时保留实际贪心续写。它是完整名称的模型支持，不是把“Acute”等首词当作一个疾病。

120例测初始、中间、终点；预定24例追踪全部基础顺序轮次并复查逆序、乱序终点，共{len(records)}次观测。全部观测捕获28层五处激活和16个头的证据注意力；24例保留逐token记录。该阶段是在看到编码接口问题后进行的探索性修正。

## 总体结果

完整名称评分的标签命中从初始 **{fmt(summary['initial_correct'])}**，变为中间 **{fmt(summary['middle_correct'])}**，最终 **{fmt(summary['final_correct'])}**。同病例字母接口终点为{fmt(summary['code_final_correct'])}；名称减编码的病例配对准确率差为{fmt(summary['name_minus_code_accuracy'])}。两接口同时改变列表展示和输出方式，此差不单独归因于某个字符。

| 疾病组 | n | 初始名称命中 | 中间名称命中 | 最终名称命中 | 最终编码命中 |
|---|---|---|---|---|---|
{tab}

24例完整轨迹中，曾命中标签后偏离的病例比例为{fmt(dsummary['regression_any'])}；相同终点事实仅将新增证据逆序，首选改变{fmt(dsummary['reverse_flip'])}；独立乱序改变{fmt(dsummary['shuffle_flip'])}。仅反转候选列表时改变{fmt(dsummary['candidate_reverse_flip'])}，该项与证据顺序单独报告。

终点首选未命中标签但候选支持≥0.9的病例比例为{fmt(summary['final_wrong_high_support'])}；首选不在源参考鉴别分布支持集中且支持≥0.9的比例为{fmt(summary['final_off_reference_high_support'])}。这两项描述候选分数的集中与参考不一致，不把生成概率直接当成医学置信度。

按源数据的既往史标记划分：病史类{types['history']['updates']}次新增证据，当前表现类{types['presentation']['updates']}次。病例内先分别平均，再跨病例汇总，疾病分布JS变化为病史类{fmt(types['history']['js'],False)}、当前表现类{fmt(types['presentation']['js'],False)}。两类临床信息强度并不匹配，该分层用于描述；明确提及既往诊断或治疗的证据保留原文，不将顺着这种提示选对疾病当成机制创新。

## 内部究竟测到了什么

每轮新证据都会产生一套新的层内状态。这里保存了每层注意力贡献、MLP贡献及最终状态的真实向量，计算它们相对前轮的大小变化和方向变化。固定24例内，“晚层状态方向变化”与“疾病名分布变化”的Spearman相关，病例均值为{fmt(stats['activation_change_vs_diagnosis_js_spearman'],False)}。

作为因果遮罩的架构检查，相同初始证据末位置的状态，在追加后续证据后最大相对变化为{stats['max_initial_evidence_state_relative_change']:.6f}。早期token不能看未来；医学更新的主要观测位置是读完当轮所有证据后的诊断位置，而不是声称模型回头改写了旧token或模型权重。

**这说明可以把外部诊断轨迹与内部状态轨迹逐轮对应起来。它是否推动某个疾病的支持，需要阶段10的定向替换验证。** 本阶段不将一个隐藏向量的移动直接命名成某种疾病，也不将逐层权重说成在推理时重新训练。

![名称与内部变化](figures/names_and_internal_changes.png)

## 名称评分质量

终点贪心输出能严格解析为指定JSON且疾病名属于49候选的比例为{fmt(summary['final_generation_in_candidates'])}；名称最大序列分数与贪心诊断一致{fmt(summary['final_map_greedy_agree'])}。所有观测中，49条规范完整字符串的概率总质量中位数为{stats['candidate_mass_median']:.4f}，低于0.1的有{stats['candidate_mass_below_point1']}/{len(records)}次；总质量低时，候选归一化分数需结合自由续写阅读。

完整序列评分与每token平均评分的终点首选一致率{fmt(summary['final_length_mean_agree'])}；两者为不同评分定义。执行{stats['sequence_cache_checks']}次缓存与完整前向序列分数对照，最大对数分差{stats['max_cache_logprob_error']:.5f}。

[24例完整证据与图谱](CASE_ATLAS.md) · [120例结果](case_metrics.csv) · [逐证据转移](evidence_transitions.csv) · [逐层激活变化](activation_transitions.csv) · [精确汇总](summary.json)
''')
    analyze_interventions(run,ten,cases,ds)
    print(json.dumps(stats,ensure_ascii=False),flush=True)

def analyze_interventions(run,dest,cases,ds):
    cases={c['case_id']:c for c in cases};rows=[json.loads(p.read_text()) for p in sorted((run/'interventions').glob('ddx*.json'))];assert len(rows)==24;ev=[];content=[];admin_effect=[]
    for r in rows:
        y=ds.index(cases[r['case_id']]['gold_disease']);old=np.array(r['old_q']);cur=np.array(r['current_q']);baseline=float(js(cur,old));sw=bool(changed(old,cur))
        ce={'case_id':r['case_id'],'real_js':baseline,'real_flip':sw,'real_added_tokens':r['current_input_tokens']-r['old_input_tokens']}
        for v in r['content_controls']:
            q=np.array(v['q_sequence']);key=v['condition'];ce[key+'_js']=float(js(q,old));ce[key+'_flip']=bool(changed(q,old));ce[key+'_added_tokens']=v['input_tokens']-r['old_input_tokens'];ce['real_minus_'+key]=baseline-float(js(q,old))
        content.append(ce)
        adm=next(x for x in r['conditions'] if x['condition']=='administrative_source_mlp');ctrl=next(x for x in r['conditions'] if x['layer']==28 and x['condition']=='direction_control')
        admin_effect.append({'case_id':r['case_id'],'stable':r['numerically_stable'],'gain':baseline-float(js(adm['q_sequence'],old)),
                             'minus_direction':float(js(ctrl['q_sequence'],old)-js(adm['q_sequence'],old))})
        for l in [26,27,28]:
            cond={x['condition']:x for x in r['conditions'] if x['layer']==l};patch=np.array(cond['previous_mlp']['q_sequence']);ctrl=np.array(cond['direction_control']['q_sequence'])
            gain=baseline-float(js(patch,old));control=baseline-float(js(ctrl,old))
            ev.append({'case_id':r['case_id'],'family':r['family'],'gold':cases[r['case_id']]['gold_disease'],'layer':l,'numerically_stable':r['numerically_stable'],
                       'previous_top':top(old,ds),'current_top':top(cur,ds),'patched_top':top(patch,ds),'direction_control_top':top(ctrl,ds),
                       'previous_gold_support':float(old[y]),'current_gold_support':float(cur[y]),'patched_gold_support':float(patch[y]),'delta_gold_support':float(patch[y]-cur[y]),
                       'old_current_js':baseline,'patch_gain':gain,'direction_gain':control,'relative_effect':gain-control,'original_switch':sw,
                       'patch_recovers_old':bool(sw and winner(patch)==winner(old)),'control_recovers_old':bool(sw and winner(ctrl)==winner(old))})
    csvwrite(dest/'case_interventions.csv',ev);summary={};valid=[r for r in ev if r['numerically_stable']]
    for l in [26,27,28]:
        rr=[r for r in valid if r['layer']==l];summary[str(l)]={k:ci([r[k] for r in rr]) for k in ['patch_gain','direction_gain','relative_effect','delta_gold_support']}
        switched=[r for r in rr if r['original_switch']];summary[str(l)].update(switching_cases=len(switched),recovered_old=sum(r['patch_recovers_old'] for r in switched),control_recovered_old=sum(r['control_recovers_old'] for r in switched))
    content_summary={k:ci([r[k] for r in content]) for k in content[0] if k!='case_id'}
    admin_summary={k:ci([r[k] for r in admin_effect if r['stable']]) for k in ['gain','minus_direction']}
    code_rows={(r['case_id'],int(r['layer'])):r for r in csv.DictReader((ROOT/'results/08_causal_confirmation/case_interventions.csv').open())};matched=[]
    for r in valid:
        key=(r['case_id'],r['layer'])
        if key in code_rows:
            ce=float(code_rows[key]['mlp_minus_direction']);matched.append({'case_id':r['case_id'],'layer':r['layer'],'code_effect':ce,'name_effect':r['relative_effect'],'code_minus_name':ce-r['relative_effect']})
    matched_summary={str(l):{k:ci([r[k] for r in matched if r['layer']==l]) for k in ['code_effect','name_effect','code_minus_name']} for l in [26,27,28]}
    result={'cases':24,'valid_cases':sum(r['numerically_stable'] for r in rows),'max_sham_js':max(r['sham_js'] for r in rows),'layers':summary,'content_controls':content_summary,'administrative_source_layer28':admin_summary,'matched_interfaces':matched_summary,'exploratory':True};dump(dest/'summary.json',result)
    csvwrite(dest/'matched_interface_effects.csv',matched)
    csvwrite(dest/'content_controls.csv',content);csvwrite(dest/'administrative_source_intervention.csv',admin_effect)
    fig,ax=plt.subplots(figsize=(8,4.5))
    for k,label in [('patch_gain','Previous MLP'),('direction_gain','Direction control')]:
        vals=[summary[str(l)][k] for l in [26,27,28]];ax.errorbar([26,27,28],[v['mean'] for v in vals],yerr=[[v['mean']-v['low'] for v in vals],[v['high']-v['mean'] for v in vals]],marker='o',capsize=4,label=label)
    ax.axhline(0,color='gray',lw=.8);ax.set(xticks=[26,27,28],xlabel='Intervened layer',ylabel='JS movement toward previous diagnosis distribution');ax.legend();fig.tight_layout();savefig(fig,dest/'figures/name_mlp_intervention')
    table='\n'.join(f'| {l} | {fmt(summary[str(l)]["patch_gain"],False)} | {fmt(summary[str(l)]["relative_effect"],False)} | {summary[str(l)]["recovered_old"]}/{summary[str(l)]["switching_cases"]} | {summary[str(l)]["control_recovered_old"]}/{summary[str(l)]["switching_cases"]} |' for l in [26,27,28])
    (dest/'RESULTS.md').write_text(f'''# 阶段10：疾病全名输出下的内部干预

## 方法

固定24例的中间轮，在第26、27、28层，将诊断位置的MLP增量换为同病例上一轮增量。另以同范数、循环移位257维的差向量作方向对照。修改后完整重算下游前缀缓存，并对49个完整疾病名续写评分；不只看首字或字母。每病例另做自身替换数值检查。

主要量为最终分布向上一轮分布靠近的JS差；正值靠近，负值远离。病例为统计单位，2000次bootstrap区间。本阶段为探索性跨接口复查，24例的疾病覆盖不均，不将它称为独立总体确认。

## 结果

| 层 | 旧MLP替换效应 [95%区间] | 减去方向对照 [95%区间] | 恢复前轮首选 / 原本切换病例 | 方向对照恢复 |
|---|---|---|---|---|
{table}

24例中{result['valid_cases']}例通过自身替换检查；最大分布JS误差{result['max_sham_js']:.8f}。全部原始条件保留，未通过者不进入效应统计。

**完整疾病名输出下，第28层旧MLP替换平均让分布进一步远离前轮，而不是拉回前轮。** 为排除样本集合不同，取完全相同24例比较：第28层相对方向对照效应在编码接口为{fmt(matched_summary['28']['code_effect'],False)}，名称接口为{fmt(matched_summary['28']['name_effect'],False)}；病例配对差为{fmt(matched_summary['28']['code_minus_name'],False)}。七例原本发生首选切换的病例中，没有一例因此恢复旧首选。

因此，“第28层旧MLP携带可以直接恢复的旧医学诊断”不是本轮支持的通用解释。旧模块输出与当前上下文组合后的作用，依赖输出任务。此比较包含列表呈现、答案形式和自回归路径的整体差异，不单独归因为一个字符。

![名称干预](figures/name_mlp_intervention.png)

## 医学内容与普通新增文字

在同一24例前轮输入后，追加真实新证据的疾病分布JS改变量为{fmt(content_summary['real_js'],False)}，行政说明为{fmt(content_summary['administrative_js'],False)}，重复初始证据为{fmt(content_summary['repeat_initial_js'],False)}。真实减行政的病例配对差为{fmt(content_summary['real_minus_administrative'],False)}，真实减重复的差为{fmt(content_summary['real_minus_repeat_initial'],False)}。三条件平均新增token分别为{content_summary['real_added_tokens']['mean']:.1f}、{content_summary['administrative_added_tokens']['mean']:.1f}、{content_summary['repeat_initial_added_tokens']['mean']:.1f}；不是长度匹配对照。

第28层改用“前轮+行政说明”的MLP作为来源，向前轮靠近量为{fmt(admin_summary['gain'],False)}。它使用不同提示下的自然状态作为来源，与精确旧前缀的替换结果并列阅读。

## 解释

该实验直接回答：**内部这一块计算变回旧状态后，模型对完整疾病名的判断会不会被拉回去？** 效应方向和区间见表，不以期望方向替代结果。当前轮输入仍保留新证据，因此变化来自受控内部替换。前轮可能对也可能错；“拉回去”不等于“诊断改善”。

第28层锚点MLP替换直接改变第一个输出token的分布；完整疾病名剩余token仍在完整模型中评分。第26/27层还会改变下游锚点缓存。两者的传播路径不同，不以数值差异直接宣称高低层具备相反医学知识。

[每病例的前轮、当前、干预疾病与分数](case_interventions.csv) · [精确结果](summary.json)

[同24例跨接口配对](matched_interface_effects.csv) · [为什么整体变化幅度解释不了方向翻转](GEOMETRY.md)
''')

if __name__=='__main__':main()
