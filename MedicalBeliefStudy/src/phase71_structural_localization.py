"""Patient-level causal maps; candidate rankings use 18 development cases only."""
import json,collections
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
import matplotlib.pyplot as plt
from phase41_multisource_analyze import ROOT,DATA,read,write,csvwrite,stat,fmt
from phase45_multisource_deep import codeobs
from analyze_stages import setup,savefig

RUN=ROOT/'runs/structural_v1';OUT=ROOT/'results/42_structural_localization'
def js(q,p):
    q=np.maximum(np.array(q,float),1e-30);p=np.maximum(np.array(p,float),1e-30);m=(q+p)/2
    return float(.5*np.sum(q*np.log(q/m)+p*np.log(p/m)))
def change(q,base,g):
    q=np.array(q);p=np.array(base);winner=int(p.argmax());runner=int(np.argsort(p)[-2])
    return dict(flip=int(q.argmax()!=winner),accuracy=int(q.argmax()==g),accuracy_change=int(q.argmax()==g)-int(winner==g),js=js(q,p),original_support_change=float(q[winner]-p[winner]),gold_support_change=float(q[g]-p[g]))
def average_patient(rows,keys,fields):
    bins=collections.defaultdict(list)
    for r in rows:bins[tuple(r[k] for k in keys)].append(r)
    return [dict(zip(keys,key),**{f:float(np.mean([r[f] for r in rr])) for f in fields}) for key,rr in bins.items()]
