"""Resume dependent analyses once the frozen GPU observation run completes."""
from pathlib import Path
import subprocess,time,json
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT.parent;RUN=ROOT/'runs/expanded_v1'
MLX=WORK/'MedicalBeliefMechanisms/.runtime_mlx/bin/python';CPU=WORK/'MedicalBeliefMechanisms/.runtime/bin/python'
def start(name,python):
 log=(ROOT/'runs'/f'{name}.log').open('w')
 p=subprocess.Popen([str(python),str(ROOT/'src'/f'{name}.py')],cwd=WORK,stdout=log,stderr=subprocess.STDOUT)
 return p,log
def finish(name,job):
 p,log=job;code=p.wait();log.close()
 print(json.dumps({'finished':name,'returncode':code}),flush=True)
 if code:raise RuntimeError(f'{name} failed; see runs/{name}.log')
def main():
 began=time.time()
 while not (RUN/'completion.json').exists():
  if time.time()-began>7200:raise TimeoutError('Observation run did not complete')
  log=ROOT/'runs/expanded_v1.log'
  if log.exists() and 'Traceback (most recent call last)' in log.read_text()[-3000:]:raise RuntimeError('Observation run failed')
  time.sleep(5)
 print('Observations complete; starting dependent experiments.',flush=True)
 cpu={name:start(name,CPU) for name in ['readouts','affine_readout','analyze_stages']}
 for name in ['intervene_and_names','content_and_depth']:finish(name,start(name,MLX))
 for name,job in cpu.items():finish(name,job)
 for name in ['summarize_mechanisms','summarize_controls']:finish(name,start(name,CPU))
 (RUN/'pipeline_completion.json').write_text(json.dumps({'complete':True,'elapsed_sec':time.time()-began},indent=2)+'\n')
if __name__=='__main__':main()
