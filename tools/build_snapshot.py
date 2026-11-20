"""Build an ACL-focused snapshot from the original workspace, without changing it."""
from pathlib import Path
import argparse,hashlib,json,shutil,tarfile,collections,time

def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--dest',type=Path,required=True);a=ap.parse_args();src=a.source.resolve();dst=a.dest.resolve();assert src!=dst
 for name in ['artifacts','.artifacts','docs']: (dst/name).mkdir(parents=True,exist_ok=True)
 skip={'.git','.runtime','.runtime_mlx','.models','.deps','__pycache__','.pytest_cache','.venv','.cache','node_modules'};rows=[];excluded=collections.Counter();pending=collections.defaultdict(list)
 acl_runs=lambda n:n.startswith('belief_v4') or n in ['structural_v1','structural_v2']
 for project in ['MedicalBeliefStudy','MedicalBeliefMechanisms','MedicalBelief1_7B','MedicalBeliefTrajectories','ClinicalBelief']:
  for p in sorted((src/project).rglob('*')):
   rel=p.relative_to(src);parts=rel.parts
   if any(x in skip or x.startswith('.runtime') or x=='.tools' for x in parts) or p.name=='.DS_Store' or p.name.startswith('.env') or p.suffix=='.pyc':continue
   if not p.is_file() or p.is_symlink():continue
   if 'deliverables' in parts:excluded['duplicate_delivery_archives']+=p.stat().st_size;continue
   kind='git';group=None
   if project=='MedicalBeliefStudy':
    if len(parts)>2 and parts[1]=='runs':
     if not acl_runs(parts[2]):
      if p.name not in ['manifest.json','completion.json'] and p.suffix not in ['.py','.md']:excluded['pre_v08_raw_runs_not_in_acl_snapshot']+=p.stat().st_size;continue
     elif parts[2]=='structural_v2':
      if p.suffix=='.npz' and 'bridge' not in parts:kind='asset';group='current-v010'
     elif p.name not in ['manifest.json','completion.json'] and p.suffix not in ['.py','.md']:kind='asset';group='acl-evidence-v008-v009'
    if len(parts)>2 and parts[1]=='data' and ('raw' in parts or 'ddx_classifier_expansion' in parts or any('rejected' in x for x in parts) or p.stat().st_size>40*2**20):kind='asset';group='source-data'
    if parts[1]=='results' and p.suffix in ['.npz','.joblib','.gz']:kind='asset';group='historical-analysis-arrays'
   elif project in ['MedicalBeliefMechanisms','MedicalBelief1_7B'] and len(parts)>2 and parts[1]=='runs':
    if p.name not in ['manifest.json','completion.json'] and p.suffix not in ['.py','.md']:excluded['pre_v08_predecessor_raw_runs_not_in_acl_snapshot']+=p.stat().st_size;continue
   elif project=='ClinicalBelief':
    if parts[1] in ['models','runs']:excluded['separate_clinicalbelief_models_runs']+=p.stat().st_size;continue
    if parts[1]=='data' and p.stat().st_size>5*2**20:kind='asset';group='source-data'
   if p.stat().st_size>40*2**20:kind='asset';group=group or 'historical-analysis-arrays'
   item=dict(path=rel.as_posix(),bytes=p.stat().st_size,sha256=digest(p),storage=kind)
   if kind=='git':
    q=dst/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
   else:pending[group].append((p,item))
   rows.append(item)
 print(json.dumps(dict(copied_git=sum(r['storage']=='git' for r in rows),artifact_files=sum(r['storage']=='asset' for r in rows))),flush=True)
 assets=[]
 for group,entries in pending.items():
  chunks=[];chunk=[];size=0
  for p,item in entries:
   if chunk and size+item['bytes']>768*2**20:chunks.append(chunk);chunk=[];size=0
   chunk.append((p,item));size+=item['bytes']
  if chunk:chunks.append(chunk)
  for i,chunk in enumerate(chunks,1):
   name=f'{group}-{i:03d}.tar.gz';out=dst/'.artifacts'/name
   with tarfile.open(out,'w:gz',compresslevel=1) as tf:
    for p,item in chunk:tf.add(p,arcname=item['path'],recursive=False);item['asset']=name
   z=dict(name=name,group=group,bytes=out.stat().st_size,sha256=digest(out),files=len(chunk));assets.append(z);print(json.dumps(z),flush=True)
 manifest=dict(schema_version=1,created='2026-11-20',repo='ZaneLing/MedBelief',release_tag='acl-v0.10-snapshot-20261120',scope='Current ACL evidence v0.8–v0.10, all paper/report/code history, frozen data and predecessor source dependencies. Pre-v0.8 raw activation caches excluded; models and environments reinstalled.',files=rows,assets=assets,excluded_bytes=dict(excluded),api_cost_usd=0)
 (dst/'artifacts/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');(dst/'artifacts/SHA256SUMS').write_text(''.join(f'{x["sha256"]}  {x["name"]}\n' for x in assets));print(json.dumps(dict(complete=True,files=len(rows),assets=len(assets),git_bytes=sum(r['bytes'] for r in rows if r['storage']=='git'),asset_bytes=sum(x['bytes'] for x in assets))),flush=True)
if __name__=='__main__':main()
