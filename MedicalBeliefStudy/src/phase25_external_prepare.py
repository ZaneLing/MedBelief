"""Source-preserving, rule-selected external diagnostic vignettes."""
import collections,hashlib,json,re
from phase23_prepare import ROOT,rank,dumpjsonl
from phase6_prepare import sha,write
DEST=ROOT/'data/external_medqa'
def main():
 raw=list(map(json.loads,(DEST/'test.jsonl').read_text().splitlines()));eligible=[];audit=[]
 for i,r in enumerate(raw):
  q=r['question'];reason=None;matches=list(re.finditer(r'(?:Which|What)\b[^.?!]*(?:most likely diagnosis|most probable diagnosis)[^.?!]*\?',q))
  if not matches:reason='not_explicit_diagnosis_question'
  elif matches[-1].end()!=len(q.rstrip()):reason='trailing_text_after_question'
  elif not re.fullmatch(r'(?:Which of the following|What) is (?:the )?(?:most likely|most probable) diagnosis\b[^.?!]*\?',matches[-1].group()):reason='question_not_direct_diagnosis'
  elif re.search(r'image|photograph|figure|picture|illustrat|shown|depicted|table below|table above',q,re.I):reason='possible_external_visual_reference'
  elif any('"' in s or '\n' in s or len(s)>180 for s in r['options'].values()):reason='complex_option_string'
  else:
   m=matches[-1];stem=q[:m.start()].strip();question=q[m.start():].strip();sentences=re.split(r'(?<=[.!?])\s+(?=[A-Z])',stem)
   assert '.' not in question and question.count('?')==1
   if not 3<=len(sentences)<=16:reason='sentence_count_outside_3_16'
   elif len(q)>3500:reason='long_vignette'
   elif re.search(r'\b(?:Dr|Mr|Mrs|Ms)\.',stem):reason='abbreviation_split_ambiguity'
   else:
    assert re.sub(r'\s+',' ',stem)==re.sub(r'\s+',' ',' '.join(sentences));cid=f'medqa_test_{i:04d}';eligible.append(dict(case_id=cid,source_index=i,question=q,diagnostic_question=question,evidence_sentences=sentences,candidate_diseases=list(r['options'].values()),source_options=r['options'],gold_disease=r['answer'],answer_idx=r['answer_idx'],family='external_exam',source_split='test',meta_info=r['meta_info']))
  audit.append({'source_index':i,'eligible':reason is None,'excluded_reason':reason})
 chosen=sorted(eligible,key=lambda c:rank(c['case_id']+':external'))[:100];jobs=[]
 for c in chosen:
  T=len(c['evidence_sentences']);wrong=next(d for d in sorted(c['candidate_diseases'],key=lambda d:rank(c['case_id']+d)) if d!=c['gold_disease'])
  for t in range(1,T+1):jobs.append(dict(job_id=c['case_id']+f'_base_t{t:02d}',case_id=c['case_id'],round=t,last_round=T,condition='base',sentences=c['evidence_sentences'][:t],question=c['diagnostic_question'],candidate_diseases=c['candidate_diseases']))
  for cond,ss in [('reverse',list(reversed(c['evidence_sentences']))),('shuffle',sorted(c['evidence_sentences'],key=lambda x:rank(c['case_id']+x))),('wrong_history',c['evidence_sentences'])]:jobs.append(dict(job_id=c['case_id']+'_'+cond,case_id=c['case_id'],round=T,last_round=T,condition=cond,sentences=ss,question=c['diagnostic_question'],candidate_diseases=c['candidate_diseases'],prior_disease=wrong if cond=='wrong_history' else None))
 dumpjsonl(DEST/'cases.private.jsonl',chosen);dumpjsonl(DEST/'jobs.jsonl',jobs);dumpjsonl(DEST/'selection_audit.jsonl',audit);write(DEST/'manifest.json',dict(source_sha256=sha(DEST/'test.jsonl'),source_rows=len(raw),eligible=len(eligible),selected=len(chosen),unique_source_answers=len({c['gold_disease'] for c in chosen}),prefixes=sum(len(c['evidence_sentences']) for c in chosen),updates=sum(len(c['evidence_sentences'])-1 for c in chosen),jobs=len(jobs),exclusion_counts=dict(collections.Counter(r['excluded_reason'] for r in audit if r['excluded_reason'])),script_sha256=sha(__file__),protocol_sha256=sha(ROOT/'research_v3/BUILDING_PLAN.md'),api_cost_usd=0));print((DEST/'manifest.json').read_text())
if __name__=='__main__':main()
