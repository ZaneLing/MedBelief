"""Describe support-interface and source-reference sensitivity, no extra inference."""
import numpy as np
from belief_v3_analysis import *
def main():
 dest=ROOT/'results/27_building_synthesis';dest.mkdir(parents=True,exist_ok=True);cs=rows(ROOT/'data/belief_v3/cases.private.jsonl');ds=rows(ROOT/'data/belief_v3/jobs.jsonl')[0]['candidate_diseases'];head=np.load(ROOT/'results/14_fixed_panel/training_heads.npz');cl=head['classes'].tolist();sub=[ds.index(d) for d in cl];output={};allrows=[]
 for model,runname,resultname in [('1.7b','belief_v3','23_new_patients'),('4b','belief_v3_4b','28_new_4b_replication')]:
  if not (ROOT/'runs'/runname/'completion.json').exists():continue
  pred=np.load(ROOT/'results'/resultname/'endpoint_predictions.npz');run=ROOT/'runs'/runname;output[model]={}
  for view in (['append','panel'] if model=='1.7b' else ['append']):
   records=[load_record(run,c,view=view) for c in cs];q=pred['q_'+view];p=pred['probe_'+view][:,-1];g=np.array([cl.index(c['gold_disease']) for c in cs]);native=q[:,sub].argmax(-1);topref=np.array([c['gold_disease']==max(c['reference_differential'],key=c['reference_differential'].get) for c in cs]);mass=np.array([r['sequence_probability_mass'] for r in records]);masks={'all':np.ones(240,bool),'canonical_mass_ge_0.1':mass>=.1,'canonical_mass_ge_0.5':mass>=.5,'greedy_is_listed':np.array([r['generated_disease'] in ds for r in records]),'pathology_is_reference_top1':topref};strata={}
   for name,mask in masks.items():strata[name]=dict(patients=int(mask.sum()),native24_correct=int(np.sum(native[mask]==g[mask])),probe_last_correct=int(np.sum(p[mask]==g[mask])),paired_probe_minus_native24=summary((p[mask]==g[mask]).astype(float)-(native[mask]==g[mask])))
   output[model][view]=dict(strata=strata,canonical_mass_min=float(mass.min()),canonical_mass_max=float(mass.max()),source_label_reference_top1=int(topref.sum()))
   for i,c in enumerate(cs):allrows.append(dict(model=model,view=view,case_id=c['case_id'],gold=c['gold_disease'],reference_top=max(c['reference_differential'],key=c['reference_differential'].get),native49=ds[q[i].argmax()],native24=cl[native[i]],probe_last=cl[p[i]],native49_in_reference=ds[q[i].argmax()] in c['reference_differential'],canonical_mass=mass[i],greedy=records[i]['generated_disease']))
 dump(dest/'measurement_audit.json',output);csvwrite(dest/'measurement_audit_cases.csv',allrows)
 tab='\n'.join(f'| {model} {view} | {name} | {v["patients"]} | {v["native24_correct"]} | {v["probe_last_correct"]} | {fmt(v["paired_probe_minus_native24"])} |' for model,mm in output.items() for view,vv in mm.items() for name,v in vv['strata'].items())
 (dest/'MEASUREMENT_AUDIT.md').write_text('# 测量接口和来源答案的敏感性分析\n\n全部队列是主结果。下面按规范病名字符串的总概率质量、实际生成是否在候选中，以及来源病是否也是来源鉴别诊断的第一名作描述性切片。它们检查差距是否只由低质量字符串评分或标签歧义产生；模型输出相关切片不是新的独立确认队列。\n\n| 配置/呈现 | 切片 | 病例 | 原模型24病命中数 | 末层读出命中数 | 配对差 |\n|---|---|---:|---:|---:|---|\n'+tab+'\n\n来源鉴别诊断是DDxPlus模拟器的参考集合，不是独立医生审核。原生分数和内部读出都衡量所定义任务，不把相对支持解释成校准临床概率。\n');print(json.dumps(clean(output),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
