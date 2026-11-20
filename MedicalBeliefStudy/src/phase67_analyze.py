"""Case-weighted analysis of the frozen 49-diagnosis experiment; no model calls."""
from pathlib import Path
import json, argparse, textwrap
import numpy as np
from scipy.stats import spearmanr
import matplotlib.pyplot as plt
from analyze_stages import setup, savefig, dump, csvwrite, winner, changed, js, ci, fmt, divinfo

ROOT=Path(__file__).resolve().parents[1]
FAMILIES={'respiratory':'呼吸','cardiovascular':'心血管','ent':'耳鼻喉','neurologic':'神经','systemic':'全身性疾病','digestive':'消化'}
def readlines(p):return [json.loads(s) for s in p.read_text().splitlines()]
def wn(q,names):
    w=int(winner(q));return names[w] if w>=0 else 'TIED'
def rank(q,y):return int(1+np.sum(q>q[y]))
def short(s):return '\n'.join(textwrap.wrap(s,30))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--skip-atlas',action='store_true');args=ap.parse_args();setup()
    run=ROOT/'runs/full49_v1';assert (run/'completion.json').exists()
    cases=readlines(ROOT/'data/full49_v1/cases.private.jsonl');jobs=readlines(ROOT/'data/full49_v1/jobs.public.jsonl')
    diseases=jobs[0]['candidate_diseases'];records=[json.loads(p.read_text()) for p in sorted((run/'observations').glob('*.json'))]
    assert len(records)==5040;lookup={(r['case_id'],r['order'],r['round'],r['rotation']):r for r in records}
    six=ROOT/'results/06_full_candidate_trajectories';seven=ROOT/'results/07_attention_and_layers'
    for folder in [six,seven]:
        (folder/'figures').mkdir(parents=True,exist_ok=True)
    (six/'cases').mkdir(exist_ok=True)
    metrics=[];events=[];layerrows=[];attrows=[];atlas=[];allprogress=[];layer_cases=[];component_cases=[];attention_cases=[];head_cases=[];transition=np.zeros((49,49),int)
    for c in cases:
        cid=c['case_id'];T=len(c['orders']['base']);y=diseases.index(c['gold_disease']);ref=np.array([c['reference_differential'].get(d,0.) for d in diseases]);assert abs(ref.sum()-1)<1e-7
        def get(order,t,m):return lookup[cid,'base' if t==0 else order,t,m]
        def traj(order):return np.array([[get(order,t,m)['q'] for m in [0,16]] for t in range(T+1)])
        qb=traj('base');qr=traj('reverse');q=qb.mean(1);pred=winner(q);correct=pred==y
        finals={o:np.array([get(o,T,m)['q'] for m in [0,16,32]]) for o in ['base','reverse','shuffle']}
        fq=finals['base'];fmean=fq.mean(0);fm=int(winner(fmean));initial=np.mean([get('base',0,m)['q'] for m in [0,16,32]],axis=0)
        stable=next((t for t in range(T+1) if np.all(correct[t:])),None);first=next((t for t in range(T+1) if correct[t]),None)
        r={'case_id':cid,'family':c['family'],'gold':c['gold_disease'],'updates':T,'reference_label_is_top':bool(winner(ref)==y),
           'initial_mean3_correct':bool(winner(initial)==y),'final_mean3_correct':bool(fm==y),'final_m0_correct':bool(winner(fq[0])==y),
           'final_mean3_top':wn(fmean,diseases),'reference_top':wn(ref,diseases),'final_reference_top_agreement':bool(fm==winner(ref) and fm>=0),
           'final_reference_mass_on_prediction':float(ref[fm]) if fm>=0 else 0.,'final_reference_js':float(js(fmean,ref)),
           'final_gold_support':float(fmean[y]),'final_gold_rank':rank(fmean,y),'final_brier':float(np.sum((fmean-np.eye(49)[y])**2)),
           'final_label_nll':float(-np.log(max(fmean[y],1e-30))),'final_gold_margin':float(fmean[y]-np.max(np.delete(fmean,y))),
           'mapping_endpoint_changes':len(set(winner(fq))-{ -1 })>1,'mapping_endpoint_ties':int(np.sum(winner(fq)<0)),
           'mapping_gold_range':float(np.ptp(fq[:,y])),'mapping_js':float(np.mean([js(fq[a],fq[b]) for a,b in [(0,1),(0,2),(1,2)]])),
           'base_reverse_flip_mean3':bool(changed(fmean,finals['reverse'].mean(0))),
           'base_shuffle_flip_mean3':bool(changed(fmean,finals['shuffle'].mean(0))),
           'base_reverse_flip_paired':float(np.mean(changed(fq,finals['reverse']))),
           'base_reverse_js_paired':float(np.mean(js(fq,finals['reverse']))),
           'base_reverse_js_mean3':float(js(fmean,finals['reverse'].mean(0))),
           'base_shuffle_js_mean3':float(js(fmean,finals['shuffle'].mean(0))),
           'regression_any_mean2':bool(np.any(correct[:-1]&~correct[1:]&(pred[1:]>=0))),
           'recovery_any_mean2':bool(np.any(~correct[:-1]&correct[1:]&(pred[:-1]>=0))),
           'switch_rate_mean2':float(np.mean(changed(q[:-1],q[1:]))),'update_js_mean2':float(np.mean(js(q[:-1],q[1:]))),
           'first_correct_round':first,'stable_correct_round':stable,'stable_correct_fraction':stable/T if stable is not None else None,
           'trajectory_tied_rounds':int(np.sum(pred<0))}
        metrics.append(r)
        # Every base prefix and both fixed mappings; state arrays are read once.
        layers=[];components=[];attentions=[];heads=[];densities=[];infos=[];case_event=[]
        for t in range(T+1):
            ls=[];comps=[];ats=[];hs=[];ds=[];dsinfo=[]
            for mi,m in enumerate([0,16]):
                rec=get('base',t,m)
                with np.load(run/rec['state_file']) as a:
                    support=a['component_support'].astype(float);attention=a['attention_by_group'].astype(float)
                    assert np.allclose(support.sum(-1),1,atol=1e-5);assert np.allclose(attention.sum(-1),1,atol=1e-5)
                    count=np.asarray(rec['group_token_counts']);density=attention/np.maximum(count,1)[None,None,:]
                    aggregate=np.stack([attention[:,:,0],attention[:,:,1],attention[:,:,2],attention[:,:,3:].sum(-1)],axis=-1)
                    ls.append(support[:,2]);comps.append(support);ats.append(aggregate.mean(1));hs.append(aggregate)
                    ds.append(np.stack([attention[:,:,3].mean(1),attention[:,:,-1].mean(1),density[:,:,3].mean(1),density[:,:,-1].mean(1)],axis=-1))
                    di=divinfo(support[:,2],y);dsinfo.append(di)
                    for l in range(28):
                        layerrows.append({'case_id':cid,'family':c['family'],'round':t,'rotation':m,'layer':l+1,'gold_support':float(support[l,2,y]),
                                          'top':wn(support[l,2],diseases),'final_top':wn(rec['q'],diseases),'candidate_mass':float(a['component_candidate_mass'][l,2]),
                                          'js_to_final':float(js(support[l,2],rec['q']))})
            layers.append(np.mean(ls,0));components.append(np.mean(comps,0));attentions.append(np.mean(ats,0));heads.append(np.mean(hs,0));densities.append(np.mean(ds,0));infos.append(dsinfo)
        layers=np.array(layers);components=np.array(components);attentions=np.array(attentions);heads=np.array(heads);densities=np.array(densities)
        finalpred=winner(q)[:,None];lpred=winner(layers)
        layer_cases.append(np.stack([layers[:,:,y].mean(0),np.mean((lpred==finalpred)&(lpred>=0),axis=0),js(layers,q[:,None,:]).mean(0)],-1))
        component_cases.append(components[:,:,:,y].mean(0));attention_cases.append(attentions.mean(0));head_cases.append(heads.mean(0))
        robust=[all(d['divergence'] for d in pair) and len({(d['late_disease'],d['final_disease']) for d in pair})==1 for pair in infos]
        r.update(any_robust_late_divergence=any(robust),raw_late_divergence_rate=float(np.mean([d['divergence'] for pair in infos for d in pair])),
                 layer27_final_disagree_rate=float(np.mean([d['l27_disagree'] for pair in infos for d in pair])))
        for t in range(1,T+1):
            a,b=int(pred[t-1]),int(pred[t]);
            if a>=0 and b>=0:transition[a,b]+=1
            newgroup=c['orders']['base'][t-1]
            er={'case_id':cid,'family':c['family'],'round':t,'new_group':newgroup,'gold':c['gold_disease'],'previous_top':wn(q[t-1],diseases),
                'current_top':wn(q[t],diseases),'switch':bool(changed(q[t-1],q[t])),'regression':bool(a==y and b>=0 and b!=y),
                'recovery':bool(a>=0 and a!=y and b==y),'delta_gold':float(q[t,y]-q[t-1,y]),'js':float(js(q[t-1],q[t])),
                'new_evidence_attention_late':float(densities[t,23:,1].mean()),'new_evidence_density_late':float(densities[t,23:,3].mean()),
                'layer27_delta_gold':float(layers[t,26,y]-layers[t-1,26,y]),
                **{f'delta_{d}':float(q[t,j]-q[t-1,j]) for j,d in enumerate(diseases)}}
            events.append(er);case_event.append(er)
        for l in range(28):
            attrows.append({'case_id':cid,'family':c['family'],'layer':l+1,**{k:float(v) for k,v in zip(['format','candidates','demographics','evidence'],attentions[:,l].mean(0))},
                            'initial_mass':float(densities[:,l,0].mean()),'latest_mass':float(densities[1:,l,1].mean()),
                            'initial_per_token':float(densities[:,l,2].mean()),'latest_per_token':float(densities[1:,l,3].mean())})
        allprogress.append([q[int(round(frac*T)),y] for frac in np.linspace(0,1,11)])
        if not args.skip_atlas:
            best=list(dict.fromkeys([y]+[int(i) for i in np.argsort(q.max(0))[::-1][:5]]))[:6]
            fig,axes=plt.subplots(3,1,figsize=(11,12),gridspec_kw={'height_ratios':[1.4,1.2,1]})
            for d in best:
                line=axes[0].plot(range(T+1),q[:,d],label=diseases[d],lw=2.5 if d==y else 1.5)[0]
                axes[0].fill_between(range(T+1),qb[:,:,d].min(1),qb[:,:,d].max(1),alpha=.12,color=line.get_color())
            axes[0].set(ylabel='Candidate support',ylim=(-.02,1.02),title=f'{cid} | label: {c["gold_disease"]}');axes[0].legend(fontsize=8,loc='upper left',bbox_to_anchor=(1.01,1))
            im=axes[1].imshow(layers[:,:,y].T,aspect='auto',origin='lower',vmin=0,vmax=1,extent=[-.5,T+.5,.5,28.5],cmap='viridis');fig.colorbar(im,ax=axes[1],label='Raw projected label support');axes[1].set(ylabel='Layer',yticks=[1,7,14,21,28])
            for j,label in enumerate(['Format','Candidates','Demographics','Evidence']):axes[2].plot(range(T+1),attentions[:,23:,j].mean(1),label=label)
            axes[2].set(xlabel='Evidence update (0 = initial group)',ylabel='Attention mass (layers 24–28)',ylim=(-.02,1.02));axes[2].legend(fontsize=8)
            fig.tight_layout();savefig(fig,six/'cases'/cid)
            evidence=[c['initial_question_group']]+c['orders']['base']
            lines=[f'# {cid}',f'\n源标签：**{c["gold_disease"]}**；参考首位：**{wn(ref,diseases)}**。\n',f'![轨迹]({cid}.png)\n',
                   '实线为两个编码的平均分，阴影为两编码范围；逐层热图为原始投影，注意力曲线为晚5层均值。终点评价使用三个编码，可能与此处两编码轨迹不同。\n',
                   '| 轮 | 新证据（原始英文） | 当前首选 | 标签支持 |','|---|---|---|---|']
            for t,g in enumerate(evidence):
                desc='<br>'.join(x['question_en']+' **'+x['answer_en']+'**' for x in c['explicit_evidence_groups'][g]).replace('|','/')
                lines.append(f'| {t} | {desc} | {wn(q[t],diseases)} | {q[t,y]:.4f} |')
            (six/'cases'/f'{cid}.md').write_text('\n'.join(lines)+'\n')
        atlas.append(f'| [{cid}](cases/{cid}.md) | {FAMILIES[c["family"]]} | {c["gold_disease"]} | {r["final_mean3_top"]} | {T} |')
        if len(metrics)%20==0:print(f'Analyzed {len(metrics)}/120',flush=True)
    measures=['initial_mean3_correct','final_mean3_correct','final_m0_correct','reference_label_is_top','final_reference_top_agreement','final_reference_js','final_gold_support','final_gold_rank','final_brier','final_label_nll','final_gold_margin','mapping_endpoint_changes','mapping_gold_range','mapping_js','base_reverse_flip_mean3','base_shuffle_flip_mean3','base_reverse_flip_paired','base_reverse_js_mean3','base_shuffle_js_mean3','regression_any_mean2','recovery_any_mean2','switch_rate_mean2','update_js_mean2','raw_late_divergence_rate','any_robust_late_divergence','layer27_final_disagree_rate']
    summaries={k:ci([r[k] for r in metrics]) for k in measures}
    fam=[]
    for f in FAMILIES:
        rr=[r for r in metrics if r['family']==f]
        fam.append({'family':f,'cases':len(rr),**{k:float(np.mean([r[k] for r in rr])) for k in measures}})
    numerical={'observations':len(records),'native_checks':sum(r['native_check'] is not None for r in records),
               'all_native_checks_pass':all(r['native_check']['allclose'] and r['native_check']['same_argmax'] for r in records if r['native_check']),
               'max_attention_reconstruction_relative_rms':max(r['max_attention_reconstruction_relative_rms'] for r in records),
               'candidate_mass_min':min(r['candidate_mass'] for r in records),'candidate_mass_mean':float(np.mean([r['candidate_mass'] for r in records])),
               'unconstrained_first_outside_candidates':sum(r['greedy_first_disease'] is None for r in records),'tied_observations':int(sum(winner(r['q'])<0 for r in records))}
    summary={'cases':120,'diseases':24,'candidates':49,'base_updates':len(events),'case_weighted':summaries,'family_macro':{k:float(np.mean([r[k] for r in fam])) for k in measures},'numerical':numerical}
    dump(six/'summary.json',summary);csvwrite(six/'case_metrics.csv',metrics);csvwrite(six/'family_metrics.csv',fam);csvwrite(six/'evidence_transitions.csv',events)
    csvwrite(seven/'layer_metrics.csv',layerrows);csvwrite(seven/'attention_metrics.csv',attrows)
    lc=np.array(layer_cases);ac=np.array(attention_cases);hc=np.array(head_cases);cc=np.array(component_cases)
    corr=[]
    for c in cases:
        ev=[r for r in events if r['case_id']==c['case_id']];x=[r['new_evidence_density_late'] for r in ev];y=[r['js'] for r in ev]
        corr.append(float(spearmanr(x,y).statistic) if len(set(x))>1 and len(set(y))>1 else np.nan)
    lsummary={'raw_layer27_final_disagreement':summaries['layer27_final_disagree_rate'],'cases_any_mapping_robust_late_divergence':int(sum(r['any_robust_late_divergence'] for r in metrics)),
              'per_case_spearman_new_evidence_density_vs_update_js':ci(corr),
              'attention_all_layers':{k:ci(ac[:,:,i].mean(1)) for i,k in enumerate(['format','candidates','demographics','evidence'])},
              'attention_late5':{k:ci(ac[:,23:,i].mean(1)) for i,k in enumerate(['format','candidates','demographics','evidence'])},
              'layer_gold_support':lc[:,:,0].mean(0).tolist(),'layer_agreement_with_final':lc[:,:,1].mean(0).tolist(),
              'layer_js_to_final':lc[:,:,2].mean(0).tolist(),'case_mean_component_gold_support':cc.mean(0).tolist(),'numerical':numerical}
    dump(seven/'summary.json',lsummary);np.savez_compressed(seven/'case_aggregates.npz',layer=lc,attention=ac,head_attention=hc,component=cc,case_ids=np.array([c['case_id'] for c in cases]))
    # Main figures: all aggregate calculations give each case equal weight.
    fig,axes=plt.subplots(1,2,figsize=(12,4.8));xx=np.arange(len(fam))
    for off,key,label in [(-.18,'initial_mean3_correct','Initial'),(.18,'final_mean3_correct','Final')]:axes[0].bar(xx+off,[r[key] for r in fam],.36,label=label)
    axes[0].set(xticks=xx,xticklabels=[FAMILIES[r['family']] for r in fam],ylabel='Label accuracy',ylim=(0,1));axes[0].legend()
    prog=np.array(allprogress);bands=[ci(prog[:,j]) for j in range(11)];axes[1].plot(np.linspace(0,1,11),prog.mean(0));axes[1].fill_between(np.linspace(0,1,11),[v['low'] for v in bands],[v['high'] for v in bands],alpha=.2)
    axes[1].set(xlabel='Fraction of available updates',ylabel='Mean label support (2 mappings)',ylim=(0,1));fig.tight_layout();savefig(fig,six/'figures/cohort_progress')
    fig,ax=plt.subplots(figsize=(9,4.8));keys=['mapping_endpoint_changes','base_reverse_flip_mean3','base_shuffle_flip_mean3','regression_any_mean2'];labels=['Different code mappings','Reverse order\n(mean 3 mappings)','Shuffle order\n(mean 3 mappings)','Correct then deviates\n(mean 2 mappings)']
    vals=[summaries[k] for k in keys];ax.bar(range(4),[v['mean'] for v in vals],yerr=np.array([[v['mean']-v['low'] for v in vals],[v['high']-v['mean'] for v in vals]]),capsize=4);ax.set(xticks=range(4),xticklabels=labels,ylabel='Fraction of cases',ylim=(0,1));fig.tight_layout();savefig(fig,six/'figures/order_mapping')
    fig,axes=plt.subplots(1,3,figsize=(15,4.6));x=np.arange(1,29)
    for j,label in enumerate(['Pre-attention','Post-attention','Post-MLP']):axes[0].plot(x,cc[:,:,j].mean(0),label=label)
    axes[0].set(xlabel='Layer',ylabel='Raw projected label support');axes[0].legend(fontsize=8)
    axes[1].plot(x,lc[:,:,1].mean(0));axes[1].set(xlabel='Layer',ylabel='Top-choice agreement with final',ylim=(0,1))
    for j,label in enumerate(['Format','Candidates','Demographics','Evidence']):axes[2].plot(x,ac[:,:,j].mean(0),label=label)
    axes[2].set(xlabel='Layer',ylabel='Attention mass',ylim=(0,1));axes[2].legend(fontsize=8);fig.tight_layout();savefig(fig,seven/'figures/layers_and_evidence')
    fig,ax=plt.subplots(figsize=(10,6));im=ax.imshow(hc[:,:,:,3].mean(0),origin='lower',aspect='auto',vmin=0,vmax=1,extent=[.5,16.5,.5,28.5]);fig.colorbar(im,ax=ax,label='Attention to clinical evidence body');ax.set(xlabel='Attention head',ylabel='Layer',yticks=[1,7,14,21,28]);fig.tight_layout();savefig(fig,seven/'figures/head_evidence_attention')
    atlashead='# 全部120例病例图谱\n\n逐例展示每轮新证据、疾病支持、逐层原始投影与注意力。全部病例均列出，不按现象挑选。\n\n| 病例 | 组 | 源标签 | 终点首选（三编码均值） | 更新数 |\n|---|---|---|---|---|\n'
    (six/'CASE_ATLAS.md').write_text(atlashead+'\n'.join(atlas)+'\n')
    f=lambda k,p=True:fmt(summaries[k],p)
    tab='\n'.join(f'| {FAMILIES[r["family"]]} | {r["cases"]} | {r["initial_mean3_correct"]:.1%} | {r["final_mean3_correct"]:.1%} | {r["base_reverse_flip_mean3"]:.1%} |' for r in fam)
    (six/'RESULTS.md').write_text(f'''# 阶段06：完整疾病空间中的诊断更新

## 方法

Qwen3-1.7B FP16，冻结参数，本机GPU。DDxPlus validate 中固定哈希抽取120个新病例，24病种各5例；六个疾病组、全部49疾病候选。病例与此前252例去重。无旧回答历史：每轮重新输入累计证据。基础和逆序各追踪全轮，独立乱序测终点；两编码贯穿全轨迹，三个编码测初始、中间与终点。完成5040次观测，基础顺序{len(events)}次新增证据。区间为2000次病例bootstrap，全0/全1二元指标使用精确二项区间；同一病例内先汇总，未将多个轮次当独立病例。

## 结果

**扩大候选后，字母接口成为主要测量问题。** 120例中，相同终点资料仅改变疾病—字母对应关系，首选发生变化的比例为{f('mapping_endpoint_changes')}。首个输出token全部落在编码候选中，仍不足以说明对应疾病判断稳定。因此阶段09使用完整疾病名重新测量；本阶段编码结果保留作对照，不单独承担医学机制的核心论证。

| 指标 | 病例均值 [95%区间] |
|---|---|
| 初始标签命中（三编码均值） | {f('initial_mean3_correct')} |
| 终点标签命中（三编码均值） | {f('final_mean3_correct')} |
| 终点标签命中（固定单编码） | {f('final_m0_correct')} |
| 标签曾命中后偏离（两编码均值轨迹） | {f('regression_any_mean2')} |
| 相同终点资料仅换编码，首选不同 | {f('mapping_endpoint_changes')} |
| 相同终点事实逆序，首选不同（三编码均值） | {f('base_reverse_flip_mean3')} |
| 相同终点事实乱序，首选不同（三编码均值） | {f('base_shuffle_flip_mean3')} |
| 与源参考分布的JS距离 | {f('final_reference_js',False)} |
| 首选与源参考分布首位一致 | {f('final_reference_top_agreement')} |

| 疾病组 | 病例数 | 初始命中 | 终点命中 | 逆序首选改变 |
|---|---|---|---|---|
{tab}

![总体结果](figures/cohort_progress.png)
![顺序与映射](figures/order_mapping.png)

## 真值与解释

所有49疾病均进入候选，完整覆盖每例参考鉴别分布。源疾病标签与参考分布首位一致的比例为{f('reference_label_is_top')}：标签评价和参考分布评价是两个问题。最终标签可用于计算命中、排名、Brier和NLL；中间每轮没有医学标准后验，“命中后偏离”仅指离开源标签，不能把所有中途改诊都叫错误。候选分数是固定接口下的模型支持，不是患者患病率。

**本阶段给出了跨疾病、跨顺序的完整诊断轨迹。是否形成稳定的医学更新机制，需要结合阶段07的内部读出和阶段08的干预。** 单个病种仅5例，病种差异只作描述；总体结果不以病例数量替代机制证明。

## 数据

- [全部120例逐轮图谱](CASE_ATLAS.md)
- [逐病例指标](case_metrics.csv)、[全部证据转移](evidence_transitions.csv)、[疾病组汇总](family_metrics.csv)
- [精确结果和数值检查](summary.json)

API成本：0美元。
''')
    a=lsummary['attention_late5'];corrtext=fmt(lsummary['per_case_spearman_new_evidence_density_vs_update_js'],False)
    (seven/'RESULTS.md').write_text(f'''# 阶段07：证据进入后，各层和注意力怎样变化

## 测量

每个观测点保留28层诊断位置的进入状态、注意力增量、注意力后状态、MLP增量和离层状态；在进入、注意力后、离层三处投影为49疾病分数。每层16个注意力头分别记录它对模板、候选、人口信息与每组证据的注意力。固定24例另保存逐token注意力、各头输出及各证据末位置状态。参数不在轮间训练；变化的是输入导致的激活与注意力。

以下总体分析采用基础顺序、两编码，每例内部先平均。逐层分数是原始输出头读出，尚未经49病独立读出校准。

## 结果

第27层与最终层首选不同的轮次比例：{f('layer27_final_disagree_rate')}。出现“24—27层一致、末层转向”且两个编码同时支持同一疾病对的病例为 **{lsummary['cases_any_mapping_robust_late_divergence']}/120**。这直接检验早期个案能否跨编码复现。

晚5层注意力平均分配：证据正文{fmt(a['evidence'])}，候选列表{fmt(a['candidates'])}，模板{fmt(a['format'])}，人口信息{fmt(a['demographics'])}。证据标题被归入模板；证据正文保留全部明确记录的问答。组总质量和每token密度同时输出，避免把更长证据误当作更受重视。

模板位置的隐藏状态也可能已整合前面的病例信息。上述比例测的是“此头直接连向哪些位置”，不是医学信息的总贡献；注意力到模板较多，不能直接解释为忽略患者。

每例内，“新增证据的每token注意力”与“本轮疾病分布改变量”的Spearman相关系数，病例均值为 **{corrtext}**。这是关联测量，因果作用由阶段08干预检验。

![逐层与证据](figures/layers_and_evidence.png)
![注意力头](figures/head_evidence_attention.png)

## 数值检查

5040次观测；{numerical['native_checks']}次完整原生前向对照全部通过：{numerical['all_native_checks_pass']}。重建注意力加权输出相对RMS误差最大{numerical['max_attention_reconstruction_relative_rms']:.6f}。无约束首token落在候选外的观测{numerical['unconstrained_first_outside_candidates']}次。模型权重前后哈希一致。

## 结论

**现在能逐轮定位疾病分数在何层变化，也能量化每个头把注意力分给了哪些证据。** 这些记录将表面的改诊与内部计算连起来；原始读出差异本身仍不能证明某层拥有一个独立且正确的诊断。阶段08测试把特定内部计算换回前轮后，最终判断是否随之改变。

[逐层数据](layer_metrics.csv) · [逐层注意力数据](attention_metrics.csv) · [结果汇总](summary.json) · [病例图谱](../06_full_candidate_trajectories/CASE_ATLAS.md)
''')
    print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
