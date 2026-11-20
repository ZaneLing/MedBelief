"""Matched-control contrasts and independent validation of the 130-case followup."""
import hashlib
import matplotlib.pyplot as plt
from structural_v1_analysis import *
from phase41_multisource_analyze import holm
from analyze_stages import setup,savefig
OUT=ROOT/'results/46_structural_head_followup'
LABELS={'baseline':'完整模型','anchor_heads_8':'所选8个头','matched_random_heads_8611':'同层随机集合1','matched_random_heads_8627':'同层随机集合2','matched_high_attention_heads':'同层高历史注意力集合'}
GEN_LABELS=dict(LABELS,anchor_heads_8='所选8头：只改输入末位置',anchor_heads_8_all_answer_tokens='所选8头：持续到全部生成词元')

def main():
    src=RUN/'followup';done=read(src/'completion.json');assert done['complete'];spec=read(src/'spec.json');meta=read(src/'manifest.json');setup();(OUT/'figures').mkdir(parents=True,exist_ok=True)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    assert meta['spec_sha256']==sha(src/'spec.json') and meta['source_sha256']==sha(ROOT/'src/phase86_structural_head_followup.py') and meta['variants_sha256']==sha(ROOT/'src/structural_v1_variants.py')
    assert meta['sustained_sha256']==sha(ROOT/'src/structural_v1_sustained.py');numerical=read(src/'numerical_control.json');assert numerical['complete'] and numerical['max_empty_gate_logit_error']<.02 and numerical['empty_gate_top_changes']==0 and numerical['selected_gate_prefill_q_error']<.01
    original=read(RUN/'screen/manifest.json');seen=set(original['screen']+original['tune']+original['test']);assert not seen&set(spec['cases']) and len(seen|set(spec['cases']))==520
    selected=spec['candidates'][1]['anchor_drop_heads'];assert sum(map(len,selected.values()))==8
    for cfg in spec['candidates'][2:]:
        mapping=cfg['anchor_drop_heads'];assert set(mapping)==set(selected)
        for l in mapping:assert len(mapping[l])==len(selected[l]) and not set(mapping[l])&set(selected[l])
    native=[]
    for cid in spec['cases']:
        ref=read(src/(cid+'_baseline.json'));prompts={(r['condition'],r['rotation']):r['prompt_sha256'] for r in ref['conditions']}
        for cfg in spec['candidates']:
            z=read(src/(cid+'_'+cfg['name']+'.json'));assert len(z['conditions'])==4 and z['configuration']==cfg
            assert {(r['condition'],r['rotation']) for r in z['conditions']}=={(c,r) for c in ['neutral','wrong'] for r in [0,2]}
            for r in z['conditions']:
                q=np.array(r['q']);lp=np.array(r['candidate_logits']);prob=np.exp(lp-lp.max());prob/=prob.sum();assert np.isfinite(q).all() and np.allclose(q,prob,atol=1e-6) and np.isclose(q.sum(),1) and 0<=r['candidate_mass']<=1.00001 and r['prompt_sha256']==prompts[r['condition'],r['rotation']]
                if 'native_q_error' in r:native.append(r['native_q_error'])
    assert len(native)==20 and max(native)<.01
    rows,sizes,_=load('followup');summaries=summarize(rows);csvwrite(OUT/'patient_code_results.csv',rows);contrasts=[]
    for name in LABELS:
        if name in ['baseline','anchor_heads_8']:continue
        for cond in ['neutral','wrong']:
            aa={r['case_id']:r for r in rows if r['candidate']=='anchor_heads_8' and r['condition']==cond};bb={r['case_id']:r for r in rows if r['candidate']==name and r['condition']==cond}
            contrasts.append(dict(control=name,condition=cond,accuracy_difference=stat([aa[cid]['accuracy']-bb[cid]['accuracy'] for cid in aa],pvalue=True),wrong_support_difference=stat([aa[cid]['wrong_support']-bb[cid]['wrong_support'] for cid in aa])))
    tests=[r['accuracy_difference'] for r in contrasts if r['condition']=='wrong'];holm(tests)
    cs={c['case_id']:c for c in map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines())};genrows=[];goldrows=[]
    for cid in spec['cases']:
        bb={r['rotation']:r for r in read(src/'gold_control'/(cid+'_baseline.json'))['conditions']}
        for name in ['baseline','anchor_heads_8']:
            rr=read(src/'gold_control'/(cid+'_'+name+'.json'))['conditions'];assert len(rr)==2 and {r['rotation'] for r in rr}=={0,2};g=cs[cid]['gold_index']
            for r in rr:
                q=np.array(r['q']);assert np.isfinite(q).all() and np.isclose(q.sum(),1) and r['condition']=='gold' and r['prompt_sha256']==bb[r['rotation']]['prompt_sha256']
            goldrows.append(dict(case_id=cid,dataset=cs[cid]['dataset'],candidate=name,accuracy=float(np.mean([np.argmax(r['q'])==g for r in rr])),accuracy_change=float(np.mean([int(np.argmax(r['q'])==g)-int(np.argmax(bb[r['rotation']]['q'])==g) for r in rr])),code_rate=float(np.mean([r['first_is_code'] for r in rr]))))
    csvwrite(OUT/'patient_gold_control.csv',goldrows);oracle=[]
    for name in ['baseline','anchor_heads_8']:
        rr=[r for r in goldrows if r['candidate']==name];oracle.append(dict(candidate=name,**{f:stat([r[f] for r in rr]) for f in ['accuracy','accuracy_change','code_rate']}))
    wr={r['case_id']:r for r in rows if r['candidate']=='anchor_heads_8' and r['condition']=='wrong'};gg={r['case_id']:r for r in goldrows if r['candidate']=='anchor_heads_8'}
    history_specificity=stat([wr[cid]['accuracy_change']-gg[cid]['accuracy_change'] for cid in gg])
    for cid in spec['cases']:
        records={n:read(src/'generation'/(cid+'_'+n+'.json'))['conditions'] for n in spec['generation_candidates']};base={r['condition']:r for r in records['baseline']}
        for name,rr in records.items():
            assert len(rr)==2
            for r in rr:
                try:d=json.loads('{"diagnosis":"'+r['text'])['diagnosis']
                except (ValueError,TypeError,KeyError):d=None
                assert r['generated_disease']==d and r['correct']==(d==cs[cid]['gold_disease']) and r['listed']==(d in cs[cid]['candidates']);b=base[r['condition']];assert r['prompt_sha256']==b['prompt_sha256']
                genrows.append(dict(case_id=cid,dataset=cs[cid]['dataset'],candidate=name,condition=r['condition'],correct=int(r['correct']),accuracy_change=int(r['correct'])-int(b['correct']),same_diagnosis=int(d is not None and d==b['generated_disease']),listed=int(r['listed'])))
    csvwrite(OUT/'patient_generation_results.csv',genrows);generation=[]
    for name in spec['generation_candidates']:
        for cond in ['neutral','wrong']:
            rr=[r for r in genrows if r['candidate']==name and r['condition']==cond];generation.append(dict(candidate=name,condition=cond,correct=sum(r['correct'] for r in rr),n=len(rr),**{('accuracy' if f=='correct' else f):stat([r[f] for r in rr]) for f in ['correct','accuracy_change','same_diagnosis','listed']}))
    summary=dict(cases=130,source_cases=spec['source_cases'],code_summaries=summaries,contrasts=contrasts,oracle_gold=oracle,wrong_minus_gold_intervention_effect=history_specificity,generation=generation,selection=spec,api_cost_usd=0);write(OUT/'summary.json',summary)
    fig,axs=plt.subplots(1,2,figsize=(12,5),layout='constrained');names=list(LABELS);yy=np.arange(5)
    for cond,c,off in [('neutral','#317f9e',-.12),('wrong','#bc534c',.12)]:
        rr=[next(r for r in summaries if r['dataset']=='all' and r['candidate']==n and r['condition']==cond) for n in names]
        for ax,key in zip(axs,['accuracy','accuracy_change']):
            m=np.array([r[key]['mean'] for r in rr]);lo=np.array([r[key]['low'] for r in rr]);hi=np.array([r[key]['high'] for r in rr]);ax.errorbar(m,yy+off,xerr=[m-lo,hi-m],fmt='o',capsize=3,c=c,label='中性历史' if cond=='neutral' else '错误历史')
    for ax in axs:ax.set(yticks=yy,yticklabels=[LABELS[n] for n in names]);ax.invert_yaxis();ax.legend(fontsize=8)
    axs[0].set(title='第二批130例：来源答案命中',xlabel='正确率，病例级95%区间');axs[1].set(title='相对完整模型的改变',xlabel='准确率配对差，病例级95%区间');axs[1].axvline(0,c='gray',lw=.8);savefig(fig,OUT/'figures/matched_head_controls')
    lines=['# 所选注意力头是否有可复现的作用\n\n由首批345例中8头干预的改善触发，随后在未参与结构选择或首批结构检验的130例上冻结复核：MedQA82、MedMCQA48。此批不包含MMLU。三个对照与所选头保持相同层位置及每层头数，分别是两个固定随机集合和同层高历史注意力集合；均排除原所选头。\n\n![同层对照](figures/matched_head_controls.png)\n\n| 结构 | 历史 | 正确率，95%CI | 相对完整模型变化，95%CI | 原诊断一致率 |\n|---|---|---|---|---|\n']
    for r in summaries:
        if r['dataset']=='all':lines.append(f'| {LABELS[r["candidate"]]} | {r["condition"]} | {fmt(r["accuracy"],True)} | {fmt(r["accuracy_change"],True)} | {fmt(r["fidelity"],True)} |\n')
    lines.append('\n## 所选头与同层对照直接比较\n\n| 对照 | 历史 | 所选头减去对照的准确率差 | 错误历史三比较Holm校正p |\n|---|---|---|---|\n')
    for r in contrasts:lines.append(f'| {LABELS[r["control"]]} | {r["condition"]} | {fmt(r["accuracy_difference"],True)} | {r["accuracy_difference"].get("p_holm","—")} |\n')
    lines.append('\n差值按百分点解释。p来自病例级配对符号置换（8000次），仅对预定三个错误历史比较做Holm校正；所有估计同时提供区间。\n\n## 同一批头遇到正确旧诊断\n\n本表明确把来源答案写入历史，是oracle正对照，不能当作正常诊断性能。\n\n| 结构 | 命中来源答案，95%CI | 相对完整模型变化，95%CI |\n|---|---|---|\n')
    for r in oracle:lines.append(f'| {LABELS[r["candidate"]]} | {fmt(r["accuracy"],True)} | {fmt(r["accuracy_change"],True)} |\n')
    lines.append('\n干预在错误历史下的准确率作用，减去在正确历史下的作用：'+fmt(history_specificity,True)+'（百分点）。\n\n## 实际生成完整候选\n\n| 结构 | 历史 | 答对/130 | 相对完整模型变化，95%CI |\n|---|---|---:|---|\n')
    for r in generation:lines.append(f'| {GEN_LABELS[r["candidate"]]} | {r["condition"]} | {r["correct"]} | {fmt(r["accuracy_change"],True)} |\n')
    lines.append('\n代码实验及首步生成只作用于最后输入位置；全生成版本在之后每个生成词元上也持续门控同一8头。两者预填充经过一致性检验，并用空门控检查缓存解码与原生实现相同。所有版本都保留模型参数，不报告头压缩或加速。[冻结追加方案](../../research_v5_structural/FOLLOWUP_HEAD_CONTROLS.md) · [全部统计](summary.json) · [逐病例代码输出](patient_code_results.csv) · [逐病例实际生成](patient_generation_results.csv)\n')
    (OUT/'RESULTS.md').write_text(''.join(lines))
    audit=dict(complete=True,cases=130,code_conditions=2600,oracle_gold_code_conditions=520,actual_generations=780,disjoint_from_initial_390=True,source_sha256=meta['source_sha256'],spec_sha256=meta['spec_sha256'],native_checks=20,max_native_q_error=max(native),cached_decode_checks=numerical,matched_control_counts=True,api_cost_usd=0);write(ROOT/'research_v5_structural/FOLLOWUP_VALIDATION.json',audit)
    final=read(ROOT/'research_v5_structural/FINAL_VALIDATION.json');final['stages']['head_followup']=audit;final['unique_cases_including_followup']=520;write(ROOT/'research_v5_structural/FINAL_VALIDATION.json',final)
    write(ROOT/'research_v5_structural/head_followup_complete.json',dict(complete=True))
    print(json.dumps(dict(complete=True,cases=130,summary=str(OUT/'summary.json'))))

if __name__=='__main__':main()
