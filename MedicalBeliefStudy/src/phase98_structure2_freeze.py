"""Freeze all confirmation methods and the primary selection using development only."""
import numpy as np
from phase90_structure2_prepare import *
def main():
    assert read(RUN/'adapter_development/completion.json')['complete'];cs=[c for c in cases() if c['cohort']=='development'];rows=[]
    for folder,cfgs in [('structure_development',read(RUN/'structural_candidates.json')),('adapter_development',read(RUN/'added_candidates.json'))]:
        for cfg in cfgs:
            zz=[read(RUN/folder/cfg['name']/(c['case_id']+'.json')) for c in cs];rr=[r for z in zz for r in z['conditions']];rates={co:float(np.mean([r['correct'] for r in rr if r['condition']==co])) for co in ['neutral','wrong']};listed={co:float(np.mean([r['listed'] for r in rr if r['condition']==co])) for co in ['neutral','wrong']}
            rows.append(dict(configuration=cfg,folder=folder,accuracy=rates,listed=listed,mean_accuracy=float(np.mean(list(rates.values()))),parameter_stats=zz[0]['parameter_stats']))
    lookup={r['configuration']['name']:r for r in rows};prune=read(RUN/'pruning_selection.json')['selected']['name'];fixed=['baseline',prune,'full_adapter16','pruned_adapter16','exit20_adapter16','exit20_bridge64']
    remaining=sorted([r for r in rows if r['configuration']['name'] not in fixed],key=lambda r:(-r['mean_accuracy'],r['parameter_stats']['parameters'],r['configuration']['name']));fixed.append(remaining[0]['configuration']['name'])
    cfgs=[lookup[n]['configuration'] for n in fixed];primary=min([lookup[n] for n in fixed],key=lambda r:(-r['mean_accuracy'],r['parameter_stats']['parameters'],r['configuration']['name']))['configuration']['name'];base_parameters=lookup['baseline']['parameter_stats']['parameters'];compression=min([lookup[n] for n in fixed if 1-lookup[n]['parameter_stats']['parameters']/base_parameters>=.08],key=lambda r:(-r['mean_accuracy'],r['parameter_stats']['parameters'],r['configuration']['name']))['configuration']['name'];trajectory=[]
    for ds in ['MedQA','MedMCQA']:trajectory += sorted([c['case_id'] for c in cases() if c['cohort']=='confirmation' and c['dataset']==ds],key=lambda c:rank(c+':trajectory'))[:12]
    trajnames=list(dict.fromkeys(['baseline','pruned_adapter16',primary]));
    if len(trajnames)<3:trajnames.append('full_adapter16')
    result=dict(status='frozen_before_any_confirmation_inference',configurations=cfgs,primary_candidate=primary,compression_candidate=compression,development_cases=80,confirmation_cases=400,conditions=['neutral','wrong'],input_control=dict(name='baseline_no_history',condition='none'),trajectory_cases=trajectory,trajectory_configurations=[lookup[n]['configuration'] for n in trajnames],development_rows=rows,cases_sha256=sha(DATA/'cases.private.jsonl'),core_sha256=sha(ROOT/'src/structure2_core.py'),decoder_sha256=sha(ROOT/'src/structure2_decode.py'),ranking_sha256=sha(RUN/'calibration/ranking.json'),source_sha256=sha(Path(__file__)),primary_analysis='Per-case mean of neutral/wrong actual-name correctness; six paired comparisons to baseline, Holm adjustment. Three separate paired contrasts (full adapter vs baseline, pruned adapter vs pruned, pruned adapter vs full adapter) form a second Holm family. Per-history/source secondary estimates. Input-only correction and oracle recoverability reported separately.',api_cost_usd=0)
    assert not (RUN/'confirmation_selection.json').exists();write(RUN/'confirmation_selection.json',result);print(json.dumps(dict(primary=primary,configurations=fixed,trajectory_cases=len(trajectory)),ensure_ascii=False))
if __name__=='__main__':main()
