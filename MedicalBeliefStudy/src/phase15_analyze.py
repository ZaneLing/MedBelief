"""Paired causal tests with lexical specificity and full sequence decomposition."""
import collections,json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from analyze_stages import ROOT,setup,savefig,ci,fmt,csvwrite,dump

def permutation_p(x):
    x=np.asarray(x);rng=np.random.default_rng(20261118);v=(rng.choice([-1.,1.],size=(20000,len(x)))*x).mean(1)
    return float((1+np.sum(abs(v)>=abs(x.mean())-1e-12))/20001)
def holm(ps):
    ps=np.array(ps);order=np.argsort(ps);out=np.zeros(len(ps));current=0
    for i,j in enumerate(order):current=max(current,min(1.,(len(ps)-i)*ps[j]));out[j]=current
    return out
def main():
    setup();run=ROOT/'runs/belief_v2/disease_interventions';assert (run/'completion.json').exists();dest=ROOT/'results/15_disease_directions';(dest/'figures').mkdir(parents=True,exist_ok=True)
    rows=[];shams=[];pairs=[];cases=[]
    for p in sorted(run.glob('ddx*.json')):
        r=json.loads(p.read_text());cases.append(r);shams.append(dict(case_id=r['case_id'],view=r['view'],sham_js=r['sham_js'],stable=r['numerically_stable']))
        b=r['baseline'];bl=np.array(b['log_probability']);bq=np.array(b['q_sequence']);bi=np.array([v[0] for v in b['token_log_probability']]);bt=bl-bi;g=r['gold_index49'];co=r['competitor_index49'];tokens=np.array(r['first_token_ids']);same=np.flatnonzero((tokens==tokens[g])&(np.arange(49)!=g));samepair=[(i,j) for i in range(49) for j in range(i) if tokens[i]==tokens[j]]
        nameindices=r['name_token_indices'];bn=np.array([sum(v[j] for j in indices) for v,indices in zip(b['token_log_probability'],nameindices)])
        top49=max((j for j in range(49) if j!=g),key=lambda j:bq[j])
        for c in r['conditions']:
            l=np.array(c['log_probability']);q=np.array(c['q_sequence']);first=np.array([v[0] for v in c['token_log_probability']]);tail=l-first;delta=l-bl;df=first-bi;dt=tail-bt
            dn=np.array([sum(v[j] for j in indices) for v,indices in zip(c['token_log_probability'],nameindices)])-bn
            rows.append(dict(case_id=r['case_id'],view=r['view'],layer=c['layer'],site=c['site'],condition=c['condition'],stable=r['numerically_stable'],gold=r['gold'],competitor=r['competitor'],
                logodds_gain=float(delta[g]-delta[co]),full49_competitor_index=top49,full49_logodds_gain=float(delta[g]-delta[top49]),gold_support_gain=float(q[g]-bq[g]),gold_support=float(q[g]),correct=bool(q.argmax()==g),baseline_correct=bool(bq.argmax()==g),baseline_top_index=int(bq.argmax()),intervened_top_index=int(q.argmax()),
                gold_logp_gain=float(delta[g]),first_logodds_gain=float(df[g]-df[co]),tail_logodds_gain=float(dt[g]-dt[co]),
                name_only_logodds_gain=float(dn[g]-dn[co]),format_logodds_gain=float((delta[g]-delta[co])-(dn[g]-dn[co])),
                same_first_competitors=len(same),same_first_selectivity=float(delta[g]-delta[same].mean()) if len(same) else None,
                max_same_first_pair_change=float(max(abs(delta[i]-delta[j]) for i,j in samepair)),mean_abs_tail=float(np.mean(abs(dt-dt.mean()))),
                relative_state_change=c['actual_relative_change'],external_margin_gain=c['external_readout_margin_change']))
    stable=[r for r in rows if r['stable']];groups=collections.defaultdict(dict)
    for r in stable:groups[(r['case_id'],r['view'],r['layer'],r['site'])][r['condition']]=r
    for key,r in groups.items():
        a=r['toward'];b=r['random'];n=r['away'];small=r.get('toward_small')
        pairs.append(dict(case_id=key[0],view=key[1],layer=key[2],site=key[3],target_minus_random_logodds=a['logodds_gain']-b['logodds_gain'],
            target_minus_random_support=a['gold_support_gain']-b['gold_support_gain'],target_minus_away_logodds=a['logodds_gain']-n['logodds_gain'],
            target_minus_random_name_only=a['name_only_logodds_gain']-b['name_only_logodds_gain'],target_minus_random_format=a['format_logodds_gain']-b['format_logodds_gain'],
            target_minus_random_same_first=(a['same_first_selectivity']-b['same_first_selectivity']) if a['same_first_selectivity'] is not None else None,
            toward_logodds=a['logodds_gain'],away_logodds=n['logodds_gain'],random_logodds=b['logodds_gain'],toward_small_logodds=small['logodds_gain'] if small else None,
            correct_gain=float(a['correct'])-float(a['baseline_correct']),target_minus_random_correct=float(a['correct'])-float(b['correct']),target_minus_random_full49_logodds=a['full49_logodds_gain']-b['full49_logodds_gain'],toward_external_margin=a['external_margin_gain'],
            sign_reversal=bool(a['logodds_gain']>0 and n['logodds_gain']<0)))
    contrasts=[]
    for view in ['append','panel']:
        for site in ['anchor','all_answer_positions']:
            for l in [21,28]:
                a=[r for r in pairs if r['view']==view and r['site']==site and r['layer']==l]
                vals=[r['target_minus_random_logodds'] for r in a]
                contrasts.append(dict(view=view,site=site,layer=l,cases=len(a),
                    **{k:ci([r[k] for r in a if r[k] is not None]) for k in ['target_minus_random_logodds','target_minus_random_support','target_minus_away_logodds','target_minus_random_same_first','target_minus_random_name_only','target_minus_random_format','toward_logodds','away_logodds','random_logodds','toward_small_logodds','correct_gain','target_minus_random_correct','target_minus_random_full49_logodds','toward_external_margin','sign_reversal']},p_two_sided=permutation_p(vals)))
    for r,p in zip(contrasts,holm([r['p_two_sided'] for r in contrasts])):r['p_holm_8']=float(p)
    summary={'cases':24,'prefixes':48,'active_conditions':len(rows),'shams':len(shams),'stable_prefixes':sum(r['stable'] for r in shams),'excluded_prefixes':[r for r in shams if not r['stable']],
        'contrasts':contrasts,'interpretation':'Independent-old-patient trained disease directions, source label as intervention target; not a deployable diagnosis method. Eight primary paired target-minus-random logodds contrasts Holm corrected.','api_cost_usd':0}
    dump(dest/'summary.json',summary);csvwrite(dest/'conditions.csv',rows);csvwrite(dest/'paired_cases.csv',pairs);csvwrite(dest/'shams.csv',shams)
    fig,axs=plt.subplots(1,2,figsize=(11,5),sharey=True)
    for ax,view in zip(axs,['append','panel']):
        for site,off,label in [('anchor',-.15,'只改回答前位置'),('all_answer_positions',.15,'同时改病名续写位置')]:
            rr=[r for r in contrasts if r['view']==view and r['site']==site];v=[r['target_minus_random_logodds'] for r in rr]
            ax.errorbar(np.array([21,28])+off,[x['mean'] for x in v],yerr=[[x['mean']-x['low'] for x in v],[x['high']-x['mean'] for x in v]],marker='o',capsize=4,label=label)
        ax.axhline(0,color='gray',lw=1);ax.set(title={'append':'逐条追加','panel':'固定问卷'}[view],xlabel='干预层',xticks=[21,28]);ax.legend(fontsize=8)
    axs[0].set_ylabel('目标方向减随机方向：疾病对数比变化');fig.tight_layout();savefig(fig,dest/'figures/direction_effects')
    fig,axs=plt.subplots(1,2,figsize=(11,5),sharey=True)
    for ax,view in zip(axs,['append','panel']):
        for site,off,label in [('anchor',-.15,'只改回答前位置'),('all_answer_positions',.15,'同时改续写')]:
            rr=[r for r in contrasts if r['view']==view and r['site']==site];v=[r['target_minus_random_same_first'] for r in rr]
            valid=[i for i,x in enumerate(v) if x['mean'] is not None]
            ax.errorbar(np.array([21,28])[valid]+off,[v[i]['mean'] for i in valid],yerr=[[v[i]['mean']-v[i]['low'] for i in valid],[v[i]['high']-v[i]['mean'] for i in valid]],marker='o',capsize=4,label=label)
        ax.axhline(0,color='gray',lw=1);ax.set(title=view,xlabel='干预层',xticks=[21,28]);ax.legend(fontsize=8)
    axs[0].set_ylabel('对同首词元其他疾病的选择性增益');fig.tight_layout();savefig(fig,dest/'figures/lexical_specificity')
    table='\n'.join(f"| {r['view']} | {r['site']} | {r['layer']} | {fmt(r['target_minus_random_logodds'],False)} | {fmt(r['target_minus_random_same_first'],False)} | {r['p_holm_8']:.5f} |" for r in contrasts)
    (dest/'RESULTS.md').write_text(f'''# 阶段15：可读出的疾病方向，能否真正改变诊断？

## 方法

仅用旧120例终点学习24类疾病线性读出器，在新24例预定中间轮干预。比较逐条追加与固定问卷两条件、第21与28层、仅回答前位置与同时覆盖整个答案续写位置（含JSON闭合符及EOS预测）。目标为来源疾病，竞争者为未干预模型的最高非目标候选（24类内）。目标方向为两类权重之差；5%原状态范数为主剂量，2%为锚点敏感性。反向与同范数随机方向为对照。标签用于实验靶向，不作为可部署方法的输入。根据分词字符偏移，将病名词元与其余格式词元的贡献另行分解。

共{len(rows)}个有效记录中的干预条件（包含数值不稳定者的原始记录），48个零干预；通过零干预数值标准{summary['stable_prefixes']}/48个病例×呈现前缀。未通过者排除主要效应但保留在原始表。疾病相对支持采用完整序列评分。

## 结果

| 呈现 | 干预位置 | 层 | 目标方向减随机：目标/竞争病对数比增益 | 对同首词元疾病的选择性增益 | 主对比Holm p |
|---|---|---|---|---|---|
{table}

第一项检验目标方向是否比随机方向更能改变相应疾病的相对输出；第二项检验变化是否超出病名首词元共同变化。第二项只有目标病存在同首词元其他候选时才适用，分母在summary中独立报告。所有区间按病例重采样，8个主对比采用配对符号置换并Holm校正；其他指标为描述性。由于原生49病首选可能不在24类读出空间内，另补充目标病相对原生49病最强非目标的对数比，以及目标干预减随机干预的49病命中差；这些事后补充不替换预定主对比。

![疾病方向效应](figures/direction_effects.png)

![同首词元选择性](figures/lexical_specificity.png)

## 解释范围

沿读出器权重方向改变状态，会直接改变该读出器自身的分数，这不是独立证据。独立结果是原模型完整病名的输出如何变化。最后层锚点只影响首词元；续写全位置干预也可能直接改变词汇生成。只有方向效应、同首词元选择性和不同呈现条件共同支持时，才能将结论推进到跨词汇形式的疾病信息使用。

[逐条件结果](conditions.csv) · [逐病例配对](paired_cases.csv) · [零干预检查](shams.csv) · [精确汇总](summary.json)
''')
    print(json.dumps(summary,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
