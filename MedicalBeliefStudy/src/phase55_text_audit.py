"""Text-only post-run quality audit, retaining the frozen cohort and all outcomes."""
import json,re,collections,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data/belief_v4'
# These patterns are applied to source text, without consulting model outcomes.
TASK=re.compile(r'(?i)^(?:based on (?:these findings|this history and physical examination|his age and overall epidemiology)|of the following options|given the following options|give your)[, .]*$')
MISSING=re.compile(r'(?i)(?:findings are attached|following is the audiometry repo|the following ECG changes are seen|shows following skin lesion|following are the gross and histological findings|x-ray reveals the following|figures A and B)')
PROCEDURE=re.compile(r'(?i)^(?:CT scan was taken|X-ray abdomen was done|Ultrasound of scrotum was performed|A brain biopsy was also taken and HPE examination was done)[.]*$')
def main():
 cases=list(map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines()));rows=[];details=[]
 for c in cases:
  task=[i+1 for i,s in enumerate(c['sentences']) if TASK.search(s)];missing=[i+1 for i,s in enumerate(c['sentences']) if MISSING.search(s)];proc=[i+1 for i,s in enumerate(c['sentences']) if PROCEDURE.search(s)]
  mixed=[i+1 for i,s in enumerate(c['sentences']) if s.rstrip().endswith('According to the clinical vignette,')]
  row=dict(case_id=c['case_id'],dataset=c['dataset'],cohort=c['cohort'],mechanism_capture=c['mechanism_capture'],task_only_rounds=task,missing_material_rounds=missing,procedure_without_report_rounds=proc,mixed_task_tail_rounds=mixed,strict_keep=not (task or missing or proc or mixed));rows.append(row)
  if not row['strict_keep']:details.append(dict(**row,sentences=c['sentences'],diagnostic_question=c['diagnostic_question']))
 (DATA/'text_audit.json').write_text(json.dumps(dict(status='post_run_text_only_sensitivity',patients=len(cases),strict_keep=sum(r['strict_keep'] for r in rows),rows=rows),ensure_ascii=False,indent=2)+'\n')
 (DATA/'text_audit_review.json').write_text(json.dumps(details,ensure_ascii=False,indent=2)+'\n')
 print('strict keep',sum(r['strict_keep'] for r in rows),'flagged',len(details),collections.Counter(c['dataset'] for c in details));print('mechanism flagged',[(r['case_id'],r['cohort']) for r in rows if r['mechanism_capture'] and not r['strict_keep']])
 for r in details:print(r['case_id'],{k:r[k] for k in ['task_only_rounds','missing_material_rounds','procedure_without_report_rounds','mixed_task_tail_rounds']})
if __name__=='__main__':main()
