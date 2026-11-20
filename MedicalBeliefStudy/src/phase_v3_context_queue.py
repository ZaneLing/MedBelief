import subprocess,time
from pathlib import Path
r=Path(__file__).resolve().parents[1]
while not (r/'runs/belief_v3/gpu_queue_complete.json').exists():time.sleep(20)
with (r/'runs/belief_v3/evidence_context.log').open('a') as f:
 subprocess.run([str(r.parent/'MedicalBeliefMechanisms/.runtime_mlx/bin/python'),str(r/'src/phase26_evidence_context.py')],cwd=r.parent,stdout=f,stderr=subprocess.STDOUT,check=True)
