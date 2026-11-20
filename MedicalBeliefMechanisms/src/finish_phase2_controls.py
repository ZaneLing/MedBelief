from pathlib import Path
import subprocess,time
ROOT=Path(__file__).resolve().parents[1];start=time.monotonic()
def wait_for(p):
    while not (ROOT/p).exists():
        if time.monotonic()-start>14400:raise TimeoutError(p)
        time.sleep(5)
def run(s):subprocess.run([str(ROOT/'.runtime/bin/python'),'src/'+s],cwd=ROOT,check=True)
wait_for('runs/phase2c_answer_control_4b/answer_control_readout/completion.json')
for s in ['analyze_answer_control_phase2.py','plot_answer_control_phase2.py','repair_source_readout_phase2.py','plot_readout_repairs_phase2.py']:run(s)
wait_for('runs/phase2d_partial_fact_4b/completion.json')
for s in ['analyze_partial_fact_phase2.py','summarize_phase2.py','write_phase2_casebook.py']:run(s)
print('All phase2 control analyses complete',flush=True)
