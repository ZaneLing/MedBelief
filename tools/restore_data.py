"""Restore the local medical research ZIP without overwriting changed files."""
import argparse, hashlib, json, shutil, zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
GROUPS = {'current': {'current-v010'}, 'acl': {'current-v010', 'acl-evidence-v008-v009'}, 'all': None}

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('zip_path', type=Path)
    ap.add_argument('--profile', choices=GROUPS, default='all')
    a = ap.parse_args()
    manifest = json.loads((ROOT / 'artifacts/manifest.json').read_text())
    package = json.loads((ROOT / 'artifacts/LOCAL_DATA_PACKAGE.json').read_text())
    assert a.zip_path.stat().st_size == package['bytes'] and digest(a.zip_path) == package['sha256'], 'The ZIP is incomplete or differs from the recorded package'
    expected = {r['path']: r for r in manifest['files']}
    groups = GROUPS[a.profile]
    selected = {p: r for p, r in expected.items() if groups is None or r['storage'] == 'git' or r['group'] in groups}
    restored = existing = 0
    with zipfile.ZipFile(a.zip_path) as z:
        names = z.namelist()
        assert len(names) == len(set(names)) and set(names) == set(expected) | {'MEDBELIEF_DATA_MANIFEST.json'}, 'Unexpected ZIP entries'
        assert json.loads(z.read('MEDBELIEF_DATA_MANIFEST.json')) == manifest, 'ZIP and repository manifests differ'
        for name, row in selected.items():
            assert not name.startswith('/') and '..' not in PurePosixPath(name).parts
            path = ROOT / name
            assert not path.is_symlink() and all(not p.is_symlink() for p in path.parents if p.is_relative_to(ROOT)), ('Symlink in destination', name)
            if path.exists():
                assert path.is_file() and path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], ('Refusing to overwrite a changed file', name)
                existing += 1
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(path.name + '.restore-part')
            with z.open(name) as source, tmp.open('wb') as out:
                shutil.copyfileobj(source, out, 8 * 1024 * 1024)
            assert tmp.stat().st_size == row['bytes'] and digest(tmp) == row['sha256'], ('Restored file mismatch', name)
            tmp.replace(path)
            restored += 1
            if restored % 5000 == 0:
                print(json.dumps(dict(restored=restored, already_identical=existing)), flush=True)
    print(json.dumps(dict(complete=True, profile=a.profile, files=len(selected), restored=restored, already_identical=existing)))

if __name__ == '__main__':
    main()
