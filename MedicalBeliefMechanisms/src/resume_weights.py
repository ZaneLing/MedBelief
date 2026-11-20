"""Resume public pinned weight downloads with checked HTTP ranges and SHA256."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
import threading
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
meta = json.loads((ROOT/"protocol/model_snapshot.json").read_text())
dest = ROOT/".models/Qwen3-1.7B"
lock = threading.Lock()
jobs = []
files = {}
hashes = []
chunk_size = 16*2**20
for item in meta['weight_files']:
    name, size = item['rfilename'], item['size']
    path = dest/name
    if path.exists() and path.stat().st_size == size:
        digest = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
        assert digest == item['lfs']['sha256'], (name, 'existing weight checksum mismatch')
        hashes.append({'file': name, 'sha256': digest, 'bytes': size})
        continue
    part = path.with_name(name+'.part')
    statepath = dest/(name+'.ranges.json')
    if statepath.exists():
        state = json.loads(statepath.read_text())
    else:
        prefix = part.stat().st_size if part.exists() else 0
        state = {'prefix': prefix, 'done': []}
        # Persist the true prefix before preallocating the sparse output file.
        # Its final logical size must never be mistaken for downloaded bytes.
        statepath.write_text(json.dumps(state))
    fd = os.open(part, os.O_RDWR | os.O_CREAT)
    os.ftruncate(fd, size)
    files[name] = (fd, path, part, statepath, state, item)
    for start in range(state['prefix'], size, chunk_size):
        end = min(start+chunk_size, size)-1
        if start not in state['done']:
            jobs.append((name, start, end))


def transfer(job):
    name, start, end = job
    url = f"https://huggingface.co/{meta['id']}/resolve/{meta['sha']}/{name}?range_start={start}"
    expected = f"bytes {start}-{end}/{files[name][5]['size']}"
    last = None
    for attempt in range(8):
        try:
            req = urllib.request.Request(url, headers={'Range': f'bytes={start}-{end}'})
            with urllib.request.urlopen(req, timeout=90) as r:
                if r.status != 206 or r.headers.get('Content-Range') != expected:
                    raise RuntimeError('Range response does not match requested bytes')
                offset = start
                while data := r.read(1024*1024):
                    written = 0
                    while written < len(data):
                        written += os.pwrite(files[name][0], data[written:], offset+written)
                    offset += len(data)
                if offset != end+1:
                    raise RuntimeError('Short range download')
            with lock:
                state = files[name][4]
                state['done'].append(start)
                temp = files[name][3].with_suffix('.tmp')
                temp.write_text(json.dumps(state))
                temp.replace(files[name][3])
            return len(data) if data else end-start+1
        except Exception as e:
            last = type(e).__name__+': '+str(e)[:100]
            time.sleep(min(2**attempt, 12))
    raise RuntimeError(f'{name} range {start} failed: {last}')


if __name__ == '__main__':
    print(json.dumps({'ranges': len(jobs), 'workers': 16}), flush=True)
    with ThreadPoolExecutor(max_workers=16) as pool:
        for i, f in enumerate(as_completed([pool.submit(transfer,j) for j in jobs]), 1):
            f.result()
            if i % 8 == 0 or i == len(jobs):
                print(json.dumps({'completed_ranges':i, 'total_ranges':len(jobs)}), flush=True)
    for name, (fd, path, part, statepath, state, item) in files.items():
        os.fsync(fd)
        os.close(fd)
        digest = hashlib.file_digest(part.open('rb'), 'sha256').hexdigest()
        assert digest == item['lfs']['sha256'], (name, 'weight checksum mismatch')
        part.replace(path)
        hashes.append({'file': name, 'sha256': digest, 'bytes': path.stat().st_size})
    assert len(hashes) == len(meta['weight_files'])
    (ROOT/'protocol/weight_checksums.json').write_text(json.dumps(hashes, indent=2)+'\n')
    print('WEIGHTS_VERIFIED', flush=True)
