"""Run the frozen answer-confound control after the existing phase 2B queue."""
from pathlib import Path
import subprocess,time
ROOT=Path(__file__).resolve().parents[1];start=time.monotonic()
while not (ROOT/'runs/phase2b_confirm_4b/completion.json').exists():
    if time.monotonic()-start>14400:raise TimeoutError('Phase 2B not completed')
    time.sleep(5)
cmd=[str(ROOT/'.runtime_mlx/bin/python'),'src/mlx_experiment_v2.py','--data','data/phase2c_answer_control.jsonl','--run-id','phase2c_answer_control_4b','--model-dir','.models/Qwen3-4B-8bit','--model-manifest','protocol/qwen3_4b_8bit_snapshot.json','--max-tokens','2048','--batch-size','16','--capture']
with (ROOT/'runs/phase2c_answer_control_4b.log').open('w') as log:subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
subprocess.run([str(ROOT/'.runtime/bin/python'),'src/probe_answer_control_phase2.py'],cwd=ROOT,check=True)
print('Phase 2C completed',flush=True)
