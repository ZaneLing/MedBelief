"""Replay a selected configuration without training or using the source answer."""
import argparse
from pathlib import Path
import json,time
from structure2_compat import *

def main():
    verify_amendment()
    p=argparse.ArgumentParser();p.add_argument('--case-id');p.add_argument('--candidate',default='compression',help='primary, compression, baseline, or any frozen configuration name');p.add_argument('--condition',choices=['neutral','wrong','none'],default='neutral');p.add_argument('--round',type=int);p.add_argument('--output',type=Path);a=p.parse_args();spec=read(RUN/'confirmation_selection.json');name=spec[a.candidate+'_candidate'] if a.candidate in ['primary','compression'] else a.candidate;cfg=next(c for c in spec['configurations']+[read(DOC/'MATCHED_OUTPUT_CONTROL.json')['control']] if c['name']==name);cid=a.case_id or spec['trajectory_cases'][0];c=next(c for c in cases() if c['case_id']==cid)
    if a.round is not None:assert 1<=a.round<=len(c['sentences'])
    model,tok=load_model();model=assemble(model,cfg);e=encode(c,tok,a.condition,a.round);start=time.time();o=(constrained_generate if cfg.get('constrained') else generate)(model,tok,e);result=dict(case_id=cid,configuration=cfg,condition=a.condition,round=a.round or len(c['sentences']),parameter_stats=parameter_stats(model),seconds=time.time()-start,**o)
    if a.output:write(a.output,result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
