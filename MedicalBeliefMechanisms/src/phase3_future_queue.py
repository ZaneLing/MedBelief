from pathlib import Path
import subprocess,time
ROOT=Path(__file__).resolve().parents[1];start=time.monotonic()
while not (ROOT/'runs/phase2d_partial_fact_4b/completion.json').exists():
    if time.monotonic()-start>14400:raise TimeoutError('Phase2D not completed')
    time.sleep(5)
cmd=[str(ROOT/'.runtime_mlx/bin/python'),'src/mlx_experiment_v2.py','--data','data/phase3_future_pilot.jsonl','--run-id','phase3_future_pilot_4b','--model-dir','.models/Qwen3-4B-8bit','--model-manifest','protocol/qwen3_4b_8bit_snapshot.json','--max-tokens','2048','--batch-size','16']
with (ROOT/'runs/phase3_future_pilot_4b.log').open('w') as log:subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
print('Phase3 future pilot completed',flush=True)
