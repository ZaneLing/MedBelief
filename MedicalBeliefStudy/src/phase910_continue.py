"""Finite adaptive follow-up after stage08 releases the GPU."""
from pathlib import Path
import subprocess,time
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent
GPU=REPO/'MedicalBeliefMechanisms/.runtime_mlx/bin/python';CPU=REPO/'MedicalBeliefMechanisms/.runtime/bin/python';run=ROOT/'runs/structured_names_v1'
start=time.time()
while not (ROOT/'runs/full49_v1/depth_interventions/completion.json').exists():
    if time.time()-start>10800:raise TimeoutError('Stage08 did not finish')
    time.sleep(5)
for interpreter,script,log in [(GPU,'phase9_names.py','observations.log'),(GPU,'phase10_names_intervene.py','interventions.log'),(CPU,'phase910_analyze.py','analysis.log')]:
    print(f'Starting {script}',flush=True)
    with (run/log).open('a') as out:subprocess.run([str(interpreter),str(ROOT/'src'/script)],stdout=out,stderr=subprocess.STDOUT,check=True,cwd=REPO)
    print(f'Completed {script}',flush=True)
print('Adaptive pipeline complete',flush=True)
