"""Build a verified, local-only ZIP of medical research files from the source workspace."""
import argparse, hashlib, json, os, re, time, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ['MedicalBeliefStudy', 'MedicalBeliefMechanisms', 'MedicalBelief1_7B', 'MedicalBeliefTrajectories', 'ClinicalBelief']
SKIP = {'.git', '.models', '.deps', '__pycache__', '.pytest_cache', '.venv', '.cache', '.tools', 'node_modules', 'deliverables'}
TEXT = {'.json', '.jsonl', '.md', '.txt', '.csv', '.tsv', '.py', '.sh', '.toml', '.yaml', '.yml', '.log', '.rst', '.bib', '.tex'}
CREDENTIAL = re.compile(rb'(?<![A-Za-z0-9])(?:sk-or-v1-[a-f0-9]{40,}|sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{40,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|AKIA[0-9A-Z]{16})')

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    src, out = a.source.resolve(), a.output.resolve()
    assert not out.exists(), 'Refusing to overwrite an existing delivery ZIP'
    old = json.loads((ROOT / 'artifacts/manifest.json').read_text())
    known = {r['path']: r for r in old['files']}
    groups = {z['name']: z['group'] for z in old.get('assets', [])}
    paths = []
    for project in PROJECTS:
        for base, dirs, files in os.walk(src / project):
            dirs[:] = sorted(d for d in dirs if d not in SKIP and not d.startswith(('.runtime', '.venv')) and not (Path(base) / d).is_symlink())
            for name in sorted(files):
                p = Path(base) / name
                if p.is_symlink() or name.startswith('.env') or name == '.DS_Store' or p.suffix == '.pyc':
                    continue
                paths.append(p)
    rows = []
    tmp = out.with_suffix(out.suffix + '.building')
    started = time.time()
    with zipfile.ZipFile(tmp, 'w', allowZip64=True) as z:
        for i, p in enumerate(paths, 1):
            rel = p.relative_to(src).as_posix()
            previous = known.get(rel)
            group = previous.get('group', groups.get(previous.get('asset'), 'git' if previous['storage'] == 'git' else 'earlier-raw')) if previous else 'earlier-raw'
            info = zipfile.ZipInfo.from_file(p, arcname=rel)
            info.compress_type = zipfile.ZIP_DEFLATED if p.suffix.lower() in TEXT else zipfile.ZIP_STORED
            info._compresslevel = 1
            h, count, tail = hashlib.sha256(), 0, b''
            with p.open('rb') as source, z.open(info, 'w', force_zip64=True) as dest:
                for block in iter(lambda: source.read(8 * 1024 * 1024), b''):
                    if p.suffix.lower() in TEXT:
                        assert not CREDENTIAL.search(tail + block), ('Credential-shaped value found; package stopped', rel)
                        tail = block[-256:]
                    h.update(block)
                    count += len(block)
                    dest.write(block)
            row = dict(path=rel, bytes=count, sha256=h.hexdigest(), storage='git' if previous and previous['storage'] == 'git' else 'zip', group=group)
            if previous:
                assert row['sha256'] == previous['sha256'] and count == previous['bytes'], ('Source changed since frozen snapshot', rel)
            rows.append(row)
            if i % 5000 == 0:
                print(json.dumps(dict(packaged=i, total=len(paths), seconds=round(time.time()-started))), flush=True)
        assert set(known).issubset({r['path'] for r in rows}), 'An existing scientific snapshot file was omitted'
        manifest = dict(schema_version=2, created='2026-11-20', repo='ZaneLing/MedBelief', delivery='local_zip', zip_name=out.name,
                        scope='All scientific files in the five medical research projects, including early raw runs and ClinicalBelief fitted models; excludes public base weights, environments, credentials, platform caches and duplicate delivery archives.',
                        files=rows, api_cost_usd=0)
        manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2) + '\n'
        z.writestr('MEDBELIEF_DATA_MANIFEST.json', manifest_text, compress_type=zipfile.ZIP_DEFLATED, compresslevel=1)
    # Read every ZIP entry back and check its uncompressed bytes, not only the ZIP CRC.
    with zipfile.ZipFile(tmp) as z:
        assert len(z.infolist()) == len(rows) + 1
        for i, row in enumerate(rows, 1):
            h, size = hashlib.sha256(), 0
            with z.open(row['path']) as f:
                for b in iter(lambda: f.read(8 * 1024 * 1024), b''):
                    h.update(b); size += len(b)
            assert size == row['bytes'] and h.hexdigest() == row['sha256'], ('ZIP round-trip mismatch', row['path'])
            if i % 10000 == 0:
                print(json.dumps(dict(verified_zip_entries=i, total=len(rows))), flush=True)
    tmp.replace(out)
    (ROOT / 'artifacts/manifest.json').write_text(manifest_text)
    report = dict(complete=True, filename=out.name, bytes=out.stat().st_size, sha256=sha(out), scientific_files=len(rows),
                  scientific_bytes=sum(r['bytes'] for r in rows), git_files=sum(r['storage']=='git' for r in rows),
                  all_entry_sha256_verified=True, credential_pattern_hits=0, original_source_unchanged=True,
                  excludes_public_base_model_weights_and_environments=True, api_cost_usd=0)
    (ROOT / 'artifacts/LOCAL_DATA_PACKAGE.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    (ROOT / 'artifacts/SHA256SUMS').write_text(report['sha256']+'  '+out.name+'\n')
    out.with_name(out.name+'.sha256').write_text(report['sha256']+'  '+out.name+'\n')
    print(json.dumps(report), flush=True)

if __name__ == '__main__':
    main()
