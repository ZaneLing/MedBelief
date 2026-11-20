"""Finite sequential GPU/CPU pipeline; never overlap GPU experiments."""
from pathlib import Path
import subprocess,time,json,os
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent
GPU=REPO/'MedicalBeliefMechanisms/.runtime_mlx/bin/python';CPU=REPO/'MedicalBeliefMechanisms/.runtime/bin/python';DOC=ROOT/'research_v5_structural'
def run(py,name,log,args=()):
    print('Starting '+name+' '+' '.join(args),flush=True)
    env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    with (DOC/log).open('a') as f:subprocess.run([str(py),'-u',str(ROOT/'src'/name),*args],stdout=f,stderr=subprocess.STDOUT,check=True,cwd=REPO,env=env)
    print('Completed '+name,flush=True)
def main():
    start=time.time()
    while not (ROOT/'runs/structural_v1/screen/completion.json').exists():
        if time.time()-start>7200:raise TimeoutError('Screening did not complete')
        time.sleep(5)
    stages=[(CPU,'phase71_structural_localization.py','localization.log',()),(GPU,'phase72_structural_training_data.py','training_data.log',()),(CPU,'phase73_structural_fit.py','linear_fit.log',()),(GPU,'phase74_structural_evaluate.py','tuning.log',('--split','tune')),(CPU,'phase75_structural_select.py','selection.log',()),(GPU,'phase74_structural_evaluate.py','holdout.log',('--split','test')),(GPU,'phase76_structural_generation.py','generation.log',()),(GPU,'phase78_structural_timing.py','timing.log',())]
    for py,name,log,args in stages:run(py,name,log,args)
    (DOC/'model_stages_complete.json').write_text(json.dumps(dict(complete=True,api_cost_usd=0))+'\n')
if __name__=='__main__':main()
