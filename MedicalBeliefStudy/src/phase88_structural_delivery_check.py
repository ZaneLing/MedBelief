"""Final report links, completed stages, source compilation and model integrity."""
import hashlib,json,re,py_compile
from pathlib import Path
from structural_v1_analysis import ROOT,RUN,read,write

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()

def main():
    doc=ROOT/'research_v5_structural';assert read(doc/'report_complete.json')['complete'];a=read(doc/'FINAL_VALIDATION.json');assert a['complete'] and a['unique_cases_including_followup']==520 and a['stages']['head_followup']['complete']
    assert read(doc/'atlas_visual_revision_complete.json')['complete'] and read(doc/'CLI_REPLAY_VALIDATION.json')['complete']
    assert read(ROOT/'results/46_structural_head_followup/paired_interface_contrasts.json')['cases']==130
    paths=[doc,ROOT/'acl_paper/v09_structure']+[ROOT/'results'/d for d in ['42_structural_localization','43_structural_development','44_structural_holdout','45_structural_synthesis','46_structural_head_followup']]
    broken=[];links=0;mds=[]
    for directory in paths:
        for p in directory.rglob('*.md'):
            mds.append(p)
            for ref in re.findall(r'\[[^\]]*\]\(([^)\n]+)\)',p.read_text()):
                if ref.startswith(('http://','https://','#','mailto:')):continue
                target=ref.split('#',1)[0].strip('<>');links+=1
                if not (p.parent/target).exists():broken.append(dict(file=str(p.relative_to(ROOT)),target=target))
    assert not broken,broken
    scripts=[p for p in (ROOT/'src').glob('*.py') if p.name.startswith(('structural_','phase70_','phase71_','phase72_','phase73_','phase74_','phase75_','phase76_','phase77_','phase78_','phase79_','phase80_','phase81_','phase82_','phase83_','phase84_','phase86_','phase87_','phase88_','phase89_'))]
    for p in scripts:py_compile.compile(str(p),doraise=True)
    original=read(ROOT/'runs/belief_v4/manifest.json')
    for name,h in original['model_hashes'].items():assert sha(ROOT.parent/'MedicalBeliefMechanisms/.models/Qwen3-1.7B'/name)==h
    assert sha(ROOT/'data/belief_v4/cases.private.jsonl')==original['cases_sha256']
    result=dict(complete=True,markdown_documents=len(mds),local_links_checked=links,broken_links=broken,scripts_compiled=len(scripts),original_model_weights_unchanged_after_followup=True,frozen_cases_unchanged=True,unique_cases=520,cli_replay=read(doc/'CLI_REPLAY_VALIDATION.json'),plots_manually_reviewed=['measurement_map','heldout_diagnoses','efficiency_tradeoff','endpoint_vs_path','selected_heads_over_evidence','medqa_train_09289','medqa_train_09289_layers','matched_head_controls','history_and_generation'],api_cost_usd=0)
    write(doc/'DOCUMENT_VALIDATION.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
