"""A new, source-preserving cohort disjoint from all 540 v4 experiment cases."""
import collections,hashlib,json,sys
from pathlib import Path
from phase55_text_audit import TASK,MISSING,PROCEDURE
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/belief_v5';RUN=ROOT/'runs/structural_v2';DOC=ROOT/'research_v6_adapters'
def read(p):return json.loads(p.read_text())
def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rank(s):return hashlib.sha256(('structure2-20261120:'+s).encode()).hexdigest()
def cases():return list(map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines()))
def main():
    assert not (DATA/'manifest.json').exists(),'Cohort frozen; do not overwrite'
    for p in [DATA,RUN,DOC,ROOT/'acl_paper/v10_adapters']:p.mkdir(parents=True,exist_ok=True)
    src=ROOT/'data/belief_v4';old={c['case_id'] for c in map(json.loads,(src/'cases.private.jsonl').read_text().splitlines())};pool=list(map(json.loads,(src/'eligible.unique.jsonl').read_text().splitlines()));out=[];audit=[]
    for c in pool:
        if c['case_id'] in old:continue
        bad=any(TASK.search(s) or MISSING.search(s) or PROCEDURE.search(s) or s.rstrip().endswith('According to the clinical vignette,') for s in c['sentences']);audit.append(dict(case_id=c['case_id'],strict_keep=not bad))
        if bad:continue
        out.append(c)
    selected=[]
    for ds in ['MedQA','MedMCQA']:
        rr=sorted([dict(c) for c in out if c['dataset']==ds],key=lambda c:rank(c['case_id']));assert len(rr)>=440
        for i,c in enumerate(rr[:440]):
            c['cohort']='train' if i<200 else 'development' if i<240 else 'confirmation'
            c['wrong_index']=min((k for k in range(4) if k!=c['gold_index']),key=lambda k:rank(c['case_id']+':wrong:'+str(k)));c['wrong_disease']=c['candidates'][c['wrong_index']];c['code_rotation']=int(rank(c['case_id']+':code')[:8],16)%4;c['mechanism_capture']=False;c['trajectory_capture']=False;selected.append(c)
    selected.sort(key=lambda c:(c['cohort'],rank(c['case_id']+':run')))
    (DATA/'cases.private.jsonl').write_text(''.join(json.dumps(c)+'\n' for c in selected))
    calibration=[]
    for ds in ['MedQA','MedMCQA']:calibration += sorted([c['case_id'] for c in selected if c['cohort']=='train' and c['dataset']==ds],key=lambda c:rank(c+':calibration'))[:32]
    manifest=dict(cases=880,source_cases={'MedQA':440,'MedMCQA':440},splits=dict(collections.Counter(c['cohort'] for c in selected)),calibration=calibration,source_unique_sha256=sha(src/'eligible.unique.jsonl'),old_cases_sha256=sha(src/'cases.private.jsonl'),cases_sha256=sha(DATA/'cases.private.jsonl'),source_sha256=sha(Path(__file__)),disjoint_from_old540=True,deduplication='Inherited global word+bigram TF-IDF cosine<0.90 from v4 preparation, including all old MedQA test questions and all source candidates.',api_cost_usd=0)
    write(DATA/'audit.json',audit);write(DATA/'manifest.json',manifest)
    structural=[dict(name='baseline'),dict(name='exit24',exit_layer=24),dict(name='exit20',exit_layer=20),dict(name='drop_tail4_keep28',drop_blocks=[24,25,26,27]),dict(name='drop_mlp4',drop_mlps=[24,25,26,28]),dict(name='mlp_width75',mlp_keep=.75),dict(name='mlp_width50',mlp_keep=.5),dict(name='late_mlp_width50',mlp_keep=.5,mlp_layers=list(range(17,29))),dict(name='attention_groups75',attention_keep_groups=6),dict(name='linear_old16',replace_mlps=[25,26],rank=16),dict(name='late_mlp_half',mlp_scale=.5,scale_layers=[25,26,27,28]),dict(name='contrast21_half',contrast_layer=21,contrast_strength=.5,plausibility=.1),dict(name='contrast21_full',contrast_layer=21,contrast_strength=1.,plausibility=.1)]
    write(RUN/'structural_candidates.json',structural);print(json.dumps(manifest,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
