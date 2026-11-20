"""Refresh case-table readability from existing scores; no model calls."""
import json
import numpy as np
from phase45_multisource_deep import DATA,DEST,codeobs,case_layer_table

def main():
    count=0
    for c in map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines()):
        if not c['mechanism_capture']:continue
        grids={};mapping={};mass={}
        for cond in ['neutral','wrong']:
            q=[];a=[];m=[]
            for t in range(1,len(c['sentences'])+1):
                rr=[codeobs(c,cond,t,r) for r in [0,2]]
                qq=[np.asarray(z['layer_code_support']) for z in rr]
                q.append(np.mean(qq,axis=0));a.append(qq[0].argmax(1)==qq[1].argmax(1));m.append(np.mean([z['layer_code_candidate_mass'] for z in rr],axis=0))
            grids[cond]=np.asarray(q);mapping[cond]=np.asarray(a);mass[cond]=np.asarray(m)
        p=DEST/'cases'/(c['case_id']+'.md');s=p.read_text()
        start=s.index('\n## 各层投影首选') if '\n## 各层投影首选' in s else s.index('\n## 关键层的投影读表')
        p.write_text(s[:start]+case_layer_table(c,grids,mapping,mass));count+=1
    assert count==94
    print(json.dumps(dict(case_tables_updated=count,model_calls=0)))
if __name__=='__main__':main()
