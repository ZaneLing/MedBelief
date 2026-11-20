"""Algebraic gain/numerator decomposition of final-MLP code-margin changes."""
import json,csv
import numpy as np
from phase41_multisource_analyze import ROOT,DATA,RUN,read,write,csvwrite,stat,fmt
DEST=ROOT/'results/40_final_mlp'
def main():
 cs=[c for c in map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines()) if c['mechanism_capture']];keep={r['case_id'] for r in read(DATA/'text_audit.json')['rows'] if r['strict_keep']};rows=[];eps=read(ROOT.parent/'MedicalBeliefMechanisms/.models/Qwen3-1.7B/config.json').get('rms_norm_eps',1e-6)
 for c in cs:
  z=read(ROOT/'runs/belief_v4_module_readout'/(c['case_id']+'.json'));g,w=c['gold_index'],c['wrong_index'];vv={}
  for cond in ['neutral','wrong']:
   dd=[]
   for rot in [0,2]:
    ob=read(RUN/'observations'/f'{c["case_id"]}_{cond}_code_r{rot}_base_t{len(c["sentences"]):02d}.json')
    with np.load(RUN/ob['state_file']) as a:h=a['residual_stages'][-1,[2,4]].astype(np.float64)
    r=1/np.sqrt(np.mean(h*h,axis=1)+eps);s=np.array(next(x for x in z['conditions'] if x['condition']==cond and x['rotation']==rot)['stage_code_logits'])[-1,[1,2]];m=s[:,g]-s[:,w];u=m/r
    numerator=(u[1]-u[0])*(r[0]+r[1])/2;gain=(r[1]-r[0])*(u[0]+u[1])/2;assert abs(numerator+gain-(m[1]-m[0]))<1e-8
    dd.append(dict(norm_gain=r[1]/r[0],margin_change=m[1]-m[0],numerator_component=numerator,norm_gain_component=gain))
   vv[cond]={k:float(np.mean([d[k] for d in dd])) for k in dd[0]}
  row=dict(case_id=c['case_id'],dataset=c['dataset'],cohort=c['cohort'],strict_keep=c['case_id'] in keep)
  for cond,d in vv.items():
   for k,v in d.items():row[cond+'_'+k]=v
  for k in ['margin_change','numerator_component','norm_gain_component']:row['history_'+k]=vv['wrong'][k]-vv['neutral'][k]
  rows.append(row)
 csvwrite(DEST/'normalization_decomposition.csv',rows);ss=[]
 for cohort in ['all','development','confirmation']:
  rr=[r for r in rows if r['strict_keep'] and (cohort=='all' or r['cohort']==cohort)];ss.append(dict(cohort=cohort,n=len(rr),metrics={k:stat([r[k] for r in rr]) for k in rows[0] if k not in ['case_id','dataset','cohort','strict_keep']}))
 write(DEST/'normalization_summary.json',dict(type='Post-hoc algebraic decomposition; not causal mediation',epsilon=eps,summaries=ss))
 with (DEST/'NORMALIZATION.md').open('w') as f:
  f.write('# 为什么读表上的大变化不等于一个有效的偏向开关\n\n输出头先对状态做RMS归一化，再映射到词元。最后MLP前后，代码分差改变可能来自投影方向的改变，也可能来自整体尺度变化。我们对同一读表做代数分解：m=r×u，r为RMS归一化系数，u为去除该系数后的代码分差。将Δm对称分为Δu×平均r与Δr×平均u，两项之和严格等于观测变化。\n\n| 严格文本队列 | n | 中性归一化增益 | 错误归一化增益 | 历史分差变化 | 分子项 | 归一化尺度项 |\n|---|---:|---|---|---|---|---|\n')
  for r in ss:
   m=r['metrics'];f.write(f'| {r["cohort"]} | {r["n"]} | '+' | '.join(fmt(m[k]) for k in ['neutral_norm_gain','wrong_norm_gain','history_margin_change','history_numerator_component','history_norm_gain_component'])+' |\n')
  f.write('\n这里是输出头读表的代数描述，不能把某项比值当成因果中介比例。该分解在查看末层干预结果后追加。对应的[直接状态替换](RESULTS.md)提供另一项检验；两者一起用于避免把读表放大误认成新疾病信念突然形成。\n')
 print(json.dumps(ss[-1],ensure_ascii=False))
if __name__=='__main__':main()
