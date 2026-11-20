"""Finish the finite v3 experiment, audit and paper build; visual QA follows."""
import json,os,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parents[1];P=R.parent/'MedicalBeliefMechanisms/.runtime/bin/python';log=R/'runs/belief_v3';env=dict(os.environ,OPENBLAS_NUM_THREADS='2',OMP_NUM_THREADS='2')
required=['25_history_and_evidence/summary.json','28_new_4b_replication/summary.json','24_natural_update_causality/replication/summary.json','29_external_internal_causality/summary.json','30_role_binding/summary.json','27_building_synthesis/score_export_manifest.json','27_building_synthesis/text_baselines.json']
while not all((R/'results'/p).exists() for p in required):time.sleep(20)
for script in ['verify_belief_v3.py','phase33_paper.py','phase34_manuscript.py']:
 with (log/(script+'.log')).open('a') as f:subprocess.run([str(P),str(R/'src'/script)],cwd=R.parent,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
with (log/'paper_compile.log').open('a') as f:subprocess.run([str(R/'.tools/tectonic'),'--keep-logs','main.tex'],cwd=R/'acl_paper/v06_building',env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
(log/'delivery_compile_complete.json').write_text(json.dumps({'experiment_verified':True,'reports_written':True,'paper_compiled':True,'visual_qa_pending':True})+'\n')
