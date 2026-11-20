"""Source-preserving, outcome-blind diagnosis cohort for belief v4."""
from pathlib import Path
import collections, csv, hashlib, json, re, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.deps'))
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

DEST=ROOT/'data/belief_v4'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rank(s):return hashlib.sha256(('belief-v4-20261120:'+s).encode()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def jsonl(p,rr):p.write_text(''.join(json.dumps(r,ensure_ascii=True)+'\n' for r in rr))
def norm(s):return re.sub(r'[^a-z0-9]+',' ',s.lower()).strip()
def parquet_rows(p):
    decoded=p.parent/'decoded'/(p.stem+'.jsonl')
    if decoded.exists():
        with decoded.open() as f:return [json.loads(line) for line in f]
    import pyarrow.parquet as pq
    return pq.read_table(p).to_pylist()

def split_question(q):
    # Only direct diagnostic questions, no mechanism/treatment/next-test tasks.
    starts=list(re.finditer(r'(?<![A-Za-z])(?:Which|What)\b[^.?!\n]{0,140}\bdiagnosis\b[^.?!\n]{0,80}[?:]?\s*$',q,re.I))
    if not starts:
        starts=list(re.finditer(r'\b(?:The\s+)?(?:most\s+(?:likely|probable)|likely|probable|provisional)\s+diagnosis\s*(?:is|would be)?\s*[:?—-]*\s*$',q,re.I))
    if not starts:return None,'not_direct_diagnosis'
    m=starts[-1];ask=q[m.start():].strip();stem=q[:m.start()].strip()
    if re.search(r'which\s+(?:one\s+)?of\s+the\s+following',stem,re.I):return None,'task_question_fragment_in_evidence'
    # The word diagnosis also occurs in questions asking for tests, mechanisms,
    # associated findings or complications. Admit direct answer requests only.
    direct=re.match(r"^(?:Which(?: one)?(?: of the following)?|What)\s+(?:is|would be|could be|best describes|represents)\s+(?:(?:the|a|your|his|her|this|patient['’]s|most|likely|probable|appropriate|possible|clinical|underlying)\s+)*diagnosis\b",ask,re.I)
    statement=re.fullmatch(r'(?:the\s+)?(?:most\s+)?(?:likely|probable|provisional)\s+diagnosis\s*(?:(?:is|would be|could be)\s*)?[:?—–-]*\s*',ask,re.I)
    if not direct and not statement:return None,'not_direct_diagnostic_answer'
    if direct:
        tail=ask[direct.end():].strip()
        if tail and not re.match(r'^(?:[?:—–-]|in\b|for\b|of\b|based on\b)',tail,re.I):return None,'diagnostic_followup_not_answer'
    if re.search(r'\b(?:test|investigation|confirm|management|treatment|mechanism|except|least|not|next step)\b',ask,re.I):return None,'non_diagnosis_target'
    if re.search(r'\b(?:image|photograph|figure|picture|illustration|shown|depicted|table below|table above)\b',q,re.I):return None,'external_visual_reference'
    if re.search(r'following findings? (?:is|are) (?:seen|observed)',q,re.I):return None,'missing_referenced_finding'
    if not 100<=len(stem)<=2800:return None,'stem_length'
    if re.search(r'\b(?:Dr|Mr|Mrs|Ms)\.',stem):return None,'ambiguous_sentence_abbreviation'
    sentences=re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])',stem)
    if not 2<=len(sentences)<=16:return None,'sentence_count'
    if any(len(s)<8 for s in sentences):return None,'short_sentence_fragment'
    assert norm(' '.join(sentences))==norm(stem)
    return (stem,ask,sentences),None

def load():
    allrows=[]
    for p in sorted((DEST/'raw').glob('medqa_*.jsonl')):
        split=p.stem.split('_',1)[1]
        for i,r in enumerate(map(json.loads,p.read_text().splitlines())):
            opts=list(r['options'].values());assert r['options'][r['answer_idx']]==r['answer']
            allrows.append(dict(dataset='MedQA',case_id=f'medqa_{split}_{i:05d}',source_file=p.name,source_index=i,source_split=split,question=r['question'],candidates=opts,gold_index=opts.index(r['answer']),subject=r.get('meta_info','unknown')))
    for p in sorted((DEST/'raw').glob('medmcqa_*.parquet')):
        split=p.name.split('_',1)[1].split('-')[0]
        if split=='test':continue
        for i,r in enumerate(parquet_rows(p)):
            if r['choice_type']!='single':continue
            assert 0<=r['cop']<4
            allrows.append(dict(dataset='MedMCQA',case_id=f'medmcqa_{split}_{r["id"]}',source_file=p.name,source_index=i,source_split=split,question=r['question'],candidates=[r[k] for k in ['opa','opb','opc','opd']],gold_index=int(r['cop']),subject=r['subject_name'],source_id=r['id']))
    for p in sorted((DEST/'raw').glob('mmlu_*.parquet')):
        base=p.stem.split('-')[0][5:];subject,split=base.rsplit('_',1)
        for i,r in enumerate(parquet_rows(p)):
            allrows.append(dict(dataset='MMLU',case_id=f'mmlu_{subject}_{split}_{i:04d}',source_file=p.name,source_index=i,source_split=split,question=r['question'],candidates=list(r['choices']),gold_index=int(r['answer']),subject=subject))
    return allrows

