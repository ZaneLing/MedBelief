import os,subprocess,time
from pathlib import Path
r=Path(__file__).resolve().parents[1]
while not (r/'runs/belief_v3/natural_interventions_replication/completion.json').exists():time.sleep(20)
with (r/'runs/belief_v3/external_internal.log').open('a') as f:
 subprocess.run([str(r.parent/'MedicalBeliefMechanisms/.runtime_mlx/bin/python'),str(r/'src/phase28_external_natural.py')],cwd=r.parent,stdout=f,stderr=subprocess.STDOUT,check=True)
with (r/'runs/belief_v3/external_internal_analysis.log').open('a') as f:
 subprocess.run([str(r.parent/'MedicalBeliefMechanisms/.runtime/bin/python'),str(r/'src/phase28_external_analyze.py')],cwd=r.parent,env=dict(os.environ,OPENBLAS_NUM_THREADS='2'),stdout=f,stderr=subprocess.STDOUT,check=True)
