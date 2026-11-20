"""Run CPU analyses as completed GPU stages become available."""
import json,os,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parents[1];P=R.parent/'MedicalBeliefMechanisms/.runtime/bin/python';LOG=R/'runs/belief_v3';env=dict(os.environ,OPENBLAS_NUM_THREADS='2',OMP_NUM_THREADS='2')
tasks=[('runs/belief_v3/completion.json','phase23_analyze.py',[]),('runs/belief_v3/natural_interventions/completion.json','phase24_analyze.py',[]),('runs/belief_v3_medqa/completion.json','phase25_analyze.py',[]),('runs/belief_v3_4b/completion.json','phase23_analyze.py',['--model','4b']),('runs/belief_v3/history_matched/completion.json','phase26_analyze.py',[])]
for marker,script,args in tasks:
 while not (R/marker).exists():time.sleep(20)
 with (LOG/(script+('_4b' if args else '')+'.log')).open('a') as f:
  subprocess.run([str(P),str(R/'src'/script),*args],cwd=R.parent,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
(LOG/'analysis_queue_complete.json').write_text(json.dumps({'complete':True,'analyses':[t[1:] for t in tasks]})+'\n')
