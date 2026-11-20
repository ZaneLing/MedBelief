"""Patient-level analysis, provenance-preserving tables and scientific plots."""
from pathlib import Path
import collections,csv,hashlib,json
import numpy as np
from scipy.stats import spearmanr,binomtest
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze_stages import setup,savefig

ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data/belief_v4';RUN=ROOT/'runs/belief_v4';DEST=ROOT/'results/32_multisource_belief'
SOURCES=['MedQA','MedMCQA','MMLU']
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def csvwrite(p,rr):
    if not rr:return
    fields=list(dict.fromkeys(k for r in rr for k in r))
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rr)
def stat(values,pvalue=False):
    x=np.array(values,float);x=x[np.isfinite(x)];n=len(x)
    if not n:return dict(n=0,mean=None,low=None,high=None)
    rng=np.random.default_rng(20261120);boot=x[rng.integers(0,n,(4000,n))].mean(1)
    result=dict(n=n,mean=float(x.mean()),median=float(np.median(x)),low=float(np.quantile(boot,.025)),high=float(np.quantile(boot,.975)))
    if np.all(x==1):
        ci=binomtest(int(x.sum()),n).proportion_ci();result.update(low=float(ci.low),high=float(ci.high),interval='exact_binomial_boundary')
    if pvalue:
        null=(rng.choice([-1,1],size=(8000,n))*x).mean(1);result['p']=float((1+np.sum(np.abs(null)>=abs(x.mean())))/(len(null)+1))
    return result
def fmt(s,percent=False):
    if not s['n']:return '无适用病例'
    z=100 if percent else 1;u='%' if percent else ''
    return f"{z*s['mean']:.2f}{u} [{z*s['low']:.2f}, {z*s['high']:.2f}]"
def obs(c,cond,t=None,mode='name',rot=0,order='base'):
    t=t or len(c['sentences']);return read(RUN/'observations'/f'{c["case_id"]}_{cond}_{mode}_r{rot}_{order}_t{t:02d}.json')
def top(z):return int(np.argmax(z['log_probability']))
def margin(z,c):return float(z['log_probability'][c['gold_index']]-z['log_probability'][c['wrong_index']])
def holm(items):
    order=sorted(range(len(items)),key=lambda i:items[i]['p']);last=0
    for j,i in enumerate(order):
        last=max(last,min(1.,(len(items)-j)*items[i]['p']));items[i]['p_holm']=last
def cohort_tables(rr):
    tables={}
    for ds in SOURCES+['all']:
        for cohort in ['all','development','confirmation']:
            sub=[r for r in rr if (ds=='all' or r['dataset']==ds) and (cohort=='all' or r['cohort']==cohort)]
            if not sub:continue
            key=ds+':'+cohort
            fields=['accuracy_none','accuracy_neutral','accuracy_wrong','accuracy_mention','accuracy_gold','wrong_minus_neutral_accuracy','wrong_minus_none_accuracy','mention_minus_neutral_accuracy','wrong_minus_mention_accuracy','order_changed','history_effect_before','history_effect_final','interaction_wrong_neutral','interaction_wrong_mention','interaction_abs','opposite_update_point1','fixed_offset_top_agreement','persistence_top_agreement','offset_error','persistence_error','offset_better_than_persistence']
            tables[key]={f:stat([r[f] for r in sub]) for f in fields}
            x=[r['update_neutral'] for r in sub];y=[r['update_wrong'] for r in sub]
            tables[key]['update_spearman']=float(spearmanr(x,y).statistic) if len(sub)>2 else None
    return tables

