"""Validate the actual tokenizer and answer boundary; no weights or inference."""
from pathlib import Path
import hashlib,json
from transformers import AutoTokenizer
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT.parent
MODEL=WORK/'MedicalBeliefMechanisms/.models/Qwen3-4B-8bit'
SYSTEM='You are analyzing a synthetic patient record for research. Compare the six listed diagnoses using only the cumulative findings shown. Distinguish past medical history from the current presentation. Missing information is unknown.'
STUB='Diagnosis code:'
def render_messages(row,rotation=0):
    diseases=row['candidate_diseases'];offset=(row['mapping_offset']+rotation)%6
    mapping={code:diseases[(i+offset)%6] for i,code in enumerate('ABCDEF')}
    lines=[f"Patient: age {row['age']} years; sex {row['sex']}.",'Cumulative findings:']
    for i,g in enumerate(row['revealed_groups']):
        lines.append(f'[Evidence group {i}]')
        lines.extend(x['question_en']+' Answer: '+x['answer_en']+'.' for x in g['items'])
    lines+=['Candidate diagnoses:']+[f'{code}: {d}' for code,d in mapping.items()]
    lines+=['Select the best-supported candidate for the current presentation at this point. Choose among these six even if the evidence is incomplete. After the prefix "Diagnosis code:", output exactly one space followed by one capital letter A, B, C, D, E, or F. Do not output a numerical probability.']
    return [{'role':'system','content':SYSTEM},{'role':'user','content':'\n'.join(lines)}],mapping
def main():
    tok=AutoTokenizer.from_pretrained(MODEL,local_files_only=True)
    codes={code:tok.encode(' '+code,add_special_tokens=False) for code in 'ABCDEF'}
    assert all(len(ids)==1 for ids in codes.values()) and len({ids[0] for ids in codes.values()})==6
    rows=list(map(json.loads,(ROOT/'data/pilot_prefixes.public.jsonl').read_text().splitlines()))
    checked=0;lengths=[];primary_hashes=[]
    for r in rows:
        for rotation in range(6):
            messages,mapping=render_messages(r,rotation)
            text=tok.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)+STUB
            ids=tok.encode(text,add_special_tokens=False)
            for code,tail in codes.items():assert tok.encode(text+' '+code,add_special_tokens=False)==ids+tail
            if rotation==0:
                lengths.append(len(ids));primary_hashes.append({'case_id':r['case_id'],'round':r['round'],'prompt_sha256':hashlib.sha256(text.encode()).hexdigest(),'anchor_token_index':len(ids)-1,'tokens':len(ids),'code_to_disease':mapping})
                if r is rows[0]:(ROOT/'data/example_prompt_direct.txt').write_text(text)
            checked+=1
    # Validate the post-thinking boundary with a format-only placeholder, not model reasoning.
    messages,_=render_messages(rows[0]);text=tok.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=True)+'<think>\nFORMAT CHECK ONLY\n</think>\n\n'+STUB
    ids=tok.encode(text,add_special_tokens=False)
    for code,tail in codes.items():assert tok.encode(text+' '+code,add_special_tokens=False)==ids+tail
    result={'date':'2026-11-18','no_model_inference':True,'tokenizer_path':str(MODEL.relative_to(WORK)),'template_version':'diagnostic_trajectory_v1',
        'answer_stub':STUB,'candidate_suffix_token_ids':{k:v[0] for k,v in codes.items()},'candidate_tokens_include_leading_space':True,
        'actual_public_prefixes':len(rows),'mapping_rotations_checked':6,'actual_direct_serializations_checked':checked,
        'direct_token_length_min':min(lengths),'direct_token_length_max':max(lengths),'post_thinking_boundary':'Format-only placeholder checked; every actual generated rationale must be rechecked at runtime.',
        'primary_frames':primary_hashes,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'tokenizer_files_sha256':{name:hashlib.sha256((MODEL/name).read_bytes()).hexdigest() for name in ['tokenizer.json','tokenizer_config.json']},'api_cost_usd':0}
    p=ROOT/'protocol/token_boundary_audit.json';assert not p.exists();p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['primary_frames','tokenizer_files_sha256']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
