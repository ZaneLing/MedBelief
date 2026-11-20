"""Download private release assets and restore only hash-verified snapshot files."""
import argparse,hashlib,json,shutil,subprocess,tarfile
from pathlib import Path,PurePosixPath
from github_auth import environment
ROOT=Path(__file__).resolve().parents[1]
PROFILES={'current':{'current-v010'},'acl':{'current-v010','acl-evidence-v008-v009'},'all':None}
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--profile',choices=PROFILES,default='current');ap.add_argument('--cache-dir',type=Path,default=ROOT/'.artifacts');ap.add_argument('--verify-only',action='store_true');a=ap.parse_args();spec=json.loads((ROOT/'artifacts/manifest.json').read_text());groups=PROFILES[a.profile];assets=[z for z in spec['assets'] if groups is None or z['group'] in groups];a.cache_dir.mkdir(parents=True,exist_ok=True);count=0
 for asset in assets:
  required={r['path']:r for r in spec['files'] if r.get('asset')==asset['name']}
  if a.verify_only:
   for path,r in required.items():assert (ROOT/path).exists() and digest(ROOT/path)==r['sha256'],('Missing/modified artifact',path)
   count+=len(required);continue
  archive=a.cache_dir/asset['name']
  if not archive.exists():subprocess.run(['gh','release','download',spec['release_tag'],'--repo',spec['repo'],'--pattern',asset['name'],'--dir',str(a.cache_dir)],env=environment(),check=True)
  assert digest(archive)==asset['sha256'],('Archive checksum mismatch',asset['name'])
  seen=set()
  with tarfile.open(archive,'r:gz') as tf:
   for member in tf:
    name=member.name;parts=PurePosixPath(name).parts
    assert member.isfile() and name in required and not name.startswith('/') and '..' not in parts and name not in seen,('Unexpected archive member',name);seen.add(name);out=ROOT/name;r=required[name]
    assert member.size==r['bytes'];assert not out.is_symlink() and all(not p.is_symlink() for p in out.parents if p!=ROOT.parent)
    if out.exists():assert digest(out)==r['sha256'],('Refusing to replace a changed experiment file',name);continue
    out.parent.mkdir(parents=True,exist_ok=True);tmp=out.with_name(out.name+'.restore-part')
    with tf.extractfile(member) as source,tmp.open('wb') as dest:shutil.copyfileobj(source,dest,8*1024*1024)
    assert digest(tmp)==r['sha256'],('Extracted checksum mismatch',name);tmp.replace(out)
  assert seen==set(required),('Missing archive members',asset['name']);count+=len(seen);print('Restored',asset['name'],flush=True)
 print(json.dumps(dict(complete=True,profile=a.profile,files=count)))
if __name__=='__main__':main()
