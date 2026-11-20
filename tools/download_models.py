"""Restore public weights at the exact research revision, checking known hashes."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 from huggingface_hub import snapshot_download
 ap=argparse.ArgumentParser();ap.add_argument('--model',choices=['1.7b','4b-mlx'],default='1.7b');ap.add_argument('--verify-only',action='store_true');a=ap.parse_args();base=ROOT/'MedicalBeliefMechanisms';fn='model_snapshot.json' if a.model=='1.7b' else 'qwen3_4b_8bit_snapshot.json';spec=json.loads((base/'protocol'/fn).read_text());name='Qwen3-1.7B' if a.model=='1.7b' else 'Qwen3-4B-8bit';dest=base/'.models'/name
 if not a.verify_only:snapshot_download(repo_id=spec['id'],revision=spec['sha'],local_dir=str(dest),allow_patterns=['*.json','*.safetensors','*.txt','*.md','LICENSE'])
 expected={r['rfilename']:r['lfs']['sha256'] for r in spec.get('weight_files',[])}
 if a.model=='1.7b':expected.update(json.loads((ROOT/'MedicalBeliefStudy/runs/belief_v4/manifest.json').read_text())['model_hashes'])
 else:expected.update({r['rfilename']:r['lfs']['sha256'] for r in spec['siblings'] if isinstance(r,dict) and r.get('lfs',{}).get('sha256')})
 for name,h in expected.items():assert (dest/name).exists() and digest(dest/name)==h,('Model hash mismatch',name)
 print(json.dumps(dict(verified=True,repo=spec['id'],revision=spec['sha'],files=len(expected),directory=str(dest))))
if __name__=='__main__':main()
