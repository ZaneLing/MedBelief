"""Finite sequential GPU queue with independent CPU reports in parallel."""
from pathlib import Path
import json,subprocess,time
ROOT=Path(__file__).resolve().parents[1]
GPU=ROOT.parent/'MedicalBeliefMechanisms/.runtime_mlx/bin/python'
CPU=ROOT.parent/'MedicalBeliefMechanisms/.runtime/bin/python'
LOG=ROOT/'research_v4'

def start(script,python,log):
    f=(LOG/log).open('a');p=subprocess.Popen([str(python),'-u',str(ROOT/'src'/script)],stdout=f,stderr=subprocess.STDOUT);return p,f
def finish(pair):
    p,f=pair;code=p.wait();f.close()
    if code:raise RuntimeError(f'Child PID {p.pid} exited {code}; see stage log')
def main():
    while not (ROOT/'runs/belief_v4/completion.json').exists():
        log=LOG/'observations.log'
        if log.exists() and 'Traceback (most recent call last)' in log.read_text()[-5000:]:raise RuntimeError('Observation stage failed; inspect observations.log')
        time.sleep(10)
    print('Observations complete; starting patient analysis and causal transfers.',flush=True)
    analysis=start('phase41_multisource_analyze.py',CPU,'analysis.log')
    finish(start('phase40_multisource_patch.py',GPU,'patches.log'));finish(analysis)
    print('Causal transfers complete; starting intervention analysis and 4B replication.',flush=True)
    analysis=start('phase42_multisource_patch_analyze.py',CPU,'patch_analysis.log')
    finish(start('phase43_multisource_4b.py',GPU,'replication4b.log'));finish(analysis)
    (LOG/'queue_completion.json').write_text(json.dumps(dict(observations=True,causal=True,replication4b=True,api_cost_usd=0),indent=2)+'\n')
    print('All queued inference and stage analyses completed.',flush=True)

if __name__=='__main__':main()
