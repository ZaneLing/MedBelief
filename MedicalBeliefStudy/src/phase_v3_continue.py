"""Finite sequential GPU queue; stop on any failure, never mark pending work complete."""
import json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];CWD=ROOT.parent;GPU=CWD/'MedicalBeliefMechanisms/.runtime_mlx/bin/python';RUN=ROOT/'runs/belief_v3'
while not (RUN/'completion.json').exists():time.sleep(20)
for script,args in [('phase24_natural_intervene.py',[]),('phase25_external_run.py',[]),('phase23_run.py',['--model','4b'])]:
 with (RUN/(script+'.log')).open('a') as f:
  r=subprocess.run([str(GPU),str(ROOT/'src'/script),*args],cwd=CWD,stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:raise RuntimeError(f'{script} failed: {r.returncode}')
(RUN/'gpu_queue_complete.json').write_text(json.dumps({'complete':True,'stages':['new_patients','natural_interventions','external_medqa','4b_replication'],'api_cost_usd':0})+'\n')
