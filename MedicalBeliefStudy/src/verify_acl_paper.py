"""Validate paper artefacts and exhaustive case synthesis; render every PDF page."""
import csv,json,re,hashlib
from pathlib import Path
import fitz
from PIL import Image,ImageDraw
from phase14_analyze import ROOT,RUN,cases
import numpy as np
P=ROOT/'acl_paper/submission';D=ROOT/'results/22_paper_case_synthesis'
s=json.loads((D/'summary.json').read_text());rows=list(csv.DictReader((D/'trajectory_categories.csv').open()));events=list(csv.DictReader((D/'all_rounds.csv').open()));_,test=cases();deep={c['case_id']:c for c in test if c['deep_capture']};assert len(rows)==72 and len(events)==624 and len(deep)==24
for v in ['append','panel','4b']:assert sum(s['trajectory_categories'][v].values())==24
for v in ['append','panel']:assert sum(s['endpoint_joint24'][v].values())==120
scores=np.load(ROOT/'results/14_fixed_panel/prefix_readout_scores.npz');big=np.load(ROOT/'results/18_model_replication/prefix_readout_scores.npz');ds=json.loads((RUN/'manifest.json').read_text())['candidate_diseases'];cl=scores['classes'].tolist()
for r in events:
 c=deep[r['case_id']];v=r['view'];t=int(r['round']);run=ROOT/'runs/belief_v2_4b' if v=='4b' else RUN;view='append' if v=='4b' else v;ob=json.loads((run/'observations'/f"{r['case_id']}_{view}_base_t{t:02d}.json").read_text());q=np.array(ob['q_sequence']);S=big[r['case_id']] if v=='4b' else scores[f"{r['case_id']}_{v}"];assert r['top']==ds[q.argmax()] and r['probe']==cl[S[t,-1].argmax()];assert abs(float(r['gold_support'])-q[ds.index(c['gold_disease'])])<1e-10
 group=c['initial_question_group'] if t==0 else c['orders']['base'][t-1];facts='; '.join(f"{f['question_en']} {f['answer_en']}" for f in c['explicit_evidence_groups'][group]);assert r['new_evidence']==facts
tex=(P/'main.tex').read_text()+(P/'sections/appendix.tex').read_text();bib=(P/'references.bib').read_text();keys=set(re.findall(r'@\w+\{([^,]+),',bib));cit=set(k.strip() for group in re.findall(r'\\cite\w*\{([^}]+)\}',tex) for k in group.split(','));assert cit<=keys
log=(P/'main.log').read_text();assert 'undefined citations' not in log.lower() and 'undefined references' not in log.lower();overfull=[x for x in log.splitlines() if 'Overfull' in x];assert not overfull,overfull
aux=(P/'main.aux').read_text();start=int(re.search(r'\\newlabel\{app:repro\}\{\{A\}\{(\d+)\}',aux).group(1));doc=fitz.open(P/'main.pdf');whole='\n'.join(p.get_text() for p in doc);assert '??' not in whole
conclusion_page=next(i+1 for i,p in enumerate(doc) if re.search(r'9\s+Conclusion',p.get_text()));assert conclusion_page<=8
for cid in deep:assert cid in whole or cid.replace('_','') in whole.replace('_','')
main=fitz.open();main.insert_pdf(doc,from_page=0,to_page=start-2);main.save(P/'paper.pdf');supp=fitz.open();supp.insert_pdf(doc,from_page=start-1);supp.save(P/'supplement.pdf')
qa=P/'qa';thumbs=[];bad=[]
for old in list(qa.glob('page_*.png'))+list(qa.glob('contact_*.png')):old.unlink()
for i,p in enumerate(doc):
 pix=p.get_pixmap(matrix=fitz.Matrix(1,1));pix.save(qa/f'page_{i+1:02d}.png');im=Image.open(qa/f'page_{i+1:02d}.png').convert('RGB');im.thumbnail((297,420));thumb=Image.new('RGB',(315,448),'#eaeaea');thumb.paste(im,((315-im.width)//2,8));ImageDraw.Draw(thumb).text((12,430),f'Page {i+1}',fill='black');thumbs.append(thumb)
 for b in p.get_text('blocks'):
  if b[0]<0 or b[1]<0 or b[2]>p.rect.width+.5 or b[3]>p.rect.height+.5:bad.append((i+1,b[:4]))
assert not bad,bad
for offset in range(0,len(thumbs),6):
 sheet=Image.new('RGB',(945,896),'white')
 for j,im in enumerate(thumbs[offset:offset+6]):sheet.paste(im,((j%3)*315,(j//3)*448))
 sheet.save(qa/f'contact_{offset//6+1:02d}.png')
# Check newly introduced local markdown links.
broken=[]
mds=[ROOT/'acl_paper/10_FULL_PAPER_ZH.md',ROOT/'acl_paper/11_ARGUMENT_ARCHITECTURE.md',D/'RESULTS.md',*(D/'cases').glob('*.md')]
for p in mds:
 for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  if '://' not in link and not link.startswith('#') and not (p.parent/link.split('#')[0]).exists():broken.append((str(p),link))
assert not broken,broken
out={'complete':True,'new_patients':0,'new_model_calls':0,'deep_cases':24,'deep_diseases':17,'case_condition_summaries':72,'round_records_verified_against_raw':624,'endpoint_patients':120,'cited_primary_works':len(keys),'undefined_citations':False,'overfull_boxes':overfull,'main_content_conclusion_page':conclusion_page,'paper_with_references_pages':len(main),'supplement_pages':len(supp),'combined_pages':len(doc),'all_pages_rendered':True,'page_boundary_violations':bad,'broken_new_markdown_links':broken,'api_cost_usd':0,'pdf_sha256':hashlib.sha256((P/'main.pdf').read_bytes()).hexdigest()}
(qa/'validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
