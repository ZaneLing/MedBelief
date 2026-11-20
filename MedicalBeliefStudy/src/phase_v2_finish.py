"""Run the final, specified template control after the main GPU pipeline exits."""
import argparse, json, os, subprocess, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--pipeline-pid', type=int, required=True); args = ap.parse_args()
    run = ROOT/'runs/belief_v2'
    while not (run/'pipeline_complete.json').exists():
        try: os.kill(args.pipeline_pid, 0)
        except ProcessLookupError: raise RuntimeError('Main pipeline stopped before completion; inspect pipeline.log')
        time.sleep(10)
    env = {**os.environ, 'OPENBLAS_NUM_THREADS':'1', 'OMP_NUM_THREADS':'1'}
    for runtime, script, log in [('.runtime_mlx','phase20_prior.py','template_prior.log'), ('.runtime','phase20_analyze.py','template_prior_analysis.log')]:
        print(json.dumps({'starting':script}), flush=True)
        with (run/log).open('w') as f:
            subprocess.run([str(ROOT.parent/'MedicalBeliefMechanisms'/runtime/'bin/python'), str(ROOT/'src'/script)], stdout=f, stderr=subprocess.STDOUT, env=env, check=True)
        print(json.dumps({'completed':script}), flush=True)
    (run/'all_experiments_complete.json').write_text(json.dumps({'complete':True,'api_cost_usd':0})+'\n')
if __name__ == '__main__': main()
