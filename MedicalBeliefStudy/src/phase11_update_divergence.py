"""Post-hoc descriptive audit of opposite native/probe updates at fixed layers."""
import json,csv
import numpy as np
from analyze_stages import ROOT,winner,ci,csvwrite,dump,fmt
def main():
    dest=ROOT/'results/11_disease_information';run=ROOT/'runs/structured_names_v1';ds=json.loads((run/'manifest.json').read_text())['candidate_diseases'];cases=[json.loads(s) for s in (ROOT/'data/full49_v1/cases.private.jsonl').read_text().splitlines()]
    probes={(r['case_id'],int(r['round']),int(r['layer'])):r for r in csv.DictReader((dest/'heldout_trajectory_readouts.csv').open())};events=[];case_rows=[]
    for c in cases:
        if not c['deep_capture']:continue
        cid=c['case_id'];T=len(c['orders']['base']);y=ds.index(c['gold_disease']);q=np.array([json.loads((run/'observations'/f'{cid}_base_t{t:02d}_m0.json').read_text())['q_sequence'] for t in range(T+1)]);pred=winner(q)
        for l in [21,28]:
            rr=[]
            for t in range(1,T+1):
                a=probes[cid,t-1,l];b=probes[cid,t,l];delta=float(q[t,y]-q[t-1,y]);rankgain=int(a['gold_rank'])-int(b['gold_rank'])
                strict=bool(pred[t-1]==y and pred[t]>=0 and pred[t]!=y and a['predicted_disease']!=c['gold_disease'] and b['predicted_disease']==c['gold_disease'])
                e={'case_id':cid,'layer':l,'round':t,'gold':c['gold_disease'],'delta_native_gold_support':delta,'probe_gold_rank_improvement':rankgain,
                   'native_previous_top':ds[pred[t-1]] if pred[t-1]>=0 else 'TIED','native_current_top':ds[pred[t]] if pred[t]>=0 else 'TIED',
                   'probe_previous_top':a['predicted_disease'],'probe_current_top':b['predicted_disease'],'strict_correctness_crossover':strict,
                   'rank_improves_native_drops_5pp':bool(rankgain>0 and delta<=-.05)};events.append(e);rr.append(e)
            case_rows.append({'case_id':cid,'layer':l,'strict_crossover_any':any(r['strict_correctness_crossover'] for r in rr),
                              'opposite_rank_support_any':any(r['rank_improves_native_drops_5pp'] for r in rr)})
    summary={str(l):{'events':sum(r['layer']==l for r in events),'strict_crossover_events':sum(r['strict_correctness_crossover'] for r in events if r['layer']==l),
                    'opposite_rank_support_events':sum(r['rank_improves_native_drops_5pp'] for r in events if r['layer']==l),
                    'strict_case_rate':ci([r['strict_crossover_any'] for r in case_rows if r['layer']==l]),'opposite_case_rate':ci([r['opposite_rank_support_any'] for r in case_rows if r['layer']==l])} for l in [21,28]}
    csvwrite(dest/'opposite_update_events.csv',events);dump(dest/'opposite_update_summary.json',summary)
    table='\n'.join(f'| {l} | {summary[str(l)]["strict_crossover_events"]}/178 | {fmt(summary[str(l)]["strict_case_rate"])} | {summary[str(l)]["opposite_rank_support_events"]}/178 | {fmt(summary[str(l)]["opposite_case_rate"])} |' for l in [21,28])
    (dest/'OPPOSITE_UPDATES.md').write_text(f'''# 内部读出与实际诊断的相反更新

在完成主要分析并查看肺栓塞病例后，补充这一描述性统计；不是事先注册的机制确认。仍固定第21、28层，不搜索最佳层。

严格交叉事件：模型名称评分从命中最终标签转为未命中，同时外部读出从未命中转为命中。更宽的反向事件：最终标签在读出中的排名提升，但模型对该标签的完整病名支持下降至少5个百分点。模型行为使用原始49候选，读出有24类；这两个任务不同，不能将交叉直接解释为模型“知道却故意不说”。完整分数与排名变化均保留。

| 层 | 严格交叉事件 | 有交叉病例比例 [95%区间] | 排名提升但支持降≥5pp事件 | 有此事件病例比例 [95%区间] |
|---|---|---|---|---|
{table}

该统计量化可读信息和实际诊断变化不同步的频率；文本结构与外部读出学习的映射仍是需要控制的解释。

[所有逐轮记录](opposite_update_events.csv) · [汇总](opposite_update_summary.json)
''')
    print(json.dumps(summary,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
