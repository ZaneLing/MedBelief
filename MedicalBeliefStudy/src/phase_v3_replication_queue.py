import os,subprocess,time
from pathlib import Path
r=Path(__file__).resolve().parents[1]
while not (r/'runs/belief_v3/history_matched/completion.json').exists():time.sleep(20)
with (r/'runs/belief_v3/natural_replication.log').open('a') as f:
 subprocess.run([str(r.parent/'MedicalBeliefMechanisms/.runtime_mlx/bin/python'),str(r/'src/phase24_natural_intervene.py'),'--replication'],cwd=r.parent,stdout=f,stderr=subprocess.STDOUT,check=True)
with (r/'runs/belief_v3/natural_replication_analysis.log').open('a') as f:
 subprocess.run([str(r.parent/'MedicalBeliefMechanisms/.runtime/bin/python'),str(r/'src/phase24_analyze.py'),'--replication'],cwd=r.parent,env=dict(os.environ,OPENBLAS_NUM_THREADS='2'),stdout=f,stderr=subprocess.STDOUT,check=True)
