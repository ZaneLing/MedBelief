"""Patient-paired frozen confirmation analysis; no method selection from test."""
import matplotlib.pyplot as plt
import time
from structure2_analysis import *
from structure2_scoring import surface_choice
from analyze_stages import setup,savefig

def main():
    while not (DOC/'matched_output_complete.json').exists():time.sleep(10)
    assert read(RUN/'confirmation/completion.json')['complete']
    setup();out=ROOT/'results/49_structure_confirmation';(out/'figures').mkdir(parents=True,exist_ok=True)
    rr,sizes,spec=load_confirmation();lookup={c['case_id']:c for c in cases()};ids=[c['case_id'] for c in cases() if c['cohort']=='confirmation'];names=[c['name'] for c in spec['configurations']];prune=read(RUN/'pruning_selection.json')['selected']['name'];by={(r['candidate'],r['case_id'],r['condition']):r for r in rr};means={n:np.array([np.mean([by[n,c,k]['correct'] for k in ['neutral','wrong']]) for c in ids]) for n in names}
    for r in rr:
        b=by['baseline',r['case_id'],r['condition']];r.update(prior_selected=int(r['generated_disease']==lookup[r['case_id']]['wrong_disease']),repair_from_listed_wrong=int(r['repaired'] and b['listed']),repair_from_invalid=int(r['repaired'] and not b['listed']))
    comparisons=[]
    for n in names:
        if n!='baseline':comparisons.append(dict(candidate=n,reference='baseline',**stat(means[n]-means['baseline'],True)))
    holm(comparisons);training=[]
    for n,b in [('full_adapter16','baseline'),('pruned_adapter16',prune),('pruned_adapter16','full_adapter16')]:training.append(dict(candidate=n,reference=b,**stat(means[n]-means[b],True)))
    holm(training);tables=[]
    output_control=[];output_repairs=[]
    for n,b in [('pruned_constrained',prune),('baseline_constrained','baseline')]:
        if n not in names:continue
        for co in ['neutral','wrong']:
            a=[by[n,c,co] for c in ids];bb=[by[b,c,co] for c in ids];output_control.append(dict(candidate=n,reference=b,condition=co,n=len(ids),difference=stat([x['correct']-y['correct'] for x,y in zip(a,bb)]),repaired_from_invalid=sum(x['correct'] and not y['correct'] and not y['listed'] for x,y in zip(a,bb)),repaired_from_listed_wrong=sum(x['correct'] and not y['correct'] and y['listed'] for x,y in zip(a,bb)),changed_when_raw_listed=sum(y['listed'] and x['generated_disease']!=y['generated_disease'] for x,y in zip(a,bb)),damaged=sum(y['correct'] and not x['correct'] for x,y in zip(a,bb))))
            for cid,x,y in zip(ids,a,bb):
                if x['correct'] and not y['correct']:
                    raw=next(r for r in read(RUN/'confirmation'/b/(cid+'.json'))['conditions'] if r['condition']==co);gold=lookup[cid]['gold_disease'];output_repairs.append(dict(case_id=cid,condition=co,candidate=n,reference=b,source_answer=gold,raw_name=raw['generated_disease'],raw_text=raw['text'],source_name_already_at_start=int(raw['text'].lstrip().startswith(gold+'"')),repaired_name=x['generated_disease']))
    for n in names:
        for ds in ['all','MedQA','MedMCQA']:
            for co in ['neutral','wrong']:
                sub=[r for r in rr if r['candidate']==n and r['condition']==co and (ds=='all' or r['dataset']==ds)];tables.append(dict(candidate=n,dataset=ds,condition=co,n=len(sub),correct=sum(r['correct'] for r in sub),listed=sum(r['listed'] for r in sub),repaired=sum(r['repaired'] for r in sub),damaged=sum(r['damaged'] for r in sub),repair_from_listed_wrong=sum(r['repair_from_listed_wrong'] for r in sub),repair_from_invalid=sum(r['repair_from_invalid'] for r in sub),prior_selected=sum(r['prior_selected'] for r in sub),accuracy=proportion([r['correct'] for r in sub]),difference=stat([r['accuracy_change'] for r in sub]),fidelity=proportion([r['fidelity'] for r in sub])))
    control_cfg=read(DOC/'MATCHED_OUTPUT_CONTROL.json')['control'];cr,control_sizes=records('output_matched_control',[control_cfg],'confirmation');sizes.update(control_sizes);cb={(r['case_id'],r['condition']):r for r in cr};cm=np.array([np.mean([cb[c,co]['correct'] for co in ['neutral','wrong']]) for c in ids]);primary=spec['primary_candidate'];factorial=[dict(contrast=label,**stat(delta)) for label,delta in [('裁剪效应：自由生成',means[prune]-means['baseline']),('输出约束效应：完整模型',cm-means['baseline']),('输出约束效应：压缩模型',means[primary]-means[prune]),('裁剪效应：相同输出约束',means[primary]-cm),('交互：压缩后约束收益增加多少',(means[primary]-means[prune])-(cm-means['baseline']))]]
    for r in cr:
        b=by['baseline',r['case_id'],r['condition']];r.update(accuracy_change=r['correct']-b['correct'],fidelity=int(r['generated_disease'] is not None and r['generated_disease']==b['generated_disease']),repaired=int(r['correct'] and not b['correct']),damaged=int(b['correct'] and not r['correct']),prior_selected=int(r['generated_disease']==lookup[r['case_id']]['wrong_disease']))
    for ds in ['all','MedQA','MedMCQA']:
        for co in ['neutral','wrong']:
            sub=[r for r in cr if r['condition']==co and (ds=='all' or r['dataset']==ds)];tables.append(dict(candidate=control_cfg['name'],dataset=ds,condition=co,n=len(sub),correct=sum(r['correct'] for r in sub),listed=sum(r['listed'] for r in sub),repaired=sum(r['repaired'] for r in sub),damaged=sum(r['damaged'] for r in sub),prior_selected=sum(r['prior_selected'] for r in sub),accuracy=proportion([r['correct'] for r in sub]),difference=stat([r['accuracy_change'] for r in sub]),fidelity=proportion([r['fidelity'] for r in sub])))
    mt=read(RUN/'output_matched_control/timing.json');matched_timing=[]
    for field in ['prefill_seconds','fixed12_decode_seconds','actual_answer_seconds']:
        values=[np.mean([np.log(t['ratios'][field]) for t in mt['trials'] if t['case_id']==cid]) for cid in sorted({t['case_id'] for t in mt['trials']})];st=stat(values);st={k:(float(np.exp(v)) if k in ['mean','low','high','median'] else v) for k,v in st.items()};matched_timing.append(dict(metric=field,ratio=st))
    none,_=records('confirmation',[dict(name='baseline_no_history')],'confirmation');noneby={r['case_id']:r for r in none};input_control=[]
    for co in ['neutral','wrong']:
        delta=[noneby[c]['correct']-by['baseline',c,co]['correct'] for c in ids];input_control.append(dict(reference_condition=co,none_accuracy=proportion([noneby[c]['correct'] for c in ids]),difference=stat(delta),repaired=sum(d==1 for d in delta),damaged=sum(d==-1 for d in delta)))
    # The union asks what is recoverable after knowing the answer; never a model score.
    recovery=[];cfgby={c['name']:c for c in spec['configurations']};untrained=[n for n in names if n!='baseline' and not cfgby[n].get('adapter_file') and not cfgby[n].get('bridge_file')]
    for c in ids:
        for co in ['neutral','wrong']:
            b=by['baseline',c,co];recovery.append(dict(case_id=c,condition=co,baseline_correct=b['correct'],input_only_correct=noneby[c]['correct'],untrained_any_correct=int(any(by[n,c,co]['correct'] for n in untrained)),any_frozen_correct=int(any(by[n,c,co]['correct'] for n in names)),all_fixed=int(any(by[n,c,co]['correct'] for n in names) or noneby[c]['correct'])))
    recover_summary={co:dict(baseline_errors=sum(not r['baseline_correct'] for r in recovery if r['condition']==co),**{k:sum(r[k] and not r['baseline_correct'] for r in recovery if r['condition']==co) for k in ['input_only_correct','untrained_any_correct','any_frozen_correct','all_fixed']}) for co in ['neutral','wrong']}
    timing=[]
    for n in names:
        if n=='baseline':continue
        z=read(RUN/'timing'/(n+'.json'))
        for field in ['prefill_seconds','fixed12_decode_seconds','actual_answer_seconds']:
            # Average within case before resampling: repetitions are not independent cases.
            values=[np.mean([np.log(t['ratios'][field]) for t in z['trials'] if t['case_id']==cid]) for cid in sorted({t['case_id'] for t in z['trials']})];s=stat(values);s={k:(float(np.exp(v)) if k in ['mean','low','high','median'] else v) for k,v in s.items()};timing.append(dict(candidate=n,metric=field,ratio=s,baseline_seconds=float(np.mean([t['baseline'][field] for t in z['trials']])),variant_seconds=float(np.mean([t['variant'][field] for t in z['trials']])),baseline_tokens=float(np.mean([t['baseline']['actual_tokens'] for t in z['trials']])),variant_tokens=float(np.mean([t['variant']['actual_tokens'] for t in z['trials']]))))
    audit=read(DATA/'source_sensitivity_audit.json');auditby={r['case_id']:r for r in audit['rows']};sensitivity=[]
    for field in ['strict_source_keep','strict_source_and_similarity_keep']:
        keep=[c for c in ids if auditby[c][field]];ix=[ids.index(c) for c in keep]
        for n in names:sensitivity.append(dict(filter=field,candidate=n,n=len(keep),neutral_correct=sum(by[n,c,'neutral']['correct'] for c in keep),wrong_correct=sum(by[n,c,'wrong']['correct'] for c in keep),difference=stat(means[n][ix]-means['baseline'][ix])))
    ix=[i for i,c in enumerate(ids) if auditby[c]['strict_source_and_similarity_keep']];matched=dict(control=control_cfg,post_primary_explanatory=True,difference=stat(means[primary]-cm),factorial=factorial,timing=matched_timing,strict=dict(n=len(ix),difference=stat(means[primary][ix]-cm[ix]),control_correct={co:sum(cb[ids[i],co]['correct'] for i in ix) for co in ['neutral','wrong']}))
    normalized_rows=[];nb={};allnames=names+[control_cfg['name']]
    for n in allnames:
        folder='output_matched_control' if n==control_cfg['name'] else 'confirmation'
        for cid in ids:
            c=lookup[cid]
            for r in read(RUN/folder/n/(cid+'.json'))['conditions']:
                choice=surface_choice(c,r);value=int(choice==c['gold_index']);nb[n,cid,r['condition']]=value;normalized_rows.append(dict(case_id=cid,candidate=n,condition=r['condition'],strict_correct=int(r['correct']),normalized_correct=value,normalized_disease=c['candidates'][choice] if choice is not None else None))
    nm={n:np.array([np.mean([nb[n,c,co] for co in ['neutral','wrong']]) for c in ids]) for n in allnames};ncomp=[dict(candidate=n,**stat(nm[n]-nm['baseline'],True)) for n in names if n!='baseline'];holm(ncomp);ntable=[]
    for n in allnames:ntable.append(dict(candidate=n,neutral_correct=sum(nb[n,c,'neutral'] for c in ids),wrong_correct=sum(nb[n,c,'wrong'] for c in ids),strict_subset=dict(n=len(ix),neutral_correct=sum(nb[n,ids[i],'neutral'] for i in ix),wrong_correct=sum(nb[n,ids[i],'wrong'] for i in ix),difference=stat(nm[n][ix]-nm['baseline'][ix]))))
    for r in output_repairs:r['normalized_prior_correct']=int(surface_choice(lookup[r['case_id']],dict(generated_disease=r['raw_name'],text=r['raw_text']))==lookup[r['case_id']]['gold_index'])
    normalized=dict(status='Post-primary scoring sensitivity, applied uniformly; no reselection.',rule_sha256=sha(ROOT/'src/structure2_scoring.py'),per_method=ntable,comparisons=ncomp,matched_difference=stat(nm[primary]-nm[control_cfg['name']]),constraint_repairs_already_correct=sum(r['normalized_prior_correct'] for r in output_repairs),constraint_repairs=len(output_repairs),factorial=[dict(contrast=label,**stat(delta)) for label,delta in [('裁剪效应：自由生成',nm[prune]-nm['baseline']),('输出约束效应：完整模型',nm[control_cfg['name']]-nm['baseline']),('输出约束效应：压缩模型',nm[primary]-nm[prune]),('裁剪效应：相同输出约束',nm[primary]-nm[control_cfg['name']])]])
    nnone={cid:int(surface_choice(lookup[cid],read(RUN/'confirmation/baseline_no_history'/(cid+'.json'))['conditions'][0])==lookup[cid]['gold_index']) for cid in ids};normalized['no_history_correct']=sum(nnone.values());normalized['input_control']=[dict(reference_condition=co,difference=stat([nnone[c]-nb['baseline',c,co] for c in ids]),repaired=sum(nnone[c] and not nb['baseline',c,co] for c in ids),damaged=sum(nb['baseline',c,co] and not nnone[c] for c in ids)) for co in ['neutral','wrong']]
    scope=read(DOC/'ANSWER_SCOPE_AUDIT.json');scope_ids={r['case_id'] for r in scope['rows']};sx=[i for i in ix if ids[i] not in scope_ids];normalized['answer_scope_sensitivity']=dict(n=len(sx),excluded_case_ids=sorted(scope_ids),rows=[dict(candidate=n,neutral_correct=sum(nb[n,ids[i],'neutral'] for i in sx),wrong_correct=sum(nb[n,ids[i],'wrong'] for i in sx),difference=stat(nm[n][sx]-nm['baseline'][sx])) for n in allnames],matched_difference=stat(nm[primary][sx]-nm[control_cfg['name']][sx]))
    base=sizes['baseline']['parameters'];summary=dict(cases=400,primary_candidate=spec['primary_candidate'],compression_candidate=spec['compression_candidate'],parameters=sizes,per_method=tables,primary_comparisons=comparisons,training_comparisons=training,input_control=input_control,output_control=output_control,output_repairs_name_already_at_start=sum(r['source_name_already_at_start'] for r in output_repairs),output_repairs_count=len(output_repairs),error_recovery_oracle=recover_summary,untrained_methods=untrained,timing=timing,source_sensitivity=sensitivity,source_audit_sha256=sha(DATA/'source_sensitivity_audit.json'),selection_sha256=sha(RUN/'confirmation_selection.json'),api_cost_usd=0)
    summary.update(matched_output_control=matched,normalized_scoring=normalized);write(out/'summary.json',summary);csvwrite(out/'per_case.csv',rr+cr);csvwrite(out/'normalized_scores.csv',normalized_rows);csvwrite(out/'recoverability_oracle.csv',recovery);csvwrite(out/'paired_comparisons.csv',comparisons+training);csvwrite(out/'accuracy_by_source.csv',[{k:v for k,v in r.items() if k not in ['accuracy','difference','fidelity']} for r in tables])
    csvwrite(out/'output_constraint_repairs.csv',output_repairs)
    fig,axs=plt.subplots(1,3,figsize=(16,6),layout='constrained');yy=np.arange(len(names))
    for co,color,offset in [('neutral','#317f9e',-.15),('wrong','#bc534c',.15)]:
        values=[next(r['accuracy'] for r in tables if r['candidate']==n and r['dataset']=='all' and r['condition']==co) for n in names];axs[0].barh(yy+offset,[100*s['mean'] for s in values],height=.28,label='中性历史' if co=='neutral' else '错误历史',color=color)
    axs[0].set(yticks=yy,yticklabels=[LABELS[n] for n in names],xlabel='预定逐字候选命中率 (%)',title='独立400例，每例两种历史');axs[0].invert_yaxis();axs[0].legend()
    axs[1].barh(yy,[100*(1-sizes[n]['parameters']/base) for n in names],color='#61a17e');axs[1].set(yticks=yy,yticklabels=[],xlabel='参数减少 (%)',title='真实移除权重后的模型大小');axs[1].invert_yaxis()
    for n in names[1:]:
        i=names.index(n);s=next(r['ratio'] for r in timing if r['candidate']==n and r['metric']=='prefill_seconds');axs[2].errorbar(s['mean'],i,xerr=[[s['mean']-s['low']],[s['high']-s['mean']]],fmt='o',color='#666b9a')
    axs[2].axvline(1,color='gray',ls='--');axs[2].set(yticks=yy,yticklabels=[],xlabel='读取病例耗时 / 原模型',title='6例配对实测；低于1更快');axs[2].invert_yaxis();savefig(fig,out/'figures/confirmation_overview')
    fig,ax=plt.subplots(figsize=(9,4.5),layout='constrained')
    for i,r in enumerate(training):ax.errorbar(100*r['mean'],i,xerr=[[100*(r['mean']-r['low'])],[100*(r['high']-r['mean'])]],fmt='o',capsize=4,color='#317f9e')
    ax.axvline(0,color='gray',ls='--');ax.set(yticks=range(3),yticklabels=[LABELS[r['candidate']]+' − '+LABELS[r['reference']] for r in training],xlabel='每病例两种历史平均准确率差（百分点；95%区间）',title='把训练收益与结构收益分开');ax.invert_yaxis();savefig(fig,out/'figures/training_vs_structure')
    lines=['# 独立400例：结构、训练和输出分别解决什么\n\nMedQA与MedMCQA各200例。确认前冻结7种方法；每例分别加入中性历史和错误历史，实际生成完整候选名称。主指标先在每病例内平均两种历史，再跨病例统计。适配器只见过另400例训练，80例开发选择检查点。\n\n下表保留原预定逐字评分；解释疾病选择时请同时看后面的规范化评分。\n\n![总体结果](figures/confirmation_overview.png)\n\n| 方法 | 中性答对/400 | 错误历史答对/400 | 参数减少 | 读取病例耗时比 |\n|---|---:|---:|---:|---:|\n']
    for n in names:
        counts=[next(r['correct'] for r in tables if r['candidate']==n and r['dataset']=='all' and r['condition']==co) for co in ['neutral','wrong']];tm=next((r['ratio'] for r in timing if r['candidate']==n and r['metric']=='prefill_seconds'),None);lines.append(f'| {LABELS[n]} | {counts[0]} | {counts[1]} | {100*(1-sizes[n]["parameters"]/base):.2f}% | {fmt(tm) if tm else "1.00（参照）"} |\n')
    np_=next(r for r in ncomp if r['candidate']==primary);lines.append(f'\n## 评分核查：严格字符串命中不能直接等同于医学判断改善\n\n原预定评分要求完整候选逐字匹配。人工查看原输出发现末尾空格、开头冠词、大小写和引号/括号位置造成丢分。因此对所有方法一致增加确定性写法规范化：保留疾病用词和数字及+-−/<>=%符号，清理表面格式，并要求唯一匹配四个原候选之一；不做同义词或模糊医学匹配，也不据真值决定怎么解析。该分析在主结果之后提出，方法选择保持冻结。[规则与登记](../../research_v6_adapters/SCORING_AUDIT.md)。\n\n规范化后主方案减原模型为**{100*np_["mean"]:+.2f}个百分点，95%区间[{100*np_["low"]:+.2f}, {100*np_["high"]:+.2f}]，敏感性六项内Holm p={np_["p_holm"]:.4g}**。候选约束修复的{len(output_repairs)}个条件中，{normalized["constraint_repairs_already_correct"]}个原回答在该规则下已经匹配正确候选。严格命中率的收益不能全部算作新的疾病判断。\n\n| 方法 | 规范化中性命中/400 | 规范化错误历史命中/400 | 严格366子集中性/错误历史 |\n|---|---:|---:|---:|\n')
    for r in ntable:lines.append(f'| {LABELS[r["candidate"]]} | {r["neutral_correct"]} | {r["wrong_correct"]} | {r["strict_subset"]["neutral_correct"]}/{r["strict_subset"]["wrong_correct"]} |\n')
    ascope=normalized['answer_scope_sensitivity'];lines.append('\n来源题干出现“诊断”不保证所有选项都是疾病名；检查特征、分子机制和组合答案等9项另行标记。在366例上再排除这些已标记项目后保留'+str(ascope['n'])+'例。它是附加来源答案类型敏感性，不是完整医学本体审核。[范围说明](../../research_v6_adapters/ANSWER_SCOPE.md)。\n\n| 方法 | 来源类型敏感性中性/错误历史命中 | 相对原模型平均差（百分点，95%区间） |\n|---|---:|---:|\n')
    for r in ascope['rows']:
        d=r['difference'];lines.append(f'| {LABELS[r["candidate"]]} | {r["neutral_correct"]}/{r["wrong_correct"]} | {100*d["mean"]:+.2f} [{100*d["low"]:+.2f}, {100*d["high"]:+.2f}] |\n')
    fig,axs=plt.subplots(1,2,figsize=(11,4.5),layout='constrained');plotnames=['baseline',prune,primary]
    for ax,co in zip(axs,['neutral','wrong']):
        xx=np.arange(3);raw=[next(r['correct'] for r in tables if r['candidate']==n and r['dataset']=='all' and r['condition']==co)/4 for n in plotnames];norm=[next(r[co+'_correct'] for r in ntable if r['candidate']==n)/4 for n in plotnames];ax.bar(xx-.16,raw,.3,label='严格字符串',color='#317f9e');ax.bar(xx+.16,norm,.3,label='规范化候选身份',color='#d09244');ax.set(xticks=xx,xticklabels=['完整模型','单纯压缩','压缩+候选约束'],ylabel='来源候选命中率 (%)',ylim=(0,65),title='中性历史' if co=='neutral' else '错误历史');ax.legend(fontsize=9)
    savefig(fig,out/'figures/scoring_audit');lines.append('\n![评分敏感性](figures/scoring_audit.png)\n\n规范化仅修复可机械判断的写法，余下差异仍可能包含错拼或医学同义词，因此它也不是医生级语义判定。[全部修复原文](output_constraint_repairs.csv)和[逐病例双评分](normalized_scores.csv)可核对。\n')
    lines.append('\n开发集预先选定的主候选：**'+LABELS[spec['primary_candidate']]+'**；压缩候选：**'+LABELS[spec['compression_candidate']]+'**。不按确认结果重新挑最好者。\n\n## 原逐字评分：相对完整模型的六项预定比较\n\n| 方法 | 平均准确率差及95%区间（百分点） | Holm校正p |\n|---|---:|---:|\n')
    for r in comparisons:lines.append(f'| {LABELS[r["candidate"]]} | {100*r["mean"]:.2f} [{100*r["low"]:.2f}, {100*r["high"]:.2f}] | {r["p_holm"]:.4g} |\n')
    fig,axs=plt.subplots(1,2,figsize=(11,4.5),layout='constrained');four=['baseline','baseline_constrained',prune,primary]
    for ax,co in zip(axs,['neutral','wrong']):
        values=[next(r['correct'] for r in tables if r['candidate']==n and r['dataset']=='all' and r['condition']==co) for n in four];bars=ax.bar(range(4),np.array(values)/4,color=['#86aec1','#317f9e','#acd1b6','#529b6c']);ax.bar_label(bars,labels=[str(v)+'/400' for v in values],fontsize=9);ax.set(xticks=range(4),xticklabels=['完整\n自由生成','完整\n候选约束','压缩\n自由生成','压缩\n候选约束'],ylim=(0,max(values)/4+10),ylabel='预定逐字候选命中率 (%)',title='中性历史' if co=='neutral' else '错误历史')
    savefig(fig,out/'figures/matched_output_control');lines.append('\n## 补充的匹配输出对照：原逐字评分的2×2比较\n\n看到预定主结果后，追加开发阶段已有的完整模型候选约束配置，在同400例上解释结构与解码的贡献；没有重新选主方法或调参数。这是明确标记的事后解释性对照，未混入原六项确认检验。[追加登记](../../research_v6_adapters/MATCHED_OUTPUT_CONTROL.json)。\n\n![同输出规则比较](figures/matched_output_control.png)\n\n| 对比 | 每病例平均准确率差（百分点，95%区间） |\n|---|---:|\n')
    for r in factorial:lines.append(f'| {r["contrast"]} | {100*r["mean"]:+.2f} [{100*r["low"]:+.2f}, {100*r["high"]:+.2f}] |\n')
    ms=matched['strict'];st=ms['difference'];lines.append(f'\n同样输出约束下，严格{ms["n"]}例的压缩减完整准确率差为{100*st["mean"]:+.2f}个百分点，95%区间[{100*st["low"]:+.2f}, {100*st["high"]:+.2f}]。完整约束模型在该子集中性/错误历史答对{ms["control_correct"]["neutral"]}/{ms["control_correct"]["wrong"]}例。\n\n两模型使用相同候选约束后的直接配对耗时：\n\n')
    for r in matched_timing:lines.append(f'- {r["metric"]}：压缩/完整={fmt(r["ratio"])}。\n')
    lines.append('\n## 原逐字评分：训练是否足够，压缩是否另外有益\n\n![训练与结构](figures/training_vs_structure.png)\n\n| 公平比较 | 平均准确率差及95%区间（百分点） | 三项内Holm校正p |\n|---|---:|---:|\n')
    for r in training:lines.append(f'| {LABELS[r["candidate"]]} − {LABELS[r["reference"]]} | {100*r["mean"]:.2f} [{100*r["low"]:.2f}, {100*r["high"]:.2f}] | {r["p_holm"]:.4g} |\n')
    lines.append('\n第一行衡量只加适配器能否改善；第二行衡量适配器能否修复压缩；第三行才直接检验“相同训练时，压缩结构是否更好”。未显著变差不等于已证明非劣，本轮没有设非劣界值。\n\n## 仅改变输入\n\n')
    reverted=[n for n in names if cfgby[n].get('adapter_file') and read(RUN/'adapters'/n/'completion.json')['best_step']==0]
    if reverted:lines.insert(-1,'\n**适配器失败说明：'+ '、'.join(LABELS[n] for n in reverted)+'在开发集未获训练收益，最终选择第0步零初始化。** 因而其确认表现反映骨干本身，不能宣称小模块修复了它。\n')
    for r in input_control:lines.append(f'- 去掉历史后答对{round(r["none_accuracy"]["mean"]*400)}/400；相对{r["reference_condition"]}，修复{r["repaired"]}例、损坏{r["damaged"]}例，净差{100*r["difference"]["mean"]:.2f}个百分点。\n')
    lines.append('\n## 同一结构，只增加输出约束\n\n这项描述性配对把结构和输出约束拆开。非法名称包含无法解析JSON和输出了候选表外名称，不全部归因于单纯格式。\n\n| 约束方法与相同骨干 | 历史 | 非法名称→正确 | 合法错误→正确 | 原本正确→错误 | 原本合法时换病名 |\n|---|---|---:|---:|---:|---:|\n')
    for r in output_control:lines.append(f'| {LABELS[r["candidate"]]} / {LABELS[r["reference"]]} | {r["condition"]} | {r["repaired_from_invalid"]} | {r["repaired_from_listed_wrong"]} | {r["damaged"]} | {r["changed_when_raw_listed"]} |\n')
    lines.append(f'\n这些修复共{len(output_repairs)}个病例—历史条件，其中{sum(r["source_name_already_at_start"] for r in output_repairs)}个原回答的开头已写出完整来源答案，但原始完整输出未被计为正确的规范候选。该计数只做字面前缀核对，不替代医学同义词审核。[全部修复前原文](output_constraint_repairs.csv)。\n')
    lines.append('\n## 原逐字错误的可恢复性（含表面格式）\n\n| 历史 | 原模型错误 | 去历史可修复 | 任一未训练方法可修复 | 任一冻结方法可修复 | 加上去历史后任一方法可修复 |\n|---|---:|---:|---:|---:|---:|\n')
    for co,r in recover_summary.items():lines.append('| '+co+' | '+' | '.join(str(r[k]) for k in ['baseline_errors','input_only_correct','untrained_any_correct','any_frozen_correct','all_fixed'])+' |\n')
    lines.append('\n错误历史下进一步区分“写出了错误候选”和“未写出合法候选”：\n\n| 方法 | 合法错误→正确 | 非法名称→正确 | 原本正确→错误 | 仍选择预设错误旧病名/400 |\n|---|---:|---:|---:|---:|\n')
    for n in names:
        r=next(r for r in tables if r['candidate']==n and r['dataset']=='all' and r['condition']=='wrong');lines.append(f'| {LABELS[n]} | {r["repair_from_listed_wrong"]} | {r["repair_from_invalid"]} | {r["damaged"]} | {r["prior_selected"]} |\n')
    lines.append('\n“任一方法修复”需要知道正确答案后挑方法，是错误可恢复性分析，**不是可部署准确率**；各列可能重叠。未训练变换可恢复说明原模型在某些输入/计算路径下有答对能力；训练适配器的改善可能包含新学习；全部方法都未修复不能证明模型完全不懂该疾病。\n\n## 时间、输出长度与数据\n\n耗时为同机GPU同步、原模型/变体交替的配对测量：6例×2种历史×2次重复。区间按6个病例聚合后重采样，反映本机小样本时延，不外推到其他硬件。固定12词元解码比较相同计算长度；实际答案耗时另含不同回答长度和候选约束开销。\n\n| 方法 | 固定12词元耗时比 | 实际回答耗时比 | 原/改平均输出词元 |\n|---|---:|---:|---:|\n')
    for n in names[1:]:
        d=next(r for r in timing if r['candidate']==n and r['metric']=='fixed12_decode_seconds');a=next(r for r in timing if r['candidate']==n and r['metric']=='actual_answer_seconds');lines.append(f'| {LABELS[n]} | {fmt(d["ratio"])} | {fmt(a["ratio"])} | {a["baseline_tokens"]:.1f}/{a["variant_tokens"]:.1f} |\n')
    lines.append('\n## 来源质量与近重复敏感性\n\n初始筛选漏掉了部分缺图引用及题干尾语；运行中发现后进行只读源文本复核，未据模型对错选病例。训练仍为原400例、开发选型仍为原80例，没有重新挑最优模型。[完整审计及分词修正](../../research_v6_adapters/SOURCE_AUDIT.md)。下表第一组仅排除源文本问题，第二组再排除与训练/开发/旧540例及确认集内部的0.80近重复；这是事后敏感性，不替代原定400例结果。\n\n| 严格子集 | 方法 | 病例数 | 中性答对 | 错误历史答对 | 相对完整模型的平均差（百分点，95%区间） |\n|---|---|---:|---:|---:|---:|\n')
    for r in sensitivity:
        s=r['difference'];lines.append(f'| {"文本" if r["filter"]=="strict_source_keep" else "文本+近重复"} | {LABELS[r["candidate"]]} | {r["n"]} | {r["neutral_correct"]} | {r["wrong_correct"]} | {100*s["mean"]:.2f} [{100*s["low"]:.2f}, {100*s["high"]:.2f}] |\n')
    lines.append('\n来源分层与逐病例结果：[CSV](accuracy_by_source.csv)、[全部生成指标](per_case.csv)、[完整统计](summary.json)。参数数量来自实际模型权重树。来源答案是考试题的最终标准答案；本轮不声称临床诊断性能，也不把每个中间前缀当作已有唯一正确诊断。模型API费用为0美元。\n')
    (out/'RESULTS.md').write_text(''.join(lines));print(json.dumps(dict(complete=True,cases=400,primary=spec['primary_candidate'],compression=spec['compression_candidate'])))
if __name__=='__main__':main()