def main():
    assert read(RUN/'screen/completion.json')['complete'];setup();(OUT/'figures').mkdir(parents=True,exist_ok=True)
    spec=read(RUN/'screen/manifest.json');cs={c['case_id']:c for c in map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines())};global_rows=[];head_rows=[];geometry=[];errors=[]
    fields=['flip','accuracy','accuracy_change','js','original_support_change','gold_support_change']
    for cid in spec['screen']:
        c=cs[cid]
        for cond in ['neutral','wrong']:
            for rot in [0,2]:
                z=read(RUN/'screen'/f'{cid}_{cond}_r{rot}.json');base=z['baseline']['q'];meta=dict(case_id=cid,dataset=c['dataset'],condition=cond,rotation=rot)
                errors.append(dict(**meta,native_q_error=z['native_q_error'],sham_q_error=z['sham_q_error'],sham_top_changes=z['sham_top_changes']))
                for r in z['global_deletions']:global_rows.append(dict(**meta,layer=r['layer'],kind=r['kind'],**change(r['q'],base,c['gold_index'])))
                shams={r['layer']:r['q'] for r in z['anchor_deletions'] if r['component']=='sham'}
                for r in z['anchor_deletions']:
                    if r['component']=='sham':continue
                    item=dict(**meta,layer=r['layer'],component=r['component'],**change(r['q'],shams[r['layer']],c['gold_index']))
                    if r['component'].startswith('head_'):
                        h=int(r['component'].split('_')[1])-1;a=z['geometry'][r['layer']-1]['attention'][h];item.update(head=h+1,history_attention=a[3],patient_attention=a[1]+a[2])
                    head_rows.append(item)
                for r in z['geometry']:geometry.append(dict(**meta,layer=r['layer'],block_influence=r['block_influence'],relative_update=r['relative_update']))
    gp=average_patient(global_rows,['case_id','dataset','condition','layer','kind'],fields);hp=average_patient([r for r in head_rows if 'head' in r],['case_id','dataset','condition','layer','head'],fields+['history_attention','patient_attention'])
    csvwrite(OUT/'global_deletions.csv',gp);csvwrite(OUT/'anchor_head_deletions.csv',hp);csvwrite(OUT/'anchor_all_components.csv',head_rows);csvwrite(OUT/'block_geometry.csv',geometry);csvwrite(OUT/'numerical_controls.csv',errors)
    summary=[]
    for kind in ['block','attention','mlp']:
        for l in range(1,29):
            rec=dict(kind=kind,layer=l)
            for cond in ['neutral','wrong']:
                rr=[r for r in gp if r['kind']==kind and r['layer']==l and r['condition']==cond]
                for f in fields:rec[cond+'_'+f]=stat([r[f] for r in rr])
            summary.append(rec)
    rankings={}
    for kind in ['block','mlp']:
        rr=[r for r in summary if r['kind']==kind]
        rankings[kind]=[r['layer'] for r in sorted(rr,key=lambda r:(np.mean([r[c+'_flip']['mean'] for c in ['neutral','wrong']]),np.mean([r[c+'_js']['mean'] for c in ['neutral','wrong']]),r['layer']))]
    head_summary=[]
    for l in range(1,29):
        for h in range(1,17):
            r=dict(layer=l,head=h)
            for cond in ['neutral','wrong']:
                rr=[x for x in hp if x['layer']==l and x['head']==h and x['condition']==cond]
                for f in fields+['history_attention']:r[cond+'_'+f]=float(np.mean([x[f] for x in rr]))
            r['repair_score']=r['wrong_accuracy_change']+r['neutral_accuracy_change']-max(0,-r['neutral_accuracy_change'])
            head_summary.append(r)
    ranked_heads=sorted(head_summary,key=lambda r:(-r['repair_score'],-r['wrong_gold_support_change'],r['neutral_flip'],r['layer'],r['head']))
    # Read existing final-head projections, but use development patients only
    # when selecting the fixed early-exit depth.
    early=[];traj=[]
    strict={r['case_id'] for r in read(DATA/'text_audit.json')['rows'] if r['strict_keep']}
    for c in cs.values():
        if not c['mechanism_capture'] or c['case_id'] not in strict:continue
        T=len(c['sentences'])
        for cond in ['neutral','wrong']:
            per_layer=collections.defaultdict(list)
            for rot in [0,2]:
                for t in range(1,T+1):
                    z=codeobs(c,cond,t,rot);q=np.array(z['layer_code_support']);final=q[-1].argmax();pred=q.argmax(1);ma=np.array(z['layer_code_candidate_mass'])
                    for l in range(28):per_layer[l].append(dict(agree=int(pred[l]==final),accuracy=int(pred[l]==c['gold_index']),mass=float(ma[l])))
                    if t==T:
                        for l in range(28):early.append(dict(case_id=c['case_id'],cohort=c['cohort'],condition=cond,rotation=rot,layer=l+1,agree=int(pred[l]==final),accuracy=int(pred[l]==c['gold_index']),baseline_accuracy=int(final==c['gold_index']),mass=float(ma[l])))
            for l,rr in per_layer.items():traj.append(dict(case_id=c['case_id'],cohort=c['cohort'],condition=cond,layer=l+1,**{f:float(np.mean([r[f] for r in rr])) for f in ['agree','accuracy','mass']}))
    csvwrite(OUT/'all_round_projection_alignment.csv',traj);csvwrite(OUT/'endpoint_projection_alignment.csv',early);early_choices=[]
    for l in range(1,29):
        r=dict(layer=l);passing=True
        for cond in ['neutral','wrong']:
            rr=[x for x in early if x['cohort']=='development' and x['layer']==l and x['condition']==cond];a=np.mean([x['agree'] for x in rr]);delta=np.mean([x['accuracy']-x['baseline_accuracy'] for x in rr]);mass=np.mean([x['mass'] for x in rr]);r.update({cond+'_fidelity':float(a),cond+'_accuracy_change':float(delta),cond+'_mass':float(mass)})
            passing &= a>=.95 and delta>=-.02 and mass>=.9
        r['passes_development']=bool(passing);early_choices.append(r)
    exit_layer=next((r['layer'] for r in early_choices if r['passes_development'] and r['layer']<28),27)
    candidates=[dict(name='baseline'),dict(name='early_exit',exit_layer=exit_layer)]
    for kind in ['block','mlp']:
        for n in ([1,2] if kind=='block' else [2,4]):candidates.append(dict(name=f'drop_{kind}_{n}',**{'drop_blocks' if kind=='block' else 'drop_mlps':rankings[kind][:n]}))
    for n in [2,4]:
        for rank in [16,64]:candidates.append(dict(name=f'linear_mlp_{n}_r{rank}',replace_mlps=rankings['mlp'][:n],rank=rank))
    for n in [2,4,8]:
        mapping=collections.defaultdict(list)
        for r in ranked_heads[:n]:mapping[str(r['layer'])].append(r['head'])
        candidates.append(dict(name=f'anchor_heads_{n}',anchor_drop_heads=dict(mapping)))
    bi=sorted(range(1,29),key=lambda l:np.mean([r['block_influence'] for r in geometry if r['layer']==l]))
    candidates.append(dict(name='block_influence_2',drop_blocks=bi[:2]))
    # Fixed-seed, nearby-depth deletion controls; do not favor obviously early
    # layers as a straw-man baseline.
    for n in [2,4]:
        chosen=rankings['mlp'][:n];random_layers=[];rng=np.random.default_rng(71100+n)
        for l in chosen:
            pool=[v for v in range(max(1,l-3),min(28,l+3)+1) if v not in chosen+random_layers]
            if not pool:pool=[v for v in range(1,29) if v not in chosen+random_layers]
            random_layers.append(int(rng.choice(pool)))
        candidates.append(dict(name=f'depth_matched_random_mlp_{n}',drop_mlps=random_layers))
    write(RUN/'development_candidates.json',dict(status='fixed_before_tuning',early_exit_criteria=early_choices,rankings=rankings,ranked_heads=ranked_heads,candidates=candidates,selection_cases=18,tuning_cases=27))
    # Associations are descriptive over component summaries, not independent heads.
    corrs={}
    for cond in ['neutral','wrong']:
        corrs[cond]=float(spearmanr([r[cond+'_history_attention'] for r in head_summary],[r[cond+'_js'] for r in head_summary]).statistic)
    write(OUT/'summary.json',dict(cases=18,prompts=72,global_summary=summary,head_summary=head_summary,early_exit=exit_layer,attention_effect_spearman=corrs,max_native_q_error=max(r['native_q_error'] for r in errors),max_sham_q_error=max(r['sham_q_error'] for r in errors),sham_top_changes=sum(r['sham_top_changes'] for r in errors)))
    fig,axs=plt.subplots(2,3,figsize=(14,7),layout='constrained')
    for j,kind in enumerate(['block','attention','mlp']):
        for cond,col in [('neutral','#317f9e'),('wrong','#bc534c')]:
            rr=[r for r in summary if r['kind']==kind];axs[0,j].plot(range(1,29),[r[cond+'_flip']['mean'] for r in rr],'-o',ms=3,label=cond,c=col);axs[1,j].plot(range(1,29),[r[cond+'_accuracy_change']['mean'] for r in rr],'-o',ms=3,label=cond,c=col)
        axs[0,j].set(title={'block':'删除整层','attention':'删除整层attention','mlp':'删除整层MLP'}[kind],ylabel='最终诊断改变比例',xlabel='层');axs[1,j].set(ylabel='来源答案命中率变化',xlabel='层');axs[1,j].axhline(0,c='gray',lw=.8);axs[0,j].legend()
    fig.suptitle('全输入词元上的单组件删除｜18例开发病例，两种代码映射');savefig(fig,OUT/'figures/global_deletion_map')
    fig,axs=plt.subplots(1,3,figsize=(14,6),layout='constrained')
    for ax,field,title in zip(axs,['wrong_history_attention','wrong_flip','wrong_accuracy_change'],['头对旧病名的注意力','移除头后最终诊断改变','移除头后正确率变化']):
        mat=np.array([r[field] for r in head_summary]).reshape(28,16);im=ax.imshow(mat,origin='lower',aspect='auto',cmap='coolwarm' if 'accuracy' in field else 'viridis');ax.set(title=title,xlabel='头',ylabel='层',xticks=[0,3,7,11,15],xticklabels=[1,4,8,12,16],yticks=[0,6,13,20,27],yticklabels=[1,7,14,21,28]);fig.colorbar(im,ax=ax)
    fig.suptitle('只移除最终诊断位置的一个头，重算后续计算｜错误历史、开发18例');savefig(fig,OUT/'figures/head_attention_vs_causality')
    fig,axs=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    for cond,col in [('neutral','#317f9e'),('wrong','#bc534c')]:
        for ax,f in zip(axs,['agree','accuracy']):
            ys=[np.mean([r[f] for r in traj if r['condition']==cond and r['layer']==l]) for l in range(1,29)];ax.plot(range(1,29),ys,label=cond,c=col)
    axs[0].set(title='逐轮投影与同轮完整模型一致率',xlabel='层',ylabel='病例内轮次平均');axs[1].set(title='逐轮投影命中最终来源答案',xlabel='层',ylabel='非中间轮医学真值准确率');axs[0].legend();axs[1].legend();savefig(fig,OUT/'figures/readout_alignment')
    (OUT/'RESULTS.md').write_text('# 哪些内部计算决定最终诊断\n\n定位使用18例开发病例、72个提示，穷尽28层×3种全序列模块删除，共6048个；另对28层×16个注意力头以及三个整体组件做诊断位置干预，共38304个，另2016个自身对照。头干预作用于最后输入位置，不等于已删除全模型的该头。\n\n![全序列删除](figures/global_deletion_map.png)\n\n![头与作用](figures/head_attention_vs_causality.png)\n\n![读出一致性](figures/readout_alignment.png)\n\n最终答案一致、来源答案正确和删除后改变分别记录。中间轮投影命中最终来源答案不代表该轮具备唯一诊断真值。注意力/作用的相关只作描述，不把448个头当成448名独立患者。\n\n[汇总](summary.json) · [患者级模块删除](global_deletions.csv) · [患者级头删除](anchor_head_deletions.csv) · [数值对照](numerical_controls.csv)\n')
    print(json.dumps(dict(output=str(OUT),early_exit=exit_layer,rankings=rankings,candidates=len(candidates))))
if __name__=='__main__':main()
