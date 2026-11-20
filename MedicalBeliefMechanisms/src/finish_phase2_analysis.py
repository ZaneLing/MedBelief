"""Sequential CPU analyses of already-authorized phase 2 runs; no model calls."""
import json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
START=time.monotonic()
def wait_for(p):
    while not (ROOT/p).exists():
        if time.monotonic()-START>14400:raise TimeoutError(str(p))
        time.sleep(5)
def run(script,*args):
    subprocess.run([str(ROOT/'.runtime/bin/python'),str(ROOT/'src'/script),*args],cwd=ROOT,check=True)
wait_for('runs/phase2_pilot_4b/completion.json');run('analyze_phase2.py','--run-id','phase2_pilot_4b')
wait_for('runs/phase2_bp_repair_confirm/completion.json');run('analyze_bp_repairs_phase2.py')
# Predictions are opened only after all states were saved and closed.
wait_for('runs/phase2b_confirm_4b/predictions.jsonl');run('transfer_phase2.py')
wait_for('runs/phase2b_confirm_4b/completion.json');run('analyze_phase2.py','--run-id','phase2b_confirm_4b');run('plot_phase2.py')
print('All phase 2 analyses and plots complete',flush=True)
