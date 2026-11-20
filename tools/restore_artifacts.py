"""Download private release assets and restore only hash-verified snapshot files."""
import argparse,hashlib,json,shutil,subprocess,tarfile,tempfile
from pathlib import Path,PurePosixPath
from github_auth import environment
ROOT=Path(__file__).resolve().parents[1]
PROFILES={'current':{'current-v010'},'acl':{'current-v010','acl-evidence-v008-v009'},'all':None}
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def download_asset(spec,item,cache):
 path=cache/item['name']
 if not path.exists():
  with tempfile.TemporaryDirectory(prefix='.download-',dir=cache) as tmp:
   subprocess.run(['gh','release','download',spec['release_tag'],'--repo',spec['repo'],'--pattern',item['name'],'--dir',tmp],env=environment(),check=True)
   downloaded=Path(tmp)/item['name']
   assert downloaded.stat().st_size==item['bytes'] and digest(downloaded)==item['sha256'],('Downloaded asset checksum mismatch',item['name'])
   downloaded.replace(path)
 assert path.stat().st_size==item['bytes'] and digest(path)==item['sha256'],('Downloaded asset checksum mismatch',item['name'])
 return path
def obtain_archive(spec,asset,cache):
 archive=cache/asset['name']
 if archive.exists():
  assert archive.stat().st_size==asset['bytes'] and digest(archive)==asset['sha256'],('Archive checksum mismatch',asset['name'])
  return archive
 if 'parts' not in asset:return download_asset(spec,asset,cache)
 parts=[download_asset(spec,p,cache) for p in asset['parts']]
 tmp=archive.with_name(archive.name+'.assembling')
 with tmp.open('wb') as out:
  for part in parts:
   with part.open('rb') as source:shutil.copyfileobj(source,out,8*1024*1024)
 assert tmp.stat().st_size==asset['bytes'] and digest(tmp)==asset['sha256'],('Reassembled archive checksum mismatch',asset['name'])
 tmp.replace(archive)
 for part in parts:part.unlink()
 return archive
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--profile',choices=PROFILES,default='current');ap.add_argument('--cache-dir',type=Path,default=ROOT/'.artifacts');ap.add_argument('--verify-only',action='store_true');a=ap.parse_args();spec=json.loads((ROOT/'artifacts/manifest.json').read_text());groups=PROFILES[a.profile];assets=[z for z in spec['assets'] if groups is None or z['group'] in groups];a.cache_dir.mkdir(parents=True,exist_ok=True);count=0
 for asset in assets:
  required={r['path']:r for r in spec['files'] if r.get('asset')==asset['name']}
  if a.verify_only:
   for path,r in required.items():assert (ROOT/path).exists() and digest(ROOT/path)==r['sha256'],('Missing/modified artifact',path)
   count+=len(required);continue
  archive=obtain_archive(spec,asset,a.cache_dir)
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
