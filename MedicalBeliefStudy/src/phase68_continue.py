"""Resume the finite stage06–08 pipeline; GPU jobs run sequentially."""
from pathlib import Path
import subprocess,time
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent
GPU=REPO/'MedicalBeliefMechanisms/.runtime_mlx/bin/python';CPU=REPO/'MedicalBeliefMechanisms/.runtime/bin/python';run=ROOT/'runs/full49_v1'
start=time.time()
while not (run/'completion.json').exists():
    if time.time()-start>7200:raise TimeoutError('Observation stage did not complete within two hours')
    time.sleep(5)
for interpreter,script,log in [(GPU,'phase6_name_control.py','names.log'),(GPU,'phase8_validate.py','validation.log'),(GPU,'phase8_intervene.py','interventions.log'),(CPU,'phase67_analyze.py','analysis67.log'),(CPU,'phase8_analyze.py','analysis8.log')]:
    print(f'Starting {script}',flush=True)
    with (run/log).open('a') as out:subprocess.run([str(interpreter),str(ROOT/'src'/script)],stdout=out,stderr=subprocess.STDOUT,check=True,cwd=REPO)
    print(f'Completed {script}',flush=True)
print('Finite pipeline complete',flush=True)
