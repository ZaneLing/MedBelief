"""Check the copied scientific files byte-for-byte against the source manifest."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--profile',choices=['git','current','acl','all'],default='git');a=ap.parse_args();m=json.loads((ROOT/'artifacts/manifest.json').read_text());groups={'git':set(),'current':{'current-v010'},'acl':{'current-v010','acl-evidence-v008-v009'},'all':None}[a.profile];assets={z['name'] for z in m['assets'] if groups is None or z['group'] in groups};required=[r for r in m['files'] if r['storage']=='git' or r.get('asset') in assets];bad=[]
 for r in required:
  p=ROOT/r['path']
  if not p.exists() or digest(p)!=r['sha256']:bad.append(r['path'])
 print(json.dumps(dict(complete=not bad,profile=a.profile,files_checked=len(required),mismatches=bad),ensure_ascii=False));raise SystemExit(bool(bad))
if __name__=='__main__':main()
