from pathlib import Path
import subprocess,json,time
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT.parent;CPU=WORK/'MedicalBeliefMechanisms/.runtime/bin/python';run=ROOT/'runs/expanded_v1'
began=time.time()
for name,args in [('analyze_stages',['--skip-atlas']),('summarize_mechanisms',[]),('summarize_controls',[])]:
 with (ROOT/'runs'/f'{name}_delivery.log').open('w') as f:
  subprocess.run([str(CPU),str(ROOT/'src'/f'{name}.py'),*args],cwd=WORK,stdout=f,stderr=subprocess.STDOUT,check=True)
 print('completed',name,flush=True)
for f in ['completion.json','readouts/completion.json','readouts/affine_completion.json','interventions/completion.json','name_scores/completion.json','content_controls/completion.json','depth_interventions/completion.json','synthesis_completion.json','controls_analysis_completion.json']:
 assert json.loads((run/f).read_text())['complete']
(run/'pipeline_completion.json').write_text(json.dumps({'complete':True,'final_analysis_elapsed_sec':time.time()-began,'resumed_after':'Report serialization fix; frozen inference not rerun','tie_policy':'both unique winners required for diagnosis switch'},indent=2)+'\n')
subprocess.run([str(CPU),str(ROOT/'src/verify_delivery.py')],cwd=WORK,check=True)
