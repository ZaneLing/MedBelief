"""Replay a frozen research case with a physically assembled structure."""
import argparse,json
from structural_v1_variants import *

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--case-id',required=True)
    ap.add_argument('--configuration',default='baseline')
    ap.add_argument('--condition',choices=['neutral','wrong'],default='neutral')
    ap.add_argument('--round',type=int)
    ap.add_argument('--rotation',type=int,choices=[0,2],default=0)
    args=ap.parse_args();lookup={c['case_id']:c for c in cases()}
    if args.case_id not in lookup:ap.error('case-id must belong to the strict frozen research cohort')
    c=lookup[args.case_id];T=args.round if args.round is not None else len(c['sentences'])
    if not 1<=T<=len(c['sentences']):ap.error('round outside evidence range')
    conf={v['name']:v for v in read(DEST/'selected.json')['candidates']}
    if args.configuration not in conf:ap.error('configuration must be one of: '+', '.join(conf))
    model,tok=load_model();model=materialize(model,conf[args.configuration]);e=encoded(c,tok,args.condition,args.rotation,T);o=score(model,e,True)
    print(json.dumps(dict(case_id=c['case_id'],dataset=c['dataset'],condition=args.condition,round=T,total_rounds=len(c['sentences']),configuration=conf[args.configuration],candidate_support=dict(zip(c['candidates'],o['q'])),selected_candidate=c['candidates'][int(np.argmax(o['q']))],source_final_answer=c['gold_disease'],candidate_mass=o['candidate_mass'],first_is_code=o['first_is_code'],parameter_stats=parameter_stats(model),api_cost_usd=0),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
