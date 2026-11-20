"""Check local artifact links and package the verified v0.6 results, not model weights."""
import json,re,zipfile,hashlib
from pathlib import Path
from urllib.parse import unquote
from belief_v3_analysis import ROOT,read,dump,sha
def main():
 paper=ROOT/'acl_paper/v06_building';audit=read(ROOT/'results/27_building_synthesis/validation.json');qa=read(paper/'qa/visual_review.json');assert audit['verified'] and qa['reviewed'] and qa['pdf_sha256']==sha(paper/'main.pdf')
 dirs=[ROOT/'research_v3',paper]+[ROOT/'results'/d for d in ['23_new_patients','24_natural_update_causality','25_history_and_evidence','26_external_medqa','27_building_synthesis','28_new_4b_replication','29_external_internal_causality','30_role_binding']];missing=[];checked=0
 for folder in dirs:
  for p in folder.rglob('*.md'):
   for raw in re.findall(r'\]\(([^)]+)\)',p.read_text()):
    target=unquote(raw.strip().split('#')[0]);
    if not target or '://' in target:continue
    checked+=1
    if not (p.parent/target).exists():missing.append({'file':str(p.relative_to(ROOT)),'target':target})
 assert not missing,missing
 changes=[]
 for name,oldhash in audit['analysis_source_hashes'].items():
  current=sha(ROOT/'src'/name)
  if current!=oldhash:changes.append({'file':name,'audit_time_sha256':oldhash,'delivery_sha256':current})
 assert {v['file'] for v in changes}<={'phase33_paper.py','phase34_manuscript.py','phase35_release.py'},changes
 release=ROOT/'deliverables';release.mkdir(exist_ok=True);manifest=dict(complete=True,new_patients_or_vignettes=327,observation_conditions=4832,api_cost_usd=0,local_markdown_links_checked=checked,missing_links=missing,paper_pdf_sha256=sha(paper/'main.pdf'),visual_qa=qa,presentation_only_source_updates_after_numeric_audit=changes,scope='Paper, reports, per-case figures, derived scores and protocols; raw activation arrays and model weights remain in the project and are not in this result bundle.')
 dump(ROOT/'results/27_building_synthesis/delivery_manifest.json',manifest)
 top='''# 最新论文与实验结果（v0.6）

[先读这一页：用人话解释](research_v3/START_HERE.md) · [完整中文论文](acl_paper/v06_building/PAPER_ZH.md) · [英文论文PDF](acl_paper/v06_building/main.pdf) · [分阶段完整结果](research_v3/RESULTS_AND_STORY.md)

本轮新增327个患者/题目，159条完整证据轨迹、1173次证据更新；含4B配对复核、历史与证据背景、自然内部更新干预及独立48例复核。4832个观测/干预条件全部完成核验。API费用0美元。旧v0.5及此前结果保留在下方。

'''
 p=ROOT/'README.md';old=p.read_text();old=re.sub(r'^# 最新论文与实验结果（v0\.6）.*?(?=# 最新论文交付（v0\.5）)', '',old,flags=re.S);p.write_text(top+old)
 bundle=release/'medical_belief_v06_results_and_paper.zip';files=[]
 with zipfile.ZipFile(bundle,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=4) as z:
  z.writestr('MedicalBeliefStudy/README_BUNDLE.md','# 医学信念 v0.6 结果与论文\n\n先读research_v3/START_HERE.md。包含论文、逐阶段报告、全部病例图、派生分数与协议。原始激活和模型权重保留在完整项目，本包不含它们；此包用于阅读和复核结果，完整重跑请使用原项目。\n')
  for folder in dirs:
   for p in sorted(folder.rglob('*')):
    if p.is_file() and 'qa' not in p.relative_to(folder).parts and p.suffix not in ['.aux','.log','.out','.blg','.bbl']:
     rel=p.relative_to(ROOT);z.write(p,'MedicalBeliefStudy/'+str(rel));files.append(str(rel))
 with zipfile.ZipFile(bundle) as z:assert z.testzip() is None
 manifest.update(bundle=str(bundle.relative_to(ROOT)),bundle_files=len(files),bundle_bytes=bundle.stat().st_size,bundle_sha256=sha(bundle));dump(release/'medical_belief_v06_manifest.json',manifest);print(json.dumps(manifest,ensure_ascii=False),flush=True)
 marker=ROOT/'runs/belief_v3/delivery_compile_complete.json';state=read(marker);state.update(visual_qa_pending=False,visual_qa_complete=True,result_bundle=str(bundle.relative_to(ROOT)));dump(marker,state)
if __name__=='__main__':main()