def main():
    assert not (DEST/'manifest.json').exists(),'Frozen cohort already exists; use a new version for changes'
    assert (DEST/'raw/medmcqa_train-00000-of-00001.parquet').exists(),'Wait for the hash-verified train download'
    raw=load();eligible=[];audit=[]
    for r in raw:
        got,reason=split_question(r['question'])
        opts=r['candidates']
        if reason is None and (len(opts)!=4 or len(set(map(norm,opts)))!=4 or any(not d or len(d)>160 or '"' in d or '\n' in d for d in opts)):reason='candidate_format'
        if reason is None and any(re.search(r'\b(?:all of (?:the )?above|none of (?:the )?above|both [abcd]|[abcd] and [abcd])\b',d,re.I) for d in opts):reason='relational_candidate'
        if reason is None:
            stem,ask,ss=got;r.update(stem=stem,diagnostic_question=ask,sentences=ss,gold_disease=opts[r['gold_index']]);eligible.append(r)
        audit.append(dict(case_id=r['case_id'],dataset=r['dataset'],eligible=reason is None,reason=reason))
    # Compare against all old MedQA questions, not only the previously selected 87.
    old=[dict(case_id=f'old_medqa_test_{i:04d}',stem=r['question']) for i,r in enumerate(map(json.loads,(ROOT/'data/external_medqa/test.jsonl').read_text().splitlines()))]
    # Prioritise MMLU so overlapping exam questions are removed from later sources.
    priority={'MMLU':0,'MedMCQA':1,'MedQA':2};eligible.sort(key=lambda r:(priority[r['dataset']],rank(r['case_id'])))
    alltext=[r['stem'] for r in old+eligible]
    vec=TfidfVectorizer(lowercase=True,ngram_range=(1,2),min_df=1,sublinear_tf=True)
    X=vec.fit_transform(alltext);accepted=list(range(len(old)));unique=[];duplicates=[]
    # Single global TF-IDF vocabulary; threshold is frozen before outcomes.
    for k,r in enumerate(eligible,start=len(old)):
        vals=(X[k]@X[accepted].T).toarray()[0];j=int(vals.argmax());v=float(vals[j]);oi=accepted[j]
        if v>=.90:
            other=(old+eligible)[oi];duplicates.append(dict(case_id=r['case_id'],dataset=r['dataset'],matched_case=other['case_id'],cosine=v));continue
        accepted.append(k);unique.append(r)
    selected=[];targets={'MedQA':300,'MedMCQA':200,'MMLU':100}
    for ds,cap in targets.items():
        pool=sorted([r for r in unique if r['dataset']==ds],key=lambda r:rank(r['case_id']+':sample'))
        chosen=pool[:cap]
        for i,c in enumerate(chosen):
            # Partition without looking at inference; 2/3 reserved confirmation.
            c['cohort']='development' if i%3==0 else 'confirmation'
            wrong=sorted((k for k in range(4) if k!=c['gold_index']),key=lambda k:rank(c['case_id']+':wrong:'+str(k)))[0]
            c['wrong_index']=wrong;c['wrong_disease']=c['candidates'][wrong]
            c['code_rotation']=int(rank(c['case_id']+':code')[:8],16)%4
            c['mechanism_capture']=False;c['trajectory_capture']=False
        # Up to 32 cases per source, balanced development/confirmation.
        for cohort in ['development','confirmation']:
            subset=[c for c in chosen if c['cohort']==cohort]
            for c in sorted(subset,key=lambda r:rank(r['case_id']+':mechanism'))[:16]:c['mechanism_capture']=True;c['trajectory_capture']=True
        selected.extend(chosen)
    selected.sort(key=lambda r:(r['cohort'],r['dataset'],rank(r['case_id']+':run')))
    jsonl(DEST/'cases.private.jsonl',selected);jsonl(DEST/'eligible.unique.jsonl',unique);jsonl(DEST/'selection_audit.jsonl',audit);jsonl(DEST/'duplicates.jsonl',duplicates)
    public=[{k:v for k,v in r.items() if k not in ['gold_index','gold_disease','wrong_index','wrong_disease']} for r in selected];jsonl(DEST/'cases.public.jsonl',public)
    summary=dict(created_date='2026-11-20',raw_rows_by_dataset=dict(collections.Counter(r['dataset'] for r in raw)),eligible_before_dedup=dict(collections.Counter(r['dataset'] for r in eligible)),unique_eligible=dict(collections.Counter(r['dataset'] for r in unique)),selected=dict(collections.Counter(r['dataset'] for r in selected)),patients=len(selected),cohorts=dict(collections.Counter(r['cohort'] for r in selected)),mechanism_cases=sum(r['mechanism_capture'] for r in selected),trajectory_prefixes=sum(len(r['sentences']) for r in selected if r['trajectory_capture']),unique_source_answers=len(set(norm(r['gold_disease']) for r in selected)),duplicates_removed=len(duplicates),similarity_threshold=.90,old_medqa_rows_compared=len(old),question_exclusions=dict(collections.Counter(r['reason'] for r in audit if r['reason'])),raw_sha256={p.name:sha(p) for p in sorted((DEST/'raw').glob('*')) if p.suffix in ['.parquet','.jsonl']},selection_source_sha256=sha(__file__),cases_sha256=sha(DEST/'cases.private.jsonl'),protocol_sha256=sha(ROOT/'research_v4/PROTOCOL.md'),api_cost_usd=0)
    write(DEST/'manifest.json',summary)
    with (DEST/'selection_review.md').open('w') as f:
        f.write('# 推理前选样审核\n\n仅诊断题；原始句子保留，解释与标准答案不进入患者事实。\n\n')
        for ds in targets:
            for c in [r for r in selected if r['dataset']==ds][:6]:
                f.write(f'## {c["case_id"]}\n\n'+c['question']+'\n\n'+str(c['candidates'])+'\n\n来源答案：'+c['gold_disease']+'\n\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
