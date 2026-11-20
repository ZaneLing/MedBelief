"""Finite local continuation; stop immediately if a dependency fails."""
import argparse,json,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--observation-pid',type=int,required=True);a=ap.parse_args();run=ROOT/'runs/belief_v2'
    while not (run/'completion.json').exists():
        try:os.kill(a.observation_pid,0)
        except ProcessLookupError:raise RuntimeError('Observation process stopped without completion; inspect observations.log')
        time.sleep(10)
    env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'}
    cpu=ROOT.parent/'MedicalBeliefMechanisms/.runtime/bin/python';gpu=ROOT.parent/'MedicalBeliefMechanisms/.runtime_mlx/bin/python'
    for python,name,log in [(cpu,'phase14_analyze.py','analysis.log'),(cpu,'phase16_update_analyze.py','update_mechanism.log'),(gpu,'phase19_presentation.py','presentation.log'),(cpu,'phase19_analyze.py','presentation_analysis.log'),(gpu,'phase15_intervene.py','disease_interventions.log'),(cpu,'phase15_analyze.py','causal_analysis.log'),(gpu,'phase17_polarity.py','polarity.log'),(cpu,'phase17_analyze.py','polarity_analysis.log'),(gpu,'phase18_run.py','model4b.log'),(cpu,'phase18_analyze.py','model4b_analysis.log')]:
        print(json.dumps({'starting':name}),flush=True)
        with (run/log).open('w') as f:subprocess.run([str(python),str(ROOT/'src'/name)],stdout=f,stderr=subprocess.STDOUT,env=env,check=True)
        print(json.dumps({'completed':name}),flush=True)
    (run/'pipeline_complete.json').write_text(json.dumps({'complete':True,'api_cost_usd':0})+'\n')
if __name__=='__main__':main()
