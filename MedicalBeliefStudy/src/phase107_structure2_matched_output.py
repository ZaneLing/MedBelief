"""One post-primary matched output control; no further method selection."""
from structure2_compat import *
from phase100_structure2_timing import timed

def main():
    verify_amendment();amend=read(DOC/'MATCHED_OUTPUT_CONTROL.json');assert amend['source_sha256']==sha(ROOT/'src/phase107_structure2_matched_output.py');spec=read(RUN/'confirmation_selection.json');cfg=amend['control'];primary=next(c for c in spec['configurations'] if c['name']==spec['primary_candidate']);assert cfg in read(RUN/'added_candidates.json') and primary.get('constrained')
    run_config(cfg,'confirmation',folder='output_matched_control');dest=RUN/'output_matched_control';ids=read(RUN/'timing/manifest.json')['cases'];lookup={c['case_id']:c for c in cases()};base,tok=load_model();variant,_=load_model();variant=assemble(variant,primary);rr=[];e=encode(lookup[ids[0]],tok);timed(base,tok,e,True);timed(variant,tok,e,True)
    for i,cid in enumerate(ids):
        for co in ['neutral','wrong']:
            e=encode(lookup[cid],tok,co)
            for rep in range(2):
                if (i+rep)%2:b=timed(variant,tok,e,True);a=timed(base,tok,e,True)
                else:a=timed(base,tok,e,True);b=timed(variant,tok,e,True)
                rr.append(dict(case_id=cid,condition=co,repetition=rep,baseline=a,variant=b,ratios={k:b[k]/a[k] for k in ['prefill_seconds','fixed12_decode_seconds','actual_answer_seconds']}))
    write(dest/'timing.json',dict(reference=cfg,primary=primary,trials=rr,reference_parameter_stats=parameter_stats(base),primary_parameter_stats=parameter_stats(variant)));write(dest/'completion.json',dict(complete=True,cases=400,generations=800,timing_pairs=24,post_primary_explanatory_control=True,amendment_sha256=sha(DOC/'MATCHED_OUTPUT_CONTROL.json'),api_cost_usd=0));print(json.dumps(dict(complete=True,control=cfg['name'],cases=400)),flush=True)
if __name__=='__main__':main()