def main():
    assert read(RUN/'completion.json')['complete']
    (DEST/'figures').mkdir(parents=True,exist_ok=True);setup()
    cases=list(map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines()));rows=[];traces=[];code=[];internal=[];geometry=[]
    for c in cases:
        T=len(c['sentences']);z={k:obs(c,k) for k in ['none','neutral','gold','wrong','mention']};b={k:obs(c,k,T-1) for k in ['neutral','gold','wrong','mention']}
        r=dict(case_id=c['case_id'],dataset=c['dataset'],cohort=c['cohort'],subject=c['subject'],gold=c['gold_disease'],wrong_prior=c['wrong_disease'],evidence_groups=T,final_evidence=c['sentences'][-1])
        for cond in z:
            r['prediction_'+cond]=c['candidates'][top(z[cond])];r['accuracy_'+cond]=int(top(z[cond])==c['gold_index']);r['margin_'+cond]=margin(z[cond],c)
            if 'generated_disease' in z[cond]:r['generated_accuracy_'+cond]=int(z[cond]['generated_disease']==c['gold_disease']);r['generated_listed_'+cond]=int(z[cond]['generated_disease'] in c['candidates'])
        for cond in b:r['update_'+cond]=margin(z[cond],c)-margin(b[cond],c)
        r['history_effect_before']=margin(b['wrong'],c)-margin(b['neutral'],c);r['history_effect_final']=margin(z['wrong'],c)-margin(z['neutral'],c)
        r['interaction_wrong_neutral']=r['update_wrong']-r['update_neutral'];r['interaction_wrong_mention']=r['update_wrong']-r['update_mention'];r['interaction_abs']=abs(r['interaction_wrong_neutral'])
        r['opposite_update_point1']=int(r['update_wrong']*r['update_neutral']<0 and min(abs(r['update_wrong']),abs(r['update_neutral']))>.1)
        for a,d in [('wrong','neutral'),('wrong','none'),('mention','neutral'),('wrong','mention')]:r[f'{a}_minus_{d}_accuracy']=r['accuracy_'+a]-r['accuracy_'+d]
        r['order_changed']=int(top(obs(c,'none',order='reverse'))!=top(z['none']))
        # Descriptive constant-history-offset prediction, with a persistence baseline.
        predicted=np.array(z['neutral']['log_probability'])+np.array(b['wrong']['log_probability'])-np.array(b['neutral']['log_probability'])
        r['fixed_offset_top_agreement']=int(int(predicted.argmax())==top(z['wrong']));r['persistence_top_agreement']=int(top(b['wrong'])==top(z['wrong']))
        r['offset_error']=abs(r['interaction_wrong_neutral']);r['persistence_error']=abs(r['update_wrong']);r['offset_better_than_persistence']=int(r['offset_error']<r['persistence_error'])
        rows.append(r)
        if c['trajectory_capture']:
            for t in range(1,T+1):
                for cond in ['neutral','gold','wrong']:
                    zz=obs(c,cond,t);traces.append(dict(case_id=c['case_id'],dataset=c['dataset'],cohort=c['cohort'],round=t,total=T,condition=cond,prediction=c['candidates'][top(zz)],gold_support=zz['q_sequence'][c['gold_index']],wrong_support=zz['q_sequence'][c['wrong_index']],margin=margin(zz,c),new_fact=c['sentences'][t-1]))
            for rot in [0,2]:
                nn=obs(c,'neutral',mode='code',rot=rot);ww=obs(c,'wrong',mode='code',rot=rot)
                code.append(dict(case_id=c['case_id'],dataset=c['dataset'],cohort=c['cohort'],rotation=rot,neutral_correct=int(top(nn)==c['gold_index']),wrong_correct=int(top(ww)==c['gold_index']),history_effect=margin(ww,c)-margin(nn,c),prediction_changed=int(top(nn)!=top(ww)),native_name_history_effect=r['history_effect_final']))
        # All 540 cases have all-layer anchors and evidence means at the matched
        # before/after checkpoints. Full trajectories are a separate subset.
        state={}
        for cond in ['neutral','wrong']:
            with np.load(RUN/z[cond]['state_file']) as f:anchor=f['residual_stages'][:,-1].astype(float)
            with np.load(RUN/'mean_repair'/(z[cond]['job_id']+'.npz')) as f:means=f['evidence_means'].astype(float)
            assert np.isfinite(anchor).all() and np.isfinite(means).all()
            state[cond]=(anchor,means)
            with np.load(RUN/b[cond]['state_file']) as f:state[cond+'_before']=f['residual_stages'][:,-1].astype(float)
        hn,en=state['neutral'];hw,ew=state['wrong']
        for l in range(len(hn)):
            for pos,an,aw in [('anchor',hn[l],hw[l]),('new_fact',en[l,0],ew[l,0]),('old_facts',en[l,1],ew[l,1])]:
                cos=float(np.dot(an,aw)/(np.linalg.norm(an)*np.linalg.norm(aw)+1e-12));rel=float(np.linalg.norm(aw-an)/(np.linalg.norm(an)+1e-12))
                internal.append(dict(case_id=c['case_id'],dataset=c['dataset'],cohort=c['cohort'],layer=l+1,position=pos,cosine_distance=1-cos,relative_change=rel))
            dn=hn[l]-state['neutral_before'][l];dw=hw[l]-state['wrong_before'][l]
            geometry.append(dict(case_id=c['case_id'],dataset=c['dataset'],cohort=c['cohort'],layer=l+1,update_cosine=float(np.dot(dn,dw)/(np.linalg.norm(dn)*np.linalg.norm(dw)+1e-12)),relative_update_interaction=float(np.linalg.norm(dw-dn)/(np.linalg.norm(dn)+1e-12)),neutral_update_norm=float(np.linalg.norm(dn)),wrong_update_norm=float(np.linalg.norm(dw))))
    tables=cohort_tables(rows);csvwrite(DEST/'patient_results.csv',rows);csvwrite(DEST/'trajectories.csv',traces);csvwrite(DEST/'code_controls.csv',code);csvwrite(DEST/'internal_history_change.csv',internal)
    csvwrite(DEST/'all_patient_update_geometry.csv',geometry)
    # Joint response summaries do not imply distinct neural mechanisms.
    trajectory_stats=[]
    for c in cases:
        if not c['trajectory_capture']:continue
        for cond in ['neutral','gold','wrong']:
            rr=sorted([r for r in traces if r['case_id']==c['case_id'] and r['condition']==cond],key=lambda r:r['round']);pred=[r['prediction'] for r in rr]
            trajectory_stats.append(dict(case_id=c['case_id'],dataset=c['dataset'],cohort=c['cohort'],condition=cond,switches=sum(a!=b for a,b in zip(pred[:-1],pred[1:])),ever_source_then_leave=int(any(a==c['gold_disease'] and b!=c['gold_disease'] for a,b in zip(pred[:-1],pred[1:]))),source_final=int(pred[-1]==c['gold_disease']),wrong_final=int(pred[-1]==c['wrong_disease'])))
    csvwrite(DEST/'trajectory_patient_summary.csv',trajectory_stats)
    # Preserve all name scores in a compact, analysis-ready export.
    import gzip
    with gzip.open(DEST/'all_candidate_scores.csv.gz','wt',newline='') as f:
        w=csv.writer(f);w.writerow(['job_id','dataset','cohort','case_id','round','condition','mode','rotation','order','candidate','log_probability','relative_support'])
        for p in sorted((RUN/'observations').glob('*.json')):
            zz=read(p)
            for d,lp,q in zip(zz['candidate_diseases'],zz['log_probability'],zz['q_sequence']):w.writerow([zz[k] for k in ['job_id','dataset','cohort','case_id','round','condition','mode','rotation','order']]+[d,lp,q])
    summary=dict(patients=len(cases),datasets=read(DATA/'manifest.json')['selected'],mechanism_patients=sum(c['mechanism_capture'] for c in cases),source_answers=read(DATA/'manifest.json')['unique_source_answers'],observations=read(RUN/'completion.json')['observations'],tables=tables,api_cost_usd=0)
    flags={r['case_id']:r for r in csv.DictReader((DATA/'quality_flags.csv').open())}
    sensitivity={}
    for label,keep in [('no_literal_answer',lambda f:f['source_answer_literal_in_stem']=='False'),('no_near_overlap_point8',lambda f:f['flag_similarity_ge_point8']=='False')]:
        sensitivity[label]=cohort_tables([r for r in rows if keep(flags[r['case_id']])])
    audit=read(DATA/'text_audit.json');keep={r['case_id'] for r in audit['rows'] if r['strict_keep']}
    sensitivity['post_run_text_audit']=cohort_tables([r for r in rows if r['case_id'] in keep])
    summary['quality_sensitivity']=sensitivity
    summary['internal_measurement_patients']=len(cases)
    summary['evidence_mean_reduction']='FP32 corrected sidecars; original FP16 auxiliary means deprecated'
    summary['update_geometry']=[dict(dataset=ds,layer=l,update_cosine=stat([r['update_cosine'] for r in geometry if r['layer']==l and (ds=='all' or r['dataset']==ds)]),relative_update_interaction=stat([r['relative_update_interaction'] for r in geometry if r['layer']==l and (ds=='all' or r['dataset']==ds)])) for ds in SOURCES+['all'] for l in [7,14,21,28]]
    write(DEST/'summary.json',summary)
    # Main figures: source-specific behavior, paired increments, layer changes.
    fig,axs=plt.subplots(1,3,figsize=(14,4.4),layout='constrained')
    labels=['无历史','尚无判断','仅提及错误病','错误旧诊断','正确旧诊断'];conds=['none','neutral','mention','wrong','gold'];colors=['#777f87','#287fa3','#c6a54a','#be514a','#45936a']
    for ax,ds in zip(axs,SOURCES):
        tt=tables[ds+':all'];ss=[tt['accuracy_'+c] for c in conds];v=np.array([s['mean'] for s in ss]);lo=np.array([s['low'] for s in ss]);hi=np.array([s['high'] for s in ss]);ax.bar(range(5),100*v,color=colors);ax.errorbar(range(5),100*v,yerr=100*np.array([v-lo,hi-v]),fmt='none',ecolor='black',capsize=3)
        ax.set(xticks=range(5),xticklabels=labels,ylim=(0,105),title=f'{ds} · n={ss[0]["n"]}',ylabel='完整题目来源答案命中率 (%)');ax.tick_params(axis='x',rotation=25)
    fig.suptitle('同样的当前事实，不同历史条件｜正确历史是含标签的强对照')
    savefig(fig,DEST/'figures/history_by_source')
    fig,axs=plt.subplots(1,3,figsize=(13,4.5),layout='constrained')
    for ax,ds in zip(axs,SOURCES):
        rr=[r for r in rows if r['dataset']==ds];x=np.array([r['update_neutral'] for r in rr]);y=np.array([r['update_wrong'] for r in rr]);ax.scatter(x,y,s=15,alpha=.55,color='#287fa3');lim=max(np.max(np.abs(x)),np.max(np.abs(y)),1)*1.05;ax.plot([-lim,lim],[-lim,lim],'--',color='gray');ax.axhline(0,c='lightgray');ax.axvline(0,c='lightgray');ax.set(xlim=(-lim,lim),ylim=(-lim,lim),xlabel='中性历史：最后一个证据组的作用',ylabel='错误历史：同一证据组的作用',title=f'{ds} · n={len(rr)}')
    fig.suptitle('来源病相对固定错误病的完整病名分差变化｜对角线表示作用相同')
    savefig(fig,DEST/'figures/evidence_update_pairs')
    fig,ax=plt.subplots(figsize=(8,4.6),layout='constrained')
    for pos,label,color in [('new_fact','新事实位置','#b77926'),('old_facts','旧事实位置','#737b86'),('anchor','诊断位置','#387fa6')]:
        ys=[];low=[];high=[]
        for l in range(1,29):
            s=stat([r['relative_change'] for r in internal if r['position']==pos and r['layer']==l]);ys.append(s['mean']);low.append(s['low']);high.append(s['high'])
        ax.plot(range(1,29),ys,label=label,c=color);ax.fill_between(range(1,29),low,high,color=color,alpha=.15)
    ax.set(xlabel='层',ylabel='相对状态变化幅度',title='同一事实在不同历史下的内部变化');ax.legend();savefig(fig,DEST/'figures/internal_history_change')
    fig,axs=plt.subplots(1,2,figsize=(11,4.3),layout='constrained')
    for ds,col in zip(SOURCES,['#287fa3','#c7903b','#6b9381']):
        for ax,field in zip(axs,['update_cosine','relative_update_interaction']):
            ss=[stat([r[field] for r in geometry if r['dataset']==ds and r['layer']==l]) for l in range(1,29)];ax.plot(range(1,29),[s['mean'] for s in ss],c=col,label=ds);ax.fill_between(range(1,29),[s['low'] for s in ss],[s['high'] for s in ss],color=col,alpha=.13)
    axs[0].set(xlabel='层',ylabel='两个更新向量的余弦',ylim=(-.1,1.05),title='同一证据组的内部更新方向是否一致');axs[1].set(xlabel='层',ylabel='更新差异 / 中性历史更新范数',title='历史改变了多少内部更新');axs[0].legend();axs[1].legend();fig.suptitle('全部540例的加入前后配对｜状态方向不是已命名的疾病方向');savefig(fig,DEST/'figures/all_patient_update_geometry')
    # Code projection: untrained head, averaged across two preassigned mappings.
    fig,axs=plt.subplots(1,3,figsize=(15,4.3),layout='constrained')
    for cond,col in [('neutral','#287fa3'),('wrong','#be514a')]:
        patients=[]
        for c in cases:
            if not c['mechanism_capture']:continue
            raw=[obs(c,cond,mode='code',rot=rot) for rot in [0,2]]
            a=np.mean([np.asarray(r['layer_code_support']) for r in raw],axis=0)
            mass=np.mean([np.asarray(r['layer_code_candidate_mass']) for r in raw],axis=0)
            patients.append((a[:,c['gold_index']],(a.argmax(1)==c['gold_index']).astype(float),mass))
        for j in [0,1,2]:
            v=np.asarray([a[j] for a in patients]);ss=[stat(v[:,l]) for l in range(28)];axs[j].plot(range(1,29),[s['mean'] for s in ss],label='中性历史' if cond=='neutral' else '错误历史',c=col);axs[j].fill_between(range(1,29),[s['low'] for s in ss],[s['high'] for s in ss],alpha=.15,color=col)
    for ax in axs:ax.set(xlabel='层',ylim=(0,1));ax.legend()
    axs[0].set(title='来源诊断的相对投影支持',ylabel='候选内支持');axs[1].set(title='投影首选与来源答案一致比例',ylabel='比例');axs[2].set(title='四个代码在全词表中的总概率',ylabel='概率总量',yscale='log',ylim=(1e-8,1));fig.suptitle('逐层代码投影：未训练的输出头，两种映射平均；不是临床后验概率')
    savefig(fig,DEST/'figures/layer_code_readout')
    with (DEST/'RESULTS.md').open('w') as f:
        f.write('# 多来源医学信念：540例之外，更重要的是区分作用环节\n\n')
        f.write(f'本阶段完成{len(cases)}个新增病例、{summary["observations"]}个观测条件；内部完整轨迹子集{summary["mechanism_patients"]}例。全部使用本地Qwen3-1.7B，API费用0美元。这里使用考试病例的逐句揭示，不是真实就诊时间线。\n\n')
        f.write('## 相同当前事实，先前判断带来多大影响\n\n| 来源 | 病例数 | 无历史命中 | 中性历史命中 | 错误历史命中 | 仅提及错误病命中 | 错误−中性，95%CI |\n|---|---:|---:|---:|---:|---:|---|\n')
        for ds in SOURCES:
            tt=tables[ds+':all'];n=tt['accuracy_none']['n'];nums=[round(tt['accuracy_'+c]['mean']*n) for c in ['none','neutral','wrong','mention']];f.write(f'| {ds} | {n} | '+ ' | '.join(map(str,nums))+' | '+fmt(tt['wrong_minus_neutral_accuracy'],True)+' |\n')
        f.write('\n![历史条件](figures/history_by_source.png)\n\n正确历史含来源答案，只作为强对照。四选项分数、自由生成和来源标签的定义分别保留；不把考试成绩当临床诊断能力。\n\n')
        f.write('## 同一条新事实的作用有没有变化\n\n分差为来源病减去预先固定的错误病。下表比较加入最后一个原文证据组前后，错误历史与中性历史下增量的差。\n\n| 来源 | 平均交互及95%CI | 交互绝对值均值 | 增量方向相反且两侧绝对值>0.1 | 更新Spearman相关 |\n|---|---|---:|---:|---:|\n')
        for ds in SOURCES:
            t=tables[ds+':all'];f.write(f'| {ds} | {fmt(t["interaction_wrong_neutral"])} | {t["interaction_abs"]["mean"]:.3f} | {round(t["opposite_update_point1"]["mean"]*t["opposite_update_point1"]["n"])}/{t["opposite_update_point1"]["n"]} | {t["update_spearman"]:.3f} |\n')
        f.write('\n![证据增量](figures/evidence_update_pairs.png)\n\n方向不同仅表示更新依赖历史，不能单凭最终来源答案把中间变化判为医学错误。signed均值与绝对变化分别报告，避免相反效应互相抵消。\n\n## 内部记录\n\n![内部状态](figures/internal_history_change.png)\n\n全部540例均有28层的加入前后诊断位置记录，以及最终新/旧事实位置的FP32均值。状态变化反映历史内容进入计算；它本身不说明模型朝哪个疾病移动。\n\n![全部病例内部更新](figures/all_patient_update_geometry.png)\n\n![逐层代码投影](figures/layer_code_readout.png)\n\n代码投影不使用旧DDxPlus24病探针；每个病例在自身四个选项内比较，两种映射平均。未训练输出头在中间层没有校准，所以该图是输出倾向的辅助读表，机制判断仍需要位置干预。\n\n')
        f.write('## 复核与可追踪材料\n\n开发与确认集结果分别保存在[summary.json](summary.json)。[逐病例指标](patient_results.csv)、[逐句轨迹](trajectories.csv)、[代码对照](code_controls.csv)、[全部候选分数](all_candidate_scores.csv.gz)与[内部变化](internal_history_change.csv)均保留。常数历史偏置预测与“不更新”基线是描述性补充，不据此宣称发现认知机制。\n\n内部干预单独交付，不能将观测阶段的完成状态当作因果实验完成。\n')
    print(json.dumps(dict(patients=len(cases),tables=len(tables),output=str(DEST)),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
