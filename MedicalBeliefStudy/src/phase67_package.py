"""Package reports, plots, scores, frozen cases and transitive source dependencies."""
from pathlib import Path
import ast,json,hashlib,zipfile,re
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 assert json.loads((ROOT/'research_v4/FINAL_VALIDATION.json').read_text())['complete']
 files=set();add=lambda p:files.add(p) if p.is_file() else None
 for folder in [ROOT/'research_v4',ROOT/'acl_paper/v08_multisource']:
  for p in folder.rglob('*'):
   if p.is_file() and '__pycache__' not in p.parts and p.name!='package.log':add(p)
 for folder in sorted((ROOT/'results').iterdir()):
  if folder.is_dir() and any(folder.name.startswith(f'{i:02d}_') for i in range(32,42)):
   for p in folder.rglob('*'):add(p)
 for p in (ROOT/'data/belief_v4').iterdir():add(p)
 for p in (ROOT/'data/belief_v4/raw').glob('download_stage*.json'):add(p)
 add(ROOT/'research_v3/RELATED_WORK_POSITION.md')
 runnames=['belief_v4','belief_v4_4b','belief_v4_layer_trajectories','belief_v4_routes_1.7b','belief_v4_routes_4b','belief_v4_module_readout','belief_v4_final_mlp','belief_v4_names_1.7b','belief_v4_names_4b']
 for name in runnames:
  for p in (ROOT/'runs'/name).rglob('*'):
   if p.is_file() and p.suffix in ['.json','.py']:add(p)
 # Include document-linked historical evidence so the portable reports have
 # no dangling local references. Directory links refer to their bundled subset.
 todo=[p for p in files if p.suffix=='.md'];seen_docs=set()
 while todo:
  p=todo.pop()
  if p in seen_docs:continue
  seen_docs.add(p)
  for u in re.findall(r'\]\(([^)]+)\)',p.read_text()):
   if re.match(r'^(https?://|mailto:|#)',u):continue
   t=(p.parent/u.split('#',1)[0].strip('<>')).resolve()
   if t.is_file() and t not in files:
    assert t.is_relative_to(ROOT) and t.suffix not in ['.npz','.safetensors']
    add(t)
    if t.suffix=='.md':todo.append(t)
 # Include local import dependencies without bundling unrelated experiments.
 modules={p.stem:p for p in (ROOT/'src').glob('*.py')};todo=[p for p in modules.values() if p.name in ['belief_v4_core.py','phase_v4_finish.py'] or any(p.name.startswith('phase'+str(i)+'_') for i in range(38,69))]+[p for p in files if p.suffix=='.py' and p.parent==ROOT/'src'];seen=set()
 while todo:
  p=todo.pop()
  if p in seen:continue
  seen.add(p);add(p)
  for node in ast.walk(ast.parse(p.read_text())):
   names=[a.name.split('.')[0] for a in node.names] if isinstance(node,ast.Import) else [node.module.split('.')[0]] if isinstance(node,ast.ImportFrom) and node.module else []
   for n in names:
    if n in modules:todo.append(modules[n])
 readme=ROOT/'research_v4/BUNDLE_README.md'
 readme.write_text('# 结果与复现代码包\n\n先打开START_HERE.md，再看RESULTS_AND_STORY.md。\n\n本包包含：本轮论文稿、十个结果目录、全部病例图谱、PNG/PDF、患者级表格、代码分数、540例冻结病例与标签、输入/干预JSON记录、协议、校验文件和运行脚本及其本地依赖。\n\n本包不含模型权重、大体积逐层原始NPZ激活、重算均值NPZ、原始完整下载库或Python环境。本机原始文件继续保留。使用本包可查看和复算导出的统计；重跑需要按REPRODUCE.md配置环境和权重。某些内部数组分析需重跑模型或另拷贝原始runs。\n\n这不是整个服务器迁移项目的替代品；不要只复制此包就认为模型、GPU环境与所有激活都已迁移。\n')
 add(readme);dest=ROOT/'deliverables';dest.mkdir(exist_ok=True);archive=dest/'medical_beliefs_v08_results.zip'
 inventory=[dict(path=str(p.relative_to(ROOT.parent)),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(files)]
 with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(files):z.write(p,p.relative_to(ROOT.parent))
  z.writestr('MedicalBeliefStudy/CONTENTS.json',json.dumps(dict(kind='results_and_reproduction_sources',raw_activation_npz_included=False,model_weights_included=False,files=inventory),ensure_ascii=False,indent=2))
 with zipfile.ZipFile(archive) as z:assert z.testzip() is None
 result=dict(archive=str(archive),files=len(files)+1,bytes=archive.stat().st_size,sha256=sha(archive),zip_integrity_passed=True,raw_activations_included=False,model_weights_included=False)
 (dest/'PACKAGE_MANIFEST.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
