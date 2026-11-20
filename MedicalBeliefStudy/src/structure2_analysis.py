"""CPU-only analysis helpers and labels."""
import csv,collections
import numpy as np
from phase90_structure2_prepare import *
from phase41_multisource_analyze import stat,fmt,holm,csvwrite
from scipy.stats import binomtest

def proportion(values):
    x=np.array(values,int);s=stat(x)
    if len(x) and (np.all(x==0) or np.all(x==1)):
        ci=binomtest(int(x.sum()),len(x)).proportion_ci();s.update(low=float(ci.low),high=float(ci.high),interval='exact_binomial_boundary')
    return s
LABELS={'baseline':'完整模型','exit24':'仅前24层','exit20':'仅前20层','drop_tail4_keep28':'删24—27层，保留28层','drop_mlp4':'删4个晚层MLP','mlp_width75':'全层MLP保留75%通道','mlp_width50':'全层MLP保留50%通道','late_mlp_width50':'后12层MLP保留50%通道','attention_groups75':'每层保留6/8组注意力头','linear_old16':'旧版两MLP线性替换','late_mlp_half':'晚层MLP贡献减半','contrast21_half':'21层对比解码，力度0.5','contrast21_full':'21层对比解码，力度1.0','full_diagonal':'完整模型+逐维适配器','full_adapter16':'完整模型+小适配器16','full_adapter64':'完整模型+小适配器64','pruned_adapter16':'所选压缩+小适配器16','exit20_adapter16':'前20层+小适配器16','exit20_bridge64':'前20层+教师状态桥接64','baseline_constrained':'完整模型+候选约束','exit20_constrained':'前20层+候选约束','pruned_constrained':'所选压缩+候选约束','baseline_no_history':'完整模型，去除历史'}
def records(folder,cfgs,cohort):
    rr=[];sizes={}
    for c in cases():
        if c['cohort']!=cohort:continue
        for cfg in cfgs:
            z=read(RUN/folder/cfg['name']/(c['case_id']+'.json'));sizes[cfg['name']]=z['parameter_stats']
            for r in z['conditions']:rr.append(dict(case_id=c['case_id'],dataset=c['dataset'],candidate=cfg['name'],condition=r['condition'],correct=int(r['correct']),listed=int(r['listed']),generated_disease=r['generated_disease'],tokens=r['tokens'],stop=r['stop']))
    return rr,sizes

def load_confirmation():
    spec=read(RUN/'confirmation_selection.json');rr,sizes=records('confirmation',spec['configurations'],'confirmation');base={(r['case_id'],r['condition']):r for r in rr if r['candidate']=='baseline'}
    for r in rr:
        b=base[r['case_id'],r['condition']];r.update(accuracy_change=r['correct']-b['correct'],fidelity=int(r['generated_disease'] is not None and r['generated_disease']==b['generated_disease']),repaired=int(r['correct'] and not b['correct']),damaged=int(b['correct'] and not r['correct']))
    return rr,sizes,spec
