"""Paired factorial pathway analysis on the frozen confirmation patients."""
import json
import numpy as np
import matplotlib.pyplot as plt
from phase41_multisource_analyze import ROOT,DATA,read,write,csvwrite,stat,fmt,holm,SOURCES
from analyze_stages import setup,savefig

DEST=ROOT/'results/36_history_routes'
ROUTES=['full','block_to_facts','block_to_decision','block_both']
LABELS=['原模型','阻断历史→事实','阻断历史→诊断段','两条都阻断']

def main():
    setup();(DEST/'figures').mkdir(parents=True,exist_ok=True)
    cases={c['case_id']:c for c in map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines()) if c['mechanism_capture'] and c['cohort']=='confirmation'}
    rows=[];effects=[];contrasts=[];checks=[]
    for model in ['1.7b','4b']:
        src=ROOT/'runs'/('belief_v4_routes_'+model);assert read(src/'completion.json')['complete']
        for cid,c in cases.items():
            z=read(src/(cid+'.json'));g,w=c['gold_index'],c['wrong_index'];lookup={}
            for route in ROUTES:
                for cond in ['neutral','wrong','mention']:
                    rr=[r for r in z['conditions'] if r['route']==route and r['condition']==cond];assert len(rr)==2
                    row=dict(case_id=cid,dataset=c['dataset'],cohort=c['cohort'],model=model,route=route,condition=cond,
                             accuracy=float(np.mean([np.argmax(r['q'])==g for r in rr])),margin=float(np.mean([r['log_probability'][g]-r['log_probability'][w] for r in rr])),
                             source_support=float(np.mean([r['q'][g] for r in rr])),wrong_support=float(np.mean([r['q'][w] for r in rr])),
                             code_mass=float(np.mean([r['candidate_mass'] for r in rr])),first_token_code_rate=float(np.mean([r['unrestricted_first_is_code'] for r in rr])),mapping_agreement=int(np.argmax(rr[0]['q'])==np.argmax(rr[1]['q'])))
                    rows.append(row);lookup[route,cond]=row
                    checks.extend(r['native_check'] for r in rr if r['native_check'])
                for cond in ['wrong','mention']:
                    e=dict(case_id=cid,dataset=c['dataset'],model=model,route=route,history=cond)
                    for field in ['accuracy','margin','source_support','wrong_support']:e[field+'_effect']=lookup[route,cond][field]-lookup[route,'neutral'][field]
                    effects.append(e)
            for cond in ['wrong','mention']:
                ee={r['route']:r for r in effects if r['case_id']==cid and r['model']==model and r['history']==cond}
                for route in ROUTES[1:]:
                    contrasts.append(dict(case_id=cid,dataset=c['dataset'],model=model,history=cond,contrast=route+'_minus_full',value=ee[route]['margin_effect']-ee['full']['margin_effect'],accuracy_effect_change=ee[route]['accuracy_effect']-ee['full']['accuracy_effect']))
                contrasts.append(dict(case_id=cid,dataset=c['dataset'],model=model,history=cond,contrast='factorial_interaction',value=ee['full']['margin_effect']-ee['block_to_facts']['margin_effect']-ee['block_to_decision']['margin_effect']+ee['block_both']['margin_effect'],accuracy_effect_change=None))
    csvwrite(DEST/'patient_conditions.csv',rows);csvwrite(DEST/'patient_history_effects.csv',effects);csvwrite(DEST/'patient_path_contrasts.csv',contrasts)
    summaries=[];es=[];cs=[]
    for model in ['1.7b','4b']:
        for ds in SOURCES+['all']:
            def take(rr):return [r for r in rr if r['model']==model and (ds=='all' or r['dataset']==ds)]
            for route in ROUTES:
                for cond in ['neutral','wrong','mention']:
                    rr=[r for r in take(rows) if r['route']==route and r['condition']==cond]
                    summaries.append(dict(model=model,dataset=ds,route=route,condition=cond,**{k:stat([r[k] for r in rr]) for k in ['accuracy','margin','source_support','code_mass','first_token_code_rate','mapping_agreement']}))
                for cond in ['wrong','mention']:
                    rr=[r for r in take(effects) if r['route']==route and r['history']==cond]
                    es.append(dict(model=model,dataset=ds,route=route,history=cond,**{k:stat([r[k] for r in rr]) for k in ['accuracy_effect','margin_effect','source_support_effect','wrong_support_effect']}))
            for cond in ['wrong','mention']:
                group=[]
                for contrast in [r+'_minus_full' for r in ROUTES[1:]]+['factorial_interaction']:
                    rr=[r for r in take(contrasts) if r['history']==cond and r['contrast']==contrast]
                    group.append(dict(model=model,dataset=ds,history=cond,contrast=contrast,**stat([r['value'] for r in rr],pvalue=True)))
                holm(group);cs.extend(group)
    assert checks and all(r['allclose'] and r['same_argmax'] for r in checks)
    write(DEST/'summary.json',dict(patients=48,models=['Qwen3-1.7B FP16','Qwen3-4B 8bit'],conditions=2304,cohort='confirmation',condition_metrics=summaries,history_effects=es,paired_path_contrasts=cs,native_forward_checks=len(checks),all_native_checks_passed=True,api_cost_usd=0))
    fig,axs=plt.subplots(2,2,figsize=(12,9),layout='constrained')
    for i,model in enumerate(['1.7b','4b']):
        for j,hist in enumerate(['wrong','mention']):
            ax=axs[i,j];rr=[next(r for r in es if r['model']==model and r['dataset']=='all' and r['route']==route and r['history']==hist)['margin_effect'] for route in ROUTES];m=np.array([r['mean'] for r in rr]);lo=np.array([r['low'] for r in rr]);hi=np.array([r['high'] for r in rr]);ax.bar(range(4),m,color=['#b7564f','#508eaf','#78a895','#b5b8bc']);ax.errorbar(range(4),m,yerr=np.array([m-lo,hi-m]),fmt='none',c='black',capsize=3);ax.axhline(0,c='gray',lw=.8);ax.set(xticks=range(4),xticklabels=LABELS,ylabel='相对中性历史的诊断分差变化',title=('1.7B FP16' if model=='1.7b' else '4B 8bit')+' · '+('错误旧诊断' if hist=='wrong' else '仅提及未采纳病名'));ax.tick_params(axis='x',rotation=18)
    fig.suptitle('阻断哪条通路，历史病名的影响才会消失？\n负值：来源答案相对错误病名的支持下降；确认48例、两种代码映射')
    savefig(fig,DEST/'figures/history_paths')
    fig,axs=plt.subplots(1,2,figsize=(12,4.7),layout='constrained')
    for ax,model in zip(axs,['1.7b','4b']):
        for cond,color,label in [('neutral','#3686a2','中性历史'),('wrong','#b7564f','错误旧诊断'),('mention','#c39c39','仅提及')]:
            rr=[next(r for r in summaries if r['model']==model and r['dataset']=='all' and r['route']==route and r['condition']==cond)['accuracy'] for route in ROUTES];ax.plot(range(4),[r['mean'] for r in rr],'-o',label=label,color=color)
        ax.set(xticks=range(4),xticklabels=LABELS,ylim=(0,1),ylabel='来源答案命中率',title=model);ax.tick_params(axis='x',rotation=18);ax.legend()
    savefig(fig,DEST/'figures/pathway_accuracy_controls')
    with (DEST/'RESULTS.md').open('w') as f:
        f.write('# 旧病名怎样影响最终诊断：两条路径的拆解\n\n固定48例确认病例，每来源16例。两个模型配置，各1152个条件，总2304个。每个病例、每种历史和遮挡都使用两种预定代码映射；先在患者内平均，再计算患者级95%区间。测量第一个答案代码词元。\n\n')
        f.write('历史可以先进入患者事实的内部计算，也可以被后面的诊断任务和输出位置直接读取。我们在所有层分别阻断这两类注意力连接。\n\n![路径作用](figures/history_paths.png)\n\n## 每种通路设置下，历史仍有多少影响\n\n| 模型 | 历史 | 设置 | 来源病−错误病的历史影响，95%CI | 准确率历史影响 |\n|---|---|---|---|---|\n')
        for r in es:
            if r['dataset']=='all':f.write(f'| {r["model"]} | {r["history"]} | {LABELS[ROUTES.index(r["route"])]} | {fmt(r["margin_effect"])} | {fmt(r["accuracy_effect"],True)} |\n')
        f.write('\n## 阻断是否破坏了正常作答\n\n![正常作答检查](figures/pathway_accuracy_controls.png)\n\n| 模型 | 设置 | 中性历史命中 | 四代码概率总量 | 全词表首选属于代码的比例 |\n|---|---|---|---|---|\n')
        for r in summaries:
            if r['dataset']=='all' and r['condition']=='neutral':f.write(f'| {r["model"]} | {LABELS[ROUTES.index(r["route"])]} | {fmt(r["accuracy"],True)} | {fmt(r["code_mass"])} | {fmt(r["first_token_code_rate"],True)} |\n')
        f.write('\n## 配对通路比较\n\n正值表示该阻断削弱了历史带来的负向分差。四项比较在每个模型×历史内做Holm校正；交互项单独解释为非加性，不是消除效应。\n\n| 模型 | 历史 | 比较 | 分差，95%CI | 校正p |\n|---|---|---|---|---:|\n')
        for r in cs:
            if r['dataset']=='all':f.write(f'| {r["model"]} | {r["history"]} | {r["contrast"]} | {fmt(r)} | {r["p_holm"]:.5f} |\n')
        f.write('\n## 测量边界\n\n两条都阻断时仍可能有历史长度导致的位置距离差。历史经事实路径传播，说明其影响经过患者事实的计算表示；这一步还没有证明某一症状的医学含义被曲解。干预不是线性中介分解，不计算“多少百分比来自某路径”。1.7B与4B还同时不同精度，因此跨配置差异不单归于模型大小。\n\n[患者条件](patient_conditions.csv) · [患者历史效应](patient_history_effects.csv) · [配对通路比较](patient_path_contrasts.csv) · [完整汇总](summary.json) · [预先记录的路径设计](../../research_v4/ROUTE_PROTOCOL.md)\n')
    print(json.dumps(dict(output=str(DEST),patients=48,conditions=2304)))

if __name__=='__main__':main()
