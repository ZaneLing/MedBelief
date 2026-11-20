"""Pick pruning using only full-name development outcomes, before adapter training."""
import numpy as np
from phase90_structure2_prepare import *
def main():
    assert read(RUN/'structure_development/completion.json')['complete'];cs=[c for c in cases() if c['cohort']=='development'];rows=[];configs=read(RUN/'structural_candidates.json')
    for cfg in configs:
        rr=[read(RUN/'structure_development'/cfg['name']/(c['case_id']+'.json')) for c in cs];params=rr[0]['parameter_stats']['parameters'];rates={co:float(np.mean([r['correct'] for z in rr for r in z['conditions'] if r['condition']==co])) for co in ['neutral','wrong']}
        rows.append(dict(configuration=cfg,parameters=params,accuracy=rates,mean_accuracy=np.mean(list(rates.values())).item()))
    base=next(r['parameters'] for r in rows if r['configuration']['name']=='baseline');compress=sorted([r for r in rows if 1-r['parameters']/base>=.08],key=lambda r:(-r['mean_accuracy'],r['parameters'],r['configuration']['name']))
    chosen=next(r for r in compress if r['configuration']['name']!='exit20');write(RUN/'pruning_selection.json',dict(rows=rows,selected=chosen['configuration'],parameter_reduction=1-chosen['parameters']/base,selection='Highest average actual name accuracy on neutral/wrong development, at least8% parameter saving; exit20 reserved for fixed aggressive adapter.',cases=80))
    adapters=[dict(name='full_diagonal',backbone=dict(name='baseline'),adapter_kind='diagonal',adapter_rank=0),dict(name='full_adapter16',backbone=dict(name='baseline'),adapter_kind='bottleneck',adapter_rank=16),dict(name='full_adapter64',backbone=dict(name='baseline'),adapter_kind='bottleneck',adapter_rank=64),dict(name='pruned_adapter16',backbone=chosen['configuration'],adapter_kind='bottleneck',adapter_rank=16),dict(name='exit20_adapter16',backbone=dict(name='exit20',exit_layer=20),adapter_kind='bottleneck',adapter_rank=16)]
    write(RUN/'adapter_plan.json',dict(adapters=adapters,steps=600,batch_size=32,learning_rate=.001,weight_decay=.01,seed=20261120,checkpoints=[0,100,300,600],selection='Lowest development full-vocabulary weighted token cross entropy; no test cases.',token_weighting='Each sequence weight1; first candidate token weight0.5, remaining tokens including JSON closure and EOS share0.5.',optimizer='AdamW, global gradient norm clipping1.0'))
    print(json.dumps(dict(selected=chosen,configurations=len(rows)),ensure_ascii=False))
if __name__=='__main__':main()
