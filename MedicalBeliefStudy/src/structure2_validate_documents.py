"""Check delivered local links and record a compact reproducibility inventory."""
import ast,re
from urllib.parse import unquote
from PIL import Image
from phase90_structure2_prepare import *

def main():
    dirs=[DOC,ROOT/'acl_paper/v10_adapters']+[ROOT/'results'/n for n in ['47_structure_search','48_adapter_training','49_structure_confirmation','50_structure_trajectories']];md=[p for d in dirs for p in d.rglob('*.md')];missing=[];links=0;figures=[];table_issues=[]
    for p in md:
        expected=None
        for lineno,line in enumerate(p.read_text().splitlines(),1):
            if line.startswith('|') and line.endswith('|'):
                count=len(re.split(r'(?<!\\)\|',line))-2
                if expected is None:expected=count
                elif count!=expected:table_issues.append(dict(file=str(p.relative_to(ROOT)),line=lineno,expected=expected,actual=count))
            else:expected=None
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
            target=target.strip('<>');target=target.split('#')[0]
            if not target or re.match(r'^[a-z]+://',target):continue
            target=unquote(target);links+=1
            if not (p.parent/target).exists():missing.append(dict(file=str(p.relative_to(ROOT)),target=target))
    for d in dirs:
        for p in d.rglob('*.png'):
            with Image.open(p) as im:assert im.width>0 and im.height>0;figures.append(dict(path=str(p.relative_to(ROOT)),width=im.width,height=im.height))
    source=sorted((ROOT/'src').glob('*structure2*.py'))
    for p in source:ast.parse(p.read_text())
    for p in [DOC/'START_HERE.md',DOC/'RESULTS_AND_STORY.md',ROOT/'acl_paper/v10_adapters/PAPER_ZH.md',DOC/'FINAL_VALIDATION.json']:
        if not p.exists():missing.append(dict(required=str(p.relative_to(ROOT))))
    z=dict(complete=not missing and not table_issues,table_issues=table_issues,markdown_files=len(md),local_links_checked=links,missing=missing,png_figures=figures,source_files=len(source),source_sha256={str(p.relative_to(ROOT)):sha(p) for p in source},api_cost_usd=0);write(DOC/'DOCUMENT_VALIDATION.json',z);assert not missing and not table_issues,json.dumps(dict(missing=missing,table_issues=table_issues),ensure_ascii=False);print(json.dumps(dict(complete=True,markdown_files=len(md),links=links,figures=len(figures),sources=len(source))))
if __name__=='__main__':main()
