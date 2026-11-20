from pathlib import Path
import json,hashlib,re
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 run=ROOT/'runs/expanded_v1'
 for f in ['completion.json','pipeline_completion.json','controls_analysis_completion.json','synthesis_completion.json']:
  assert json.loads((run/f).read_text())['complete']
 records=[json.loads(p.read_text()) for p in (run/'observations').glob('*.json')];assert len(records)==6600
 native=[];maxerr=0;full=0
 for i,r in enumerate(records):
  path=run/r['state_file'];assert sha(path)==r['state_sha256']
  q=np.array(r['layer_q']);assert q.shape==(28,6) and np.isfinite(q).all() and (q>=0).all();assert np.allclose(q.sum(-1),1,atol=1e-6)
  if r['native_check']:native.append(r['native_check'])
  with np.load(path) as a:
   assert a['residual_stages'].shape==(28,5,2048)
   z=a['layer_candidate_logits'].astype(float);w=np.exp(z-z.max(-1,keepdims=True));w/=w.sum(-1,keepdims=True)
   maxerr=max(maxerr,float(np.abs(w-q).max()));assert np.allclose(w,q,atol=3e-7,rtol=2e-6)
   if 'terminal_logits' in a.files:
    full+=1;v=a['terminal_logits'].astype(float);p=np.exp(v-v.max());p/=p.sum();assert np.allclose(p[a['candidate_ids']],r['p'],atol=3e-7,rtol=2e-6)
 assert len(native)==27 and all(x['allclose'] and x['argmax_equal'] for x in native)
 links=0
 for p in (ROOT/'results').rglob('*.md'):
  for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
   if link.startswith(('https://','http://','#')):continue
   assert (p.parent/link).exists(),(p,link);links+=1
 for p in (ROOT/'results').rglob('*.png'):assert p.stat().st_size>1000
 summaries={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'results').rglob('RESULTS.md')}
 outcome={'complete':True,'observations_checked':6600,'state_hashes_and_shapes':'passed','independent_float64_probability_check_max_error':maxerr,
  'full_vocabulary_checks':full,'native_forward_checks':len(native),'markdown_local_links_checked':links,
  'png_figures':len(list((ROOT/'results').rglob('*.png'))),'pdf_figures':len(list((ROOT/'results').rglob('*.pdf'))),
  'case_atlas_markdown':len(list((ROOT/'results/02_replication/cases').glob('*.md'))),'stage_reports':summaries,
  'api_cost_usd':0}
 (ROOT/'protocol/delivery_verification.json').write_text(json.dumps(outcome,indent=2)+'\n');print(json.dumps(outcome,indent=2))
if __name__=='__main__':main()
