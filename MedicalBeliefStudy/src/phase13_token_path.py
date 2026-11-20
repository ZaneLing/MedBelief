"""Decompose existing causal disease-name changes into first-token and tail effects."""
import json,hashlib
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from analyze_stages import ROOT,setup,savefig,ci,fmt,csvwrite,dump
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    setup();run=ROOT/'runs/structured_names_v1';dest=ROOT/'results/13_token_path';(dest/'figures').mkdir(parents=True,exist_ok=True)
    cases={c['case_id']:c for c in map(json.loads,(ROOT/'data/full49_v1/cases.private.jsonl').read_text().splitlines())}
    diseases=json.loads((run/'manifest.json').read_text())['candidate_diseases'];rows=[];groups=[]
    for p in sorted((run/'interventions').glob('ddx*.json')):
        r=json.loads(p.read_text());cid=r['case_id'];t=r['round'];base=json.loads((run/'observations'/f'{cid}_base_t{t:02d}_m0.json').read_text())
        first=np.array([v[0] for v in base['token_log_probability']]);tail=np.array([sum(v[1:]) for v in base['token_log_probability']]);total=np.array(base['log_probability'])
        tokens=np.array([s[0] for s in base['suffix_ids']]);gold=diseases.index(cases[cid]['gold_disease'])
        other=[i for i in range(49) if i!=gold];comp=max(other,key=lambda i:total[i])
        for cond in r['conditions']:
            if cond['condition']!='previous_mlp':continue
            df=np.array([v[0] for v in cond['token_log_probability']])-first
            dt=np.array([sum(v[1:]) for v in cond['token_log_probability']])-tail
            da=np.array(cond['log_probability'])-total
            assert np.allclose(da,df+dt,atol=1e-9)
            # Relative disease scores eliminate common log-normalizer shifts.
            pairs=[(i,j) for i in range(49) for j in range(i) if tokens[i]==tokens[j]]
            within=max([abs(da[i]-da[j]) for i,j in pairs],default=0.)
            centered=lambda x:x-x.mean()
            rows.append(dict(case_id=cid,layer=cond['layer'],gold=diseases[gold],competitor=diseases[comp],
                mean_abs_first=float(np.mean(abs(centered(df)))),mean_abs_tail=float(np.mean(abs(centered(dt)))),
                max_abs_tail=float(abs(dt).max()),max_same_first_token_logodds_change=float(within),same_first_pairs=len(pairs),
                total_gold_competitor=float(da[gold]-da[comp]),first_gold_competitor=float(df[gold]-df[comp]),tail_gold_competitor=float(dt[gold]-dt[comp]),
                same_first_gold_competitor=bool(tokens[gold]==tokens[comp])))
        if not groups:
            for tok in sorted(set(tokens)):
                names=[diseases[i] for i in range(49) if tokens[i]==tok]
                if len(names)>1:groups.append({'first_token_id':int(tok),'diseases':names})
    summary={'cases':len({r['case_id'] for r in rows}),'analysis':'post-hoc decomposition of frozen phase10 previous-MLP interventions; no additional forward passes',
        'layers':{str(l):{k:ci([r[k] for r in rows if r['layer']==l]) for k in ['mean_abs_first','mean_abs_tail','max_abs_tail','max_same_first_token_logodds_change']} for l in [26,27,28]},
        'first_token_groups':groups,'source_sha256':sha(__file__)}
    csvwrite(dest/'case_decomposition.csv',rows);dump(dest/'summary.json',summary)
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for key,label in [('mean_abs_first','首个词元'),('mean_abs_tail','后续词元')]:
        v=[summary['layers'][str(l)][key] for l in [26,27,28]]
        axes[0].errorbar([26,27,28],[x['mean'] for x in v],yerr=[[x['mean']-x['low'] for x in v],[x['high']-x['mean'] for x in v]],marker='o',label=label)
    axes[0].set(xlabel='替换旧MLP的位置',ylabel='疾病间对数分数变化幅度',title='病名变化来自哪段输出？',xticks=[26,27,28]);axes[0].legend()
    v=[summary['layers'][str(l)]['max_same_first_token_logodds_change'] for l in [26,27,28]]
    axes[1].bar([26,27,28],[x['mean'] for x in v]);axes[1].set(xlabel='替换旧MLP的位置',ylabel='同首词元疾病之间最大对数比变化',title='能否区分具有相同开头的疾病？',xticks=[26,27,28])
    fig.tight_layout();savefig(fig,dest/'figures/token_path')
    table='\n'.join(f"| {l} | {fmt(summary['layers'][str(l)]['mean_abs_first'],False)} | {fmt(summary['layers'][str(l)]['mean_abs_tail'],False)} | {fmt(summary['layers'][str(l)]['max_same_first_token_logodds_change'],False)} |" for l in [26,27,28])
    (dest/'RESULTS.md').write_text(f'''# 阶段13：最后一层改变的是疾病，还是病名开头？

## 方法

对阶段10固定24例完整病名、旧MLP替换结果作事后分解，不重新选择病例。每个疾病的完整序列对数概率等于首个词元与后续词元对数概率之和。干预前后相减后，分别统计两部分在49个疾病之间的变化（先减疾病平均值，去掉共同归一化偏移）。另比较首词元相同疾病之间的相对分数，排除仅改变病名开头的效应。

## 结果

| 层 | 首词元变化幅度 | 后续词元变化幅度 | 同首词元疾病的最大相对变化 |
|---|---|---|---|
{table}

![输出路径分解](figures/token_path.png)

## 机制解释

在最后一层、回答前的最后一个位置替换MLP，只改变接下来第一个词元的分数。该层的KV缓存已经由替换前的输入生成；没有更晚的层可以将这一变化写入新的KV缓存。因此，在固定同一个候选病名的教师强制续写中，后续词元分数不因这次替换而改变。第26/27层则仍可经过后面的层影响缓存。

这项架构事实解释了为什么“最后一层干预能改变病名概率”本身不是选择性操纵疾病表征的证据。共享首词元的疾病可一起升降，但它们之间的相对支持不变。先前末层干预效果仍是真实计算效应，其解释应收窄为对诊断输出入口的作用。

下一阶段使用独立病例训练的疾病方向，同时比较第21/28层、仅锚点/续写过程，并单独检验同首词元疾病的区分。表中数字按病例bootstrap，未作为事先假设检验。

[逐病例分解](case_decomposition.csv) · [精确汇总](summary.json)
''')
    print(json.dumps(summary['layers'],ensure_ascii=False),flush=True)
if __name__=='__main__':main()
