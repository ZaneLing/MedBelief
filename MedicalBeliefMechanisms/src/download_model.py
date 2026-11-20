"""Download public, revision-pinned model files. No API key or inference service."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
meta = json.loads((ROOT / "protocol/model_snapshot.json").read_text())
dest = ROOT / ".models" / "Qwen3-1.7B"
dest.mkdir(parents=True, exist_ok=True)
names = [x for x in meta["siblings"] if x.endswith((".json", ".txt", ".md")) or x == "LICENSE"]


def download(name):
    path = dest / name
    if path.exists() and path.stat().st_size:
        return {"file": name, "bytes": path.stat().st_size, "cached": True}
    temp = path.with_name(path.name + ".part")
    url = f"https://huggingface.co/{meta['id']}/resolve/{meta['sha']}/{name}"
    start = time.time()
    p = subprocess.run(["curl", "--silent", "--show-error", "--fail", "--location",
                        "--retry", "2", "--connect-timeout", "30", "--max-time", "1200",
                        "--output", str(temp), url], capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(f"Download failed for {name}: curl exit {p.returncode}")
    temp.rename(path)
    out = {"file": name, "bytes": path.stat().st_size, "seconds": round(time.time()-start, 2)}
    print(json.dumps(out), flush=True)
    return out


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(download, names))
    (ROOT / "protocol/model_files.json").write_text(json.dumps(results, indent=2)+"\n")
    subprocess.run([sys.executable, str(ROOT / "src/resume_weights.py")], check=True)
    print("DOWNLOAD_COMPLETE", flush=True)
