import os,subprocess,time
from pathlib import Path
r=Path(__file__).resolve().parents[1]
while not (r/'runs/belief_v3_medqa/natural_interventions/completion.json').exists():time.sleep(20)
with (r/'runs/belief_v3/roles.log').open('a') as f:
 subprocess.run([str(r.parent/'MedicalBeliefMechanisms/.runtime_mlx/bin/python'),str(r/'src/phase29_roles.py')],cwd=r.parent,stdout=f,stderr=subprocess.STDOUT,check=True)
with (r/'runs/belief_v3/roles_analysis.log').open('a') as f:
 subprocess.run([str(r.parent/'MedicalBeliefMechanisms/.runtime/bin/python'),str(r/'src/phase29_roles_analyze.py')],cwd=r.parent,env=dict(os.environ,OPENBLAS_NUM_THREADS='2'),stdout=f,stderr=subprocess.STDOUT,check=True)
