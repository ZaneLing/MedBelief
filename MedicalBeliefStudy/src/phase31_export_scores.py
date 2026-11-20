"""Human/tool-readable long tables for every natural trajectory and disease."""
import csv,gzip
import numpy as np
from belief_v3_analysis import *
def main():
 cases=rows(ROOT/'data/belief_v3/cases.private.jsonl');ds=rows(ROOT/'data/belief_v3/jobs.jsonl')[0]['candidate_diseases'];manifest={}
 for model,runname,resultname in [('1.7b','belief_v3','23_new_patients'),('4b','belief_v3_4b','28_new_4b_replication')]:
  run=ROOT/'runs'/runname;dest=ROOT/'results'/resultname;pack=np.load(dest/'prefix_readout_scores.npz');cl=pack['classes'].tolist();selected=[c for c in cases if c['mechanism_capture' if model=='4b' else 'deep_capture']];native=0;internal=0
  with gzip.open(dest/'all_native_disease_scores.csv.gz','wt',newline='') as f,gzip.open(dest/'all_layer_disease_scores.csv.gz','wt',newline='') as g:
   a=csv.writer(f);b=csv.writer(g);a.writerow(['case_id','round','disease','log_sequence_probability','relative_support','token_mean_support','is_source_label']);b.writerow(['case_id','round','layer','disease','readout_score','rank','is_source_label'])
   for c in selected:
    s=pack[c['case_id']];ranks=1+(s[:,:,:,None]<s[:,:,None,:]).sum(-1)
    for t in range(len(c['orders']['base'])+1):
     r=load_record(run,c,t)
     for i,d in enumerate(ds):a.writerow([c['case_id'],t,d,r['log_probability'][i],r['q_sequence'][i],r['q_token_mean'][i],int(d==c['gold_disease'])]);native+=1
     for l in range(s.shape[1]):
      for i,d in enumerate(cl):b.writerow([c['case_id'],t,l+1,d,float(s[t,l,i]),int(ranks[t,l,i]),int(d==c['gold_disease'])]);internal+=1
  manifest[model]={'native_rows':native,'internal_rows':internal,'patients':len(selected)}
 dest=ROOT/'results/26_external_medqa';run=ROOT/'runs/belief_v3_medqa';native=0
 with gzip.open(dest/'all_native_disease_scores.csv.gz','wt',newline='') as f:
  a=csv.writer(f);a.writerow(['case_id','round','candidate','log_sequence_probability','relative_support','token_mean_support','is_source_answer'])
  for c in rows(ROOT/'data/external_medqa/cases.private.jsonl'):
   for t in range(1,len(c['evidence_sentences'])+1):
    r=read(run/'observations'/f"{c['case_id']}_base_t{t:02d}.json")
    for i,d in enumerate(c['candidate_diseases']):a.writerow([c['case_id'],t,d,r['log_probability'][i],r['q_sequence'][i],r['q_token_mean'][i],int(d==c['gold_disease'])]);native+=1
 manifest['external_medqa']={'native_rows':native,'patients':87};dump(ROOT/'results/27_building_synthesis/score_export_manifest.json',manifest);print(manifest)
if __name__=='__main__':main()
