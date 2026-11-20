"""Download public model files at a pinned revision, with full content hashes."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import argparse,hashlib,json,os,threading,time,urllib.request
ROOT=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--repo',required=True);ap.add_argument('--dest',required=True);ap.add_argument('--manifest',required=True)
a=ap.parse_args();manifest=ROOT/a.manifest;dest=ROOT/a.dest;dest.mkdir(parents=True,exist_ok=True)
if manifest.exists():meta=json.loads(manifest.read_text())
else:
    meta=json.load(urllib.request.urlopen(f'https://huggingface.co/api/models/{a.repo}?blobs=true'))
    manifest.write_text(json.dumps(meta,indent=2)+'\n')
assert meta['id']==a.repo
files=[x for x in meta['siblings'] if '/' not in x['rfilename'] and (x['rfilename'].endswith(('.json','.txt','.safetensors','.md')) or x['rfilename']=='LICENSE')]
checks=[];lock=threading.Lock();jobs=[];open_files={};chunk=8*2**20
for f in files:
    name=f['rfilename'];p=dest/name
    url=f"https://huggingface.co/{meta['id']}/resolve/{meta['sha']}/{name}"
    if 'lfs' not in f:
        b=p.read_bytes() if p.exists() else urllib.request.urlopen(url,timeout=90).read()
        digest=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
        assert digest==f['blobId'],(name,'git blob mismatch')
        if not p.exists():p.write_bytes(b)
        checks.append({'file':name,'git_blob_sha1':digest,'bytes':len(b)});continue
    size=f['size'];expected=f['lfs']['sha256']
    if p.exists():
        actual=hashlib.file_digest(p.open('rb'),'sha256').hexdigest();assert actual==expected,(name,'existing checksum mismatch')
        checks.append({'file':name,'sha256':actual,'bytes':size});continue
    state_path=dest/(name+'.ranges.json');part=dest/(name+'.part')
    state=json.loads(state_path.read_text()) if state_path.exists() else {'done':[],'chunk_size':chunk}
    assert state['chunk_size']==chunk
    state_path.write_text(json.dumps(state))
    fd=os.open(part,os.O_RDWR|os.O_CREAT);os.ftruncate(fd,size)
    open_files[name]=(fd,p,part,state_path,state,f,url)
    for start in range(0,size,chunk):
        if start not in state['done']:jobs.append((name,start,min(start+chunk,size)-1))

def transfer(job):
    name,start,end=job;fd,p,part,sp,state,f,url=open_files[name];error=None
    for attempt in range(8):
        try:
            req=urllib.request.Request(url+f'?range_start={start}',headers={'Range':f'bytes={start}-{end}'})
            with urllib.request.urlopen(req,timeout=90) as r:
                assert r.status==206 and r.headers.get('Content-Range')==f"bytes {start}-{end}/{f['size']}"
                offset=start
                while block:=r.read(1024*1024):
                    written=0
                    while written<len(block):written+=os.pwrite(fd,block[written:],offset+written)
                    offset+=len(block)
                assert offset==end+1
            with lock:
                state['done'].append(start);tmp=sp.with_suffix('.tmp');tmp.write_text(json.dumps(state));tmp.replace(sp)
            return
        except Exception as e:error=repr(e);time.sleep(min(2**attempt,12))
    raise RuntimeError(f'{name}:{start} failed: {error}')

print(json.dumps({'repo':a.repo,'revision':meta['sha'],'ranges_to_download':len(jobs),'workers':32}),flush=True)
with ThreadPoolExecutor(max_workers=32) as pool:
    for i,future in enumerate(as_completed([pool.submit(transfer,j) for j in jobs]),1):
        future.result()
        if i%16==0 or i==len(jobs):print(json.dumps({'completed_ranges':i,'total_ranges':len(jobs)}),flush=True)
for name,(fd,p,part,sp,state,f,url) in open_files.items():
    os.fsync(fd);os.close(fd);digest=hashlib.file_digest(part.open('rb'),'sha256').hexdigest()
    assert digest==f['lfs']['sha256'],(name,'downloaded checksum mismatch')
    part.replace(p);checks.append({'file':name,'sha256':digest,'bytes':f['size']})
(dest/'verified_download.json').write_text(json.dumps({'repo':a.repo,'revision':meta['sha'],'files':checks},indent=2)+'\n')
print('ALL_MODEL_FILES_VERIFIED',flush=True)
