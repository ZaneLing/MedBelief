"""Publish this snapshot to the configured private repository with digest checks.

Uploads a draft release first. --finalize only publishes after all remote asset
sizes and GitHub-computed SHA-256 digests match the local manifest.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import argparse,hashlib,json,subprocess,time
from github_auth import environment
ROOT=Path(__file__).resolve().parents[1]

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--finalize',action='store_true');ap.add_argument('--workers',type=int,choices=range(1,9),default=4);a=ap.parse_args();m=json.loads((ROOT/'artifacts/manifest.json').read_text());env=environment();repo=m['repo'];tag=m['release_tag'];start=time.time()
 transport=[p for archive in m['assets'] for p in archive.get('parts',[archive])]
 def gh(args,**kw):return subprocess.run(['gh',*args],env=env,text=True,capture_output=True,**kw)
 def api(path,method=None,fields=None):
  args=['api',path]
  if method:args+=['--method',method]
  for k,v in (fields or {}).items():args+=['-f',k+'='+str(v)]
  p=gh(args);p.check_returncode();return json.loads(p.stdout) if p.stdout.strip() else None
 info=api('repos/'+repo);assert info['private'] and info['permissions']['push'],'Expected the authorized private repository'
 while True:
  p=gh(['api','repos/'+repo+'/git/ref/heads/main'])
  if p.returncode==0:break
  if time.time()-start>900:raise RuntimeError('main was not pushed within15minutes')
  time.sleep(10)
 release=next((x for x in api('repos/'+repo+'/releases?per_page=100') if x['tag_name']==tag),None)
 if release is None:
  q=gh(['release','create',tag,'--repo',repo,'--target','main','--draft','--title','ACL medical belief research v0.10','--notes-file',str(ROOT/'docs/RELEASE_NOTES.md')]);q.check_returncode()
  release=next(x for x in api('repos/'+repo+'/releases?per_page=100') if x['tag_name']==tag)
 def inventory():return {x['name']:x for x in api('repos/'+repo+'/releases/'+str(release['id'])+'/assets?per_page=100')}
 def matches(remote,local):return remote.get('state')=='uploaded' and remote['size']==local['bytes'] and remote.get('digest')=='sha256:'+local['sha256']
 existing=inventory();pending=[]
 for z in transport:
  if z['name'] in existing:
   assert matches(existing[z['name']],z),('Existing remote asset differs',z['name'])
  else:pending.append(z)
 def upload(z):
  f=ROOT/'.artifacts'/z['name'];assert f.exists() and f.stat().st_size==z['bytes']
  for attempt in range(3):
   p=gh(['release','upload',tag,str(f),'--repo',repo]);remote=inventory().get(z['name'])
   if remote and matches(remote,z):print(json.dumps(dict(uploaded=z['name'],bytes=z['bytes'],elapsed_seconds=round(time.time()-start))),flush=True);return z['name']
   if remote:
    # Only delete an incomplete upload created by this invocation; never clobber an existing valid asset.
    if remote.get('state')=='starter' or remote.get('size')==0:api('repos/'+repo+'/releases/assets/'+str(remote['id']),method='DELETE')
    else:raise RuntimeError('Remote checksum mismatch: '+z['name'])
   if attempt==2:raise RuntimeError('Upload failed for '+z['name']+': '+p.stderr[-1000:])
   time.sleep(5)
 with ThreadPoolExecutor(max_workers=a.workers) as pool:
  for f in as_completed([pool.submit(upload,z) for z in sorted(pending,key=lambda x:(x['group']!='current-v010',x['bytes']))]):f.result()
 remote=inventory();assert all(x['name'] in remote and matches(remote[x['name']],x) for x in transport)
 # Upload the scientific manifest and checksums as convenient release companions.
 for f in [ROOT/'artifacts/manifest.json',ROOT/'artifacts/SHA256SUMS']:
  h=hashlib.sha256(f.read_bytes()).hexdigest();old=remote.get(f.name)
  if old:assert old.get('digest')=='sha256:'+h,('Companion differs',f.name)
  else:
   p=gh(['release','upload',tag,str(f),'--repo',repo]);p.check_returncode()
 remote=inventory()
 for f in [ROOT/'artifacts/manifest.json',ROOT/'artifacts/SHA256SUMS']:
  expected=dict(bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest())
  assert f.name in remote and matches(remote[f.name],expected),('Companion verification failed',f.name)
 if a.finalize:
  p=gh(['release','edit',tag,'--repo',repo,'--draft=false','--latest']);p.check_returncode()
 release=api('repos/'+repo+'/releases/'+str(release['id']))
 if a.finalize:assert not release['draft'] and release.get('published_at'),'Release was not published'
 report=dict(complete=True,repository=repo,private=info['private'],release_url='https://github.com/'+repo+'/releases/tag/'+tag,draft=release['draft'],published_at=release.get('published_at'),logical_archives=len(m['assets']),remote_data_assets=len(transport),companion_assets=2,bytes=sum(x['bytes'] for x in m['assets']),all_remote_sha256_verified=True,companions_sha256_verified=True,api_inference_cost_usd=0)
 (ROOT/'docs/UPLOAD_VALIDATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
